from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QListWidget
)
from PySide6.QtCore import Signal

from data.models import EVENTS


class EventPanel(QWidget):
    """Grille de boutons d'événements + historique + bouton annuler.
    Émet event_triggered(event_type) ; ne connaît rien de la vidéo ou du joueur."""

    event_triggered = Signal(str)
    undo_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(140)

        undo_button = QPushButton("Annuler le dernier événement")
        undo_button.clicked.connect(self.undo_requested.emit)

        grid = QGridLayout()
        cols = 3
        for i, event in enumerate(EVENTS):
            button = QPushButton(event)
            button.clicked.connect(lambda checked=False, e=event: self.event_triggered.emit(e))
            grid.addWidget(button, i // cols, i % cols)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Événements enregistrés :"))
        layout.addWidget(self.history_list)
        layout.addWidget(undo_button)
        layout.addWidget(QLabel("Enregistrer un événement :"))
        layout.addLayout(grid)
        self.setLayout(layout)

    def add_history_line(self, text: str):
        self.history_list.addItem(text)
        self.history_list.scrollToBottom()

    def refresh_history(self, lines: list[str]):
        self.history_list.clear()
        self.history_list.addItems(lines)
        self.history_list.scrollToBottom()
