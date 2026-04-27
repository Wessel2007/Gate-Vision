"""
pipeline.py — detecção de placa (YOLO) + OCR (EasyOCR) com suporte a debug.

Fluxo:
  1. YOLO detecta regiões de placa na imagem.
  2. Cada região é recortada com uma pequena margem.
  3. Três variantes de pré-processamento são geradas e enviadas ao EasyOCR.
  4. Os textos retornados são filtrados, combinados em janelas de 7 caracteres
     e pontuados pelo padrão Mercosul.
  5. O melhor candidato é retornado junto com dados de debug opcionais.
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

# Textos que aparecem na placa mas não são os dígitos — ignorar
_OCR_IGNORE = {"BRASIL", "BR", "MERCOSUL", "BRAZIL"}


# ── Inicialização ──────────────────────────────────────────────

def load_models(plates_path: str, chars_path: str = None,
                conf: float = 0.15, imgsz: int = 1280):
    """Carrega modelo YOLO de placas e leitor EasyOCR.

    chars_path é aceito por compatibilidade mas ignorado.
    conf: limiar de confiança para detecção YOLO (padrão 0.15).
    imgsz: tamanho de entrada para o YOLO (padrão 1280).
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


# ── Crop com margem ────────────────────────────────────────────

def _safe_crop(img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
               margin: float = 0.08) -> np.ndarray:
    """Recorta a bounding box adicionando margem relativa para não cortar bordas."""
    h, w = img.shape[:2]
    mw = int((x2 - x1) * margin)
    mh = int((y2 - y1) * margin)
    x1 = max(0, x1 - mw)
    y1 = max(0, y1 - mh)
    x2 = min(w, x2 + mw)
    y2 = min(h, y2 + mh)
    return img[y1:y2, x1:x2]


# ── Variantes de pré-processamento ─────────────────────────────

def _make_variants(crop: np.ndarray) -> dict[str, np.ndarray]:
    """Retorna três variantes do crop para testar no OCR."""
    # 1. Colorido ampliado (mais fiel ao original)
    color_up = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # 2. Cinza + CLAHE (equalização adaptativa — melhora contraste uniforme)
    gray = cv2.cvtColor(color_up, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)

    # 3. Threshold binário com desfoque leve para limpar ruído
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return {"color": color_up, "clahe": clahe_img, "binary": binary}


# ── OCR com detalhe ────────────────────────────────────────────

def _run_ocr(img_variant: np.ndarray) -> list[tuple[str, float]]:
    """Executa EasyOCR com detail=1 e retorna lista de (texto_limpo, confianca)."""
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
    """Aplica correções de confusão letra/dígito por posição (padrão Mercosul)."""
    chars = list(text)
    for i in range(min(7, len(chars))):
        if i < 3 or i == 4:          # posições de letras
            if chars[i] in _DIGIT_TO_LETTER:
                chars[i] = _DIGIT_TO_LETTER[chars[i]]
        else:                         # posições de dígitos
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
    """
    Extrai e pontua candidatos a placa a partir dos hits do OCR.

    Estratégia de prioridade:
      1. Hits individuais recebem bônus de confiança alto (×60) — um único bloco
         detectado como a placa é o candidato mais confiável.
      2. Janelas deslizantes de 7 chars sobre todos os hits concatenados recebem
         bônus de confiança ponderado menor (×30) — servem de fallback quando o
         OCR fragmenta a leitura.

    Isso resolve o empate em score base (220) quando vários padrões Mercosul
    são encontrados: o hit direto com alta confiança vence.
    """
    if not ocr_hits:
        return []

    candidates: dict[str, int] = {}

    # ── 1. Hits individuais (prioridade máxima) ────────────────────────────
    for text, conf in ocr_hits:
        if 4 <= len(text) <= 10:
            corrected = _correct_mercosul(text)
            # bônus alto: int(conf * 60) → até +60 pontos
            sc = _score(corrected) + int(conf * 60)
            if corrected not in candidates or sc > candidates[corrected]:
                candidates[corrected] = sc

    # ── 2. Janelas deslizantes sobre texto concatenado (fallback) ──────────
    # Monta mapa char→confiança para ponderar cada janela
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
        # bônus menor: int(avg_conf * 30) → até +30 pontos
        sc = _score(corrected) + int(avg_conf * 30)
        if corrected not in candidates or sc > candidates[corrected]:
            candidates[corrected] = sc

    return sorted(candidates.items(), key=lambda x: x[1], reverse=True)


# ── Detecção principal ─────────────────────────────────────────

def detect(image_bytes: bytes, debug: bool = False) -> dict:
    """Pipeline completo: YOLO + OCR Mercosul.

    Retorna:
        {
            "placa":    str | None,
            "confianca": float,          # confiança YOLO
            "debug":    dict | None      # presente apenas quando debug=True
        }
    """
    if _model_plates is None or _ocr_reader is None:
        raise RuntimeError("Modelos nao carregados. Chame load_models() primeiro.")

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"placa": None, "confianca": 0, "debug": None}

    results = _model_plates(img, conf=_detect_conf, imgsz=_detect_imgsz, verbose=False)

    debug_info = {"detections": [], "fallback_used": False} if debug else None

    best_plate = None
    best_conf = 0.0
    best_candidates = []

    detections = [(r, box) for r in results for box in r.boxes]

    if not detections:
        # ── Fallback: tenta OCR na região central-inferior da imagem ──────────
        h, w = img.shape[:2]
        region = img[int(h * 0.55):int(h * 0.90), int(w * 0.15):int(w * 0.85)]
        if debug_info is not None:
            debug_info["fallback_used"] = True
            debug_info["fallback_region"] = region.copy()

        all_hits: list[tuple[str, float]] = []
        variants = _make_variants(region)
        for vname, variant in variants.items():
            hits = _run_ocr(variant)
            if debug_info is not None:
                debug_info.setdefault("fallback_variants", {})[vname] = variant
                debug_info.setdefault("fallback_hits", {})[vname] = hits
            all_hits.extend(hits)

        candidates = _extract_candidates(all_hits)
        if candidates:
            best_plate, _ = candidates[0]
            best_conf = 0.0
            best_candidates = candidates

        if debug_info is not None:
            debug_info["fallback_candidates"] = candidates

        return {
            "placa": best_plate,
            "confianca": round(best_conf, 4),
            "debug": debug_info,
        }

    # ── Processamento normal com caixas YOLO ──────────────────────────────────
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
        top_text = candidates[0][0] if candidates else None
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
            best_candidates = candidates

    return {
        "placa": best_plate,
        "confianca": round(best_conf, 4),
        "debug": debug_info,
    }
