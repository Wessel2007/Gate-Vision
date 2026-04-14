from ultralytics import YOLO
import cv2
import re

# =========================
# MODELOS
# =========================
modelo_placa = YOLO("C:/Users/rafit/Desktop/deteccao-placas-veiculares-main/models/best.pt")
modelo_chars = YOLO("C:/Users/rafit/Desktop/projeto_i/projetin/train/weights/best.pt")

classes = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

# =========================
# REMOVE DUPLICADOS
# =========================
def filtrar_boxes(detections):
    detections = sorted(detections, key=lambda x: x[0])
    filtrados = []

    for d in detections:
        if not filtrados:
            filtrados.append(d)
            continue

        ultimo = filtrados[-1]

        if abs(d[0] - ultimo[0]) < 20:
            if d[5] > ultimo[5]:
                filtrados[-1] = d
        else:
            filtrados.append(d)

    return filtrados

# =========================
# MONTA TEXTO
# =========================
def montar_texto(detections):
    detections = sorted(detections, key=lambda x: x[0])
    return "".join([classes[d[4]] for d in detections])

# =========================
# CORREÇÃO FORTE (🔥 NOVO)
# =========================
def corrigir_forte(texto):
    texto = list(texto)

    mapa_letras = {
        '0': 'O', '1': 'I', '4': 'A', '8': 'B', '7': 'T'
    }

    mapa_numeros = {
        'O': '0', 'I': '1', 'A': '4', 'B': '8', 'T': '7', 'L': '1'
    }

    for i in range(len(texto)):
        if i < 3:  # letras
            if texto[i] in mapa_letras:
                texto[i] = mapa_letras[texto[i]]

        elif i == 4:  # letra (padrão Mercosul)
            if texto[i] in mapa_letras:
                texto[i] = mapa_letras[texto[i]]

        else:  # números
            if texto[i] in mapa_numeros:
                texto[i] = mapa_numeros[texto[i]]

    return "".join(texto[:7])

# =========================
# SCORE INTELIGENTE
# =========================
def score_placa(texto):
    score = 0

    if len(texto) == 7:
        score += 20

    if re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', texto):
        score += 200

    # penaliza repetição estranha
    if len(set(texto[:3])) == 1:
        score -= 30

    return score

# =========================
# ESCOLHER MELHOR
# =========================
def escolher_melhor(candidatos):
    melhor = None
    melhor_score = -999

    for c in candidatos:
        c_corr = corrigir_forte(c)
        s = score_placa(c_corr)

        print(f"{c} → {c_corr} | score={s}")

        if s > melhor_score:
            melhor_score = s
            melhor = c_corr

    return melhor

# =========================
# IMAGEM
# =========================
img = cv2.imread("C:/Users/rafit/Pictures/placa/dadaw.jpeg")

results = modelo_placa(img, conf=0.3)

placas = []

# =========================
# PIPELINE
# =========================
for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        placa = img[y1:y2, x1:x2]

        # 🔥 escala forte
        placa = cv2.resize(placa, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

        results_chars = modelo_chars(placa, conf=0.01)

        detections = []

        for rc in results_chars:
            for b in rc.boxes:
                bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                cls = int(b.cls[0])
                conf = float(b.conf[0])

                detections.append((bx1, by1, bx2, by2, cls, conf))

        print("Bruto:", len(detections))

        # 🔥 remove duplicados
        detections = filtrar_boxes(detections)

        print("Filtrado:", len(detections))

        candidatos = []

        if len(detections) >= 4:
            texto = montar_texto(detections)
            print("YOLO bruto:", texto)
            candidatos.append(texto)

        # 🔥 escolha inteligente
        melhor = escolher_melhor(candidatos)

        print("🏆 FINAL:", melhor)

        if melhor:
            placas.append(melhor)

# =========================
# RESULTADO FINAL
# =========================
print("\n🚗 RESULTADO FINAL:")
for p in placas:
    print("👉", p)