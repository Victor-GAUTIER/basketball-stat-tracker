"""Fenêtre de lancement de l'application.

Première fenêtre affichée : permet de créer un nouveau match ou de rouvrir
un match déjà enregistré en base (équipes, joueurs et événements associés
sont conservés d'une session à l'autre grâce à SQLite).

Les matchs peuvent être groupés par saison (ex: "NF2 2025-26") : la liste
principale affiche d'abord les saisons disponibles (façon dossiers), et
sélectionner une saison affiche la liste des matchs qui lui appartiennent.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from data.database import Database


# Valeur spéciale utilisée dans la liste des "dossiers" pour représenter
# tous les matchs sans distinction de saison (par opposition à None, qui
# signifie ici spécifiquement "les matchs qui n'appartiennent à aucune
# saison").
ALL_GAMES = "__ALL_GAMES__"


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

        # Saison actuellement "ouverte" dans la liste des matchs :
        # None = matchs sans saison, ALL_GAMES = tous les matchs
        # confondus, un id = matchs de cette saison précise.
        self._current_season_id = None


        self.setWindowTitle(
            "Basketball Stat Tracker"
        )

        self.resize(
            600,
            720
        )


        self._build_ui()

        self._load_seasons()

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


        # -------------------------
        # Zone Matchs : deux "pages" empilées (liste des saisons,
        # puis liste des matchs d'une saison choisie).
        # -------------------------

        self.games_section_label = QLabel(
            "Matchs déjà enregistrés :",
            self
        )

        layout.addWidget(
            self.games_section_label
        )


        self.games_stack = QStackedWidget(
            self
        )

        layout.addWidget(
            self.games_stack,
            stretch=1
        )


        self.games_stack.addWidget(
            self._build_seasons_page()
        )

        self.games_stack.addWidget(
            self._build_games_page()
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
    # Page 0 : liste des saisons ("dossiers")
    # =====================================================

    def _build_seasons_page(self) -> QWidget:

        page = QWidget()

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        self.seasons_list = QListWidget(page)

        self.seasons_list.itemDoubleClicked.connect(
            lambda _item:
            self._on_open_season()
        )

        page_layout.addWidget(
            self.seasons_list,
            stretch=1
        )

        seasons_actions_row = QHBoxLayout()

        open_season_btn = QPushButton("Ouvrir")
        open_season_btn.clicked.connect(self._on_open_season)

        new_season_btn = QPushButton("+ Nouvelle saison")
        new_season_btn.clicked.connect(self._on_new_season)

        rename_season_btn = QPushButton("Renommer")
        rename_season_btn.clicked.connect(self._on_rename_season)

        delete_season_btn = QPushButton("Supprimer")
        delete_season_btn.clicked.connect(self._on_delete_season)

        seasons_actions_row.addWidget(open_season_btn)
        seasons_actions_row.addWidget(new_season_btn)
        seasons_actions_row.addWidget(rename_season_btn)
        seasons_actions_row.addWidget(delete_season_btn)

        page_layout.addLayout(seasons_actions_row)

        return page


    # =====================================================
    # Page 1 : liste des matchs d'une saison choisie
    # =====================================================

    def _build_games_page(self) -> QWidget:

        page = QWidget()

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        back_row = QHBoxLayout()

        back_btn = QPushButton("◀ Retour aux saisons")
        back_btn.clicked.connect(self._on_back_to_seasons)

        self.current_season_label = QLabel("")
        self.current_season_label.setStyleSheet("font-weight: bold;")

        back_row.addWidget(back_btn)
        back_row.addWidget(self.current_season_label)
        back_row.addStretch()

        page_layout.addLayout(back_row)

        self.games_list = QListWidget(page)

        self.games_list.itemDoubleClicked.connect(
            lambda _item:
            self._on_open_selected()
        )

        page_layout.addWidget(
            self.games_list,
            stretch=1
        )

        actions_row = QHBoxLayout()

        self.edit_game_button = QPushButton("Modifier le match")
        self.edit_game_button.clicked.connect(self._on_edit_game)

        self.change_season_button = QPushButton("Changer de saison")
        self.change_season_button.clicked.connect(self._on_change_game_season)

        self.delete_game_button = QPushButton("Supprimer le match")
        self.delete_game_button.clicked.connect(self._on_delete_game)

        actions_row.addWidget(self.edit_game_button)
        actions_row.addWidget(self.change_season_button)
        actions_row.addWidget(self.delete_game_button)

        page_layout.addLayout(actions_row)

        return page


    # =====================================================
    # Navigation saisons <-> matchs
    # =====================================================

    def _load_seasons(self) -> None:

        self.seasons_list.clear()

        # Entrées spéciales toujours présentes en tête de liste.
        all_item = QListWidgetItem(
            f"📁 Tous les matchs ({len(self.database.get_games())})"
        )
        all_item.setData(Qt.ItemDataRole.UserRole, ALL_GAMES)
        self.seasons_list.addItem(all_item)

        no_season_count = len(self.database.get_games_by_season(None))
        no_season_item = QListWidgetItem(
            f"📁 Sans saison ({no_season_count})"
        )
        no_season_item.setData(Qt.ItemDataRole.UserRole, None)
        self.seasons_list.addItem(no_season_item)

        for season in self.database.get_seasons():

            count = self.database.count_games_in_season(season.id)

            item = QListWidgetItem(
                f"📁 {season.name} ({count})"
            )
            item.setData(Qt.ItemDataRole.UserRole, season.id)

            self.seasons_list.addItem(item)

        self.games_stack.setCurrentIndex(0)

    def _on_open_season(self) -> None:

        item = self.seasons_list.currentItem()

        if item is None:
            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez une saison (ou \"Tous les matchs\")."
            )
            return

        self._current_season_id = item.data(Qt.ItemDataRole.UserRole)

        self.current_season_label.setText(
            item.text().replace("📁 ", "")
        )

        self._load_games()

        self.games_stack.setCurrentIndex(1)

    def _on_back_to_seasons(self) -> None:

        self._load_seasons()


    # =====================================================
    # Gestion des saisons
    # =====================================================

    def _on_new_season(self) -> None:

        name, ok = QInputDialog.getText(
            self, "Nouvelle saison", "Nom (ex: NF2 2025-26) :"
        )

        if not ok or not name.strip():
            return

        try:
            self.database.create_season(name.strip())
        except Exception:
            QMessageBox.warning(
                self,
                "Nom déjà utilisé",
                "Une saison porte déjà ce nom."
            )
            return

        self._load_seasons()

    def _on_rename_season(self) -> None:

        item = self.seasons_list.currentItem()

        season_id = item.data(Qt.ItemDataRole.UserRole) if item else None

        if season_id in (None, ALL_GAMES):
            QMessageBox.information(
                self,
                "Sélection invalide",
                "Sélectionnez une saison existante (pas \"Tous les "
                "matchs\" ni \"Sans saison\")."
            )
            return

        current_name = item.text().split(" (")[0].replace("📁 ", "")

        name, ok = QInputDialog.getText(
            self, "Renommer la saison", "Nouveau nom :", text=current_name
        )

        if not ok or not name.strip():
            return

        self.database.rename_season(season_id, name.strip())

        self._load_seasons()

    def _on_delete_season(self) -> None:

        item = self.seasons_list.currentItem()

        season_id = item.data(Qt.ItemDataRole.UserRole) if item else None

        if season_id in (None, ALL_GAMES):
            QMessageBox.information(
                self,
                "Sélection invalide",
                "Sélectionnez une saison existante (pas \"Tous les "
                "matchs\" ni \"Sans saison\")."
            )
            return

        reply = QMessageBox.question(
            self,
            "Supprimer la saison",
            "Supprimer cette saison ? Les matchs qu'elle contient ne "
            "seront pas supprimés : ils redeviendront simplement "
            "\"Sans saison\"."
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.database.delete_season(season_id)

        self._load_seasons()


    # =====================================================
    # Chargement matchs (scope = self._current_season_id)
    # =====================================================

    def _load_games(self) -> None:

        self.games_list.clear()


        if self._current_season_id == ALL_GAMES:
            games = self.database.get_games()
        else:
            games = self.database.get_games_by_season(self._current_season_id)


        if not games:

            placeholder = QListWidgetItem(
                "Aucun match dans cette saison pour l'instant."
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



    def _on_edit_game(self) -> None:

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


        game = self.database.get_game(
            game_id
        )


        if game is None:

            return


        from ui.setup.game_edit_dialog import EditGameDialog


        dialog = EditGameDialog(
            self.database,
            game,
            self
        )


        if dialog.exec() != EditGameDialog.DialogCode.Accepted:

            return


        self._load_games()


    def _on_change_game_season(self) -> None:

        item = self.games_list.currentItem()

        game_id = (
            item.data(Qt.ItemDataRole.UserRole)
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

        seasons = self.database.get_seasons()

        options = ["Sans saison"] + [s.name for s in seasons]

        current_season = self.database.get_season_for_game(game_id)
        current_index = 0
        if current_season is not None:
            for i, s in enumerate(seasons, start=1):
                if s.id == current_season.id:
                    current_index = i
                    break

        choice, ok = QInputDialog.getItem(
            self,
            "Changer de saison",
            "Nouvelle saison pour ce match :",
            options,
            current_index,
            editable=False,
        )

        if not ok:
            return

        if choice == "Sans saison":
            self.database.set_game_season(game_id, None)
        else:
            season_id = next(
                (s.id for s in seasons if s.name == choice), None
            )
            self.database.set_game_season(game_id, season_id)

        self._load_games()



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
