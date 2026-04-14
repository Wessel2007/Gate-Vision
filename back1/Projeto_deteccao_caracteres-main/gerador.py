import cv2
import numpy as np
import random
import os
import string

# =========================
# CONFIG
# =========================
OUTPUT = "dataset_chars"
IMG_SIZE = (320, 80)

os.makedirs(f"{OUTPUT}/images/train", exist_ok=True)
os.makedirs(f"{OUTPUT}/labels/train", exist_ok=True)

classes = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

# =========================
# GERAR PLACA MERCOSUL
# =========================
def gerar_placa():
    letras = string.ascii_uppercase

    placa = (
        random.choice(letras) +
        random.choice(letras) +
        random.choice(letras) +
        str(random.randint(0,9)) +
        random.choice(letras) +
        str(random.randint(0,9)) +
        str(random.randint(0,9))
    )

    return placa

# =========================
# DESENHAR PLACA
# =========================
def desenhar_placa(texto):
    img = np.ones((IMG_SIZE[1], IMG_SIZE[0], 3), dtype=np.uint8) * 255

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.8
    thickness = 3

    x_offset = 15
    y = 55

    boxes = []

    for i, char in enumerate(texto):
        (w, h), _ = cv2.getTextSize(char, font, scale, thickness)

        x = x_offset + i * 40

        cv2.putText(img, char, (x, y), font, scale, (0,0,0), thickness)

        # bounding box
        x1 = x
        y1 = y - h
        x2 = x + w
        y2 = y

        boxes.append((char, x1, y1, x2, y2))

    return img, boxes

# =========================
# SALVAR YOLO
# =========================
def salvar_yolo(nome, img, boxes):
    h, w = img.shape[:2]

    label_path = f"{OUTPUT}/labels/train/{nome}.txt"
    img_path = f"{OUTPUT}/images/train/{nome}.jpg"

    with open(label_path, "w") as f:
        for char, x1, y1, x2, y2 in boxes:
            cls = classes.index(char)

            xc = (x1 + x2) / 2 / w
            yc = (y1 + y2) / 2 / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h

            f.write(f"{cls} {xc} {yc} {bw} {bh}\n")

    cv2.imwrite(img_path, img)

# =========================
# AUGMENTATION
# =========================
def augmentar(img):
    # brilho
    alpha = random.uniform(0.7, 1.3)
    beta = random.randint(-30, 30)

    img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    # blur
    if random.random() < 0.3:
        img = cv2.GaussianBlur(img, (3,3), 0)

    # ruído
    if random.random() < 0.3:
        noise = np.random.randint(0, 30, img.shape, dtype='uint8')
        img = cv2.add(img, noise)

    return img

# =========================
# GERAR DATASET
# =========================
def gerar_dataset(qtd=2000):
    for i in range(qtd):
        texto = gerar_placa()

        img, boxes = desenhar_placa(texto)

        img = augmentar(img)

        salvar_yolo(f"img_{i}", img, boxes)

        if i % 100 == 0:
            print(f"{i} imagens geradas...")

# =========================
# RUN
# =========================
gerar_dataset(3000)