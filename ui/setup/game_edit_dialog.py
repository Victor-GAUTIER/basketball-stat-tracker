"""Dialogue de modification d'un match déjà enregistré.

Regroupe en un seul endroit ce qu'on doit pouvoir corriger après coup sur
un match : nom, date, chemin de la vidéo, couleurs des deux équipes, et
joueuses présentes (via le dialogue déjà utilisé pendant l'analyse,
ui.analysis.game_players_dialog.GamePlayersDialog).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Tuple

from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data.database import Database
from data.models import Game


DEFAULT_HOME_COLOR = "#297ffe"
DEFAULT_AWAY_COLOR = "#e67e22"


class EditGameDialog(QDialog):
    """Permet de modifier les informations générales d'un match, les
    couleurs des deux équipes, et d'ouvrir la gestion des joueuses
    présentes."""

    def __init__(
        self,
        database: Database,
        game: Game,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.database = database
        self.game = game

        self.setWindowTitle("Modifier le match")
        self.setMinimumWidth(420)

        teams = database.get_game_teams(game.id)
        self.home_team = next((t for t, is_home in teams if is_home), None)
        self.away_team = next((t for t, is_home in teams if not is_home), None)

        self._home_color = self.home_team.color if self.home_team else DEFAULT_HOME_COLOR
        self._away_color = self.away_team.color if self.away_team else DEFAULT_AWAY_COLOR

        layout = QVBoxLayout(self)

        # -------------------------
        # Informations générales
        # -------------------------

        self.name_edit = QLineEdit(game.name, self)

        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)

        parsed_date = QDate.fromString(game.date, "yyyy-MM-dd")
        self.date_edit.setDate(
            parsed_date if parsed_date.isValid() else QDate.currentDate()
        )

        self.video_path_edit = QLineEdit(game.video_path, self)
        self.video_path_edit.setReadOnly(True)

        browse_button = QPushButton("Parcourir...", self)
        browse_button.clicked.connect(self._on_browse_video)

        video_row = QHBoxLayout()
        video_row.addWidget(self.video_path_edit)
        video_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Nom du match :", self.name_edit)
        form.addRow("Date :", self.date_edit)
        form.addRow("Vidéo :", video_row)

        layout.addLayout(form)

        # -------------------------
        # Couleurs des équipes
        # -------------------------

        colors_form = QFormLayout()

        self.home_swatch, home_color_row = self._build_color_row(
            self._home_color, self._on_pick_home_color
        )
        self.away_swatch, away_color_row = self._build_color_row(
            self._away_color, self._on_pick_away_color
        )

        colors_form.addRow(
            f"Couleur {self.home_team.name if self.home_team else 'domicile'} :",
            home_color_row,
        )
        colors_form.addRow(
            f"Couleur {self.away_team.name if self.away_team else 'extérieur'} :",
            away_color_row,
        )

        layout.addLayout(colors_form)

        # -------------------------
        # Joueuses présentes
        # -------------------------

        players_button = QPushButton("Joueuses présentes...", self)
        players_button.clicked.connect(self._on_edit_players)
        layout.addWidget(players_button)

        # -------------------------
        # Boutons
        # -------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Couleurs
    # ------------------------------------------------------------------
    def _build_color_row(
        self, color: str, on_pick
    ) -> Tuple[QLabel, QHBoxLayout]:

        swatch = QLabel(self)
        swatch.setFixedSize(24, 24)
        swatch.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")

        button = QPushButton("Couleur...", self)
        button.clicked.connect(on_pick)

        row = QHBoxLayout()
        row.addWidget(swatch)
        row.addWidget(button)
        row.addStretch(1)

        return swatch, row

    def _on_pick_home_color(self) -> None:

        color = QColorDialog.getColor(
            QColor(self._home_color), self, "Couleur de l'équipe à domicile"
        )

        if color.isValid():
            self._home_color = color.name()
            self.home_swatch.setStyleSheet(
                f"background-color: {self._home_color}; border: 1px solid #888;"
            )

    def _on_pick_away_color(self) -> None:

        color = QColorDialog.getColor(
            QColor(self._away_color), self, "Couleur de l'équipe à l'extérieur"
        )

        if color.isValid():
            self._away_color = color.name()
            self.away_swatch.setStyleSheet(
                f"background-color: {self._away_color}; border: 1px solid #888;"
            )

    # ------------------------------------------------------------------
    # Vidéo
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

    # ------------------------------------------------------------------
    # Joueuses présentes
    # ------------------------------------------------------------------
    def _on_edit_players(self) -> None:

        # Import différé : évite toute dépendance circulaire au chargement
        # du module (ui.analysis importe lui aussi des choses côté setup).
        from ui.analysis.game_players_dialog import GamePlayersDialog

        home_roster = (
            self.database.get_players_by_team(self.home_team.id)
            if self.home_team
            else []
        )

        away_roster = (
            self.database.get_players_by_team(self.away_team.id)
            if self.away_team
            else []
        )

        home_present = (
            self.database.get_game_players(self.game.id, self.home_team.id)
            if self.home_team
            else []
        )

        away_present = (
            self.database.get_game_players(self.game.id, self.away_team.id)
            if self.away_team
            else []
        )

        # Pré-remplit le numéro affiché avec celui déjà utilisé pour CE
        # match, sinon le numéro par défaut de l'équipe (même logique que
        # AnalysisWindow._on_edit_game_players).
        home_match_numbers = {p.id: p.number for p in home_present}
        away_match_numbers = {p.id: p.number for p in away_present}

        home_roster = [
            replace(p, number=home_match_numbers.get(p.id, p.number))
            for p in home_roster
        ]
        away_roster = [
            replace(p, number=away_match_numbers.get(p.id, p.number))
            for p in away_roster
        ]

        dialog = GamePlayersDialog(
            self.home_team.name if self.home_team else "Domicile",
            home_roster,
            [p.id for p in home_present],
            self.away_team.name if self.away_team else "Extérieur",
            away_roster,
            [p.id for p in away_present],
            self,
        )

        if dialog.exec() != GamePlayersDialog.DialogCode.Accepted:
            return

        self.database.set_game_players(
            self.game.id,
            dialog.present_player_ids(),
            dialog.present_player_numbers(),
        )

        QMessageBox.information(
            self, "Joueuses présentes", "Mise à jour effectuée."
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _on_accept(self) -> None:

        name = self.name_edit.text().strip()
        video_path = self.video_path_edit.text().strip()

        if not name:
            QMessageBox.warning(
                self, "Nom invalide", "Le nom du match ne peut pas être vide."
            )
            return

        self.database.update_game(
            self.game.id,
            name,
            self.date_edit.date().toString("yyyy-MM-dd"),
            video_path,
        )

        if self.home_team:
            self.database.update_team(
                self.home_team.id, self.home_team.name, self._home_color
            )

        if self.away_team:
            self.database.update_team(
                self.away_team.id, self.away_team.name, self._away_color
            )

        self.accept()
