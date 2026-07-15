"""Widget de saisie d'une équipe : nom, effectif et ajout de joueurs."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from ui.setup.player_editor import PlayerEditorDialog


class TeamEditor(QGroupBox):
    """Groupe de widgets permettant de composer une équipe pour un match."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)

        self._players: List[Tuple[str, int]] = []

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
        layout.addWidget(QLabel("Nom de l'équipe :"))
        layout.addWidget(self.team_name_edit)
        layout.addWidget(QLabel("Effectif :"))
        layout.addWidget(self.player_list)
        layout.addLayout(buttons_row)
        self.setLayout(layout)

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
