"""
pipeline.py — detecção de placa (YOLO) + OCR (EasyOCR) com suporte a debug.

Fluxo padrão (modo rápido):
  1. CLAHE na imagem inteira.
  2. YOLO sem TTA (augment=False) — inferência mais rápida.
  3. OCR na variante "color" do melhor crop apenas.
  4. Se não encontrar placa válida → OCR nas variantes "clahe" e "binary".
  5. Se ainda não encontrar → nova inferência YOLO com TTA + confiança reduzida.
  6. Repete OCR completo no novo crop.

Parâmetros controláveis por env var / load_models():
  DETECT_CONF   — limiar de confiança YOLO (padrão: 0.25)
  DETECT_IMGSZ  — tamanho de entrada YOLO (padrão: 640)
"""

import re
import time
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

_model_plates = None
_ocr_reader = None
_detect_conf = 0.25   # padrão mais alto → menos detecções falsas na passagem rápida
_detect_imgsz = 640   # padrão 640 → inferência ~2× mais rápida que 1280

_OCR_IGNORE = {"BRASIL", "BR", "MERCOSUL", "BRAZIL"}

# Score mínimo para aceitar resultado e encerrar cedo o OCR
_EARLY_STOP_SCORE = 180


# ── Inicialização ──────────────────────────────────────────────

def load_models(plates_path: str, chars_path: str = None,
                conf: float = 0.25, imgsz: int = 640):
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
    """Equalização adaptativa de contraste (CLAHE) no canal L do espaço LAB."""
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

    for text, conf in ocr_hits:
        if 4 <= len(text) <= 10:
            corrected = _correct_mercosul(text)
            sc = _score(corrected) + int(conf * 60)
            if corrected not in candidates or sc > candidates[corrected]:
                candidates[corrected] = sc

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


# ── OCR com parada antecipada (variante a variante) ────────────

def _ocr_crop_fast(crop: np.ndarray, debug_variants: dict | None = None
                   ) -> tuple[list[tuple[str, float]], bool]:
    """Roda OCR variante a variante; para assim que encontrar placa válida.

    Retorna (all_hits, found_early) onde found_early=True significa que a
    parada antecipada foi acionada antes de processar todas as variantes.
    """
    variants = _make_variants(crop)
    # Ordem de preferência: color primeiro (melhor relação qualidade/tempo)
    order = ["color", "clahe", "binary"]

    all_hits: list[tuple[str, float]] = []
    found_early = False

    for vname in order:
        variant = variants[vname]
        hits = _run_ocr(variant)
        all_hits.extend(hits)

        if debug_variants is not None:
            debug_variants[vname] = {"img": variant, "hits": hits}

        candidates = _extract_candidates(all_hits)
        if candidates and candidates[0][1] >= _EARLY_STOP_SCORE:
            found_early = True
            # preencher variantes restantes no debug como não processadas
            if debug_variants is not None:
                for remaining in order:
                    if remaining not in debug_variants:
                        debug_variants[remaining] = {"img": variants[remaining],
                                                     "hits": [], "skipped": True}
            break

    return all_hits, found_early


# ── Inferência YOLO ────────────────────────────────────────────

def _run_yolo_fast(img: np.ndarray) -> list[tuple]:
    """Inferência rápida: sem TTA, confiança padrão."""
    results = _model_plates(img, conf=_detect_conf, imgsz=_detect_imgsz,
                             augment=False, verbose=False)
    return [(r, box) for r in results for box in r.boxes]


def _run_yolo_robust(img: np.ndarray) -> list[tuple]:
    """Inferência robusta: com TTA e confiança reduzida — usada como fallback."""
    results = _model_plates(img, conf=_detect_conf, imgsz=_detect_imgsz,
                             augment=True, verbose=False)
    detections = [(r, box) for r in results for box in r.boxes]

    if not detections:
        fallback_conf = max(0.04, _detect_conf / 3)
        results = _model_plates(img, conf=fallback_conf, imgsz=_detect_imgsz,
                                 augment=True, verbose=False)
        detections = [(r, box) for r in results for box in r.boxes]

    return detections


# ── Processar um conjunto de detecções YOLO → melhor placa ─────

def _process_detections(detections: list[tuple], img: np.ndarray,
                         debug_info: dict | None, timings: dict | None
                         ) -> tuple[str | None, float]:
    """Itera pelas detecções YOLO, roda OCR e devolve (melhor_placa, conf_yolo)."""
    best_plate = None
    best_conf = 0.0

    # Ordenar por confiança YOLO descendente: processar o mais provável primeiro
    sorted_dets = sorted(detections, key=lambda x: float(x[1].conf[0]), reverse=True)

    for r, box in sorted_dets:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        plate_conf = float(box.conf[0])
        crop = _safe_crop(img, x1, y1, x2, y2)

        variant_debug: dict | None = {} if debug_info is not None else None
        t_ocr = time.perf_counter()
        all_hits, early = _ocr_crop_fast(crop, variant_debug)
        if timings is not None:
            timings.setdefault("ocr_ms", []).append(
                round((time.perf_counter() - t_ocr) * 1000, 1))

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
                "early_stop": early,
            })

        if top_text and top_score > _score(best_plate or ""):
            best_plate = top_text
            best_conf = plate_conf

        # Se já encontramos placa válida com score alto, não processar mais caixas
        if best_plate and _score(best_plate) >= _EARLY_STOP_SCORE:
            break

    return best_plate, best_conf


# ── Detecção principal ─────────────────────────────────────────

def detect(image_bytes: bytes, debug: bool = False) -> dict:
    """Pipeline completo: pré-processamento → YOLO (rápido) → OCR Mercosul.

    Modo rápido por padrão:
      - YOLO sem TTA.
      - OCR com parada antecipada por placa válida.
      - Fallback automático para YOLO com TTA se nada encontrado.

    Retorna {"placa": str|None, "confianca": float, "debug": dict|None}.
    """
    if _model_plates is None or _ocr_reader is None:
        raise RuntimeError("Modelos nao carregados. Chame load_models() primeiro.")

    t_total = time.perf_counter()
    timings: dict = {}

    # Decodificação
    t0 = time.perf_counter()
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    timings["decode_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    if img is None:
        return {"placa": None, "confianca": 0, "debug": None}

    # CLAHE
    t0 = time.perf_counter()
    enhanced = _enhance_full_image(img)
    timings["clahe_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    debug_info = {"detections": [], "yolo_passes": 1, "timings": timings} if debug else None

    # ── Passagem rápida: YOLO sem TTA ─────────────────────────
    t0 = time.perf_counter()
    detections = _run_yolo_fast(enhanced)
    timings["yolo_fast_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    best_plate = None
    best_conf = 0.0

    if detections:
        best_plate, best_conf = _process_detections(detections, img, debug_info, timings)

    # ── Fallback: YOLO com TTA quando placa não encontrada ────
    if not best_plate:
        if debug_info is not None:
            debug_info["yolo_passes"] = 2

        t0 = time.perf_counter()
        detections_robust = _run_yolo_robust(enhanced)
        timings["yolo_robust_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        if detections_robust:
            best_plate, best_conf = _process_detections(
                detections_robust, img, debug_info, timings)

    timings["total_ms"] = round((time.perf_counter() - t_total) * 1000, 1)

    return {
        "placa": best_plate,
        "confianca": round(best_conf, 4),
        "debug": debug_info,
    }
