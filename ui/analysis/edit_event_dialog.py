"""Boîte de dialogue permettant de corriger un événement déjà enregistré.

Ouverte depuis le bouton "Modifier" (✏️) du tableau play-by-play : permet de
changer la joueuse, le type d'événement, la phase de jeu et le système d'une
ligne existante, sans toucher à son horodatage ni à son quart-temps (ces
derniers restent liés au moment réel où l'action a été cliquée pendant
l'analyse vidéo).
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
from ui.analysis.phase_panel import PHASES


class EditEventDialog(QDialog):
    """Formulaire modal pour corriger la joueuse, le type, la phase et le système d'un événement."""

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

        self.phase_combo = QComboBox(self)
        self.phase_combo.addItems(PHASES.keys())
        phase_index = self.phase_combo.findText(event.phase or "")
        if phase_index >= 0:
            self.phase_combo.setCurrentIndex(phase_index)

        self.system_combo = QComboBox(self)
        self.phase_combo.currentTextChanged.connect(self._update_systems)
        self._update_systems(self.phase_combo.currentText())

        system_index = self.system_combo.findText(event.system or "")
        if system_index >= 0:
            self.system_combo.setCurrentIndex(system_index)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Joueuse :", self.player_combo)
        form.addRow("Événement :", self.event_combo)
        form.addRow("Phase :", self.phase_combo)
        form.addRow("Système :", self.system_combo)
        form.addRow(buttons)

    def _update_systems(self, phase: str) -> None:
        self.system_combo.clear()
        self.system_combo.addItem("")
        self.system_combo.addItems(PHASES.get(phase, []))

    def result_values(self) -> Tuple[int, str, str, Optional[str]]:
        """Retourne (player_id, event_type, phase, system) sélectionnés dans le formulaire."""
        system = self.system_combo.currentText().strip() or None
        return (
            self.player_combo.currentData(),
            self.event_combo.currentData(),
            self.phase_combo.currentText(),
            system,
        )
