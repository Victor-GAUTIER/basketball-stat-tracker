"""Dialogue de modification des joueuses présentes à un match déjà créé.

Affiche l'effectif complet de chaque équipe (pas seulement celles déjà
liées au match), avec une case à cocher par joueuse, pour ajouter ou
retirer des présences a posteriori.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


class GamePlayersDialog(QDialog):
    """Deux listes cochables (domicile / extérieur) pour choisir les
    joueuses présentes à un match, parmi l'effectif complet de chaque équipe."""

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
        self.setMinimumSize(420, 400)

        self.home_list = self._build_list(home_roster, home_present_ids)
        self.away_list = self._build_list(away_roster, away_present_ids)

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
    ) -> QListWidget:

        present = set(present_ids)

        list_widget = QListWidget(self)

        for player in sorted(roster, key=lambda p: p.number):
            item = QListWidgetItem(f"#{player.number}  {player.name}")
            item.setData(Qt.ItemDataRole.UserRole, player.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if player.id in present
                else Qt.CheckState.Unchecked
            )
            list_widget.addItem(item)

        return list_widget

    def _checked_ids(self, list_widget: QListWidget) -> List[int]:
        result = []
        for row in range(list_widget.count()):
            item = list_widget.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    def present_player_ids(self) -> List[int]:
        """Ids de toutes les joueuses cochées, des deux équipes."""
        return self._checked_ids(self.home_list) + self._checked_ids(self.away_list)
