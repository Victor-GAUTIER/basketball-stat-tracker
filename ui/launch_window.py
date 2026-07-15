"""Fenêtre de lancement de l'application.

Première fenêtre affichée : permet de créer un nouveau match ou de rouvrir
un match déjà enregistré en base (équipes, joueurs et événements associés
sont conservés d'une session à l'autre grâce à SQLite).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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


class LaunchWindow(QMainWindow):
    """Écran d'accueil : nouveau match, ou reprise d'un match existant."""

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        # Références gardées pour éviter que les fenêtres ouvertes ensuite
        # ne soient détruites par le garbage collector.
        self.setup_window: Optional[QWidget] = None
        self.analysis_window: Optional[QWidget] = None

        self.setWindowTitle("Basketball Stat Tracker")
        self.resize(600, 520)

        self._build_ui()
        self._load_games()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Basketball Stat Tracker", self)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.new_game_button = QPushButton("+ Nouveau match", self)
        self.new_game_button.setMinimumHeight(42)
        self.new_game_button.clicked.connect(self._on_new_game)
        layout.addWidget(self.new_game_button)

        layout.addWidget(QLabel("Matchs déjà enregistrés :", self))

        self.games_list = QListWidget(self)
        self.games_list.itemDoubleClicked.connect(lambda _item: self._on_open_selected())
        layout.addWidget(self.games_list, stretch=1)

        actions_row = QHBoxLayout()
        self.open_button = QPushButton("Ouvrir la sélection", self)
        self.open_button.clicked.connect(self._on_open_selected)
        self.refresh_button = QPushButton("Actualiser la liste", self)
        self.refresh_button.clicked.connect(self._load_games)
        actions_row.addWidget(self.open_button)
        actions_row.addWidget(self.refresh_button)
        layout.addLayout(actions_row)

    # ------------------------------------------------------------------
    # Chargement des matchs enregistrés
    # ------------------------------------------------------------------
    def _load_games(self) -> None:
        self.games_list.clear()
        games = self.database.get_games()
        if not games:
            placeholder = QListWidgetItem("Aucun match enregistré pour l'instant.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.games_list.addItem(placeholder)
            return
        for game in games:
            item = QListWidgetItem(f"{game.name}  —  {game.date}")
            item.setData(Qt.ItemDataRole.UserRole, game.id)
            self.games_list.addItem(item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_new_game(self) -> None:
        # Import différé pour éviter toute dépendance circulaire au chargement du module.
        from ui.setup.setup_window import SetupWindow

        self.setup_window = SetupWindow(self.database)
        self.setup_window.show()
        self.close()

    def _on_open_selected(self) -> None:
        item = self.games_list.currentItem()
        game_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if game_id is None:
            QMessageBox.information(
                self, "Aucune sélection", "Sélectionnez un match dans la liste."
            )
            return

        from ui.analysis.analysis_window import AnalysisWindow

        self.analysis_window = AnalysisWindow(self.database, game_id)
        self.analysis_window.show()
        self.close()
