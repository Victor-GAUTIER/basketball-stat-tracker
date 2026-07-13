from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox

from controller import GameController
from data.database import Database
from data.stats import player_summary
from export.csv_export import export_events

from ui.video_panel import VideoPanel
from ui.player_panel import PlayerPanel
from ui.event_panel import EventPanel
from ui.stats_panel import StatsPanel


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Basket Scout")
        self.resize(1300, 800)

        self.db = Database("basket_scout.db")
        self.controller = GameController(self.db)

        self.video_panel = VideoPanel()
        self.player_panel = PlayerPanel()
        self.event_panel = EventPanel()
        self.stats_panel = StatsPanel()

        # -- Connexions --
        self.video_panel.video_loaded.connect(self._on_video_loaded)
        self.player_panel.player_selected.connect(self.controller.set_active_player)
        self.player_panel.player_added.connect(self._on_player_added)
        self.event_panel.event_triggered.connect(self._on_event_triggered)
        self.event_panel.undo_requested.connect(self._on_undo)

        # -- Layout --
        left_column = QVBoxLayout()
        left_column.addWidget(self.video_panel, stretch=3)
        left_column.addWidget(self.stats_panel, stretch=1)

        right_column = QVBoxLayout()
        right_column.addWidget(self.player_panel, stretch=1)
        right_column.addWidget(self.event_panel, stretch=2)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_column, stretch=3)
        main_layout.addLayout(right_column, stretch=1)
        self.setLayout(main_layout)

        self._refresh_players()

    # ---------- Handlers ----------

    def _on_video_loaded(self, path: str):
        self.controller.load_video(path)
        self._refresh_history()
        self._refresh_stats()

    def _on_player_added(self, draft_player):
        self.controller.add_player(draft_player.name, draft_player.number)
        self._refresh_players()

    def _refresh_players(self):
        self.player_panel.set_players(self.controller.get_players())

    def _on_event_triggered(self, event_type: str):
        if not self.player_panel.require_active_player():
            return
        try:
            timestamp = self.video_panel.current_time()
            self.controller.record_event(event_type, timestamp)
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
            return

        self.event_panel.add_history_line(f"{timestamp:.2f}s - {event_type}")
        self._refresh_stats()

    def _on_undo(self):
        self.controller.undo_last_event()
        self._refresh_history()
        self._refresh_stats()

    def _refresh_history(self):
        players = {p.id: p for p in self.controller.get_players()}
        lines = [
            f"{e.timestamp:.2f}s - {players[e.player_id].name} - {e.event_type}"
            for e in self.controller.get_events()
            if e.player_id in players
        ]
        self.event_panel.refresh_history(lines)

    def _refresh_stats(self):
        if self.controller.current_game is None:
            return
        summary = player_summary(self.db, self.controller.current_game.id)
        self.stats_panel.update_stats(summary)

    def export_csv(self):
        if self.controller.current_game is None:
            QMessageBox.warning(self, "Erreur", "Aucune vidéo chargée.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en CSV", "events.csv", "CSV (*.csv)")
        if not path:
            return
        players = {p.id: p for p in self.controller.get_players()}
        export_events(self.controller.get_events(), players, path)

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
