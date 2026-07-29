from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List

from PySide6.QtCore import QObject, QThread, Signal

from data.models import Event


class VideoExportWorker(QObject):

    progress = Signal(int, int)   # (segment_courant, total)
    finished = Signal(str)        # chemin du fichier de sortie
    error = Signal(str)

    def __init__(
        self,
        video_path: str,
        events: List[Event],
        before: float,
        after: float,
        output_path: str,
    ):
        super().__init__()
        self.video_path = video_path
        self.events = events
        self.before = before
        self.after = after
        self.output_path = output_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                segment_paths = []

                total = len(self.events)

                for i, event in enumerate(self.events, start=1):

                    if self._cancelled:
                        return

                    start = max(0.0, event.timestamp - self.before)
                    duration = self.before + self.after

                    segment_path = os.path.join(tmp_dir, f"seg_{i:04d}.mp4")

                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-ss", f"{start:.3f}",
                        "-i", self.video_path,
                        "-t", f"{duration:.3f}",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-c:a", "aac",
                        "-avoid_negative_ts", "make_zero",
                        segment_path,
                    ]

                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )

                    if result.returncode != 0:
                        self.error.emit(
                            f"Erreur ffmpeg sur le segment {i} "
                            f"(t={event.timestamp:.1f}s) :\n"
                            f"{result.stderr.decode(errors='ignore')}"
                        )
                        return

                    segment_paths.append(segment_path)
                    self.progress.emit(i, total)

                if self._cancelled:
                    return

                # Fichier de concaténation ffmpeg
                concat_list_path = os.path.join(tmp_dir, "concat.txt")

                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for path in segment_paths:
                        # ffmpeg concat demuxer veut des chemins échappés
                        safe_path = path.replace("'", "'\\''")
                        f.write(f"file '{safe_path}'\n")

                concat_cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy",
                    self.output_path,
                ]

                result = subprocess.run(
                    concat_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                if result.returncode != 0:
                    self.error.emit(
                        "Erreur ffmpeg lors de la concaténation :\n"
                        f"{result.stderr.decode(errors='ignore')}"
                    )
                    return

                self.finished.emit(self.output_path)

        except Exception as exc:
            self.error.emit(str(exc))
