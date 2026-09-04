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
                segment_paths = []
                total = len(self.events)

                for i, event in enumerate(self.events, start=1):
                    if self._cancelled:
                        self._emit_cancelled()
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
                    segment_path = os.path.join(
                        tmp_dir,
                        f"seg_{i:04d}.mp4"
                    )

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
                        "-fps_mode", "cfr",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-af", "aresample=async=1",
                        "-avoid_negative_ts", "make_zero",
                        segment_path,
                    ]

                    returncode, stdout, stderr = self._run_ffmpeg(cmd)

                    if self._cancelled:
                        self._emit_cancelled()
                        return

                    if returncode != 0:
                        self.error.emit(
                            stderr.decode(
                                "utf-8",
                                errors="replace"
                            ).strip()
                            or f"FFmpeg a échoué pour le segment {i}."
                        )
                        return

                    segment_paths.append(segment_path)
                    self.progress.emit(i, total)

                if self._cancelled:
                    self._emit_cancelled()
                    return

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

                concat_inputs = "".join(
                    f"[v{i}][a{i}]"
                    for i in range(n)
                )

                filter_complex = (
                    f"{filter_parts}"
                    f"{concat_inputs}"
                    f"concat=n={n}:v=1:a=1[outv][outa]"
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
                    self._emit_cancelled()
                    return

                if returncode != 0:
                    self.error.emit(
                        stderr.decode(
                            "utf-8",
                            errors="replace"
                        ).strip()
                        or "FFmpeg a échoué lors de l'assemblage du montage."
                    )
                    return

                self.finished.emit(self.output_path)

        except Exception as exc:
            if self._cancelled:
                self._emit_cancelled()
            else:
                self.error.emit(str(exc))
