from ultralytics import YOLO

model = YOLO("models/best.pt")

results = model("samples/teste.jpg", save=True, conf=0.25)