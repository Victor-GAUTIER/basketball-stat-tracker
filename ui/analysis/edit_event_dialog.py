"""Boîte de dialogue permettant de corriger un événement déjà enregistré.

Ouverte depuis le bouton "Modifier" (✏️) du tableau play-by-play :
permet de changer :
- la joueuse
- le type d'événement
- le quart-temps
- la phase de jeu
- le système

L'horodatage reste inchangé.
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
    """Formulaire modal de modification d'un événement."""

    def __init__(
        self,
        event: Event,
        players: List[Player],
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)


        self.setWindowTitle(
            "Modifier l'événement"
        )

        self.setMinimumWidth(
            320
        )



        # -------------------------
        # Joueuse
        # -------------------------

        self.player_combo = QComboBox(
            self
        )


        selected_index = 0


        for index, player in enumerate(players):

            self.player_combo.addItem(
                f"#{player.number} {player.name}",
                player.id
            )


            if player.id == event.player_id:

                selected_index = index



        self.player_combo.setCurrentIndex(
            selected_index
        )





        # -------------------------
        # Événement
        # -------------------------

        self.event_combo = QComboBox(
            self
        )


        for code, label in EVENT_CHOICES:

            self.event_combo.addItem(
                label,
                code
            )


        existing_index = self.event_combo.findData(
            event.event_type
        )


        if existing_index >= 0:

            self.event_combo.setCurrentIndex(
                existing_index
            )





        # -------------------------
        # Quart temps
        # -------------------------

        self.quarter_combo = QComboBox(
            self
        )


        self.quarter_combo.addItems([
            "1",
            "2",
            "3",
            "4",
        ])


        quarter_index = self.quarter_combo.findText(
            str(event.quarter)
        )


        if quarter_index >= 0:

            self.quarter_combo.setCurrentIndex(
                quarter_index
            )






        # -------------------------
        # Phase
        # -------------------------

        self.phase_combo = QComboBox(
            self
        )


        self.phase_combo.addItems(
            PHASES.keys()
        )


        phase_index = self.phase_combo.findText(
            event.phase or ""
        )


        if phase_index >= 0:

            self.phase_combo.setCurrentIndex(
                phase_index
            )





        # -------------------------
        # Système
        # -------------------------

        self.system_combo = QComboBox(
            self
        )


        self.phase_combo.currentTextChanged.connect(
            self._update_systems
        )


        self._update_systems(
            self.phase_combo.currentText()
        )


        system_index = self.system_combo.findText(
            event.system or ""
        )


        if system_index >= 0:

            self.system_combo.setCurrentIndex(
                system_index
            )





        # -------------------------
        # Boutons
        # -------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )


        buttons.accepted.connect(
            self.accept
        )


        buttons.rejected.connect(
            self.reject
        )





        # -------------------------
        # Layout
        # -------------------------

        form = QFormLayout(
            self
        )


        form.addRow(
            "Joueuse :",
            self.player_combo
        )


        form.addRow(
            "Événement :",
            self.event_combo
        )


        form.addRow(
            "Quart temps :",
            self.quarter_combo
        )


        form.addRow(
            "Phase :",
            self.phase_combo
        )


        form.addRow(
            "Système :",
            self.system_combo
        )


        form.addRow(
            buttons
        )






    def _update_systems(
        self,
        phase: str
    ) -> None:


        self.system_combo.clear()


        self.system_combo.addItem(
            ""
        )


        self.system_combo.addItems(
            PHASES.get(
                phase,
                []
            )
        )





    def result_values(
        self
    ) -> Tuple[int, str, int, str, Optional[str]]:
        """
        Retourne :
        (
            player_id,
            event_type,
            quarter,
            phase,
            system
        )
        """


        system = (
            self.system_combo.currentText().strip()
            or None
        )


        return (

            self.player_combo.currentData(),

            self.event_combo.currentData(),

            int(
                self.quarter_combo.currentText()
            ),

            self.phase_combo.currentText(),

            system,

        )
