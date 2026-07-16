from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QWidget
)


EVENT_TYPES: List[Tuple[str, str, str]] = [

    ("FT_MADE", "LF+", "E"),
    ("FT_MISSED", "LF-", "Shift+E"),

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
        parent: Optional[QWidget]=None,
        columns:int=3
    ):

        super().__init__(parent)


        self._shortcuts = []


        layout = QGridLayout(
            self
        )


        for index, (
            code,
            label,
            shortcut
        ) in enumerate(EVENT_TYPES):


            button = QPushButton(
                f"{label}\n[{shortcut}]",
                self
            )


            button.setMinimumHeight(
                50
            )


            button.clicked.connect(
                lambda checked=False,
                c=code:
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



            sc = QShortcut(
                QKeySequence(shortcut),
                self
            )


            sc.setContext(
                Qt.ShortcutContext.ApplicationShortcut
            )


            sc.activated.connect(
                lambda c=code:
                self.event_triggered.emit(c)
            )


            self._shortcuts.append(
                sc
            )
