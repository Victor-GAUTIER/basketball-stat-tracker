"""Fenêtre principale d'analyse vidéo d'un match."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QTimer
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
from ui.analysis.stats_panel import StatsPanel
from ui.analysis.shot_chart_widget import ShotChartWidget
from ui.analysis.play_by_play_panel import PlayByPlayPanel
from ui.analysis.edit_event_dialog import EditEventDialog
from ui.analysis.shot_map_widget import ShotChartSummaryPanel
from ui.analysis.phase_panel import PhasePanel
from ui.analysis.team_comparison_panel import TeamComparisonPanel



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


        self.home_players: List[Player] = []

        self.away_players: List[Player] = []


        self.home_team = None

        self.away_team = None


        # True = équipe domicile attaque le panier de droite
        self.home_attacks_right = True

        self._shortcuts = []


        # Référence vers le popup temporaire actuellement affiché
        self._toast_label = None


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
    # Construction interface
    # =====================================================

    def _build_ui(self):

        central = QWidget(
            self
        )

        self.setCentralWidget(
            central
        )


        main_layout = QVBoxLayout(
            central
        )


        self.tabs = QTabWidget(
            self
        )



        # =========================
        # ONGLET ANALYSE
        # =========================

        analysis_tab = QWidget()

        analysis_layout = QHBoxLayout(
            analysis_tab
        )


        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )



        # -------------------------
        # Partie vidéo
        # -------------------------
        video_container = QWidget()

        video_layout = QVBoxLayout(
            video_container
        )


        self.score_label = QLabel(
            "0 - 0",
            self
        )

        self.score_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.score_label.setStyleSheet(
            "font-size: 22px; font-weight: bold; padding: 6px;"
        )

        video_layout.addWidget(
            self.score_label
        )


        self.video_panel = VideoPanel(
            self
        )


        video_layout.addWidget(
            self.video_panel,
            stretch=8
        )

        self.phase_panel = PhasePanel(
            self
        )

        video_layout.addWidget(
            self.phase_panel
        )


        splitter.addWidget(
            video_container
        )



        # -------------------------
        # Partie droite
        # -------------------------

        right_widget = QWidget()

        right_layout = QVBoxLayout(
            right_widget
        )


        self.player_panel = PlayerPanel(
            self
        )


        self.selected_player_label = QLabel(
            "Aucune joueuse sélectionnée"
        )


        self.selected_player_label.setStyleSheet(
            "font-weight:bold;"
        )



        # Terrain de tirs

        self.shot_chart = ShotChartWidget(
            "assets/court.svg",
            self
        )


        self.shot_chart.shot_clicked.connect(
            self._on_shot_clicked
        )



        # Evénements classiques

        self.event_panel = EventPanel(
            self
        )

        self.event_panel.setMaximumHeight(
            280
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
            self.shot_chart,
            stretch=3
        )


        right_layout.addWidget(
            self.event_panel
        )


        right_layout.addLayout(
            buttons_layout
        )


        splitter.addWidget(
            right_widget
        )


        splitter.setStretchFactor(
            0,
            3
        )


        splitter.setStretchFactor(
            1,
            1
        )


        analysis_layout.addWidget(
            splitter
        )



        # =========================
        # ONGLET STATS
        # =========================

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

        self.team_comparison_panel = TeamComparisonPanel(self)

        self.tabs.addTab(
            self.team_comparison_panel,
            "Comparaison"
        )


        main_layout.addWidget(
            self.tabs
        )



        self.player_panel.player_selected.connect(
            self._on_player_selected
        )

        self.player_panel.team_name_changed.connect(self._on_team_name_changed)
        self.player_panel.player_edited.connect(self._on_player_edited)


        self.event_panel.event_triggered.connect(
            self._on_event_triggered
        )

        # =========================
        # ONGLET SHOT CHART
        # =========================

        self.shot_chart_summary_panel = ShotChartSummaryPanel(
            "assets/court.svg",
            self
        )


        self.tabs.addTab(
            self.shot_chart_summary_panel,
            "Shot chart"
        )

        # =========================
        # ONGLET PLAY BY PLAY
        # =========================

        playbyplay_tab = QWidget()


        playbyplay_layout = QVBoxLayout(
            playbyplay_tab
        )


        self.playbyplay_panel = PlayByPlayPanel(
            self
        )


        playbyplay_layout.addWidget(
            self.playbyplay_panel
        )


        self.tabs.addTab(
            playbyplay_tab,
            "Play by play"
        )


        self.playbyplay_panel.event_deleted.connect(
            self._on_delete_event
        )


        self.playbyplay_panel.event_edit_requested.connect(
            self._on_edit_event
        )


        self.playbyplay_panel.event_seek_requested.connect(
            self._on_seek_from_playbyplay
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
        # Inverser les côtés du terrain
        # -------------------------

        invert_sides_action = QAction(
            "Inverser les côtés du terrain",
            self
        )


        invert_sides_action.triggered.connect(
            self._toggle_court_sides
        )


        options_menu.addAction(
            invert_sides_action
        )



        # -------------------------
        # Changer de match
        # -------------------------

        change_game_action = QAction(
            "Changer de match",
            self
        )


        change_game_action.triggered.connect(
            self._change_game
        )


        options_menu.addAction(
            change_game_action
        )



    def _change_quarter(
        self,
        quarter: int
    ):

        self.controller.set_quarter(
            quarter
        )


        # Mise à jour automatique du côté attaqué
        self._update_shot_chart_orientation()


        self.statusBar().showMessage(
            f"Quart-temps {quarter}",
            3000
        )



    # =====================================================
    # Orientation du terrain
    # =====================================================

    def _toggle_court_sides(self):

        """
        Inversion manuelle des côtés attaqués.
        Utile si la caméra ou le terrain est inversé.
        """

        self.home_attacks_right = not self.home_attacks_right


        self._update_shot_chart_orientation()


        self.statusBar().showMessage(
            "Côtés du terrain inversés",
            3000
        )



    def _current_home_attacks_right(self) -> bool:

        """
        Retourne le côté actuellement attaqué par l'équipe domicile.

        Avant la mi-temps :
            home_attacks_right

        Après la mi-temps :
            côté inverse
        """

        attacks_right = self.home_attacks_right


        if self.controller.get_current_quarter() >= 3:

            attacks_right = not attacks_right


        return attacks_right



    def _update_shot_chart_orientation(self):

        """
        Met à jour l'affichage du terrain :
        - équipe qui attaque à droite
        - noms des équipes
        """

        home_name = (
            self.home_team.name
            if self.home_team
            else "Domicile"
        )


        away_name = (
            self.away_team.name
            if self.away_team
            else "Extérieur"
        )


        self.shot_chart.set_orientation(
            self._current_home_attacks_right(),
            home_name,
            away_name,
        )

    # =====================================================
    # Shot chart récapitulatif
    # =====================================================
    def _compute_shot_markers(self):

        home_ids = {
            p.id
            for p in self.home_players
        }

        markers = []

        for event in self.controller.get_events():

            if event.x is None or event.y is None:
                continue

            if not event.event_type.startswith(("2PTS_", "3PTS_")):
                continue

            is_home = event.player_id in home_ids

            canonical_right = (
                self.home_attacks_right
                if is_home
                else not self.home_attacks_right
            )

            attacked_right_then = (
                canonical_right
                if event.quarter <= 2
                else not canonical_right
            )

            x = event.x
            y = event.y

            if attacked_right_then != canonical_right:
                # Symétrie centrale (rotation 180°) : on ramène le tir côté
                # canonique de l'équipe tout en conservant sa position relative
                # par rapport à SON panier.
                x = 1.0 - x
                y = 1.0 - y

            markers.append({
                "x": x,
                "y": y,
                "made": event.event_type.endswith("_MADE"),
                "is_home": is_home,
                "player_id": event.player_id,
            })

        return markers

    def _compute_score(self):
        """Calcule le score des deux équipes à partir des tirs marqués."""

        home_ids = {p.id for p in self.home_players}

        home_score = 0
        away_score = 0

        for event in self.controller.get_events():

            if event.event_type == "FT_MADE":
                points = 1

            elif event.event_type == "2PTS_MADE":
                points = 2

            elif event.event_type == "3PTS_MADE":
                points = 3

            else:
                continue

            if event.player_id in home_ids:
                home_score += points
            else:
                away_score += points

        return home_score, away_score

# =====================================================
    # Comparaison d'équipes (onglet "Comparaison")
    # =====================================================

    def _compute_quarter_scores(self):
        """Retourne {quart_temps: (points_domicile, points_exterieur)}."""

        home_ids = {p.id for p in self.home_players}

        quarter_scores = {}

        for event in self.controller.get_events():

            if event.event_type == "FT_MADE":
                points = 1
            elif event.event_type == "2PTS_MADE":
                points = 2
            elif event.event_type == "3PTS_MADE":
                points = 3
            else:
                continue

            home_pts, away_pts = quarter_scores.get(event.quarter, (0, 0))

            if event.player_id in home_ids:
                home_pts += points
            else:
                away_pts += points

            quarter_scores[event.quarter] = (home_pts, away_pts)

        return quarter_scores

    def _aggregate_team_stats(self, players, stats):
        """Agrège les stats de tous les joueurs d'une équipe (mêmes clés
        que celles utilisées par StatsPanel)."""

        totals = {
            "PTS": 0,
            "FG_MADE": 0, "FG_ATT": 0,
            "2PTS_MADE": 0, "2PTS_ATT": 0,
            "3PTS_MADE": 0, "3PTS_ATT": 0,
            "FT_MADE": 0, "FT_ATT": 0,
            "REB": 0, "AST": 0, "TO": 0,
            "STL": 0, "BLK": 0, "PF": 0,
        }

        for player in players:

            player_stats = stats.get(player.id, {})

            two_made = player_stats.get("2PTS_MADE", 0)
            two_att = two_made + player_stats.get("2PTS_MISSED", 0)

            three_made = player_stats.get("3PTS_MADE", 0)
            three_att = three_made + player_stats.get("3PTS_MISSED", 0)

            ft_made = player_stats.get("FT_MADE", 0)
            ft_att = ft_made + player_stats.get("FT_MISSED", 0)

            oreb = player_stats.get("OFF_REBOUND", 0)
            dreb = player_stats.get("DEF_REBOUND", 0)

            totals["PTS"] += two_made * 2 + three_made * 3 + ft_made

            totals["2PTS_MADE"] += two_made
            totals["2PTS_ATT"] += two_att

            totals["3PTS_MADE"] += three_made
            totals["3PTS_ATT"] += three_att

            totals["FG_MADE"] += two_made + three_made
            totals["FG_ATT"] += two_att + three_att

            totals["FT_MADE"] += ft_made
            totals["FT_ATT"] += ft_att

            totals["REB"] += oreb + dreb
            totals["AST"] += player_stats.get("ASSIST", 0)
            totals["TO"] += player_stats.get("TURNOVER", 0)
            totals["STL"] += player_stats.get("STEAL", 0)
            totals["BLK"] += player_stats.get("BLOCK", 0)
            totals["PF"] += player_stats.get("FOUL", 0)

        return totals

    def _compute_leaders(self, players, stats):
        """Retourne {"PTS": (player, valeur) | None, "REB": ..., "AST": ...}
        pour l'équipe donnée."""

        best = {"PTS": None, "REB": None, "AST": None}

        for player in players:

            player_stats = stats.get(player.id, {})

            pts = (
                player_stats.get("2PTS_MADE", 0) * 2
                + player_stats.get("3PTS_MADE", 0) * 3
                + player_stats.get("FT_MADE", 0)
            )

            reb = (
                player_stats.get("OFF_REBOUND", 0)
                + player_stats.get("DEF_REBOUND", 0)
            )

            ast = player_stats.get("ASSIST", 0)

            for key, value in (("PTS", pts), ("REB", reb), ("AST", ast)):

                current = best[key]

                if current is None or value > current[1]:
                    best[key] = (player, value)

        return best

    # =====================================================
    # Changer de match
    # =====================================================

    def _change_game(self):

        reply = QMessageBox.question(
            self,
            "Changer de match",
            "Retourner à la sélection des matchs ?"
        )


        if reply != QMessageBox.StandardButton.Yes:

            return



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

            (
                "Space",
                self.video_panel.toggle_play_pause
            ),


            (
                "Left",
                lambda:
                self.video_panel.seek_relative(-5000)
            ),


            (
                "Right",
                lambda:
                self.video_panel.seek_relative(5000)
            ),



            *[
                (
                    key,
                    lambda c=code:
                    self._on_event_triggered(c)
                )

                for code, label, key
                in EVENT_TYPES
            ],


        ]



        for key, callback in shortcuts:


            shortcut = QShortcut(
                QKeySequence(key),
                self
            )


            shortcut.setContext(
                Qt.ShortcutContext.WindowShortcut
            )


            shortcut.activated.connect(
                callback
            )


            self._shortcuts.append(
                shortcut
            )



    # =====================================================
    # Popup temporaire (toast)
    # =====================================================

    def _show_toast(
        self,
        message: str,
        duration_ms: int = 3000
    ):

        """
        Affiche un petit bandeau semi-transparent en haut de la fenêtre
        pendant `duration_ms` millisecondes, sans bloquer l'interface.
        """

        # Si un toast est déjà affiché, on le retire immédiatement
        if self._toast_label is not None:

            self._toast_label.deleteLater()

            self._toast_label = None


        toast = QLabel(
            message,
            self
        )


        toast.setStyleSheet(
            "background-color: rgba(30, 30, 30, 220);"
            "color: white;"
            "font-weight: bold;"
            "font-size: 14px;"
            "padding: 10px 18px;"
            "border-radius: 8px;"
        )


        toast.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )


        toast.adjustSize()


        x = (self.width() - toast.width()) // 2

        y = 40


        toast.move(
            x,
            y
        )


        toast.show()

        toast.raise_()


        self._toast_label = toast


        QTimer.singleShot(
            duration_ms,
            lambda: self._hide_toast(toast)
        )



    def _hide_toast(
        self,
        toast: QLabel
    ):

        # On ne supprime que si c'est toujours le toast actif
        # (évite de supprimer un toast plus récent par erreur)
        if self._toast_label is toast:

            self._toast_label = None


        toast.deleteLater()



    def _event_label(
        self,
        event_code: str
    ) -> str:

        """
        Retourne le libellé lisible d'un code événement classique
        (ex: "REB", "FAUTE", ...), défini dans EVENT_TYPES.
        """

        for code, label, key in EVENT_TYPES:

            if code == event_code:

                return label


        return event_code



    # =====================================================
    # Chargement du match
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



        # -------------------------
        # Equipes
        # -------------------------

        teams = self.controller.get_teams()



        home = next(
            (
                team
                for team, is_home
                in teams
                if is_home
            ),
            None
        )



        away = next(
            (
                team
                for team, is_home
                in teams
                if not is_home
            ),
            None
        )



        # Sauvegarde des équipes
        self.home_team = home

        self.away_team = away



        # -------------------------
        # Joueurs
        # -------------------------

        self.home_players = (

            self.controller.get_players_for_team(
                home.id
            )

            if home
            else []

        )



        self.away_players = (

            self.controller.get_players_for_team(
                away.id
            )

            if away
            else []

        )



        self.player_panel.set_teams(

            home.name
            if home
            else "Equipe A",

            self.home_players,


            away.name
            if away
            else "Equipe B",

            self.away_players

        )



        self._all_players = (

            self.home_players
            +
            self.away_players

        )

        self.shot_chart_summary_panel.set_players(self._all_players)

        self._refresh_data()


        self._update_shot_chart_orientation()

        self.video_panel.setFocus()



    # =====================================================
    # Sélection joueur
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
                f"Joueuse sélectionnée : #{player.number} {player.name}"
            )

    def _on_team_name_changed(self, is_home: bool, new_name: str):
        team = self.home_team if is_home else self.away_team
        if team is None or new_name == team.name:
            return

        self.database.update_team(team.id, new_name)
        self._load_game_data()

    def _on_player_edited(self, player_id: int, name: str, number: int):
        self.database.update_player(player_id, name, number)
        self._load_game_data()

    # =====================================================
    # Enregistrement événement classique
    # =====================================================

    def _on_event_triggered(
        self,
        event_code: str
    ):


        player_id = self.player_panel.selected_player_id()



        if player_id is None:

            QMessageBox.warning(
                self,
                "Aucune joueuse",
                "Sélectionnez une joueuse avant d'ajouter un événement."
            )

            return


        phase = self.phase_panel.current_phase()
        system = self.phase_panel.current_system()

        self.controller.record_event(
            player_id,
            self.video_panel.current_timestamp(),
            event_code,
            phase=phase,
            system=system,
        )



        player = self.database.get_player(
            player_id
        )


        if player:

            label = self._event_label(
                event_code
            )


            self._show_toast(
                f"#{player.number} {player.name} : {label}"
            )


        self._refresh_data()



    # =====================================================
    # Enregistrement tir
    # =====================================================

    def _on_shot_clicked(
        self,
        x: float,
        y: float,
        missed: bool
    ):


        player_id = self.player_panel.selected_player_id()



        if player_id is None:


            QMessageBox.warning(
                self,
                "Aucune joueuse",
                "Sélectionnez une joueuse avant d'ajouter un tir."
            )

            return



        # -------------------------
        # Vérification équipe
        # -------------------------

        is_home = any(

            p.id == player_id

            for p in self.home_players

        )



        home_attacks_right = (

            self._current_home_attacks_right()

        )



        team_attacks_right = (

            home_attacks_right

            if is_home

            else not home_attacks_right

        )



        click_is_right = x >= 0.5



        if click_is_right != team_attacks_right:


            side_label = (

                "droite"

                if team_attacks_right

                else "gauche"

            )



            QMessageBox.warning(

                self,

                "Mauvais côté du terrain",

                f"Cette joueuse attaque le panier de {side_label}. "
                "Cliquez de ce côté du terrain pour enregistrer le tir."

            )


            return



        # -------------------------
        # Valeur du tir
        # -------------------------

        shot_value = self.shot_chart.shot_value(
            x,
            y
        )



        if missed:

            event_type = (
                shot_value
                +
                "_MISSED"
            )

        else:

            event_type = (
                shot_value
                +
                "_MADE"
            )



        phase = self.phase_panel.current_phase()
        system = self.phase_panel.current_system()

        self.controller.record_event(
            player_id,
            self.video_panel.current_timestamp(),
            event_type,
            phase=phase,
            system=system,
            x=x,
            y=y
        )



        player = self.database.get_player(
            player_id
        )


        if player:

            points = shot_value.replace(
                "PTS",
                ""
            )


            if missed:

                message = (
                    f"#{player.number} {player.name} "
                    f"a manqué un tir à {points} points"
                )

            else:

                message = (
                    f"#{player.number} {player.name} "
                    f"a marqué {points} points"
                )


            self._show_toast(
                message
            )



        self._refresh_data()

    # =====================================================
    # Annulation dernier événement
    # =====================================================

    def _on_undo_event(self):

        self.controller.undo_last_event()

        self._refresh_data()



    # =====================================================
    # Suppression événement Play by Play
    # =====================================================

    def _on_delete_event(
        self,
        event_id: int
    ):

        self.database.delete_event(
            event_id
        )

        self._refresh_data()



    # =====================================================
    # Modification événement Play by Play
    # =====================================================

    def _on_edit_event(
        self,
        event_id: int
    ):

        """
        Ouvre la fenêtre de modification d'un événement.
        """

        event = next(
            (
                e
                for e in self.controller.get_events()
                if e.id == event_id
            ),
            None
        )


        if event is None:

            return



        dialog = EditEventDialog(
            event,
            self._all_players,
            self
        )


        if dialog.exec() != EditEventDialog.DialogCode.Accepted:

            return

        player_id, event_type, quarter, phase, system = dialog.result_values()

        if player_id is None or event_type is None:

            return

        self.database.update_event(
            event_id,
            player_id,
            event_type,
            quarter,
            phase,
            system,
        )

        self._refresh_data()



    # =====================================================
    # Double clic Play by Play
    # =====================================================

    def _on_seek_from_playbyplay(
        self,
        timestamp: float
    ):

        """
        Retourne dans la vidéo quelques secondes avant l'action.
        """

        target = max(
            0.0,
            timestamp - 5.0
        )


        self.video_panel.seek(
            target
        )


        # Retour automatique dans l'onglet analyse
        self.tabs.setCurrentIndex(
            0
        )



    # =====================================================
    # Export CSV
    # =====================================================

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

            p.id: p

            for p in self._all_players

        }



        export_events_to_csv(

            path,

            events,

            players

        )



    # =====================================================
    # Actualisation affichage
    # =====================================================

    def _refresh_data(self):


        events = self.controller.get_events()



        players = {

            p.id: p

            for p in self._all_players

        }

        home_name = (
            self.home_team.name
            if self.home_team
            else "Domicile"
        )

        away_name = (
            self.away_team.name
            if self.away_team
            else "Extérieur"
        )

        self.playbyplay_panel.refresh(

            events,

            players,

            self.home_players,

            self.away_players,

            home_name,

            away_name

        )

        player_stats = self.controller.get_player_stats()

        self.stats_panel.refresh(

            self.home_players,

            self.away_players,

            player_stats,

            home_name,

            away_name

        )

        self.team_comparison_panel.refresh(
            home_name,
            away_name,
            self._compute_quarter_scores(),
            self._aggregate_team_stats(self.home_players, player_stats),
            self._aggregate_team_stats(self.away_players, player_stats),
            self._compute_leaders(self.home_players, player_stats),
            self._compute_leaders(self.away_players, player_stats),
        )

        self.shot_chart_summary_panel.set_team_labels(
            home_name,
            away_name
        )

        self.shot_chart_summary_panel.set_shots(
            self._compute_shot_markers()
        )

        home_score, away_score = self._compute_score()

        self.score_label.setText(
            f"{home_name}  {home_score} - {away_score}  {away_name}"
        )
