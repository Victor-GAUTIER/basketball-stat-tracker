"""Fenêtre principale d'analyse vidéo d'un match."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controller.analysis_controller import AnalysisController

from data.database import Database
from data.models import Player

from export.csv_export import export_events_to_csv

from ui.analysis.video_panel import VideoPanel
from ui.analysis.player_panel import PlayerPanel
from ui.analysis.event_panel import EventPanel, EVENT_TYPES
from ui.analysis.recent_events_panel import RecentEventsPanel
from ui.analysis.stats_panel import StatsPanel
from ui.launch_window import LaunchWindow



class AnalysisWindow(QMainWindow):

    def __init__(
        self,
        database: Database,
        game_id: int,
        launch_window=None
    ):

        super().__init__()


        self.database = database
        self.launch_window = launch_window

        self.controller = AnalysisController(
            database,
            game_id
        )


        self._all_players: List[Player] = []

        self._shortcuts = []


        game = self.controller.get_game()

        self.setWindowTitle(
            f"Analyse - {game.name}"
            if game
            else "Analyse du match"
        )


        self.resize(
            1400,
            850
        )


        self._build_ui()

        self._create_menu()

        self._register_shortcuts()

        self._load_game_data()


        self.setStatusBar(
            QStatusBar(self)
        )



    # =====================================================
    # Construction UI
    # =====================================================

    def _build_ui(self):

        central = QWidget(
            self
        )

        self.setCentralWidget(
            central
        )


        layout = QVBoxLayout(
            central
        )


        self.tabs = QTabWidget(
            self
        )


        # ==============================
        # ONGLET ANALYSE
        # ==============================

        analysis_tab = QWidget()

        analysis_layout = QHBoxLayout(
            analysis_tab
        )


        main_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )



        # ------------------------------
        # Partie vidéo + derniers events
        # ------------------------------

        video_container = QWidget()

        video_layout = QVBoxLayout(
            video_container
        )


        self.video_panel = VideoPanel(
            self
        )


        self.recent_events_panel = RecentEventsPanel(
            self
        )


        video_layout.addWidget(
            self.video_panel,
            stretch=8
        )


        video_layout.addWidget(
            QLabel(
                "Derniers événements :"
            )
        )


        video_layout.addWidget(
            self.recent_events_panel,
            stretch=1
        )


        main_splitter.addWidget(
            video_container
        )



        # ------------------------------
        # Partie droite
        # ------------------------------

        right_widget = QWidget()

        right_layout = QVBoxLayout(
            right_widget
        )


        self.player_panel = PlayerPanel(
            self
        )


        self.selected_player_label = QLabel(
            "Aucun joueur sélectionné"
        )

        self.selected_player_label.setStyleSheet(
            "font-weight:bold;"
        )



        self.event_panel = EventPanel(
            self
        )



        buttons_layout = QHBoxLayout()


        self.undo_button = QPushButton(
            "Annuler"
        )


        self.undo_button.clicked.connect(
            self._on_undo_event
        )



        self.export_button = QPushButton(
            "Exporter CSV"
        )


        self.export_button.clicked.connect(
            self._on_export_csv
        )


        buttons_layout.addWidget(
            self.undo_button
        )


        buttons_layout.addWidget(
            self.export_button
        )



        right_layout.addWidget(
            self.player_panel,
            stretch=2
        )


        right_layout.addWidget(
            self.selected_player_label
        )



        right_layout.addWidget(
            self.event_panel
        )


        right_layout.addLayout(
            buttons_layout
        )



        main_splitter.addWidget(
            right_widget
        )


        main_splitter.setStretchFactor(
            0,
            3
        )


        main_splitter.setStretchFactor(
            1,
            1
        )


        analysis_layout.addWidget(
            main_splitter
        )



        # ==============================
        # ONGLET STATS
        # ==============================

        stats_tab = QWidget()

        stats_layout = QVBoxLayout(
            stats_tab
        )


        self.stats_panel = StatsPanel(
            stats_tab
        )


        stats_layout.addWidget(
            self.stats_panel
        )



        self.tabs.addTab(
            analysis_tab,
            "Analyse"
        )


        self.tabs.addTab(
            stats_tab,
            "Statistiques"
        )


        layout.addWidget(
            self.tabs
        )



        self.player_panel.player_selected.connect(
            self._on_player_selected
        )


        self.event_panel.event_triggered.connect(
            self._on_event_triggered
        )

    # =====================================================
    # Menu
    # =====================================================

    def _create_menu(self):

        menu_bar = self.menuBar()


        options_menu = menu_bar.addMenu(
            "Options"
        )


        # -------------------------
        # Changer quart-temps
        # -------------------------

        quarter_menu = options_menu.addMenu(
            "Changer de quart-temps"
        )


        quarters = [
            ("Quart-temps 1", 1),
            ("Quart-temps 2", 2),
            ("Quart-temps 3", 3),
            ("Quart-temps 4", 4),
            ("Prolongation", 5),
        ]


        for text, value in quarters:

            action = QAction(
                text,
                self
            )


            action.triggered.connect(
                lambda checked=False, q=value:
                self._change_quarter(q)
            )


            quarter_menu.addAction(
                action
            )



        # -------------------------
        # Changer de match
        # -------------------------

        change_game = QAction(
            "Changer de match",
            self
        )


        change_game.triggered.connect(
            self._change_game
        )


        options_menu.addAction(
            change_game
        )



    def _change_quarter(
        self,
        quarter: int
    ):

        self.controller.set_quarter(
            quarter
        )


        self.quarter_combo.setCurrentIndex(
            quarter - 1
        )


        self.statusBar().showMessage(
            f"Quart-temps {quarter}",
            3000
        )



    def _change_game(self):

        reply = QMessageBox.question(
            self,
            "Changer de match",
            "Retourner à la sélection des matchs ?"
        )


        if reply == QMessageBox.StandardButton.Yes:

            if self.launch_window:

                self.launch_window.show()
                self.launch_window.raise_()
                self.launch_window.activateWindow()
                self.launch_window._load_games()


            self.close()

    # =====================================================
    # Raccourcis clavier
    # =====================================================

    def _register_shortcuts(self):

        shortcuts = [
            # Vidéo
            (
                "Space",
                self.video_panel.toggle_play_pause
            ),

            (
                "Left",
                lambda: self.video_panel.seek_relative(-5000)
            ),

            (
                "Right",
                lambda: self.video_panel.seek_relative(5000)
            ),

            # Événements
            *[
                (
                    key,
                    lambda c=code: self._on_event_triggered(c)
                )
                for code, label, key in EVENT_TYPES
            ],

            # Actions
            (
                "Ctrl+Z",
                self._on_undo_event
            ),

            (
                "Ctrl+E",
                self._on_export_csv
            ),
        ]


        for key, callback in shortcuts:

            shortcut = QShortcut(
                QKeySequence(key),
                self
            )


            shortcut.setContext(
                Qt.ShortcutContext.ApplicationShortcut
            )


            shortcut.activated.connect(
                callback
            )


            self._shortcuts.append(
                shortcut
            )


    # =====================================================
    # Chargement
    # =====================================================

    def _load_game_data(self):

        game = self.controller.get_game()


        if game is None:

            QMessageBox.critical(
                self,
                "Erreur",
                "Match introuvable."
            )

            return



        self.video_panel.load_video(
            game.video_path
        )


        teams = self.controller.get_teams()


        home = next(
            (
                t for t, is_home in teams
                if is_home
            ),
            None
        )


        away = next(
            (
                t for t, is_home in teams
                if not is_home
            ),
            None
        )


        home_players = (
            self.controller.get_players_for_team(home.id)
            if home
            else []
        )


        away_players = (
            self.controller.get_players_for_team(away.id)
            if away
            else []
        )


        self.player_panel.set_teams(
            home.name if home else "Equipe A",
            home_players,
            away.name if away else "Equipe B",
            away_players
        )


        self._all_players = (
            home_players +
            away_players
        )


        self._refresh_data()



    # =====================================================
    # Actions
    # =====================================================

    def _on_player_selected(
        self,
        player_id: int
    ):

        player = self.database.get_player(
            player_id
        )


        if player:

            self.selected_player_label.setText(
                f"Joueur sélectionné : #{player.number} {player.name}"
            )



    def _on_quarter_changed(
        self,
        index: int
    ):

        self.controller.set_quarter(
            index + 1
        )



    def _on_event_triggered(
        self,
        event_code: str
    ):

        player_id = (
            self.player_panel.selected_player_id()
        )


        if player_id is None:

            return


        self.controller.record_event(
            player_id,
            self.video_panel.current_timestamp(),
            event_code
        )


        self._refresh_data()



    def _on_undo_event(self):

        self.controller.undo_last_event()

        self._refresh_data()



    def _on_export_csv(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter CSV",
            "evenements.csv",
            "CSV (*.csv)"
        )


        if not path:

            return


        events = self.controller.get_events()


        players = {
            p.id:p
            for p in self._all_players
        }


        export_events_to_csv(
            path,
            events,
            players
        )



    # =====================================================
    # Actualisation
    # =====================================================

    def _refresh_data(self):

        events = self.controller.get_events()


        players = {
            p.id:p
            for p in self._all_players
        }


        self.recent_events_panel.refresh(
            events,
            players
        )


        self.stats_panel.refresh(
            self._all_players,
            self.controller.get_player_stats()
        )
