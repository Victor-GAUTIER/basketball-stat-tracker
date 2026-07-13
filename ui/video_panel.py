from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QSizePolicy
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, Signal


class VideoPanel(QWidget):
    """Encapsule le lecteur vidéo. Émet video_loaded(path) quand un fichier
    est choisi, pour que le reste de l'appli (controller) réagisse."""

    video_loaded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setMinimumSize(640, 360)
        self.player.setVideoOutput(self.video_widget)

        self.info_label = QLabel("Aucune vidéo")
        self.info_label.setAlignment(Qt.AlignCenter)

        open_button = QPushButton("Ouvrir une vidéo")
        play_button = QPushButton("Lecture / Pause")
        back_button = QPushButton("-5s")
        forward_button = QPushButton("+5s")

        open_button.clicked.connect(self.open_video)
        play_button.clicked.connect(self.play_pause)
        back_button.clicked.connect(lambda: self.seek(-5000))
        forward_button.clicked.connect(lambda: self.seek(5000))

        controls = QHBoxLayout()
        controls.addWidget(open_button)
        controls.addWidget(back_button)
        controls.addWidget(play_button)
        controls.addWidget(forward_button)

        layout = QVBoxLayout()
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.info_label)
        layout.addLayout(controls)
        self.setLayout(layout)

    def open_video(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir une vidéo", "", "Videos (*.mp4 *.avi *.mov)"
        )
        if file:
            self.player.setSource(QUrl.fromLocalFile(file))
            self.info_label.setText(file)
            self.player.play()
            self.video_loaded.emit(file)

    def play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek(self, offset_ms: int):
        new_pos = max(0, self.player.position() + offset_ms)
        self.player.setPosition(new_pos)

    def current_time(self) -> float:
        """Position actuelle en secondes."""
        return self.player.position() / 1000
