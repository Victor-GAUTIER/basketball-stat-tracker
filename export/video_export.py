from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Union

from PySide6.QtCore import QObject, QThread, Signal

from data.models import Event
from data.ffmpeg_path import get_ffmpeg_path


class VideoExportWorker(QObject):

    progress = Signal(int, int)   # (segment_courant, total)
    finished = Signal(str)        # chemin du fichier de sortie
    error = Signal(str)

    def __init__(
        self,
        video_path: Union[str, Dict[int, str]],
        events: List[Event],
        before: float,
        after: float,
        output_path: str,
    ):
        super().__init__()

        if isinstance(video_path, dict):
            self.video_paths = video_path
        else:
            self.video_paths = {None: video_path}

        self.events = events
        self.before = before
        self.after = after
        self.output_path = output_path
        self._cancelled = False

        # Référence vers le process ffmpeg actuellement en cours
        # d'exécution, pour pouvoir le tuer immédiatement depuis cancel()
        # plutôt que d'attendre qu'il se termine de lui-même.
        self._current_process: Optional[subprocess.Popen] = None

    # =====================================================
    # Résolution du chemin vidéo pour un événement donné
    # =====================================================

    def _video_path_for(self, event: Event) -> Optional[str]:

        game_id = getattr(event, "game_id", None)

        if game_id in self.video_paths:
            return self.video_paths[game_id]

        if len(self.video_paths) == 1:
            return next(iter(self.video_paths.values()))

        return None

    # =====================================================
    # Annulation
    # =====================================================

    def cancel(self):
        self._cancelled = True

        if self._current_process is not None:
            self._current_process.kill()

    # =====================================================
    # Exécution d'une commande ffmpeg (avec suivi du process en cours)
    # =====================================================

    def _run_ffmpeg(self, cmd: List[str]):
        """Lance une commande ffmpeg en gardant une référence au process,
        pour permettre son annulation immédiate depuis cancel()."""

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self._current_process = process

        stdout, stderr = process.communicate()

        self._current_process = None

        return process.returncode, stdout, stderr

    # =====================================================
    # Point d'entrée
    # =====================================================

    def run(self):
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:

                segment_paths = []
                total = len(self.events)

                # -------------------------
                # 1. Découpe de chaque segment (frame rate constant,
                #    ré-échantillonnage audio forcé, pour limiter la
                #    dérive audio/vidéo à la source).
                # -------------------------

                for i, event in enumerate(self.events, start=1):

                    if self._cancelled:
                        return

                    video_path = self._video_path_for(event)

                    if not video_path:
                        self.error.emit(
                            f"Aucune vidéo associée au segment {i} "
                            f"(t={event.timestamp:.1f}s)."
                        )
                        return

                    start = max(0.0, event.timestamp - self.before)
                    duration = self.before + self.after

                    segment_path = os.path.join(tmp_dir, f"seg_{i:04d}.mp4")

                    cmd = [
                        get_ffmpeg_path(),
                        "-y",
                        "-ss", f"{start:.3f}",
                        "-i", video_path,
                        "-t", f"{duration:.3f}",
                        "-map", "0:v:0",
                        "-map", "0:a:0?",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-vsync", "cfr",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-af", "aresample=async=1",
                        "-avoid_negative_ts", "make_zero",
                        segment_path,
                    ]

                    returncode, stdout, stderr = self._run_ffmpeg(cmd)

                    if self._cancelled:
                        return

                    if returncode != 0:
                        self.error.emit(
                            f"Erreur ffmpeg sur le segment {i} "
                            f"(t={event.timestamp:.1f}s) :\n"
                            f"{stderr.decode(errors='ignore')}"
                        )
                        return

                    segment_paths.append(segment_path)
                    self.progress.emit(i, total)

                if self._cancelled:
                    return

                # -------------------------
                # 2. Concaténation via le filtre concat, avec
                #    normalisation préalable de chaque segment (résolution,
                #    SAR, fps) : les vidéos sources peuvent provenir de
                #    caméras/exports différents selon les matchs (ex.
                #    1920x1080/30fps vs 854x480/29.97fps), et le filtre
                #    concat exige que tous les flux d'entrée aient
                #    exactement les mêmes paramètres.
                # -------------------------

                concat_cmd = [get_ffmpeg_path(), "-y"]

                for path in segment_paths:
                    concat_cmd += ["-i", path]

                n = len(segment_paths)

                TARGET_W = 1920
                TARGET_H = 1080
                TARGET_FPS = 30

                filter_parts = "".join(
                    f"[{i}:v:0]"
                    f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,"
                    f"setsar=1,"
                    f"fps={TARGET_FPS},"
                    f"setpts=PTS-STARTPTS[v{i}];"
                    f"[{i}:a:0]"
                    f"aresample=48000,"
                    f"asetpts=PTS-STARTPTS[a{i}];"
                    for i in range(n)
                )

                concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))

                filter_complex = (
                    f"{filter_parts}{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]"
                )

                concat_cmd += [
                    "-filter_complex", filter_complex,
                    "-map", "[outv]",
                    "-map", "[outa]",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-c:a", "aac",
                    self.output_path,
                ]

                returncode, stdout, stderr = self._run_ffmpeg(concat_cmd)

                if self._cancelled:
                    return

                if returncode != 0:
                    self.error.emit(
                        "Erreur ffmpeg lors de la concaténation :\n"
                        f"{stderr.decode(errors='ignore')}"
                    )
                    return

                self.finished.emit(self.output_path)

        except Exception as exc:
            if not self._cancelled:
                self.error.emit(str(exc))
