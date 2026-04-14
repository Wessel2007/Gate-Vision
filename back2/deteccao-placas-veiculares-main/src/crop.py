from ultralytics import YOLO
import cv2

model = YOLO("best.pt")

img_path = "teste.jpg"
img = cv2.imread(img_path)

results = model(img_path)

for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = img[y1:y2, x1:x2]
        cv2.imwrite("placa_recortada.jpg", crop)