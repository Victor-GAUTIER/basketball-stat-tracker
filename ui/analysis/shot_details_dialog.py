"""Popup affiché après l'enregistrement d'un tir (clic sur le terrain de
tir) ou d'un lancer franc, pour préciser :
- le type d'action ayant amené le tir (remplace l'ancienne ligne de
  boutons "Type d'action" de PhasePanel, qui ne concernait de toute façon
  quasiment que les tirs) ;
- le niveau de défense subi (tirs de jeu uniquement) ;
- si le tir suit un rebond offensif dans la même possession (indépendant
  du type d'action : un tir peut suivre un rebond offensif ET plusieurs
  passes, auquel cas le type d'action sera par exemple "Mouvement de
  balle" tout en ayant cette case cochée) ;
- le nombre de dribbles pris juste avant le tir (tirs de jeu uniquement :
  n'a pas de sens pour un lancer franc).

Pour les lancers francs, `show_defense=False, show_dribbles=False` réduit
le popup au type d'action et au rebond offensif préalable uniquement.

Contrairement aux raccourcis utilisés pendant la saisie en direct, ce
popup n'a pas besoin d'être ultra-rapide : il apparaît une fois le tir
cliqué, donc après coup, ce qui laisse le temps de rembobiner la vidéo si
besoin (notamment pour compter les dribbles avec précision).

Les types d'action et niveaux de défense affichés viennent de la
configuration personnalisable (data.event_config), modifiable depuis le
menu Affichage > Configuration des événements. La présence de chaque
champ (type d'action, défense, rebond offensif préalable, dribbles), et
du popup lui-même, dépend en plus des préférences d'affichage locales au
poste (ui.feature_flags), également réglables depuis cette même fenêtre.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from data.event_config import event_config
from ui.analysis.phase_panel import BUTTON_STYLE
from ui.feature_flags import feature_flags


class ShotDetailsDialog(QDialog):
    """Détails d'un tir : type d'action, défense, rebond offensif
    préalable, nombre de dribbles. Tous les champs sont optionnels (aucune
    sélection = non renseigné), seul le nombre de dribbles a une valeur
    par défaut (0)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        show_defense: bool = True,
        show_dribbles: bool = True,
        title: str = "Détails du tir",
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        # La visibilité effective de chaque champ combine le paramètre
        # d'appel (ex: show_defense=False pour un lancer franc, où la
        # défense n'a pas de sens) et la préférence d'affichage locale du
        # poste (voir ui.feature_flags).
        self._show_action_type = feature_flags.is_field_enabled("action_type")
        self._show_defense = show_defense and feature_flags.is_field_enabled("defense")
        self._show_prior_oreb = feature_flags.is_field_enabled("prior_oreb")
        self._show_dribbles = show_dribbles and feature_flags.is_field_enabled("dribbles")

        self._current_action_type: Optional[str] = None
        self._current_defense_level: Optional[str] = None

        self._action_buttons: dict[str, QPushButton] = {}
        self._defense_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)

        # -------------------------
        # Type d'action
        # -------------------------

        if self._show_action_type:

            layout.addWidget(QLabel("Type d'action"))

            action_row = QHBoxLayout()

            for action in event_config.active_action_type_names():

                btn = self._make_button(action)

                btn.clicked.connect(
                    lambda checked=False, a=action: self._on_action_clicked(a)
                )

                self._action_buttons[action] = btn

                action_row.addWidget(btn)

            action_row.addStretch()

            layout.addLayout(action_row)

        # -------------------------
        # Défense (tirs de jeu uniquement)
        # -------------------------

        if self._show_defense:

            layout.addWidget(QLabel("Défense"))

            defense_row = QHBoxLayout()

            for label in event_config.active_defense_level_names():

                btn = self._make_button(label)

                btn.clicked.connect(
                    lambda checked=False, l=label: self._on_defense_clicked(l)
                )

                self._defense_buttons[label] = btn

                defense_row.addWidget(btn)

            defense_row.addStretch()

            layout.addLayout(defense_row)

        # -------------------------
        # Rebond offensif préalable
        # -------------------------

        self.prior_oreb_checkbox: Optional[QCheckBox] = None

        if self._show_prior_oreb:

            self.prior_oreb_checkbox = QCheckBox(
                "Après un rebond offensif (même possession)", self
            )

            layout.addWidget(self.prior_oreb_checkbox)

        # -------------------------
        # Nombre de dribbles préalables (tirs de jeu uniquement)
        # -------------------------

        self.dribbles_spin: Optional[QSpinBox] = None

        if self._show_dribbles:

            dribbles_row = QHBoxLayout()

            dribbles_row.addWidget(QLabel("Dribbles avant le tir"))

            self.dribbles_spin = QSpinBox(self)
            self.dribbles_spin.setRange(0, 15)

            dribbles_row.addWidget(self.dribbles_spin)
            dribbles_row.addStretch()

            layout.addLayout(dribbles_row)

        # -------------------------
        # Boutons
        # -------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    # =====================================================
    # Construction bouton
    # =====================================================

    def _make_button(self, text: str) -> QPushButton:

        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet(BUTTON_STYLE)

        return btn

    # =====================================================
    # Sélection (single-select avec désélection au reclic, comme PhasePanel)
    # =====================================================

    def _on_action_clicked(self, action: str) -> None:

        if self._current_action_type == action:

            self._current_action_type = None
            self._action_buttons[action].setChecked(False)

        else:

            for a, btn in self._action_buttons.items():
                btn.setChecked(a == action)

            self._current_action_type = action

    def _on_defense_clicked(self, label: str) -> None:

        if self._current_defense_level == label:

            self._current_defense_level = None
            self._defense_buttons[label].setChecked(False)

        else:

            for l, btn in self._defense_buttons.items():
                btn.setChecked(l == label)

            self._current_defense_level = label

    # =====================================================
    # Accès externe
    # =====================================================

    def selected_action_type(self) -> Optional[str]:
        return self._current_action_type

    def selected_defense_level(self) -> Optional[str]:
        return self._current_defense_level

    def prior_oreb(self) -> bool:
        if self.prior_oreb_checkbox is None:
            return False
        return self.prior_oreb_checkbox.isChecked()

    def dribbles_count(self) -> Optional[int]:
        if self.dribbles_spin is None:
            return None
        return self.dribbles_spin.value()
