"""Fenêtre principale d'analyse vidéo d'un match.

Assemble le lecteur vidéo, les listes de joueurs, le panneau d'événements et
le tableau de statistiques. C'est ici que les clics utilisateur sont
transformés en événements horodatés, enregistrés via AnalysisController.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from controller.analysis_controller import AnalysisController
from data.database import Database
from data.models import Player
from export.csv_export import export_events_to_csv
from ui.analysis.event_panel import EventPanel
from ui.analysis.player_panel import PlayerPanel
from ui.analysis.stats_panel import StatsPanel
from ui.analysis.video_panel import VideoPanel


class AnalysisWindow(QMainWindow):
    """Fenêtre d'enregistrement des événements pendant le visionnage du match."""

    def __init__(self, database: Database, game_id: int) -> None:
        super().__init__()
        self.database = database
        self.controller = AnalysisController(database, game_id)

        self.home_team = None
        self.away_team = None
        self._all_players: List[Player] = []

        game = self.controller.get_game()
        title = f"Analyse - {game.name}" if game else "Analyse du match"
        self.setWindowTitle(title)
        self.resize(1350, 820)

        self._build_ui()
        self._load_game_data()

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Sélectionnez un joueur, puis un événement.")

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # --- Colonne gauche : vidéo ---
        self.video_panel = VideoPanel(self)
        splitter.addWidget(self.video_panel)

        # --- Colonne droite : joueurs + événements + stats ---
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)

        self.player_panel = PlayerPanel(self)
        self.selected_player_label = QLabel("Aucun joueur sélectionné", self)
        self.selected_player_label.setStyleSheet("font-weight: bold;")

        quarter_row = QHBoxLayout()
        quarter_row.addWidget(QLabel("Quart-temps :", self))
        self.quarter_combo = QComboBox(self)
        self.quarter_combo.addItems(["1", "2", "3", "4", "Prolongation"])
        self.quarter_combo.currentIndexChanged.connect(self._on_quarter_changed)
        quarter_row.addWidget(self.quarter_combo)
        quarter_row.addStretch(1)

        self.event_panel = EventPanel(self)

        actions_row = QHBoxLayout()
        self.undo_button = QPushButton("Annuler le dernier événement", self)
        self.undo_button.clicked.connect(self._on_undo_event)
        self.export_button = QPushButton("Exporter en CSV", self)
        self.export_button.clicked.connect(self._on_export_csv)
        actions_row.addWidget(self.undo_button)
        actions_row.addWidget(self.export_button)

        self.stats_panel = StatsPanel(self)

        right_layout.addWidget(self.player_panel, stretch=2)
        right_layout.addWidget(self.selected_player_label)
        right_layout.addLayout(quarter_row)
        right_layout.addWidget(self.event_panel)
        right_layout.addLayout(actions_row)
        right_layout.addWidget(self.stats_panel, stretch=2)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        self.player_panel.player_selected.connect(self._on_player_selected)
        self.event_panel.event_triggered.connect(self._on_event_triggered)

    # ------------------------------------------------------------------
    # Chargement des données du match
    # ------------------------------------------------------------------
    def _load_game_data(self) -> None:
        game = self.controller.get_game()
        if game is None:
            QMessageBox.critical(self, "Erreur", "Match introuvable en base de données.")
            return

        self.video_panel.load_video(game.video_path)

        teams = self.controller.get_teams()
        home = next((t for t, is_home in teams if is_home), None)
        away = next((t for t, is_home in teams if not is_home), None)

        self.home_team = home
        self.away_team = away

        home_players = self.controller.get_players_for_team(home.id) if home else []
        away_players = self.controller.get_players_for_team(away.id) if away else []

        self.player_panel.set_teams(
            home.name if home else "Équipe A",
            home_players,
            away.name if away else "Équipe B",
            away_players,
        )

        self._all_players = home_players + away_players
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_player_selected(self, player_id: int) -> None:
        player = self.database.get_player(player_id)
        if player is not None:
            self.selected_player_label.setText(
                f"Joueur sélectionné : #{player.number} {player.name}"
            )

    def _on_quarter_changed(self, index: int) -> None:
        # L'index 0 correspond au quart-temps 1, ... l'index 4 à la prolongation (5).
        self.controller.set_quarter(index + 1)

    def _on_event_triggered(self, event_code: str) -> None:
        player_id = self.player_panel.selected_player_id()
        if player_id is None:
            QMessageBox.information(
                self, "Aucun joueur sélectionné", "Veuillez d'abord sélectionner un joueur."
            )
            return

        timestamp = self.video_panel.current_timestamp()
        self.controller.record_event(player_id, timestamp, event_code)
        self.statusBar().showMessage(
            f"Événement '{event_code}' enregistré à {timestamp:.1f}s", 3000
        )
        self._refresh_stats()

    def _on_undo_event(self) -> None:
        removed = self.controller.undo_last_event()
        if removed is None:
            self.statusBar().showMessage("Aucun événement à annuler.", 3000)
        else:
            self.statusBar().showMessage("Dernier événement annulé.", 3000)
            self._refresh_stats()

    def _on_export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter les événements en CSV", "evenements.csv", "CSV (*.csv)"
        )
        if not path:
            return

        events = self.controller.get_events()
        players_by_id = {p.id: p for p in self._all_players}
        export_events_to_csv(path, events, players_by_id)
        self.statusBar().showMessage(f"Export CSV effectué : {path}", 5000)

    # ------------------------------------------------------------------
    # Rafraîchissement
    # ------------------------------------------------------------------
    def _refresh_stats(self) -> None:
        stats = self.controller.get_player_stats()
        self.stats_panel.refresh(self._all_players, stats)
