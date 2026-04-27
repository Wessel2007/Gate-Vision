"""CLI para leitura de placa veicular a partir de uma imagem.

Uso:
    python read_plate.py <imagem> [opcoes]

Exemplos:
    python read_plate.py foto.jpg
    python read_plate.py foto.jpg --debug
    python read_plate.py foto.jpg --model ../back2/deteccao-placas-veiculares-main/models/best.pt
    python read_plate.py foto.jpg --conf 0.1 --imgsz 1280 --debug
"""

import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = str(
    BASE_DIR / ".." / "back2" / "deteccao-placas-veiculares-main" / "models" / "best.pt"
)


def _save_debug(debug_info: dict, out_dir: Path, img_stem: str):
    """Salva imagens intermediárias de debug em out_dir."""
    import cv2
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, det in enumerate(debug_info.get("detections", [])):
        cv2.imwrite(str(out_dir / f"{img_stem}_det{idx}_crop.jpg"), det["crop"])
        for vname, vdata in det.get("variants", {}).items():
            if not vdata.get("skipped"):
                cv2.imwrite(str(out_dir / f"{img_stem}_det{idx}_{vname}.jpg"),
                            vdata["img"])


def _print_debug(debug_info: dict):
    """Imprime detalhes de diagnóstico no terminal."""
    if debug_info is None:
        return

    sep = "─" * 60
    print(f"\n{sep}")

    timings = debug_info.get("timings", {})
    if timings:
        print("  [TEMPOS]")
        for key, val in timings.items():
            if key == "ocr_ms":
                print(f"    ocr_ms (por crop): {val}")
            else:
                print(f"    {key}: {val} ms")

    yolo_passes = debug_info.get("yolo_passes", 1)
    detections = debug_info.get("detections", [])
    print(f"\n  [DEBUG] Passagens YOLO: {yolo_passes} | "
          f"Deteccoes processadas: {len(detections)}")

    for idx, det in enumerate(detections):
        x1, y1, x2, y2 = det["box"]
        early = det.get("early_stop", False)
        print(f"\n  --- Deteccao #{idx} ---")
        print(f"    Caixa      : ({x1},{y1}) -> ({x2},{y2})")
        print(f"    Conf YOLO  : {det['yolo_conf']:.2%}")
        print(f"    OCR rapido : {'sim (parada antecipada)' if early else 'nao (todas variantes)'}")
        for vname, vdata in det.get("variants", {}).items():
            skipped = vdata.get("skipped", False)
            hits_info = "(ignorada)" if skipped else str(vdata["hits"])
            print(f"    OCR [{vname}]: {hits_info}")
        print(f"    Todos hits : {det['all_hits']}")
        cands = det.get("candidates", [])
        print(f"    Candidatos : {cands[:8]}")
    print(sep)


def main():
    parser = argparse.ArgumentParser(
        description="Detecta e le a placa de um veiculo em uma imagem."
    )
    parser.add_argument("imagem", help="Caminho para a imagem do veiculo")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_PLATES", DEFAULT_MODEL),
        help="Caminho para o peso YOLO do detector de placas (.pt)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Limiar de confianca para deteccao YOLO (padrao: 0.25)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Tamanho de entrada para o YOLO (padrao: 640)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug: mostra detalhes e salva imagens intermediarias em debug/",
    )
    args = parser.parse_args()

    image_path = Path(args.imagem)
    if not image_path.exists():
        print(f"Erro: arquivo nao encontrado: {image_path}", file=sys.stderr)
        sys.exit(1)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Erro: modelo nao encontrado: {model_path}", file=sys.stderr)
        print(
            "Informe o caminho correto com --model ou via variavel MODEL_PLATES.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Carregando modelos (pode demorar na primeira execucao)...")
    from pipeline import load_models, detect

    load_models(str(model_path), conf=args.conf, imgsz=args.imgsz)

    print(f"Processando imagem : {image_path}")
    if args.debug:
        print(f"Conf YOLO          : {args.conf}")
        print(f"imgsz              : {args.imgsz}")

    image_bytes = image_path.read_bytes()
    result = detect(image_bytes, debug=args.debug)

    placa = result.get("placa")
    confianca = result.get("confianca", 0)
    debug_info = result.get("debug")

    if args.debug:
        _print_debug(debug_info)
        debug_dir = BASE_DIR / "debug"
        _save_debug(debug_info, debug_dir, image_path.stem)
        print(f"\n  Imagens de debug salvas em: {debug_dir}")

    print()
    if placa:
        print(f"Placa detectada : {placa}")
        print(f"Confianca YOLO  : {confianca:.2%}")
    else:
        print("Nenhuma placa detectada na imagem.")
        if not args.debug:
            print("Dica: rode com --debug para ver detalhes do pipeline.")


if __name__ == "__main__":
    main()
