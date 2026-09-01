"""Fenêtre de préparation du match (SetupWindow).

Permet de saisir les informations générales du match, la vidéo à analyser,
la saison à laquelle rattacher le match (optionnel), ainsi que la
composition des deux équipes, avant de lancer l'analyse.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
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


# Valeur spéciale utilisée dans season_combo pour déclencher la création
# d'une nouvelle saison à la volée.
_NEW_SEASON = "__NEW_SEASON__"


class SetupWindow(QMainWindow):
    """Fenêtre affichée au lancement de l'application, pour préparer un match."""

    def __init__(
        self,
        database: Database,
        initial_season_id: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.database = database
        self.controller = SetupController(database)

        # Saison à présélectionner (ex: le match est créé depuis
        # l'intérieur d'une saison ouverte dans LaunchWindow).
        self._initial_season_id = initial_season_id

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

        self.season_combo = QComboBox(self)
        self.season_combo.currentIndexChanged.connect(self._on_season_combo_changed)
        self._reload_seasons()

        form = QFormLayout()
        form.addRow("Nom du match :", self.match_name_edit)
        form.addRow("Date :", self.match_date_edit)
        form.addRow("Vidéo :", video_row)
        form.addRow("Saison :", self.season_combo)

        main_layout.addLayout(form)

        # --- Composition des équipes ---
        teams_row = QHBoxLayout()
        self.home_team_editor = TeamEditor("Équipe à domicile", self.database, self)
        self.away_team_editor = TeamEditor("Équipe à l'extérieur", self.database, self)
        teams_row.addWidget(self.home_team_editor)
        teams_row.addWidget(self.away_team_editor)

        main_layout.addLayout(teams_row)

        # --- Bouton de lancement ---
        self.start_button = QPushButton("Commencer l'analyse", self)
        self.start_button.setMinimumHeight(42)
        self.start_button.clicked.connect(self._on_start_analysis)
        main_layout.addWidget(self.start_button)

    # ------------------------------------------------------------------
    # Saison
    # ------------------------------------------------------------------
    def _reload_seasons(self) -> None:
        """(Re)construit la liste déroulante des saisons, en essayant de
        conserver la sélection courante (ou self._initial_season_id lors
        du tout premier appel)."""

        previous_data = (
            self.season_combo.currentData()
            if self.season_combo.count() > 0
            else self._initial_season_id
        )

        self.season_combo.blockSignals(True)

        self.season_combo.clear()

        self.season_combo.addItem("Sans saison", None)

        for season in self.database.get_seasons():
            self.season_combo.addItem(season.name, season.id)

        self.season_combo.insertSeparator(self.season_combo.count())

        self.season_combo.addItem("+ Nouvelle saison...", _NEW_SEASON)

        index = self.season_combo.findData(previous_data)
        self.season_combo.setCurrentIndex(index if index >= 0 else 0)

        self.season_combo.blockSignals(False)

    def _on_season_combo_changed(self, _index: int) -> None:

        if self.season_combo.currentData() != _NEW_SEASON:
            return

        name, ok = QInputDialog.getText(
            self, "Nouvelle saison", "Nom (ex: NF2 2025-26) :"
        )

        if not ok or not name.strip():
            # Annulé : retombe sur "Sans saison" plutôt que de laisser
            # l'entrée "+ Nouvelle saison..." sélectionnée.
            self.season_combo.setCurrentIndex(0)
            return

        try:
            new_id = self.database.create_season(name.strip())
        except Exception:
            QMessageBox.warning(
                self, "Nom déjà utilisé", "Une saison porte déjà ce nom."
            )
            self.season_combo.setCurrentIndex(0)
            return

        self._initial_season_id = new_id
        self._reload_seasons()

    def _selected_season_id(self) -> Optional[int]:

        data = self.season_combo.currentData()

        return None if data == _NEW_SEASON else data

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
            home_present_players=self.home_team_editor.present_players(),
            home_color=self.home_team_editor.team_color(),
            away_team_name=self.away_team_editor.team_name(),
            away_players=self.away_team_editor.players(),
            away_present_players=self.away_team_editor.present_players(),
            away_color=self.away_team_editor.team_color(),
            season_id=self._selected_season_id(),
        )

        self._open_analysis_window(game_id)

    def _validate_form(self) -> List[str]:
        errors: List[str] = []
        if not self.match_name_edit.text().strip():
            errors.append("- Le nom du match est requis.")
        if not self.video_path_edit.text().strip():
            errors.append("- Une vidéo doit être sélectionnée.")
        if not self.home_team_editor.is_valid():
            errors.append(
                "- L'équipe à domicile doit avoir un nom et au moins un "
                "joueur présent."
            )
        if not self.away_team_editor.is_valid():
            errors.append(
                "- L'équipe à l'extérieur doit avoir un nom et au moins un "
                "joueur présent."
            )
        return errors

    def _open_analysis_window(self, game_id: int) -> None:
        # Import différé pour éviter toute dépendance circulaire au chargement du module.
        from ui.analysis.analysis_window import AnalysisWindow

        self.analysis_window = AnalysisWindow(self.database, game_id)
        self.analysis_window.show()
        self.close()
