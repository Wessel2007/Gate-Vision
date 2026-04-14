import re
import cv2
import numpy as np
from ultralytics import YOLO

CLASSES = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

_model_plates = None
_model_chars = None


def load_models(plates_path: str, chars_path: str):
    global _model_plates, _model_chars
    _model_plates = YOLO(plates_path)
    _model_chars = YOLO(chars_path)


# ── Box de-duplication ────────────────────────────────────────

def _filter_boxes(detections: list) -> list:
    detections = sorted(detections, key=lambda x: x[0])
    filtered = []

    for d in detections:
        if not filtered:
            filtered.append(d)
            continue
        last = filtered[-1]
        if abs(d[0] - last[0]) < 20:
            if d[5] > last[5]:
                filtered[-1] = d
        else:
            filtered.append(d)

    return filtered


# ── Assemble raw text from detections ─────────────────────────

def _assemble_text(detections: list) -> str:
    detections = sorted(detections, key=lambda x: x[0])
    return "".join(CLASSES[d[4]] for d in detections)


# ── Mercosul pattern correction ───────────────────────────────

_DIGIT_TO_LETTER = {"0": "O", "1": "I", "4": "A", "8": "B", "7": "T"}
_LETTER_TO_DIGIT = {"O": "0", "I": "1", "A": "4", "B": "8", "T": "7", "L": "1"}


def _correct_mercosul(text: str) -> str:
    chars = list(text)
    for i in range(len(chars)):
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
    if re.match(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$", text):
        s += 200
    if len(text) >= 3 and len(set(text[:3])) == 1:
        s -= 30
    return s


def _pick_best(candidates: list[str]) -> str | None:
    best, best_score = None, -999
    for c in candidates:
        corrected = _correct_mercosul(c)
        sc = _score(corrected)
        if sc > best_score:
            best_score = sc
            best = corrected
    return best


# ── Public API ────────────────────────────────────────────────

def detect(image_bytes: bytes) -> dict:
    """Run the full plate-detection + character-recognition pipeline.

    Returns {"placa": "ABC1D23", "confianca": 0.92} or
            {"placa": None, "confianca": 0} when nothing is found.
    """
    if _model_plates is None or _model_chars is None:
        raise RuntimeError("Models not loaded. Call load_models() first.")

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"placa": None, "confianca": 0}

    results = _model_plates(img, conf=0.3)

    best_plate = None
    best_conf = 0.0

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_conf = float(box.conf[0])
            crop = img[y1:y2, x1:x2]

            crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

            char_results = _model_chars(crop, conf=0.01)

            detections = []
            for rc in char_results:
                for b in rc.boxes:
                    bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                    cls = int(b.cls[0])
                    conf = float(b.conf[0])
                    detections.append((bx1, by1, bx2, by2, cls, conf))

            detections = _filter_boxes(detections)

            if len(detections) < 4:
                continue

            raw_text = _assemble_text(detections)
            candidate = _pick_best([raw_text])

            if candidate and _score(candidate) > _score(best_plate or ""):
                best_plate = candidate
                best_conf = plate_conf

    return {"placa": best_plate, "confianca": round(best_conf, 4)}
