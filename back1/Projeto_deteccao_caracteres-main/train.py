from ultralytics import YOLO
if __name__ == '__main__':
    model = YOLO("yolo11n.pt")

    model.train(
        data="C:/Users/rafit/Desktop/projeto_i/projetin/data.yaml",
        epochs=200,
        imgsz=640,
        batch=16,
        device=0,
        project="C:/Users/rafit/Desktop/projeto_i/projetin"

)
