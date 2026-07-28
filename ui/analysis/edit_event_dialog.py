"""Boîte de dialogue permettant de corriger un événement déjà enregistré.

Ouverte depuis le bouton "Modifier" (✏️) du tableau play-by-play :
permet de changer :
- la joueuse
- le type d'événement
- le quart-temps
- la phase de jeu
- le système
- le type d'action
- le type de perte de balle (si l'événement en est une)

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
from ui.analysis.phase_panel import ACTION_TYPES, PHASES
from ui.analysis.turnover_dialog import TURNOVER_TYPES


TURNOVER_CODES = {code for code, _ in TURNOVER_TYPES} | {"TURNOVER"}



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


        self.event_combo.currentIndexChanged.connect(
            self._on_event_changed
        )





        # -------------------------
        # Type de perte de balle
        # -------------------------

        self.turnover_combo = QComboBox(
            self
        )


        for code, label in TURNOVER_TYPES:

            self.turnover_combo.addItem(
                label,
                code
            )


        self.turnover_combo.currentIndexChanged.connect(
            self._on_turnover_changed
        )


        self._sync_turnover_from_event(
            event.event_type
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
        # Type d'action
        # -------------------------

        self.action_type_combo = QComboBox(
            self
        )


        self.action_type_combo.addItem(
            ""
        )


        self.action_type_combo.addItems(
            ACTION_TYPES
        )


        action_type_index = self.action_type_combo.findText(
            event.action_type or ""
        )


        if action_type_index >= 0:

            self.action_type_combo.setCurrentIndex(
                action_type_index
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
            "Type de perte de balle :",
            self.turnover_combo
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
            "Type d'action :",
            self.action_type_combo
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



    # =====================================================
    # Synchronisation Événement <-> Type de perte de balle
    # =====================================================

    def _sync_turnover_from_event(
        self,
        event_code: str
    ) -> None:
        """
        Active le combo "Type de perte de balle" et le pré-sélectionne si
        l'événement courant est une perte de balle ; le désactive sinon.
        """

        is_turnover = event_code in TURNOVER_CODES


        self.turnover_combo.setEnabled(
            is_turnover
        )


        if is_turnover:

            turnover_index = self.turnover_combo.findData(
                event_code
            )


            self.turnover_combo.blockSignals(
                True
            )


            self.turnover_combo.setCurrentIndex(
                turnover_index
                if turnover_index >= 0
                else 0
            )


            self.turnover_combo.blockSignals(
                False
            )



    def _on_event_changed(
        self,
        _index: int
    ) -> None:

        event_code = self.event_combo.currentData()


        self._sync_turnover_from_event(
            event_code
        )



    def _on_turnover_changed(
        self,
        _index: int
    ) -> None:
        """
        Met à jour l'affichage de event_combo pour rester cohérent
        visuellement. Ce n'est PAS cette valeur qui est utilisée pour
        l'enregistrement : result_values() lit directement turnover_combo
        quand il est actif, pour éviter tout problème de synchronisation.
        """

        turnover_code = self.turnover_combo.currentData()


        if turnover_code is None:

            return


        target_index = self.event_combo.findData(
            turnover_code
        )


        if target_index < 0:

            return


        self.event_combo.blockSignals(
            True
        )


        self.event_combo.setCurrentIndex(
            target_index
        )


        self.event_combo.blockSignals(
            False
        )





    def result_values(
        self
    ) -> Tuple[int, str, int, str, Optional[str], Optional[str]]:
        """
        Retourne :
        (
            player_id,
            event_type,
            quarter,
            phase,
            system,
            action_type
        )
        """


        system = (
            self.system_combo.currentText().strip()
            or None
        )


        action_type = (
            self.action_type_combo.currentText().strip()
            or None
        )


        # Si le combo "Type de perte de balle" est actif, c'est lui qui
        # fait foi pour event_type : plus fiable que de relire event_combo,
        # dont la mise à jour dépend d'une synchronisation indirecte via
        # signaux Qt.
        if self.turnover_combo.isEnabled():

            event_type = self.turnover_combo.currentData()

        else:

            event_type = self.event_combo.currentData()


        return (

            self.player_combo.currentData(),

            event_type,

            int(
                self.quarter_combo.currentText()
            ),

            self.phase_combo.currentText(),

            system,

            action_type,

        )
