"""Panneau de boutons d'événements statistiques."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QWidget,
)


EVENT_TYPES: List[Tuple[str, str, str]] = [

    ("2PTS_MADE", "2PTS+", "A"),
    ("2PTS_MISS", "2PTS-", "Shift+A"),

    ("3PTS_MADE", "3PTS+", "Z"),
    ("3PTS_MISS", "3PTS-", "Shift+Z"),

    ("FT_MADE", "LF+", "E"),
    ("FT_MISS", "LF-", "Shift+E"),

    ("OFF_REBOUND", "RO", "Shift+Q"),
    ("DEF_REBOUND", "RD", "Q"),

    ("ASSIST", "AST", "S"),
    ("TURNOVER", "TO", "D"),
    ("STEAL", "STL", "W"),
    ("BLOCK", "BLK", "X"),
    ("FOUL", "FAUTE", "C"),
]



class EventPanel(QWidget):

    event_triggered = Signal(str)



    def __init__(
        self,
        parent: Optional[QWidget] = None,
        columns: int = 3
    ):

        super().__init__(parent)


        layout = QGridLayout(
            self
        )


        for index, (code, label, shortcut) in enumerate(EVENT_TYPES):

            button = QPushButton(
                f"{label}\n[{shortcut}]",
                self
            )


            button.setMinimumHeight(
                50
            )


            button.clicked.connect(
                lambda checked=False, c=code:
                self.event_triggered.emit(c)
            )


            row, col = divmod(
                index,
                columns
            )


            layout.addWidget(
                button,
                row,
                col
            )
