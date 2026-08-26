from __future__ import annotations

import os
import sys


def get_ffmpeg_path() -> str:
    """Retourne le chemin vers ffmpeg, que l'appli tourne en mode
    développement (python main.py) ou compilée (PyInstaller)."""

    if getattr(sys, "frozen", False):
        # Mode PyInstaller : les fichiers embarqués sont extraits
        # dans sys._MEIPASS (--onefile) ou à côté de l'exécutable (--onedir).
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        # Mode développement : on prend le binaire du dossier bin/ du projet.
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffmpeg_path = os.path.join(base_path, "bin", exe_name)

    if os.path.exists(ffmpeg_path):
        return ffmpeg_path

    # Fallback : ffmpeg installé sur le système (PATH)
    return "ffmpeg"
