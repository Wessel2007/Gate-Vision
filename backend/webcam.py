"""
webcam.py — Leitura contínua de placas via câmera (webcam ou IP).

Projetado para uso em portarias, cancelas e entradas de edifícios.

Uso:
    python webcam.py --model <modelo.pt>
    python webcam.py --model <modelo.pt> --camera 0
    python webcam.py --model <modelo.pt> --camera rtsp://192.168.1.10/stream
    python webcam.py --model <modelo.pt> --show --conf 0.15 --imgsz 1280

Parâmetros importantes:
    --camera        Índice da webcam (0, 1...) ou URL RTSP de câmera IP
    --model         Caminho para o .pt do YOLO detector de placas
    --conf          Limiar de confiança do YOLO (padrão: 0.15)
    --imgsz         Tamanho de entrada do YOLO (padrão: 1280)
    --sample-every  Processar 1 a cada N frames (padrão: 5)
    --confirm       Número de frames consecutivos com a mesma placa
                    para confirmar uma leitura (padrão: 3)
    --cooldown      Segundos mínimos entre duas confirmações da mesma placa
                    (evita acionar duas vezes seguidas) (padrão: 10)
    --show          Exibe janela com o frame atual e a última placa lida

Pressione Q (na janela) ou Ctrl+C para encerrar.
"""

import argparse
import os
import sys
import time
import signal
from collections import deque
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = str(
    BASE_DIR / ".." / "back2" / "deteccao-placas-veiculares-main" / "models" / "best.pt"
)


def _on_plate_confirmed(placa: str, conf_yolo: float):
    """Callback chamado quando uma placa é confirmada.
    Aqui você pode adicionar: gravar no banco, acionar Arduino, etc.
    """
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] PLACA CONFIRMADA: {placa}  (confianca YOLO: {conf_yolo:.0%})")


def run(camera, model_path: str, conf: float, imgsz: int,
        sample_every: int, confirm_frames: int, cooldown: float,
        show: bool):

    import cv2
    from pipeline import load_models, detect

    print("Carregando modelos (pode demorar na primeira execucao)...")
    load_models(model_path, conf=conf, imgsz=imgsz)
    print(f"Modelos carregados. Abrindo camera: {camera}")

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        print(f"Erro: nao foi possivel abrir a camera '{camera}'.", file=sys.stderr)
        sys.exit(1)

    # Informações da câmera
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f"Camera: {width}x{height} @ {fps:.0f}fps")
    print(f"Processando 1 a cada {sample_every} frames | "
          f"Confirmacao: {confirm_frames} frames consecutivos | "
          f"Cooldown: {cooldown}s")
    print("Pressione Ctrl+C para encerrar.\n")

    recent_plates: deque[str | None] = deque(maxlen=confirm_frames)
    last_confirmed: str | None = None
    last_confirmed_time: float = 0.0
    frame_count = 0
    last_display_plate = ""

    # Permite encerrar com Ctrl+C limpo
    running = [True]
    def _sigint(sig, frame):
        running[0] = False
    signal.signal(signal.SIGINT, _sigint)

    while running[0]:
        ret, frame = cap.read()
        if not ret:
            print("Aviso: falha ao capturar frame. Tentando novamente...")
            time.sleep(0.1)
            continue

        frame_count += 1

        # Processar apenas 1 a cada sample_every frames
        if frame_count % sample_every != 0:
            if show:
                _draw_overlay(frame, last_display_plate)
                cv2.imshow("GateVision", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            continue

        # Codifica o frame como JPEG e envia ao pipeline
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            continue

        result = detect(buf.tobytes())
        placa   = result.get("placa")
        conf_yolo = result.get("confianca", 0.0)

        recent_plates.append(placa)

        # Verificar se a fila está cheia e toda leitura é a mesma placa válida
        if (len(recent_plates) == confirm_frames
                and len(set(recent_plates)) == 1
                and recent_plates[0] is not None):

            confirmed = recent_plates[0]
            now = time.time()

            # Cooldown: mesma placa não dispara duas vezes em menos de X segundos
            same_plate_cooldown = (confirmed == last_confirmed
                                   and (now - last_confirmed_time) < cooldown)

            if not same_plate_cooldown:
                _on_plate_confirmed(confirmed, conf_yolo)
                last_confirmed      = confirmed
                last_confirmed_time = now
                last_display_plate  = confirmed
                recent_plates.clear()

        if show:
            _draw_overlay(frame, last_display_plate)
            cv2.imshow("GateVision", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    if show:
        cv2.destroyAllWindows()
    print("\nEncerrado.")


def _draw_overlay(frame, placa: str):
    """Desenha a última placa confirmada sobre o frame (apenas para --show)."""
    import cv2
    h, w = frame.shape[:2]
    label = f"Placa: {placa}" if placa else "Aguardando..."
    cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 0), -1)
    cv2.putText(frame, label, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser(
        description="Leitura continua de placas via webcam ou camera IP."
    )
    parser.add_argument(
        "--camera", default=0,
        help="Indice da webcam (0, 1...) ou URL RTSP. Padrao: 0"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_PLATES", DEFAULT_MODEL),
        help="Caminho para o .pt do detector YOLO de placas"
    )
    parser.add_argument("--conf",   type=float, default=0.25,
                        help="Limiar de confianca YOLO (padrao: 0.25)")
    parser.add_argument("--imgsz",  type=int,   default=640,
                        help="Tamanho de entrada do YOLO (padrao: 640)")
    parser.add_argument("--sample-every", type=int, default=5,
                        help="Processar 1 a cada N frames (padrao: 5)")
    parser.add_argument("--confirm", type=int, default=3,
                        help="Frames consecutivos para confirmar placa (padrao: 3)")
    parser.add_argument("--cooldown", type=float, default=10.0,
                        help="Segundos entre disparos da mesma placa (padrao: 10)")
    parser.add_argument("--show", action="store_true",
                        help="Exibir janela com preview da camera")
    args = parser.parse_args()

    # Converter --camera para int se for número
    camera = args.camera
    try:
        camera = int(camera)
    except (ValueError, TypeError):
        pass  # É uma URL RTSP, manter como string

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Erro: modelo nao encontrado: {model_path}", file=sys.stderr)
        print("Informe o caminho com --model ou via variavel MODEL_PLATES.",
              file=sys.stderr)
        sys.exit(1)

    run(
        camera=camera,
        model_path=str(model_path),
        conf=args.conf,
        imgsz=args.imgsz,
        sample_every=args.sample_every,
        confirm_frames=args.confirm,
        cooldown=args.cooldown,
        show=args.show,
    )


if __name__ == "__main__":
    main()
