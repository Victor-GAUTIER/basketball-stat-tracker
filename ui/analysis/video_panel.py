"""Panneau vidéo : lecture/pause, avance/recul et chronomètre."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


def format_timestamp(seconds: float) -> str:
    """Formate un temps en secondes vers le format mm:ss."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


class SeekSlider(QSlider):
    """QSlider dont un clic direct sur la barre déplace immédiatement le curseur.

    Par défaut, un QSlider ne saute à la position cliquée que pour le clic
    molette ; un clic gauche ne fait avancer que d'un "page step". On
    surcharge donc mousePressEvent pour qu'un simple clic gauche sur la
    barre de progression déplace directement la lecture à cet endroit.
    """

    def mousePressEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), int(event.position().x()), self.width()
            )
            self.setValue(value)
            self.sliderMoved.emit(value)


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

        # Bouton unique lecture/pause : son libellé change selon l'état.
        self.play_pause_button = QPushButton("▶ Lecture", self)
        self.play_pause_button.setShortcut(QKeySequence(Qt.Key.Key_Space))
        self.play_pause_button.setToolTip("Raccourci : Espace")

        self.back_button = QPushButton("⏮ -5s", self)
        self.back_button.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.back_button.setToolTip("Raccourci : Flèche gauche")

        self.forward_button = QPushButton("⏭ +5s", self)
        self.forward_button.setShortcut(QKeySequence(Qt.Key.Key_Right))
        self.forward_button.setToolTip("Raccourci : Flèche droite")

        self.position_slider = SeekSlider(Qt.Orientation.Horizontal, self)
        self.position_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Empêche les mises à jour automatiques de la barre de venir
        # perturber un glissement en cours par l'utilisateur.
        self._user_seeking = False

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.back_button)
        controls_row.addWidget(self.play_pause_button)
        controls_row.addWidget(self.forward_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addWidget(self.time_label)
        layout.addLayout(controls_row)

    def _connect_signals(self) -> None:
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.back_button.clicked.connect(lambda: self.seek_relative(-5000))
        self.forward_button.clicked.connect(lambda: self.seek_relative(5000))

        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

        # Pendant que l'utilisateur fait glisser le curseur : on suit la
        # position en direct mais on n'écrase plus la valeur de la barre
        # avec la position réelle du lecteur (cf. _on_position_changed).
        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        self.position_slider.sliderReleased.connect(self._on_slider_released)

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

    def toggle_play_pause(self) -> None:
        """Bascule entre lecture et pause (un seul bouton pour les deux actions)."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    # ------------------------------------------------------------------
    # Slots internes
    # ------------------------------------------------------------------
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setText("⏸ Pause")
        else:
            self.play_pause_button.setText("▶ Lecture")

    def _on_position_changed(self, position_ms: int) -> None:
        # On ne touche pas à la barre tant que l'utilisateur la manipule,
        # sinon la position réelle (qui met un instant à suivre) viendrait
        # "tirer en arrière" le curseur pendant le glissement.
        if not self._user_seeking:
            self.position_slider.setValue(position_ms)
        self._update_time_label()
        self.position_changed.emit(position_ms / 1000.0)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.position_slider.setRange(0, duration_ms)
        self._update_time_label()

    def _on_slider_pressed(self) -> None:
        self._user_seeking = True

    def _on_slider_moved(self, position_ms: int) -> None:
        # Recherche en direct pendant le glissement pour un retour immédiat.
        self.player.setPosition(position_ms)
        self._update_time_label(override_position_ms=position_ms)

    def _on_slider_released(self) -> None:
        self.player.setPosition(self.position_slider.value())
        self._user_seeking = False

    def _update_time_label(self, override_position_ms: Optional[int] = None) -> None:
        position_ms = (
            override_position_ms if override_position_ms is not None else self.player.position()
        )
        current = format_timestamp(position_ms / 1000.0)
        total = format_timestamp(self.player.duration() / 1000.0)
        self.time_label.setText(f"{current} / {total}")
