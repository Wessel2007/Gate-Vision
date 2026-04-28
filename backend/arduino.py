"""
arduino.py — Controle serial do Arduino para abertura de cancela/portão.

Exporta:
    conectar_arduino(porta, baud) -> bool
    fechar_arduino()
    enviar_arduino(comando) -> bool
    abrir_cancela(tempo_aberta)
    arduino_conectado  -> bool (leitura)
"""

import os
import threading
import time

try:
    import serial
except ImportError:
    serial = None

GATE_OPEN_SECONDS = float(os.getenv("GATE_OPEN_SECONDS", "5"))

_arduino = None
_arduino_conectado = False
_arduino_lock = threading.Lock()


def arduino_conectado() -> bool:
    return _arduino_conectado


def conectar_arduino(porta: str, baud: int) -> bool:
    global _arduino, _arduino_conectado

    if serial is None:
        print("Pacote pyserial nao instalado. Arduino ficara em modo simulacao.")
        return False

    try:
        print(f"Tentando conectar ao Arduino em {porta}...")
        _arduino = serial.Serial(porta, baud, timeout=1)
        time.sleep(2)
        _arduino_conectado = True
        print("Arduino conectado com sucesso.\n")
        return True
    except Exception as exc:
        _arduino = None
        _arduino_conectado = False
        print(f"Modo simulacao. Nao foi possivel conectar ao Arduino: {exc}\n")
        return False


def fechar_arduino():
    global _arduino, _arduino_conectado

    if _arduino is not None:
        try:
            _arduino.close()
        except Exception:
            pass

    _arduino = None
    _arduino_conectado = False


def enviar_arduino(comando: bytes) -> bool:
    if not _arduino_conectado or _arduino is None:
        return False

    try:
        with _arduino_lock:
            _arduino.reset_input_buffer()
            _arduino.write(comando)
            _arduino.flush()
        return True
    except Exception as exc:
        print(f"Erro ao comunicar com Arduino: {exc}")
        return False


def abrir_cancela(tempo_aberta: float | None = None):
    if tempo_aberta is None:
        tempo_aberta = GATE_OPEN_SECONDS

    def acao():
        print("Autorizado -> abrindo portao")
        if not enviar_arduino(b"A"):
            print("Arduino indisponivel. Simulando abertura/fechamento.")
            return

        time.sleep(tempo_aberta)
        enviar_arduino(b"F")
        print("Portao fechado")

    threading.Thread(target=acao, daemon=True).start()
