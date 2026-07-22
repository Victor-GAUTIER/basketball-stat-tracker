"""Panneau vidéo : lecture/pause, avance/recul, chronomètre et son."""

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
    QStyle,
    QVBoxLayout,
    QWidget,
)



def format_timestamp(seconds: float) -> str:
    """Formate un temps en secondes vers mm:ss."""

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    return f"{minutes:02d}:{secs:02d}"



class SeekSlider(QSlider):
    """Slider avec déplacement direct par clic."""

    def mousePressEvent(self, event) -> None:

        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:

            value = QStyle.sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                int(event.position().x()),
                self.width()
            )

            self.setValue(value)

            self.sliderMoved.emit(
                value
            )



class VideoPanel(QWidget):
    """Widget lecteur vidéo."""

    position_changed = Signal(float)



    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:

        super().__init__(parent)


        # --------------------------
        # Lecteur
        # --------------------------

        self.player = QMediaPlayer(
            self
        )


        self.video_widget = QVideoWidget(
            self
        )


        self.video_widget.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )


        self.player.setVideoOutput(
            self.video_widget
        )


        self.audio_output = QAudioOutput(
            self
        )


        self.player.setAudioOutput(
            self.audio_output
        )



        # --------------------------
        # Boutons
        # --------------------------

        self.play_pause_button = QPushButton(
            "▶ Lecture",
            self
        )


        self.back_button = QPushButton(
            "⏮ -5s",
            self
        )


        self.forward_button = QPushButton(
            "⏭ +5s",
            self
        )


        self.mute_button = QPushButton(
            "🔊",
            self
        )


        # Les boutons ne prennent pas le focus
        # pour ne pas bloquer les raccourcis
        self.play_pause_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.back_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.forward_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.mute_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )



        self.play_pause_button.setToolTip(
            "Espace : Lecture / Pause"
        )

        self.back_button.setToolTip(
            "Flèche gauche : -5 secondes"
        )

        self.forward_button.setToolTip(
            "Flèche droite : +5 secondes"
        )

        self.mute_button.setToolTip(
            "M : Couper / rétablir le son"
        )



        # --------------------------
        # Barre progression
        # --------------------------

        self.position_slider = SeekSlider(
            Qt.Orientation.Horizontal,
            self
        )


        self.position_slider.setRange(
            0,
            0
        )


        self.time_label = QLabel(
            "00:00 / 00:00",
            self
        )


        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )


        self._user_seeking = False



        self._build_layout()

        self._connect_signals()



    # ==================================================
    # Interface
    # ==================================================

    def _build_layout(self):

        controls = QHBoxLayout()


        controls.addWidget(
            self.back_button
        )


        controls.addWidget(
            self.play_pause_button
        )


        controls.addWidget(
            self.forward_button
        )


        controls.addWidget(
            self.mute_button
        )



        layout = QVBoxLayout(
            self
        )


        layout.addWidget(
            self.video_widget,
            stretch=1
        )


        layout.addWidget(
            self.position_slider
        )


        layout.addWidget(
            self.time_label
        )


        layout.addLayout(
            controls
        )



    # ==================================================
    # Connexions
    # ==================================================

    def _connect_signals(self):

        self.play_pause_button.clicked.connect(
            self.toggle_play_pause
        )


        self.back_button.clicked.connect(
            lambda:
                self.seek_relative(-5000)
        )


        self.forward_button.clicked.connect(
            lambda:
                self.seek_relative(5000)
        )


        self.mute_button.clicked.connect(
            self.toggle_mute
        )


        self.player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )


        self.player.positionChanged.connect(
            self._on_position_changed
        )


        self.player.durationChanged.connect(
            self._on_duration_changed
        )


        self.position_slider.sliderPressed.connect(
            self._on_slider_pressed
        )


        self.position_slider.sliderMoved.connect(
            self._on_slider_moved
        )


        self.position_slider.sliderReleased.connect(
            self._on_slider_released
        )



    # ==================================================
    # API publique
    # ==================================================

    def load_video(
        self,
        path: str
    ):

        if path:

            self.player.setSource(
                QUrl.fromLocalFile(path)
            )



    def current_timestamp(self) -> float:

        return (
            self.player.position()
            /
            1000.0
        )



    def seek_relative(
        self,
        delta_ms: int
    ):

        new_position = max(
            0,
            self.player.position()
            +
            delta_ms
        )


        self.player.setPosition(
            new_position
        )

    def seek(
        self,
        timestamp: float
    ):
        """
        Place la vidéo à un temps donné en secondes.
        """

        self.player.setPosition(
            int(timestamp * 1000)
        )



    def toggle_play_pause(self):

        if (
            self.player.playbackState()
            ==
            QMediaPlayer.PlaybackState.PlayingState
        ):

            self.player.pause()

        else:

            self.player.play()



    def toggle_mute(self):

        muted = not self.audio_output.isMuted()

        self.audio_output.setMuted(
            muted
        )

        self.mute_button.setText(
            "🔇" if muted else "🔊"
        )



    # ==================================================
    # Slots
    # ==================================================

    def _on_playback_state_changed(
        self,
        state
    ):

        if (
            state
            ==
            QMediaPlayer.PlaybackState.PlayingState
        ):

            self.play_pause_button.setText(
                "⏸ Pause"
            )

        else:

            self.play_pause_button.setText(
                "▶ Lecture"
            )



    def _on_position_changed(
        self,
        position_ms: int
    ):

        if not self._user_seeking:

            self.position_slider.setValue(
                position_ms
            )


        self._update_time_label()


        self.position_changed.emit(
            position_ms / 1000.0
        )



    def _on_duration_changed(
        self,
        duration_ms: int
    ):

        self.position_slider.setRange(
            0,
            duration_ms
        )


        self._update_time_label()



    def _on_slider_pressed(self):

        self._user_seeking = True



    def _on_slider_moved(
        self,
        position_ms: int
    ):

        self.player.setPosition(
            position_ms
        )


        self._update_time_label(
            position_ms
        )



    def _on_slider_released(self):

        self.player.setPosition(
            self.position_slider.value()
        )


        self._user_seeking = False



    def _update_time_label(
        self,
        override_position_ms: Optional[int] = None
    ):

        position_ms = (
            override_position_ms
            if override_position_ms is not None
            else self.player.position()
        )


        current = format_timestamp(
            position_ms / 1000
        )


        total = format_timestamp(
            self.player.duration()
            /
            1000
        )


        self.time_label.setText(
            f"{current} / {total}"
        )
