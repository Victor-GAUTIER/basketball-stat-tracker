"""Dialogue de modification des joueuses présentes à un match déjà créé.

Affiche l'effectif complet de chaque équipe (pas seulement celles déjà
liées au match), avec une case à cocher par joueuse pour sa présence, et un
champ numéro modifiable propre à CE match (le numéro par défaut de
l'équipe est utilisé si rien n'est précisé).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


class _PlayerRow(QWidget):
    """Une ligne : case à cocher (présence) + numéro modifiable + nom."""

    def __init__(
        self,
        player: Player,
        present: bool,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.player_id = player.id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.checkbox = QCheckBox(self)
        self.checkbox.setChecked(present)

        self.number_spin = QSpinBox(self)
        self.number_spin.setRange(0, 99)
        self.number_spin.setValue(player.number)
        self.number_spin.setPrefix("#")
        self.number_spin.setFixedWidth(70)

        self.name_label = QLabel(player.name, self)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.number_spin)
        layout.addWidget(self.name_label, stretch=1)

    def is_present(self) -> bool:
        return self.checkbox.isChecked()

    def number(self) -> int:
        return self.number_spin.value()


class GamePlayersDialog(QDialog):
    """Deux listes (domicile / extérieur) pour choisir les joueuses
    présentes à un match et leur numéro de maillot pour ce match précis,
    parmi l'effectif complet de chaque équipe."""

    def __init__(
        self,
        home_name: str,
        home_roster: List[Player],
        home_present_ids: List[int],
        away_name: str,
        away_roster: List[Player],
        away_present_ids: List[int],
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle("Joueuses présentes")
        self.setMinimumSize(460, 420)

        self.home_list, self._home_rows = self._build_list(
            home_roster, home_present_ids
        )
        self.away_list, self._away_rows = self._build_list(
            away_roster, away_present_ids
        )

        lists_row = QHBoxLayout()

        home_col = QVBoxLayout()
        home_col.addWidget(QLabel(home_name, self))
        home_col.addWidget(self.home_list)
        lists_row.addLayout(home_col)

        away_col = QVBoxLayout()
        away_col.addWidget(QLabel(away_name, self))
        away_col.addWidget(self.away_list)
        lists_row.addLayout(away_col)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(lists_row)
        layout.addWidget(buttons)

    def _build_list(
        self, roster: List[Player], present_ids: List[int]
    ) -> Tuple[QListWidget, List[_PlayerRow]]:

        present = set(present_ids)

        list_widget = QListWidget(self)
        rows: List[_PlayerRow] = []

        for player in sorted(roster, key=lambda p: p.number):

            row = _PlayerRow(player, player.id in present, list_widget)

            item = QListWidgetItem(list_widget)
            item.setSizeHint(row.sizeHint())

            list_widget.addItem(item)
            list_widget.setItemWidget(item, row)

            rows.append(row)

        return list_widget, rows

    def _present_ids(self, rows: List[_PlayerRow]) -> List[int]:
        return [row.player_id for row in rows if row.is_present()]

    def _numbers(self, rows: List[_PlayerRow]) -> Dict[int, int]:
        return {row.player_id: row.number() for row in rows if row.is_present()}

    def present_player_ids(self) -> List[int]:
        """Ids de toutes les joueuses cochées, des deux équipes."""
        return self._present_ids(self._home_rows) + self._present_ids(self._away_rows)

    def present_player_numbers(self) -> Dict[int, int]:
        """{player_id: numéro pour ce match}, pour toutes les joueuses cochées."""
        numbers = self._numbers(self._home_rows)
        numbers.update(self._numbers(self._away_rows))
        return numbers
