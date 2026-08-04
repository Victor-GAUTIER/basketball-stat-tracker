"""Fenêtre de lancement de l'application.

Première fenêtre affichée : permet de créer un nouveau match ou de rouvrir
un match déjà enregistré en base (équipes, joueurs et événements associés
sont conservés d'une session à l'autre grâce à SQLite).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data.database import Database


class TeamDetailsDialog(QDialog):
    """Affiche le détail d'une équipe : son nom et la liste de ses joueuses."""

    def __init__(
        self,
        database: Database,
        team_id: int,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        team = next(
            (
                t
                for t in database.get_teams()
                if t.id == team_id
            ),
            None
        )

        self.setWindowTitle(
            team.name
            if team
            else "Équipe"
        )

        self.setMinimumWidth(
            320
        )


        layout = QVBoxLayout(
            self
        )


        title = QLabel(
            team.name
            if team
            else "Équipe introuvable",
            self
        )

        title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            title
        )


        players_list = QListWidget(
            self
        )


        players = (
            database.get_players_by_team(
                team_id
            )
            if team
            else []
        )


        if players:

            for player in sorted(
                players,
                key=lambda p: p.number
            ):

                players_list.addItem(
                    f"#{player.number} {player.name}"
                )

        else:

            placeholder = QListWidgetItem(
                "Aucune joueuse enregistrée pour cette équipe."
            )

            placeholder.setFlags(
                Qt.ItemFlag.NoItemFlags
            )

            players_list.addItem(
                placeholder
            )


        layout.addWidget(
            players_list
        )


        close_button = QPushButton(
            "Fermer",
            self
        )

        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(
            close_button
        )


class LaunchWindow(QMainWindow):
    """Écran d'accueil : nouveau match, ou reprise d'un match existant."""

    def __init__(
        self,
        database: Database
    ) -> None:

        super().__init__()

        self.database = database

        # Références conservées pour éviter
        # la destruction automatique des fenêtres
        self.setup_window: Optional[QWidget] = None
        self.analysis_window: Optional[QWidget] = None


        self.setWindowTitle(
            "Basketball Stat Tracker"
        )

        self.resize(
            600,
            680
        )


        self._build_ui()

        self._load_games()

        self._load_teams()



    # =====================================================
    # Construction interface
    # =====================================================

    def _build_ui(self) -> None:

        central = QWidget(
            self
        )

        self.setCentralWidget(
            central
        )


        layout = QVBoxLayout(
            central
        )


        title = QLabel(
            "Basketball Stat Tracker",
            self
        )

        title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            title
        )



        self.new_game_button = QPushButton(
            "+ Nouveau match",
            self
        )

        self.new_game_button.setMinimumHeight(
            42
        )

        self.new_game_button.clicked.connect(
            self._on_new_game
        )

        layout.addWidget(
            self.new_game_button
        )



        layout.addWidget(
            QLabel(
                "Matchs déjà enregistrés :",
                self
            )
        )



        self.games_list = QListWidget(
            self
        )


        self.games_list.itemDoubleClicked.connect(
            lambda _item:
            self._on_open_selected()
        )


        layout.addWidget(
            self.games_list,
            stretch=1
        )



        actions_row = QHBoxLayout()


        self.open_button = QPushButton(
            "Ouvrir la sélection",
            self
        )

        self.open_button.clicked.connect(
            self._on_open_selected
        )


        self.delete_game_button = QPushButton(
            "Supprimer le match",
            self
        )

        self.delete_game_button.clicked.connect(
            self._on_delete_game
        )


        self.refresh_button = QPushButton(
            "Actualiser la liste",
            self
        )

        self.refresh_button.clicked.connect(
            self._load_games
        )


        actions_row.addWidget(
            self.open_button
        )

        actions_row.addWidget(
            self.delete_game_button
        )


        actions_row.addWidget(
            self.refresh_button
        )


        layout.addLayout(
            actions_row
        )



        # -------------------------
        # Equipes enregistrées
        # -------------------------

        layout.addWidget(
            QLabel(
                "Équipes enregistrées :",
                self
            )
        )


        self.teams_list = QListWidget(
            self
        )


        self.teams_list.itemDoubleClicked.connect(
            lambda _item:
            self._on_view_team()
        )


        layout.addWidget(
            self.teams_list,
            stretch=1
        )


        teams_actions_row = QHBoxLayout()


        self.edit_team_button = QPushButton(
            "Modifier l'équipe",
            self
        )

        self.edit_team_button.clicked.connect(
            self._on_edit_team
        )


        self.delete_team_button = QPushButton(
            "Supprimer l'équipe",
            self
        )

        self.delete_team_button.clicked.connect(
            self._on_delete_team
        )


        self.analyze_team_button = QPushButton(
            "Analyser l'équipe",
            self
        )

        self.analyze_team_button.clicked.connect(
            self._on_analyze_team
        )


        teams_actions_row.addWidget(
            self.edit_team_button
        )

        teams_actions_row.addWidget(
            self.delete_team_button
        )

        teams_actions_row.addWidget(
            self.analyze_team_button
        )


        layout.addLayout(
            teams_actions_row
        )



    # =====================================================
    # Chargement matchs
    # =====================================================

    def _load_games(self) -> None:

        self.games_list.clear()


        games = self.database.get_games()


        if not games:

            placeholder = QListWidgetItem(
                "Aucun match enregistré pour l'instant."
            )

            placeholder.setFlags(
                Qt.ItemFlag.NoItemFlags
            )

            self.games_list.addItem(
                placeholder
            )

            return



        for game in games:

            item = QListWidgetItem(
                f"{game.name}  —  {game.date}"
            )


            item.setData(
                Qt.ItemDataRole.UserRole,
                game.id
            )


            self.games_list.addItem(
                item
            )



    # =====================================================
    # Chargement équipes
    # =====================================================

    def _load_teams(self) -> None:

        self.teams_list.clear()


        teams = self.database.get_teams()


        if not teams:

            placeholder = QListWidgetItem(
                "Aucune équipe enregistrée pour l'instant."
            )

            placeholder.setFlags(
                Qt.ItemFlag.NoItemFlags
            )

            self.teams_list.addItem(
                placeholder
            )

            return



        for team in teams:

            item = QListWidgetItem(
                team.name
            )


            item.setData(
                Qt.ItemDataRole.UserRole,
                team.id
            )


            self.teams_list.addItem(
                item
            )



    # =====================================================
    # Actions matchs
    # =====================================================

    def _on_new_game(self) -> None:

        from ui.setup.setup_window import SetupWindow


        self.setup_window = SetupWindow(
            self.database
        )


        self.setup_window.show()


        # On cache seulement pour pouvoir revenir plus tard
        self.hide()



    def _on_open_selected(self) -> None:

        item = self.games_list.currentItem()


        game_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )


        if game_id is None:

            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez un match dans la liste."
            )

            return



        from ui.analysis.analysis_window import AnalysisWindow


        self.analysis_window = AnalysisWindow(
            self.database,
            game_id,
            self
        )


        self.analysis_window.show()


        # Important :
        # on garde la fenêtre en mémoire
        # pour pouvoir revenir dessus
        self.hide()



    def _on_delete_game(self) -> None:

        item = self.games_list.currentItem()


        game_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )


        if game_id is None:

            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez un match dans la liste."
            )

            return



        reply = QMessageBox.question(
            self,
            "Supprimer le match",
            "Supprimer définitivement ce match ainsi que tous ses "
            "événements enregistrés ? Cette action est irréversible."
        )


        if reply != QMessageBox.StandardButton.Yes:

            return



        self.database.delete_game(
            game_id
        )


        self._load_games()



    # =====================================================
    # Actions équipes
    # =====================================================

    def _on_view_team(self) -> None:

        item = self.teams_list.currentItem()


        team_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )


        if team_id is None:

            return



        dialog = TeamDetailsDialog(
            self.database,
            team_id,
            self
        )


        dialog.exec()


    def _on_edit_team(self) -> None:

        item = self.teams_list.currentItem()

        team_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )

        if team_id is None:

            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez une équipe dans la liste."
            )

            return

        team = self.database.get_team(team_id)

        if team is None:

            return

        from ui.setup.team_edit_dialog import TeamEditDialog

        dialog = TeamEditDialog(team, self)

        if dialog.exec() != TeamEditDialog.DialogCode.Accepted:

            return

        name = dialog.team_name()

        if not name:

            QMessageBox.warning(
                self,
                "Nom invalide",
                "Le nom de l'équipe ne peut pas être vide."
            )

            return

        self.database.update_team(
            team_id,
            name,
            dialog.team_color()
        )

        self._load_teams()
        self._load_games()


    def _on_analyze_team(self) -> None:

        item = self.teams_list.currentItem()

        team_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )

        if team_id is None:

            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez une équipe dans la liste."
            )

            return

        from ui.analysis.team_analysis_window import TeamAnalysisWindow

        self.team_analysis_window = TeamAnalysisWindow(
            self.database,
            team_id,
            self
        )

        self.team_analysis_window.show()

    def _on_delete_team(self) -> None:

        item = self.teams_list.currentItem()


        team_id = (
            item.data(
                Qt.ItemDataRole.UserRole
            )
            if item is not None
            else None
        )


        if team_id is None:

            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez une équipe dans la liste."
            )

            return



        reply = QMessageBox.question(
            self,
            "Supprimer l'équipe",
            "Supprimer définitivement cette équipe ainsi que ses "
            "joueuses ? Les matchs associés ne seront pas supprimés, "
            "mais perdront cette équipe. Cette action est irréversible."
        )


        if reply != QMessageBox.StandardButton.Yes:

            return



        self.database.delete_team(
            team_id
        )


        self._load_teams()


        # Les matchs affichés peuvent référencer l'équipe supprimée
        self._load_games()
