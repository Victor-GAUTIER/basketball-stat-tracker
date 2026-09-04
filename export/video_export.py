from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Union

from PySide6.QtCore import QObject, Signal

from data.models import Event
from data.ffmpeg_path import get_ffmpeg_path


class VideoExportWorker(QObject):

    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()

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
        self._cancel_signal_emitted = False
        self._current_process: Optional[subprocess.Popen] = None

    def _emit_cancelled(self):
        if not self._cancel_signal_emitted:
            self._cancel_signal_emitted = True
            self.cancelled.emit()

    def _video_path_for(self, event: Event) -> Optional[str]:
        game_id = getattr(event, "game_id", None)
        if game_id in self.video_paths:
            return self.video_paths[game_id]
        if len(self.video_paths) == 1:
            return next(iter(self.video_paths.values()))
        return None

    def cancel(self):
        self._cancelled = True

        process = self._current_process
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    def _run_ffmpeg(self, cmd: List[str]):
        startupinfo = None
        creationflags = 0

        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

        self._current_process = process
        stdout, stderr = process.communicate()
        self._current_process = None

        return process.returncode, stdout, stderr

    def run(self):
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:

                TARGET_W = 1920
                TARGET_H = 1080
                TARGET_FPS = 30

                segment_paths = []
                total = len(self.events)

                for i, event in enumerate(self.events, start=1):

                    if self._cancelled:
                        self.cancelled.emit()
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
                        "-vf",
                        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                        "-r", str(TARGET_FPS),
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-fps_mode", "cfr",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-af", "aresample=async=1",
                        "-avoid_negative_ts", "make_zero",
                        segment_path,
                    ]

                    returncode, stdout, stderr = self._run_ffmpeg(cmd)

                    if self._cancelled:
                        self.cancelled.emit()
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
                    self.cancelled.emit()
                    return

                # -------------------------
                # 2. Concaténation : tous les segments ont déjà la même
                #    résolution/fps (normalisés à l'étape 1), donc un simple
                #    concat demuxer + copie de flux suffit. Contrairement au
                #    filter_complex précédent, ffmpeg ne lit les fichiers que
                #    séquentiellement, sans les garder tous ouverts en
                #    mémoire à la fois : ça passe à l'échelle quel que soit
                #    le nombre de segments.
                # -------------------------

                concat_list_path = os.path.join(tmp_dir, "concat_list.txt")

                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for path in segment_paths:
                        escaped = path.replace("'", "'\\''")
                        f.write(f"file '{escaped}'\n")

                concat_cmd = [
                    get_ffmpeg_path(),
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy",
                    self.output_path,
                ]

                returncode, stdout, stderr = self._run_ffmpeg(concat_cmd)

                if self._cancelled:
                    self.cancelled.emit()
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
