"""Widget de saisie d'une équipe : nom, effectif, ajout de joueurs et
réutilisation d'une équipe déjà enregistrée en base."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data.database import Database
from ui.setup.player_editor import PlayerEditorDialog


class TeamEditor(QGroupBox):
    """Groupe de widgets permettant de composer une équipe pour un match.

    Si une base de données est fournie, un menu déroulant permet de
    sélectionner une équipe déjà enregistrée : son nom et son effectif
    sont alors préremplis, évitant de ressaisir les joueurs à chaque match.
    """

    def __init__(
        self,
        title: str,
        database: Optional[Database] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)

        self.database = database
        self._players: List[Tuple[str, int]] = []

        self.existing_team_combo = QComboBox(self)
        self.existing_team_combo.addItem("-- Nouvelle équipe --", None)
        if self.database is not None:
            for team in self.database.get_teams():
                self.existing_team_combo.addItem(team.name, team.id)
        self.existing_team_combo.currentIndexChanged.connect(self._on_existing_team_selected)

        self.team_name_edit = QLineEdit(self)
        self.team_name_edit.setPlaceholderText("Nom de l'équipe")

        self.player_list = QListWidget(self)
        self.player_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.add_player_button = QPushButton("Ajouter un joueur", self)
        self.remove_player_button = QPushButton("Retirer le joueur", self)

        self.add_player_button.clicked.connect(self._on_add_player)
        self.remove_player_button.clicked.connect(self._on_remove_player)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.add_player_button)
        buttons_row.addWidget(self.remove_player_button)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Équipe déjà enregistrée :"))
        layout.addWidget(self.existing_team_combo)
        layout.addWidget(QLabel("Nom de l'équipe :"))
        layout.addWidget(self.team_name_edit)
        layout.addWidget(QLabel("Effectif :"))
        layout.addWidget(self.player_list)
        layout.addLayout(buttons_row)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Réutilisation d'une équipe existante
    # ------------------------------------------------------------------
    def _on_existing_team_selected(self, index: int) -> None:
        team_id = self.existing_team_combo.itemData(index)
        if team_id is None or self.database is None:
            return

        self.team_name_edit.setText(self.existing_team_combo.itemText(index))
        self.player_list.clear()
        self._players.clear()
        for player in self.database.get_players_by_team(team_id):
            self._add_player_entry((player.name, player.number))

    # ------------------------------------------------------------------
    # Gestion des joueurs
    # ------------------------------------------------------------------
    def _on_add_player(self) -> None:
        dialog = PlayerEditorDialog(self)
        if dialog.exec() == PlayerEditorDialog.DialogCode.Accepted:
            player = dialog.get_player()
            if player is not None:
                self._add_player_entry(player)

    def _add_player_entry(self, player: Tuple[str, int]) -> None:
        name, number = player
        self._players.append(player)
        item = QListWidgetItem(f"#{number}  {name}")
        item.setData(Qt.ItemDataRole.UserRole, player)
        self.player_list.addItem(item)

    def _on_remove_player(self) -> None:
        row = self.player_list.currentRow()
        if row < 0:
            return
        item = self.player_list.takeItem(row)
        player = item.data(Qt.ItemDataRole.UserRole)
        if player in self._players:
            self._players.remove(player)

    # ------------------------------------------------------------------
    # Accès aux données saisies
    # ------------------------------------------------------------------
    def team_name(self) -> str:
        return self.team_name_edit.text().strip()

    def players(self) -> List[Tuple[str, int]]:
        return list(self._players)

    def is_valid(self) -> bool:
        return bool(self.team_name()) and len(self._players) > 0
