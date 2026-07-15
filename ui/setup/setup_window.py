"""Fenêtre de préparation du match (SetupWindow).

Permet de saisir les informations générales du match, la vidéo à analyser,
ainsi que la composition des deux équipes, avant de lancer l'analyse.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from controller.setup_controller import SetupController
from data.database import Database
from ui.setup.team_editor import TeamEditor


class SetupWindow(QMainWindow):
    """Fenêtre affichée au lancement de l'application, pour préparer un match."""

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.controller = SetupController(database)
        # Référence gardée pour empêcher la fenêtre d'analyse d'être détruite
        # par le garbage collector Python une fois SetupWindow fermée.
        self.analysis_window: Optional[QWidget] = None

        self.setWindowTitle("Préparation du match - Basketball Stat Tracker")
        self.resize(950, 680)

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        # --- Informations générales du match ---
        self.match_name_edit = QLineEdit(self)
        self.match_name_edit.setPlaceholderText("Ex : Finale Coupe de France")

        self.match_date_edit = QDateEdit(self)
        self.match_date_edit.setCalendarPopup(True)
        self.match_date_edit.setDate(QDate.currentDate())

        self.video_path_edit = QLineEdit(self)
        self.video_path_edit.setReadOnly(True)
        browse_button = QPushButton("Parcourir...", self)
        browse_button.clicked.connect(self._on_browse_video)

        video_row = QHBoxLayout()
        video_row.addWidget(self.video_path_edit)
        video_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Nom du match :", self.match_name_edit)
        form.addRow("Date :", self.match_date_edit)
        form.addRow("Vidéo :", video_row)

        main_layout.addLayout(form)

        # --- Composition des équipes ---
        teams_row = QHBoxLayout()
        self.home_team_editor = TeamEditor("Équipe à domicile", self)
        self.away_team_editor = TeamEditor("Équipe à l'extérieur", self)
        teams_row.addWidget(self.home_team_editor)
        teams_row.addWidget(self.away_team_editor)

        main_layout.addLayout(teams_row)

        # --- Bouton de lancement ---
        self.start_button = QPushButton("Commencer l'analyse", self)
        self.start_button.setMinimumHeight(42)
        self.start_button.clicked.connect(self._on_start_analysis)
        main_layout.addWidget(self.start_button)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner la vidéo du match",
            "",
            "Fichiers vidéo (*.mp4 *.avi *.mov *.mkv);;Tous les fichiers (*)",
        )
        if path:
            self.video_path_edit.setText(path)

    def _on_start_analysis(self) -> None:
        errors = self._validate_form()
        if errors:
            QMessageBox.warning(self, "Formulaire incomplet", "\n".join(errors))
            return

        game_id = self.controller.start_analysis(
            game_name=self.match_name_edit.text().strip(),
            game_date=self.match_date_edit.date().toString("yyyy-MM-dd"),
            video_path=self.video_path_edit.text().strip(),
            home_team_name=self.home_team_editor.team_name(),
            home_players=self.home_team_editor.players(),
            away_team_name=self.away_team_editor.team_name(),
            away_players=self.away_team_editor.players(),
        )

        self._open_analysis_window(game_id)

    def _validate_form(self) -> List[str]:
        errors: List[str] = []
        if not self.match_name_edit.text().strip():
            errors.append("- Le nom du match est requis.")
        if not self.video_path_edit.text().strip():
            errors.append("- Une vidéo doit être sélectionnée.")
        if not self.home_team_editor.is_valid():
            errors.append("- L'équipe à domicile doit avoir un nom et au moins un joueur.")
        if not self.away_team_editor.is_valid():
            errors.append("- L'équipe à l'extérieur doit avoir un nom et au moins un joueur.")
        return errors

    def _open_analysis_window(self, game_id: int) -> None:
        # Import différé pour éviter toute dépendance circulaire au chargement du module.
        from ui.analysis.analysis_window import AnalysisWindow

        self.analysis_window = AnalysisWindow(self.database, game_id)
        self.analysis_window.show()
        self.close()
