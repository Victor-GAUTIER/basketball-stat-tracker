"""Panneau d'affichage des effectifs des deux équipes sous forme de listes."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


class TeamListWidget(QListWidget):
    """Liste de joueurs pour une équipe, à sélection unique."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def load_players(self, players: List[Player]) -> None:
        self.clear()
        for player in players:
            item = QListWidgetItem(f"#{player.number}  {player.name}")
            item.setData(Qt.ItemDataRole.UserRole, player.id)
            self.addItem(item)


class PlayerPanel(QWidget):
    """Regroupe les deux listes de joueurs (équipe A / équipe B) et gère la sélection."""

    # Émis avec l'id du joueur sélectionné (dans l'une ou l'autre équipe).
    player_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.home_label = QLabel("Équipe A", self)
        self.home_label.setStyleSheet("font-weight: bold;")
        self.home_list = TeamListWidget(self)

        self.away_label = QLabel("Équipe B", self)
        self.away_label.setStyleSheet("font-weight: bold;")
        self.away_list = TeamListWidget(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.home_label)
        layout.addWidget(self.home_list, stretch=1)
        layout.addWidget(self.away_label)
        layout.addWidget(self.away_list, stretch=1)

        self.home_list.itemClicked.connect(self._on_home_selected)
        self.away_list.itemClicked.connect(self._on_away_selected)

        self._selected_player_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Chargement des données
    # ------------------------------------------------------------------
    def set_teams(
        self,
        home_name: str,
        home_players: List[Player],
        away_name: str,
        away_players: List[Player],
    ) -> None:
        self.home_label.setText(home_name)
        self.away_label.setText(away_name)
        self.home_list.load_players(home_players)
        self.away_list.load_players(away_players)

    # ------------------------------------------------------------------
    # Sélection
    # ------------------------------------------------------------------
    def _on_home_selected(self, item: QListWidgetItem) -> None:
        # Un seul joueur sélectionné à la fois, toutes équipes confondues.
        self.away_list.clearSelection()
        self._select(item)

    def _on_away_selected(self, item: QListWidgetItem) -> None:
        self.home_list.clearSelection()
        self._select(item)

    def _select(self, item: QListWidgetItem) -> None:
        player_id = item.data(Qt.ItemDataRole.UserRole)
        self._selected_player_id = player_id
        self.player_selected.emit(player_id)

    def selected_player_id(self) -> Optional[int]:
        return self._selected_player_id
