"""Boîte de dialogue de sélection du type de perte de balle.

Ouverte automatiquement quand l'utilisateur déclenche l'événement
"Perte de balle" (bouton ou raccourci) : demande de préciser le type de
perte avant d'enregistrer l'événement en base, avec un code dédié
(TO_PASS, TO_DRIBBLE, TO_VIOLATION, TO_SORTIE, TO_FAUTE, TO_TEMPS, TO_AUTRE).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


TURNOVER_TYPES = [
    ("TO_PASS", "Passe"),
    ("TO_DRIBBLE", "Dribble"),
    ("TO_VIOLATION", "Violation"),
    ("TO_SORTIE", "Sortie"),
    ("TO_FAUTE", "Faute"),
    ("TO_TEMPS", "Temps"),
    ("TO_AUTRE", "Autre"),
]


class TurnoverTypeDialog(QDialog):
    """Demande de préciser le type de perte de balle."""

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle(
            "Type de perte de balle"
        )

        self._selected_code: Optional[str] = None

        layout = QVBoxLayout(self)

        grid = QGridLayout()

        for index, (code, label) in enumerate(TURNOVER_TYPES):

            button = QPushButton(
                label,
                self
            )

            button.setMinimumHeight(
                40
            )

            button.clicked.connect(
                lambda checked=False, c=code:
                self._on_choice(c)
            )

            row, col = divmod(
                index,
                3
            )

            grid.addWidget(
                button,
                row,
                col
            )

        layout.addLayout(
            grid
        )

    def _on_choice(
        self,
        code: str
    ) -> None:

        self._selected_code = code

        self.accept()

    def selected_code(
        self
    ) -> Optional[str]:

        return self._selected_code
