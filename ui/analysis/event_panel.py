"""Panneau de boutons d'événements statistiques (2PTS+, 3PTS-, rebond, etc.)."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

# Liste des événements disponibles : (code interne stocké en base, libellé
# affiché, raccourci clavier). Modulaire : il suffit d'ajouter une entrée ici
# pour qu'un nouveau bouton apparaisse automatiquement dans le panneau, dans
# le tableau de stats et dans la liste des derniers événements.
EVENT_TYPES: List[Tuple[str, str, str]] = [
    ("2PTS_MADE", "2PTS+", "2"),
    ("2PTS_MISS", "2PTS-", "Shift+2"),
    ("3PTS_MADE", "3PTS+", "3"),
    ("3PTS_MISS", "3PTS-", "Shift+3"),
    ("FT_MADE", "LF+", "1"),
    ("FT_MISS", "LF-", "Shift+1"),
    ("OFF_REBOUND", "RO", "O"),
    ("DEF_REBOUND", "RD", "D"),
    ("ASSIST", "AST", "A"),
    ("TURNOVER", "TO", "T"),
    ("STEAL", "STL", "S"),
    ("BLOCK", "BLK", "B"),
    ("FOUL", "FAUTE", "F"),
]


class EventPanel(QWidget):
    """Grille de boutons permettant d'enregistrer un type d'événement.

    Chaque bouton porte son raccourci clavier (voir EVENT_TYPES), actif tant
    que la fenêtre d'analyse a le focus, pour une saisie rapide au clavier
    sans quitter la vidéo des yeux.
    """

    # Émis avec le code interne de l'événement cliqué (ex : "3PTS_MADE").
    event_triggered = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, columns: int = 3) -> None:
        super().__init__(parent)

        layout = QGridLayout(self)
        for index, (code, label, shortcut) in enumerate(EVENT_TYPES):
            button = QPushButton(f"{label}\n[{shortcut}]", self)
            button.setMinimumHeight(50)
            button.setShortcut(QKeySequence(shortcut))
            button.setToolTip(f"Raccourci : {shortcut}")
            button.clicked.connect(lambda _checked=False, c=code: self.event_triggered.emit(c))
            row, col = divmod(index, columns)
            layout.addWidget(button, row, col)
