"""Panneau d'affichage des effectifs des deux équipes sous forme de listes."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


class EditPlayerDialog(QDialog):
    """Petite boîte de dialogue pour corriger le nom et le numéro d'une joueuse."""

    def __init__(self, player: Player, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modifier la joueuse")

        self.name_edit = QLineEdit(player.name, self)

        self.number_spin = QSpinBox(self)
        self.number_spin.setRange(0, 99)
        self.number_spin.setValue(player.number)

        form = QFormLayout()
        form.addRow("Nom", self.name_edit)
        form.addRow("Numéro", self.number_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result_values(self) -> Tuple[str, int]:
        return self.name_edit.text(), self.number_spin.value()


class TeamListWidget(QListWidget):
    """Liste de joueurs pour une équipe, à sélection unique."""

    player_edit_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def load_players(self, players: List[Player]) -> None:
        self.clear()
        for player in players:
            item = QListWidgetItem(f"#{player.number}  {player.name}")
            item.setData(Qt.ItemDataRole.UserRole, player.id)
            self.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        player_id = item.data(Qt.ItemDataRole.UserRole)
        self.player_edit_requested.emit(player_id)


class PlayerPanel(QWidget):
    """Regroupe les deux listes de joueurs (équipe A / équipe B), côte à côte,
    et permet de sélectionner une joueuse ou de corriger un nom d'équipe / une joueuse."""

    # Émis avec l'id du joueur sélectionné (dans l'une ou l'autre équipe).
    player_selected = Signal(int)

    # Émis quand le nom d'une équipe est modifié : (is_home, nouveau_nom)
    team_name_changed = Signal(bool, str)

    # Émis quand une joueuse est modifiée : (player_id, nom, numéro)
    player_edited = Signal(int, str, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._players_by_id: Dict[int, Player] = {}

        self.home_name_edit = QLineEdit("Équipe A", self)
        self.home_name_edit.setStyleSheet("font-weight: bold;")
        self.home_list = TeamListWidget(self)

        self.away_name_edit = QLineEdit("Équipe B", self)
        self.away_name_edit.setStyleSheet("font-weight: bold;")
        self.away_list = TeamListWidget(self)

        home_column = QVBoxLayout()
        home_column.addWidget(self.home_name_edit)
        home_column.addWidget(self.home_list, stretch=1)

        away_column = QVBoxLayout()
        away_column.addWidget(self.away_name_edit)
        away_column.addWidget(self.away_list, stretch=1)

        layout = QHBoxLayout(self)
        layout.addLayout(home_column)
        layout.addLayout(away_column)

        self.home_list.itemClicked.connect(self._on_home_selected)
        self.away_list.itemClicked.connect(self._on_away_selected)

        self.home_list.player_edit_requested.connect(self._on_edit_player)
        self.away_list.player_edit_requested.connect(self._on_edit_player)

        self.home_name_edit.editingFinished.connect(
            lambda: self._on_team_name_edited(is_home=True)
        )
        self.away_name_edit.editingFinished.connect(
            lambda: self._on_team_name_edited(is_home=False)
        )

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
        self.home_name_edit.setText(home_name)
        self.away_name_edit.setText(away_name)
        self.home_list.load_players(home_players)
        self.away_list.load_players(away_players)

        self._players_by_id = {p.id: p for p in home_players + away_players}

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

    # ------------------------------------------------------------------
    # Modification du nom d'équipe
    # ------------------------------------------------------------------
    def _on_team_name_edited(self, is_home: bool) -> None:
        edit = self.home_name_edit if is_home else self.away_name_edit
        new_name = edit.text().strip()

        if new_name:
            self.team_name_changed.emit(is_home, new_name)

    # ------------------------------------------------------------------
    # Modification d'une joueuse
    # ------------------------------------------------------------------
    def _on_edit_player(self, player_id: int) -> None:
        player = self._players_by_id.get(player_id)

        if player is None:
            return

        dialog = EditPlayerDialog(player, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        name, number = dialog.result_values()

        if name.strip():
            self.player_edited.emit(player_id, name.strip(), number)
