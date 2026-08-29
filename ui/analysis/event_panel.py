from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QWidget
)

from data.event_config import event_config


class EventPanel(QWidget):
    """Panneau de boutons pour les événements classiques (LF+, Rebonds,
    Passe décisive, Perte de balle, Interception, Contre, Faute...).

    La liste des événements affichés (libellé, raccourci indiqué sur le
    bouton) vient de la configuration personnalisable (data.event_config),
    modifiable depuis le menu Affichage > Configuration des événements. Le
    panneau se reconstruit automatiquement à chaque modification."""

    event_triggered = Signal(str)


    def __init__(
        self,
        parent: Optional[QWidget]=None,
        columns:int=3
    ):

        super().__init__(parent)

        self._columns = columns

        self._layout = QGridLayout(self)

        event_config.changed.connect(self._rebuild)

        self._rebuild()

    def _rebuild(self) -> None:

        while self._layout.count():

            item = self._layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        for index, (code, label, shortcut) in enumerate(
            event_config.active_event_types()
        ):

            button_text = (
                f"{label}\n[{shortcut}]"
                if shortcut
                else label
            )

            button = QPushButton(
                button_text,
                self
            )

            button.setMinimumHeight(
                50
            )

            # Empêche le bouton de voler le focus au clavier
            button.setFocusPolicy(
                Qt.FocusPolicy.NoFocus
            )

            button.clicked.connect(
                lambda checked=False,
                c=code:
                self.event_triggered.emit(c)
            )

            row, col = divmod(
                index,
                self._columns
            )

            self._layout.addWidget(
                button,
                row,
                col
            )
