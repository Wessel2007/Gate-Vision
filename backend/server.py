import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from pipeline import load_models, detect

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

MODEL_PLATES = os.getenv("MODEL_PLATES", str(BASE_DIR / ".." / "back2" / "deteccao-placas-veiculares-main" / "models" / "best.pt"))
MODEL_CHARS = os.getenv("MODEL_CHARS", str(BASE_DIR / ".." / "back1" / "Projeto_deteccao_caracteres-main" / "train" / "weights" / "best.pt"))
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title="GateVision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    print(f"Loading plate model   : {MODEL_PLATES}")
    print(f"Loading char model    : {MODEL_CHARS}")
    load_models(MODEL_PLATES, MODEL_CHARS)
    print("Models loaded successfully.")


@app.get("/")
def health():
    return {"status": "ok", "service": "GateVision API"}


@app.post("/api/detect")
async def detect_plate(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = detect(image_bytes)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
