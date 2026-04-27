"""
pipeline.py — detecção de placa (YOLO) + OCR (EasyOCR) com suporte a debug.

Melhorias para uso em produção (portaria / câmera):
  - CLAHE aplicado na imagem inteira antes do YOLO para lidar com variações
    de iluminação (noite, chuva, contraluz, garagem).
  - augment=True ativa Test-Time Augmentation no YOLO (multi-escala/flip),
    aumentando a confiança em posições e distâncias variadas.
  - Segunda passagem com confiança reduzida quando a primeira não detecta nada.
  - Fallback de região central fixo REMOVIDO: posição da placa é imprevisível
    em câmera real (motos, caminhões, diferentes alturas de veículo).
"""

import re
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

_model_plates = None
_ocr_reader = None
_detect_conf = 0.15
_detect_imgsz = 1280

_OCR_IGNORE = {"BRASIL", "BR", "MERCOSUL", "BRAZIL"}


# ── Inicialização ──────────────────────────────────────────────

def load_models(plates_path: str, chars_path: str = None,
                conf: float = 0.15, imgsz: int = 1280):
    """Carrega modelo YOLO de placas e leitor EasyOCR.

    chars_path é aceito por compatibilidade mas ignorado.
    """
    global _model_plates, _ocr_reader, _detect_conf, _detect_imgsz
    import easyocr

    model_file = Path(plates_path)
    if not model_file.exists():
        raise FileNotFoundError(
            f"Modelo YOLO nao encontrado: {plates_path}\n"
            "Defina MODEL_PLATES ou passe --model com o caminho correto do .pt"
        )

    _model_plates = YOLO(str(model_file))
    _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    _detect_conf = conf
    _detect_imgsz = imgsz


# ── Pré-processamento da imagem inteira (antes do YOLO) ────────

def _enhance_full_image(img: np.ndarray) -> np.ndarray:
    """Equalização adaptativa de contraste (CLAHE) no canal L do espaço LAB.

    Melhora detecção em cenas com iluminação irregular:
    garagens escuras, contraluz, noite, chuva, faróis.
    Não altera matiz nem saturação — apenas contraste local.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


# ── Crop com margem ────────────────────────────────────────────

def _safe_crop(img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
               margin: float = 0.08) -> np.ndarray:
    h, w = img.shape[:2]
    mw = int((x2 - x1) * margin)
    mh = int((y2 - y1) * margin)
    x1 = max(0, x1 - mw)
    y1 = max(0, y1 - mh)
    x2 = min(w, x2 + mw)
    y2 = min(h, y2 + mh)
    return img[y1:y2, x1:x2]


# ── Variantes de pré-processamento do crop ─────────────────────

def _make_variants(crop: np.ndarray) -> dict[str, np.ndarray]:
    color_up = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(color_up, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return {"color": color_up, "clahe": clahe_img, "binary": binary}


# ── OCR com detalhe ────────────────────────────────────────────

def _run_ocr(img_variant: np.ndarray) -> list[tuple[str, float]]:
    results = _ocr_reader.readtext(img_variant, detail=1, paragraph=False,
                                   allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    out = []
    for (_, text, conf) in results:
        clean = re.sub(r"[^A-Z0-9]", "", text.upper())
        if clean and clean not in _OCR_IGNORE:
            out.append((clean, float(conf)))
    return out


# ── Extração e pontuação de candidatos Mercosul ───────────────

_DIGIT_TO_LETTER = {"0": "O", "1": "I", "4": "A", "8": "B", "7": "T"}
_LETTER_TO_DIGIT = {"O": "0", "I": "1", "A": "4", "B": "8", "T": "7", "L": "1"}

_MERCOSUL_RE = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")
_OLD_RE      = re.compile(r"^[A-Z]{3}[0-9]{4}$")


def _correct_mercosul(text: str) -> str:
    chars = list(text)
    for i in range(min(7, len(chars))):
        if i < 3 or i == 4:
            if chars[i] in _DIGIT_TO_LETTER:
                chars[i] = _DIGIT_TO_LETTER[chars[i]]
        else:
            if chars[i] in _LETTER_TO_DIGIT:
                chars[i] = _LETTER_TO_DIGIT[chars[i]]
    return "".join(chars[:7])


def _score(text: str) -> int:
    s = 0
    if len(text) == 7:
        s += 20
    if _MERCOSUL_RE.match(text):
        s += 200
    elif _OLD_RE.match(text):
        s += 100
    if len(text) >= 3 and len(set(text[:3])) == 1:
        s -= 30
    return s


def _extract_candidates(ocr_hits: list[tuple[str, float]]) -> list[tuple[str, int]]:
    if not ocr_hits:
        return []

    candidates: dict[str, int] = {}

    # Hits individuais recebem bônus alto (×60): hit direto é o melhor candidato
    for text, conf in ocr_hits:
        if 4 <= len(text) <= 10:
            corrected = _correct_mercosul(text)
            sc = _score(corrected) + int(conf * 60)
            if corrected not in candidates or sc > candidates[corrected]:
                candidates[corrected] = sc

    # Janelas deslizantes de 7 chars como fallback (bônus menor ×30)
    conf_map: list[tuple[str, float]] = []
    for text, conf in ocr_hits:
        for ch in text:
            conf_map.append((ch, conf))

    full = "".join(ch for ch, _ in conf_map)
    for start in range(max(0, len(full) - 6)):
        window = full[start:start + 7]
        if len(window) < 7:
            break
        avg_conf = sum(c for _, c in conf_map[start:start + 7]) / 7
        corrected = _correct_mercosul(window)
        sc = _score(corrected) + int(avg_conf * 30)
        if corrected not in candidates or sc > candidates[corrected]:
            candidates[corrected] = sc

    return sorted(candidates.items(), key=lambda x: x[1], reverse=True)


# ── Detecção YOLO (com TTA e dois passes) ─────────────────────

def _run_yolo(img: np.ndarray) -> list[tuple]:
    """Roda YOLO com augment=True (TTA). Se não encontrar nada, repete com
    confiança reduzida para cobrir casos difíceis (distância, ângulo, luz baixa).
    Retorna lista de (box_r, box) prontos para processar.
    """
    results = _model_plates(img, conf=_detect_conf, imgsz=_detect_imgsz,
                             augment=True, verbose=False)
    detections = [(r, box) for r in results for box in r.boxes]

    if not detections:
        # Segunda passagem com confiança reduzida
        fallback_conf = max(0.04, _detect_conf / 3)
        results = _model_plates(img, conf=fallback_conf, imgsz=_detect_imgsz,
                                 augment=True, verbose=False)
        detections = [(r, box) for r in results for box in r.boxes]

    return detections


# ── Detecção principal ─────────────────────────────────────────

def detect(image_bytes: bytes, debug: bool = False) -> dict:
    """Pipeline completo: pré-processamento → YOLO (TTA) → OCR Mercosul.

    Retorna {"placa": str|None, "confianca": float, "debug": dict|None}.
    """
    if _model_plates is None or _ocr_reader is None:
        raise RuntimeError("Modelos nao carregados. Chame load_models() primeiro.")

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"placa": None, "confianca": 0, "debug": None}

    # Equalização de contraste na imagem inteira antes do YOLO
    enhanced = _enhance_full_image(img)

    debug_info = {"detections": [], "yolo_passes": 1} if debug else None

    detections = _run_yolo(enhanced)

    if not detections:
        if debug_info is not None:
            debug_info["yolo_passes"] = 2
            debug_info["fallback_used"] = False
            debug_info["no_detection"] = True
        return {"placa": None, "confianca": 0, "debug": debug_info}

    best_plate = None
    best_conf = 0.0

    for r, box in detections:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        plate_conf = float(box.conf[0])
        crop = _safe_crop(img, x1, y1, x2, y2)

        all_hits: list[tuple[str, float]] = []
        variant_debug = {}

        variants = _make_variants(crop)
        for vname, variant in variants.items():
            hits = _run_ocr(variant)
            all_hits.extend(hits)
            if debug_info is not None:
                variant_debug[vname] = {"img": variant, "hits": hits}

        candidates = _extract_candidates(all_hits)
        top_text  = candidates[0][0] if candidates else None
        top_score = candidates[0][1] if candidates else -999

        if debug_info is not None:
            debug_info["detections"].append({
                "box": (x1, y1, x2, y2),
                "yolo_conf": plate_conf,
                "crop": crop.copy(),
                "variants": variant_debug,
                "all_hits": all_hits,
                "candidates": candidates,
            })

        if top_text and top_score > _score(best_plate or ""):
            best_plate = top_text
            best_conf = plate_conf

    return {
        "placa": best_plate,
        "confianca": round(best_conf, 4),
        "debug": debug_info,
    }
