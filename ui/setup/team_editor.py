"""Widget de saisie d'une équipe : nom, couleur, effectif, ajout de joueurs
et réutilisation d'une équipe déjà enregistrée en base."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
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
    QMenu,
)

from data.database import Database
from ui.setup.player_editor import PlayerEditorDialog


DEFAULT_TEAM_COLOR = "#297ffe"


class TeamEditor(QGroupBox):
    """Groupe de widgets permettant de composer une équipe pour un match.

    Si une base de données est fournie, un menu déroulant permet de
    sélectionner une équipe déjà enregistrée : son nom, sa couleur et son
    effectif sont alors préremplis, évitant de ressaisir les joueurs à
    chaque match. Chaque joueur de l'effectif peut ensuite être coché ou
    décoché pour indiquer s'il est présent à CE match précis (l'effectif
    complet de l'équipe reste, lui, inchangé en base).
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
        self._color = DEFAULT_TEAM_COLOR

        self.existing_team_combo = QComboBox(self)
        self.existing_team_combo.addItem("-- Nouvelle équipe --", None)
        if self.database is not None:
            for team in self.database.get_teams():
                self.existing_team_combo.addItem(team.name, team.id)
        self.existing_team_combo.currentIndexChanged.connect(self._on_existing_team_selected)

        self.team_name_edit = QLineEdit(self)
        self.team_name_edit.setPlaceholderText("Nom de l'équipe")

        # -------------------------
        # Couleur de l'équipe
        # -------------------------
        self.color_swatch = QLabel(self)
        self.color_swatch.setFixedSize(24, 24)
        self._update_color_swatch()

        self.color_button = QPushButton("Couleur...", self)
        self.color_button.clicked.connect(self._on_pick_color)

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_swatch)
        color_row.addWidget(self.color_button)
        color_row.addStretch(1)

        self.player_list = QListWidget(self)
        self.player_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.player_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.player_list.customContextMenuRequested.connect(
            self._show_player_context_menu
        )

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
        layout.addWidget(QLabel("Couleur :"))
        layout.addLayout(color_row)
        layout.addWidget(QLabel("Effectif (décocher les joueuses absentes de ce match) :"))
        layout.addWidget(self.player_list)
        layout.addLayout(buttons_row)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Couleur
    # ------------------------------------------------------------------
    def _update_color_swatch(self) -> None:
        self.color_swatch.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888;"
        )

    def _on_pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Couleur de l'équipe")
        if color.isValid():
            self._color = color.name()
            self._update_color_swatch()

    def team_color(self) -> str:
        return self._color

    # ------------------------------------------------------------------
    # Réutilisation d'une équipe existante
    # ------------------------------------------------------------------
    def _on_existing_team_selected(self, index: int) -> None:
        team_id = self.existing_team_combo.itemData(index)
        if team_id is None or self.database is None:
            return

        team = self.database.get_team(team_id)

        self.team_name_edit.setText(self.existing_team_combo.itemText(index))

        self._color = team.color if team is not None else DEFAULT_TEAM_COLOR
        self._update_color_swatch()

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

    def _show_player_context_menu(self, position) -> None:
        item = self.player_list.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        edit_action = menu.addAction("Modifier")

        remove_action = menu.addAction("Supprimer")


        action = menu.exec(
            self.player_list.mapToGlobal(position)
        )


        if action == edit_action:
            self._on_edit_player()

        elif action == remove_action:
            self._on_remove_player()

    def _on_edit_player(self) -> None:
        row = self.player_list.currentRow()

        if row < 0:
            return

        item = self.player_list.item(row)

        old_player = item.data(
            Qt.ItemDataRole.UserRole
        )


        dialog = PlayerEditorDialog(
            self,
            player=old_player
        )


        if dialog.exec() != PlayerEditorDialog.DialogCode.Accepted:
            return


        new_player = dialog.get_player()

        if new_player is None:
            return


        self._players[row] = new_player


        item.setText(
            f"#{new_player[1]}  {new_player[0]}"
        )

        item.setData(
            Qt.ItemDataRole.UserRole,
            new_player
        )

    def _add_player_entry(self, player: Tuple[str, int]) -> None:
        name, number = player
        self._players.append(player)
        item = QListWidgetItem(f"#{number}  {name}")
        item.setData(Qt.ItemDataRole.UserRole, player)
        # Cochée par défaut : présente au match, décochable pour les
        # joueuses de l'effectif absentes de cette rencontre précise.
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
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
        """Effectif complet de l'équipe (créé/mis à jour en base)."""
        return list(self._players)

    def present_players(self) -> List[Tuple[str, int]]:
        """Sous-ensemble de l'effectif coché comme présent à ce match."""
        present = []
        for row in range(self.player_list.count()):
            item = self.player_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                present.append(item.data(Qt.ItemDataRole.UserRole))
        return present

    def is_valid(self) -> bool:
        return bool(self.team_name()) and len(self.present_players()) > 0
