"""Panneau de boutons d'événements statistiques (2PTS+, 3PTS-, rebond, etc.)."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

# Liste des événements disponibles : (code interne stocké en base, libellé affiché).
# Modulaire : il suffit d'ajouter une entrée ici pour qu'un nouveau bouton
# apparaisse automatiquement dans le panneau et dans le tableau de stats.
EVENT_TYPES: List[Tuple[str, str]] = [
    ("2PTS_MADE", "2PTS+"),
    ("2PTS_MISS", "2PTS-"),
    ("3PTS_MADE", "3PTS+"),
    ("3PTS_MISS", "3PTS-"),
    ("FT_MADE", "LF+"),
    ("FT_MISS", "LF-"),
    ("OFF_REBOUND", "RO"),
    ("DEF_REBOUND", "RD"),
    ("ASSIST", "AST"),
    ("TURNOVER", "TO"),
    ("STEAL", "STL"),
    ("BLOCK", "BLK"),
    ("FOUL", "FAUTE"),
]


class EventPanel(QWidget):
    """Grille de boutons permettant d'enregistrer un type d'événement."""

    # Émis avec le code interne de l'événement cliqué (ex : "3PTS_MADE").
    event_triggered = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, columns: int = 3) -> None:
        super().__init__(parent)

        layout = QGridLayout(self)
        for index, (code, label) in enumerate(EVENT_TYPES):
            button = QPushButton(label, self)
            button.setMinimumHeight(45)
            button.clicked.connect(lambda _checked=False, c=code: self.event_triggered.emit(c))
            row, col = divmod(index, columns)
            layout.addWidget(button, row, col)
