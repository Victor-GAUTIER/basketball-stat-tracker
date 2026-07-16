"""Boîte de dialogue permettant de corriger un événement déjà enregistré.

Ouverte depuis le bouton "Modifier" (✏️) du tableau play-by-play : permet de
changer la joueuse et/ou le type d'événement d'une ligne existante, sans
toucher à son horodatage ni à son quart-temps (ces derniers restent liés au
moment réel où l'action a été cliquée pendant l'analyse vidéo).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QWidget,
)

from data.models import Event, Player
from ui.analysis.event_labels import EVENT_CHOICES


class EditEventDialog(QDialog):
    """Formulaire modal pour corriger la joueuse et/ou le type d'un événement."""

    def __init__(
        self,
        event: Event,
        players: List[Player],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modifier l'événement")
        self.setMinimumWidth(320)

        self.player_combo = QComboBox(self)
        selected_index = 0
        for index, player in enumerate(players):
            self.player_combo.addItem(f"#{player.number} {player.name}", player.id)
            if player.id == event.player_id:
                selected_index = index
        self.player_combo.setCurrentIndex(selected_index)

        self.event_combo = QComboBox(self)
        for code, label in EVENT_CHOICES:
            self.event_combo.addItem(label, code)
        existing_index = self.event_combo.findData(event.event_type)
        if existing_index >= 0:
            self.event_combo.setCurrentIndex(existing_index)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Joueuse :", self.player_combo)
        form.addRow("Événement :", self.event_combo)
        form.addRow(buttons)

    def result_values(self) -> Tuple[int, str]:
        """Retourne (player_id, event_type) sélectionnés dans le formulaire."""
        return self.player_combo.currentData(), self.event_combo.currentData()
