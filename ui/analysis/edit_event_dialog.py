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
- les détails de tir : défense subie, rebond offensif préalable, nombre
  de dribbles (si l'événement est un tir)

L'horodatage reste inchangé.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)

from data.models import Event, Player
from ui.analysis.event_labels import EVENT_CHOICES
from data.event_config import event_config
from ui.analysis.turnover_dialog import TURNOVER_TYPES


TURNOVER_CODES = {code for code, _ in TURNOVER_TYPES} | {"TURNOVER"}

SHOT_TYPES = {"2PTS_MADE", "2PTS_MISSED", "3PTS_MADE", "3PTS_MISSED"}



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
            event_config.active_phase_names()
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
            event_config.active_action_type_names()
        )


        action_type_index = self.action_type_combo.findText(
            event.action_type or ""
        )


        if action_type_index >= 0:

            self.action_type_combo.setCurrentIndex(
                action_type_index
            )




        # -------------------------
        # Détails de tir (défense, rebond off. préalable, dribbles)
        # -------------------------

        self.defense_combo = QComboBox(
            self
        )

        self.defense_combo.addItem(
            "",
            None
        )

        for label in event_config.active_defense_level_names():

            self.defense_combo.addItem(
                label,
                label
            )

        defense_index = self.defense_combo.findData(
            event.defense_level
        )

        if defense_index >= 0:

            self.defense_combo.setCurrentIndex(
                defense_index
            )


        self.prior_oreb_checkbox = QCheckBox(
            "Après un rebond offensif (même possession)",
            self
        )

        self.prior_oreb_checkbox.setChecked(
            bool(event.prior_oreb)
        )


        self.dribbles_spin = QSpinBox(
            self
        )

        self.dribbles_spin.setRange(
            0,
            15
        )

        self.dribbles_spin.setValue(
            event.dribbles or 0
        )


        self._sync_shot_details_from_event(
            event.event_type
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
            "Défense (tir) :",
            self.defense_combo
        )


        form.addRow(
            "",
            self.prior_oreb_checkbox
        )


        form.addRow(
            "Dribbles avant le tir :",
            self.dribbles_spin
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
            event_config.active_system_names(phase)
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


    def _sync_shot_details_from_event(
        self,
        event_code: str
    ) -> None:
        """
        Active les champs de détails de tir (défense, rebond offensif
        préalable, dribbles) si l'événement courant est un tir ; les
        désactive sinon (ils n'ont pas de sens pour un autre type
        d'événement).
        """

        is_shot = event_code in SHOT_TYPES

        self.defense_combo.setEnabled(
            is_shot
        )

        self.prior_oreb_checkbox.setEnabled(
            is_shot
        )

        self.dribbles_spin.setEnabled(
            is_shot
        )



    def _on_event_changed(
        self,
        _index: int
    ) -> None:

        event_code = self.event_combo.currentData()


        self._sync_turnover_from_event(
            event_code
        )

        self._sync_shot_details_from_event(
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
    ) -> Tuple[
        int, str, int, Optional[str], Optional[str], Optional[str],
        Optional[str], Optional[bool], Optional[int]
    ]:
        """
        Retourne :
        (
            player_id,
            event_type,
            quarter,
            phase,
            system,
            action_type,
            defense_level,
            prior_oreb,
            dribbles
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


        # Les détails de tir n'ont de sens que si l'événement final en est
        # un : on les remet à None sinon, plutôt que de conserver une
        # valeur résiduelle sans rapport avec le nouvel événement.
        is_shot = event_type in SHOT_TYPES

        defense_level = (
            self.defense_combo.currentData()
            if is_shot
            else None
        )

        prior_oreb = (
            self.prior_oreb_checkbox.isChecked()
            if is_shot
            else None
        )

        dribbles = (
            self.dribbles_spin.value()
            if is_shot
            else None
        )


        return (

            self.player_combo.currentData(),

            event_type,

            int(
                self.quarter_combo.currentText()
            ),

            self.phase_combo.currentText(),

            system,

            action_type,

            defense_level,

            prior_oreb,

            dribbles,

        )
