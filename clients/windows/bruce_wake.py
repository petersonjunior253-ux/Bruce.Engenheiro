"""Local Windows wake-word listener.

Requires a custom Picovoice Porcupine keyword file trained for the phrase BRUCE.
Detection runs on-device. No audio is sent to the BRUCE API by this process.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pvporcupine
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()
running = True


def stop(*_):
    global running
    running = False


def main() -> int:
    access_key = os.getenv("PICOVOICE_ACCESS_KEY", "").strip()
    keyword_path = Path(os.getenv("BRUCE_KEYWORD_PATH", "./models/bruce_windows.ppn"))
    command = os.getenv("BRUCE_ON_WAKE_COMMAND", "").strip()

    if not access_key:
        print("Configure PICOVOICE_ACCESS_KEY no arquivo .env.")
        return 2
    if not keyword_path.is_file():
        print(f"Modelo personalizado não encontrado: {keyword_path}")
        print("Crie/baixe um modelo da palavra BRUCE no Picovoice Console e coloque-o nesse caminho.")
        return 2

    porcupine = pvporcupine.create(
        access_key=access_key,
        keyword_paths=[str(keyword_path.resolve())],
        sensitivities=[0.68],
    )
    audio_queue = []
    import queue
    audio_queue = queue.Queue()

    def on_audio(indata, frames, timing, status):
        if status:
            print(f"Áudio: {status}", file=sys.stderr)
        audio_queue.put(np.squeeze(indata.copy()))

    print("BRUCE está aguardando a palavra de ativação localmente.")
    print("Detecção local ativa. Ctrl+C para encerrar.")
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        with sd.InputStream(
            samplerate=porcupine.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=porcupine.frame_length,
            callback=on_audio,
        ):
            while running:
                try:
                    pcm = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if len(pcm) != porcupine.frame_length:
                    continue
                if porcupine.process(pcm) >= 0:
                    print("\nBRUCE ativado!")
                    if command:
                        subprocess.Popen(command, shell=True)
                    print("Ação de ativação concluída. Aguardando nova chamada.")
    finally:
        porcupine.delete()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
