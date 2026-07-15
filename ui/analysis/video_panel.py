"""Panneau vidéo : lecture, pause, avance/recul et chronomètre."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def format_timestamp(seconds: float) -> str:
    """Formate un temps en secondes vers le format mm:ss."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


class VideoPanel(QWidget):
    """Widget encapsulant le lecteur vidéo et ses contrôles de navigation."""

    # Émis à chaque changement de position de lecture, en secondes.
    position_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.play_button = QPushButton("▶ Lecture", self)
        self.pause_button = QPushButton("⏸ Pause", self)
        self.back_button = QPushButton("⏮ -5s", self)
        self.forward_button = QPushButton("⏭ +5s", self)

        self.position_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.position_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.back_button)
        controls_row.addWidget(self.play_button)
        controls_row.addWidget(self.pause_button)
        controls_row.addWidget(self.forward_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addWidget(self.time_label)
        layout.addLayout(controls_row)

    def _connect_signals(self) -> None:
        self.play_button.clicked.connect(self.player.play)
        self.pause_button.clicked.connect(self.player.pause)
        self.back_button.clicked.connect(lambda: self.seek_relative(-5000))
        self.forward_button.clicked.connect(lambda: self.seek_relative(5000))

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.position_slider.sliderMoved.connect(self.player.setPosition)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def load_video(self, path: str) -> None:
        """Charge le fichier vidéo à analyser."""
        if path:
            self.player.setSource(QUrl.fromLocalFile(path))

    def current_timestamp(self) -> float:
        """Retourne la position de lecture courante, en secondes."""
        return self.player.position() / 1000.0

    def seek_relative(self, delta_ms: int) -> None:
        """Avance ou recule la lecture d'un nombre de millisecondes donné."""
        new_position = max(0, self.player.position() + delta_ms)
        self.player.setPosition(new_position)

    # ------------------------------------------------------------------
    # Slots internes
    # ------------------------------------------------------------------
    def _on_position_changed(self, position_ms: int) -> None:
        self.position_slider.setValue(position_ms)
        self._update_time_label()
        self.position_changed.emit(position_ms / 1000.0)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.position_slider.setRange(0, duration_ms)
        self._update_time_label()

    def _update_time_label(self) -> None:
        current = format_timestamp(self.player.position() / 1000.0)
        total = format_timestamp(self.player.duration() / 1000.0)
        self.time_label.setText(f"{current} / {total}")
