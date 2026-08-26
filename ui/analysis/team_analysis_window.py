"""Fenêtre de tableau de bord d'analyse d'une équipe.

Agrège les statistiques de tous les matchs enregistrés pour une équipe et
les affiche sous forme de graphiques, avec des filtres interactifs.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.models import Player
from export.video_export import VideoExportWorker
from ui.analysis.team_play_by_play_panel import TeamPlayByPlayEvent, TeamPlayByPlayPanel

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


from controller.team_analysis_controller import (
    TeamDashboard,
    aggregate_boxes,
    aggregate_fga_by_action,
    aggregate_player_box,
    aggregate_points_by_action,
    aggregate_turnover_breakdown,
    compute_player_averages,
    compute_team_dashboard,
    win_pct_by_shooting_comparison,
)

from data.database import Database

from ui.analysis.boxscore_panel import BoxscorePanel
from ui.analysis.filters import MultiSelectFilter
from ui.analysis.shot_map_widget import ShotChartSummaryPanel



# =====================================================
# Style sombre
# =====================================================

TEAM_COLOR = "#297ffe"
OPPONENT_COLOR = "#b0b0b0"

MADE_COLOR = "#297ffe"
MISSED_COLOR = "#e51f1f"

DARK_BG = "#121212"
CARD_BG = "#252525"
BORDER_COLOR = "#555555"

TEXT_COLOR = "#eeeeee"
SECONDARY_TEXT = "#aaaaaa"



# =====================================================
# Fonctions utilitaires
# =====================================================


def _scrollable_tab() -> Tuple[QScrollArea, QVBoxLayout]:

    inner = QWidget()

    layout = QVBoxLayout(
        inner
    )


    scroll = QScrollArea()

    scroll.setWidgetResizable(
        True
    )

    scroll.setWidget(
        inner
    )

    return scroll, layout



def _clear_layout(layout: QVBoxLayout) -> None:

    while layout.count():

        item = layout.takeAt(0)

        widget = item.widget()

        if widget:

            widget.deleteLater()



def _style_figure(fig: Figure) -> None:
    """
    Applique le thème sombre aux graphiques matplotlib.
    """

    fig.patch.set_facecolor(
        CARD_BG
    )

    for ax in fig.axes:

        ax.set_facecolor(
            CARD_BG
        )


        for spine in ax.spines.values():

            spine.set_visible(
                False
            )


        ax.tick_params(
            colors=SECONDARY_TEXT,
            labelcolor=SECONDARY_TEXT,
        )


        ax.title.set_color(
            TEXT_COLOR
        )


        if ax.xaxis.label:

            ax.xaxis.label.set_color(
                TEXT_COLOR
            )


        if ax.yaxis.label:

            ax.yaxis.label.set_color(
                TEXT_COLOR
            )



def _make_canvas(
    figure: Figure
) -> QWidget:

    _style_figure(
        figure
    )


    canvas = FigureCanvas(
        figure
    )


    container = QWidget()

    container.setStyleSheet(
        f"""
        QWidget {{
            background-color:{CARD_BG};
            border-radius:14px;
        }}
        """
    )


    layout = QVBoxLayout(
        container
    )

    layout.setContentsMargins(
        0,
        0,
        0,
        0
    )


    canvas.setStyleSheet(
        """
        background:transparent;
        border:none;
        """
    )


    layout.addWidget(
        canvas
    )


    container.setMinimumHeight(
        int(
            figure.get_size_inches()[1]
            *
            figure.dpi
        )
    )


    return container


def _build_stat_row(
    stats: List[Tuple[str, str]]
) -> QWidget:
    """
    Création de cartes statistiques.
    """

    row = QWidget()

    row_layout = QHBoxLayout(
        row
    )


    for value, label in stats:


        card = QWidget()


        card.setStyleSheet(
            f"""
            QWidget {{
                background-color:{CARD_BG};
                border:none;
                border-radius:14px;
            }}
            """
        )


        card_layout = QVBoxLayout(
            card
        )


        value_label = QLabel(
            value
        )


        value_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )


        value_label.setStyleSheet(
            f"""
            color:{TEAM_COLOR};
            font-size:22px;
            font-weight:bold;
            """
        )


        caption_label = QLabel(
            label
        )


        caption_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )


        caption_label.setWordWrap(
            True
        )


        caption_label.setStyleSheet(
            f"""
            color:{SECONDARY_TEXT};
            font-size:12px;
            """
        )


        card_layout.addWidget(
            value_label
        )

        card_layout.addWidget(
            caption_label
        )


        row_layout.addWidget(
            card
        )


    return row

_ACTION_COLOR_PALETTE = [
    "#297ffe", "#e51f1f", "#2ecc71", "#f1c40f", "#9b59b6",
    "#e67e22", "#1abc9c", "#e84393", "#7f8c8d", "#3498db",
]


def _build_action_color_map(*data_dicts: Dict[str, float]) -> Dict[str, str]:
    """Attribue une couleur fixe à chaque type d'action, identique quel
    que soit le graphique où elle apparaît (points marqués / encaissés,
    domicile / extérieur...). Les actions sont triées par ordre
    alphabétique pour que l'attribution reste stable d'un rafraîchissement
    à l'autre."""

    actions = sorted({
        action
        for d in data_dicts
        for action in d
    })

    return {
        action: _ACTION_COLOR_PALETTE[i % len(_ACTION_COLOR_PALETTE)]
        for i, action in enumerate(actions)
    }


def _plot_pie(
    ax,
    data: Dict[str, float],
    title: str,
    color_map: Optional[Dict[str, str]] = None,
):

    if not data:

        ax.set_title(
            title,
            color=TEXT_COLOR
        )

        ax.axis(
            "off"
        )

        return

    # Tri par taille de secteur décroissante, pour une lecture plus
    # naturelle (plus gros secteur en premier). Les couleurs restent
    # associées à l'action via color_map, donc cet ordre peut différer
    # d'un camembert à l'autre sans casser la cohérence des couleurs.
    sorted_items = sorted(
        data.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    colors = (
        [color_map.get(label) for label in labels]
        if color_map
        else None
    )

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.0f%%",
        textprops={
            "fontsize":8,
            "color":TEXT_COLOR,
        },
    )


    for text in texts + autotexts:

        text.set_color(
            TEXT_COLOR
        )


    ax.set_title(
        title,
        fontsize=10,
        fontweight="bold",
        color=TEXT_COLOR
    )


def _plot_pie_2(
    ax,
    val1: float,
    val2: float,
    label1: str,
    label2: str,
    color1: str,
    color2: str,
    title: str,
) -> None:
    """
    Camembert à 2 parts (ex. OREB équipe vs DREB adversaire), avec le
    pourcentage à l'intérieur des tranches et le libellé à l'extérieur,
    coloré selon la couleur du secteur associé.
    """

    total = val1 + val2

    if total <= 0:

        ax.set_title(
            title,
            color=TEXT_COLOR
        )

        ax.axis(
            "off"
        )

        return


    colors = [color1, color2]


    wedges, texts, autotexts = ax.pie(
        [val1, val2],
        labels=[label1, label2],
        colors=colors,
        autopct="%1.0f%%",
        pctdistance=0.6,
        textprops={
            "fontweight": "bold",
        },
    )


    for autotext in autotexts:

        autotext.set_color(
            "white"
        )

        autotext.set_fontweight(
            "bold"
        )

        autotext.set_fontsize(
            15
        )


    for text, color in zip(
        texts,
        colors
    ):

        text.set_color(
            color
        )

        text.set_fontweight(
            "bold"
        )


    ax.set_title(
        title,
        fontsize=11,
        fontweight="bold",
        color=TEXT_COLOR,
    )

def _plot_bar(
    ax,
    data: Dict[str,float],
    title:str,
    ylabel:str
):

    if not data:

        ax.set_title(
            title,
            color=TEXT_COLOR
        )

        ax.axis(
            "off"
        )

        return


    items = sorted(
        data.items(),
        key=lambda x:x[1],
        reverse=True
    )


    labels = [
        x[0]
        for x in items
    ]


    values = [
        x[1]
        for x in items
    ]


    bars = ax.bar(
        labels,
        values,
        color=TEAM_COLOR
    )


    for bar,value in zip(
        bars,
        values
    ):

        ax.text(
            bar.get_x()+bar.get_width()/2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=TEXT_COLOR,
        )


    ax.set_title(
        title,
        color=TEXT_COLOR,
        fontsize=10,
        fontweight="bold"
    )


    ax.set_ylabel(
        ylabel,
        color=TEXT_COLOR
    )

def _plot_grouped_bar(
    ax,
    labels: List[str],
    series: Dict[str, List[float]],
    title: str,
    ylabel: str,
    colors: Optional[List[str]] = None,
) -> None:
    """
    Histogramme groupé pour comparer plusieurs séries.
    """

    if not labels:

        ax.set_title(
            title,
            fontsize=10,
            color=TEXT_COLOR
        )

        ax.axis(
            "off"
        )

        return


    n_series = len(series)

    x = list(
        range(len(labels))
    )

    width = 0.8 / max(
        n_series,
        1
    )


    for i, (name, values) in enumerate(series.items()):

        offset = (
            i - (n_series - 1) / 2
        ) * width


        positions = [
            xi + offset
            for xi in x
        ]


        color = (
            colors[i]
            if colors and i < len(colors)
            else TEAM_COLOR
        )


        bars = ax.bar(
            positions,
            values,
            width=width,
            label=name,
            color=color,
        )


        for bar, value in zip(
            bars,
            values
        ):

            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=TEXT_COLOR,
            )


    ax.set_xticks(
        x
    )


    ax.set_xticklabels(
        labels,
        rotation=30,
        ha="right",
        fontsize=7,
        color=SECONDARY_TEXT,
    )


    ax.set_title(
        title,
        fontsize=10,
        fontweight="bold",
        color=TEXT_COLOR,
    )


    ax.set_ylabel(
        ylabel,
        color=TEXT_COLOR
    )


    ax.tick_params(
        axis="y",
        labelcolor=SECONDARY_TEXT
    )


    ax.legend(
        fontsize=7,
        facecolor=CARD_BG,
        labelcolor=TEXT_COLOR,
    )

# =====================================================
# Fenêtre principale
# =====================================================


class TeamAnalysisWindow(QMainWindow):


    def __init__(
        self,
        database: Database,
        team_id: int,
        launch_window=None,
    ) -> None:


        super().__init__()


        self.database = database

        self.launch_window = launch_window
        self._analysis_windows: Dict[int, "AnalysisWindow"] = {}
        self._playbyplay_video_paths: Dict[int, str] = {}


        self.dashboard: TeamDashboard = (
            compute_team_dashboard(
                database,
                team_id
            )
        )


        self.setWindowTitle(
            f"Analyse - {self.dashboard.team_name}"
        )


        self.resize(
            1200,
            850
        )


        self._build_ui()

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


        central.setStyleSheet(
            f"""
            QWidget {{
                background-color:{DARK_BG};
                color:{TEXT_COLOR};
            }}
            """
        )


        layout = QVBoxLayout(
            central
        )


        title = QLabel(
            f"Tableau de bord — {self.dashboard.team_name}"
        )


        title.setStyleSheet(
            f"""
            font-size:20px;
            font-weight:bold;
            color:{TEXT_COLOR};
            padding:8px;
            """
        )


        layout.addWidget(
            title
        )


        subtitle = QLabel(
            f"{len(self.dashboard.games)} match(s) analysé(s)"
        )


        subtitle.setStyleSheet(
            f"""
            color:{SECONDARY_TEXT};
            padding-bottom:8px;
            """
        )


        layout.addWidget(
            subtitle
        )


        tabs = QTabWidget(
            self
        )


        layout.addWidget(
            tabs
        )


        tabs.addTab(
            self._build_overview_tab(),
            "Overview"
        )


        tabs.addTab(
            self._build_adresse_tab(),
            "Adresse"
        )


        tabs.addTab(
            self._build_boxscore_tab(),
            "Boxscore"
        )


        tabs.addTab(
            self._build_shot_chart_tab(),
            "Shot chart"
        )


        tabs.addTab(
            self._build_rebounds_tab(),
            "Rebonds"
        )


        tabs.addTab(
            self._build_turnovers_tab(),
            "Pertes de balle"
        )


        tabs.addTab(
            self._build_fouls_tab(),
            "Fautes & lancers francs"
        )

        tabs.addTab(
            self._build_playbyplay_tab(),
            "Play by play"
        )



    # =====================================================
    # Onglet Overview
    # =====================================================

    def _build_overview_tab(self) -> QWidget:

        scroll, layout = _scrollable_tab()


        dash = self.dashboard


        if not dash.games:

            layout.addWidget(
                QLabel(
                    "Aucun match enregistré pour cette équipe."
                )
            )

            return scroll



        record = QLabel(
            f"Bilan : {dash.wins} victoire(s) — {dash.losses} défaite(s)"
        )


        record.setStyleSheet(
            f"""
            color:{TEXT_COLOR};
            font-size:16px;
            font-weight:bold;
            padding:6px;
            """
        )


        layout.addWidget(
            record
        )


        team = dash.team_totals

        opponent = dash.opponent_totals



        factors = [
            "eFG%",
            "TOV%",
            "Reb. Off %",
            "FT Rate",
        ]


        team_values = [
            team.efg_pct,
            team.tov_pct,
            team.oreb_pct(opponent.dreb),
            team.ft_rate,
        ]


        opponent_values = [
            opponent.efg_pct,
            opponent.tov_pct,
            opponent.oreb_pct(team.dreb),
            opponent.ft_rate,
        ]



        fig = Figure(
            figsize=(7,3.2)
        )


        ax = fig.subplots()


        _plot_grouped_bar(
            ax,
            factors,
            {
                dash.team_name: team_values,
                "Adversaires": opponent_values,
            },
            "Four Factors",
            "%",
            colors=[
                TEAM_COLOR,
                OPPONENT_COLOR,
            ],
        )


        layout.addWidget(
            _make_canvas(fig)
        )



        layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{dash.avg_possessions:.1f}",
                        "Possessions / match"
                    ),

                    (
                        f"{dash.avg_points_per_shot:.2f}",
                        "Points / tir"
                    ),

                    (
                        f"{dash.avg_points_per_possession:.2f}",
                        "Points / possession"
                    ),
                ]
            )
        )



        quarters = sorted(
            dash.diff_by_quarter.keys()
        )


        if quarters:

            values = [
                dash.diff_by_quarter[q]
                for q in quarters
            ]


            fig2 = Figure(
                figsize=(7,3)
            )


            ax2 = fig2.subplots()


            bars = ax2.bar(
                [
                    f"Q{q}"
                    for q in quarters
                ],
                values,
                color=[
                    TEAM_COLOR
                    if v >= 0
                    else MISSED_COLOR
                    for v in values
                ],
            )


            for bar, value in zip(
                bars,
                values
            ):

                ax2.text(
                    bar.get_x()+bar.get_width()/2,
                    bar.get_height(),
                    f"{value:+.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=TEXT_COLOR,
                    fontweight="bold",
                )


            ax2.axhline(
                0,
                color=SECONDARY_TEXT,
                linewidth=0.8
            )


            ax2.set_title(
                "Différentiel moyen par quart-temps",
                fontsize=10,
                fontweight="bold",
                color=TEXT_COLOR,
            )


            layout.addWidget(
                _make_canvas(fig2)
            )


        return scroll



    # =====================================================
    # Onglet Adresse
    # =====================================================

    def _build_adresse_tab(self) -> QWidget:

        scroll, outer_layout = _scrollable_tab()


        dash = self.dashboard


        if not dash.games:

            outer_layout.addWidget(
                QLabel(
                    "Aucun match enregistré."
                )
            )

            return scroll



        filters = QHBoxLayout()


        player_filter = MultiSelectFilter(
            "Joueuses",
            [
                (
                    p.id,
                    f"#{p.number} {p.name}"
                )
                for p in dash.players
            ],
        )


        match_filter = MultiSelectFilter(
            "Matchs",
            [
                (
                    g.game.id,
                    f"vs {g.opponent_name}"
                )
                for g in dash.games
            ],
        )


        filters.addWidget(
            player_filter
        )


        filters.addWidget(
            match_filter
        )


        filters.addStretch(
            1
        )


        outer_layout.addLayout(
            filters
        )


        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )


        outer_layout.addWidget(
            content
        )


        def refresh():

            _clear_layout(
                content_layout
            )


            self._populate_adresse_content(
                content_layout,
                player_filter.selected_ids(),
                match_filter.selected_ids(),
            )


        player_filter.on_change = refresh

        match_filter.on_change = refresh


        refresh()


        return scroll

    def _populate_adresse_content(
        self,
        layout: QVBoxLayout,
        player_ids: Optional[List[int]],
        game_ids: Optional[List[int]],
    ) -> None:


        dash = self.dashboard


        team_box, opponent_box = aggregate_boxes(
            dash.games,
            game_ids
        )


        if player_ids is not None:

            team_box = aggregate_player_box(
                dash.games,
                player_ids,
                game_ids
            )



        layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{team_box.efg_pct:.1f}%",
                        "eFG%"
                    ),

                    (
                        f"{team_box.fgm2}/{team_box.fga2} ({team_box.two_pt_pct:.0f}%)",
                        "2 points"
                    ),

                    (
                        f"{team_box.p3m}/{team_box.fga3} ({team_box.three_pt_pct:.0f}%)",
                        "3 points"
                    ),
                ]
            )
        )



        better_pct, worse_pct, n_better, n_worse = (
            win_pct_by_shooting_comparison(
                dash.games,
                game_ids
            )
        )


        label = QLabel(
            "Victoires quand eFG% > adversaire : "
            +
            (
                f"{better_pct:.0f}% ({n_better})"
                if better_pct is not None
                else "N/A"
            )
            +
            " | "
            +
            "Victoires quand eFG% < adversaire : "
            +
            (
                f"{worse_pct:.0f}% ({n_worse})"
                if worse_pct is not None
                else "N/A"
            )
        )


        label.setStyleSheet(
            f"color:{SECONDARY_TEXT};"
        )


        layout.addWidget(
            label
        )



        points = aggregate_points_by_action(
            dash.games,
            player_ids,
            game_ids
        )


        points_against = aggregate_points_by_action(
            dash.games,
            None,
            game_ids,
            conceded=True
        )


        action_colors = _build_action_color_map(
            points,
            points_against
        )


        fig = Figure(
            figsize=(8,3.5)
        )


        ax1, ax2 = fig.subplots(
            1,
            2
        )


        _plot_pie(
            ax1,
            points,
            "Points marqués par action",
            action_colors,
        )


        _plot_pie(
            ax2,
            points_against,
            "Points encaissés par action",
            action_colors,
        )


        layout.addWidget(
            _make_canvas(fig)
        )



        fga = aggregate_fga_by_action(
            dash.games,
            player_ids,
            game_ids
        )


        pps = {

            action:
            points[action] / fga[action]

            for action in points

            if fga.get(action)
            and fga[action] >= 5
            and action.lower() != "non renseigné"

        }


        fig2 = Figure(
            figsize=(8,3.2)
        )


        ax3 = fig2.subplots()


        _plot_bar(
            ax3,
            pps,
            "Points par tir selon l'action",
            "Points / tir"
        )


        layout.addWidget(
            _make_canvas(fig2)
        )



    # =====================================================
    # Onglet Boxscore
    # =====================================================

    def _build_boxscore_tab(self) -> QWidget:

        dash = self.dashboard

        panel = BoxscorePanel()

        if not dash.players:

            return panel

        averages = compute_player_averages(
            self.database,
            dash.players
        )

        panel.refresh(
            sorted(dash.players, key=lambda p: p.number),
            averages,
            dash.team_name
        )

        return panel



    # =====================================================
    # Onglet Shot Chart
    # =====================================================

    def _build_shot_chart_tab(self) -> QWidget:


        scroll, outer_layout = _scrollable_tab()


        dash = self.dashboard


        if not dash.shots:

            outer_layout.addWidget(
                QLabel(
                    "Aucun tir avec coordonnées enregistré."
                )
            )

            return scroll



        filters = QHBoxLayout()



        player_filter = MultiSelectFilter(
            "Joueuses",
            [
                (
                    p.id,
                    f"#{p.number} {p.name}"
                )
                for p in dash.players
            ],
        )


        team_filter = MultiSelectFilter(
            "Equipes",
            dash.teams_faced
        )


        match_filter = MultiSelectFilter(
            "Matchs",
            [
                (
                    g.game.id,
                    f"vs {g.opponent_name}"
                )
                for g in dash.games
            ],
        )



        filters.addWidget(
            player_filter
        )


        filters.addWidget(
            team_filter
        )


        filters.addWidget(
            match_filter
        )


        filters.addStretch(
            1
        )


        outer_layout.addLayout(
            filters
        )



        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )


        outer_layout.addWidget(
            content
        )



        def refresh():

            _clear_layout(
                content_layout
            )


            self._populate_shot_chart_content(
                content_layout,
                player_filter.selected_ids(),
                team_filter.selected_ids(),
                match_filter.selected_ids(),
            )



        player_filter.on_change = refresh

        team_filter.on_change = refresh

        match_filter.on_change = refresh



        refresh()


        return scroll



    def _populate_shot_chart_content(
        self,
        layout: QVBoxLayout,
        player_ids: Optional[List[int]],
        team_ids: Optional[List[int]],
        game_ids: Optional[List[int]],
    ) -> None:


        dash = self.dashboard



        panel = ShotChartSummaryPanel(
            "assets/court.svg"
        )


        panel.set_players(
            dash.players
        )


        panel.set_team_labels(
            dash.team_name,
            "Adversaires"
        )



        markers = []



        for shot in dash.shots:


            if player_ids is not None:

                if shot.player_id not in player_ids:

                    continue



            if team_ids is not None:

                if shot.team_id not in team_ids:

                    continue



            if game_ids is not None:

                if shot.game_id not in game_ids:

                    continue



            x = shot.x
            y = shot.y

            is_team = shot.team_id == dash.team_id

            if is_team:
                # équipe analysée : côté gauche
                if shot.quarter in (3, 4):
                    x = -x
                    y = -y

            else:
                # adversaires : côté droit
                if shot.quarter in (1, 2):
                    x = -x
                    y = -y

            markers.append(
                {
                    "x": x,
                    "y": y,
                    "made": shot.made,
                    "is_home": (
                        shot.team_id == dash.team_id
                    ),
                    "player_id": shot.player_id,
                }
            )



        panel.set_shots(
            markers
        )


        layout.addWidget(
            panel
        )

    # =====================================================
    # Onglet Rebonds
    # =====================================================

    def _build_rebounds_tab(self) -> QWidget:

        scroll, outer_layout = _scrollable_tab()

        dash = self.dashboard


        if not dash.games:

            outer_layout.addWidget(
                QLabel(
                    "Aucun match enregistré."
                )
            )

            return scroll



        filters = QHBoxLayout()


        match_filter = MultiSelectFilter(
            "Matchs",
            [
                (
                    g.game.id,
                    f"vs {g.opponent_name}"
                )
                for g in dash.games
            ],
        )


        filters.addWidget(
            match_filter
        )


        filters.addStretch(
            1
        )


        outer_layout.addLayout(
            filters
        )



        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )


        outer_layout.addWidget(
            content
        )



        def refresh():

            _clear_layout(
                content_layout
            )


            self._populate_rebounds_content(
                content_layout,
                match_filter.selected_ids(),
            )


        match_filter.on_change = refresh


        refresh()


        return scroll

    def _populate_rebounds_content(
            self,
            layout: QVBoxLayout,
            game_ids: Optional[List[int]],
        ) -> None:


            dash = self.dashboard


            team_box, opponent_box = aggregate_boxes(
                dash.games,
                game_ids
            )



            # Nombre de matchs pris en compte par le filtre courant, pour
            # calculer les moyennes (et non les totaux bruts)
            games_considered = [
                g
                for g in dash.games
                if game_ids is None
                or g.game.id in game_ids
            ]


            n_games = len(
                games_considered
            ) or 1



            points_oreb = aggregate_points_by_action(
                dash.games,
                None,
                game_ids
            ).get(
                "Reb off",
                0
            )

            avg_points_oreb = points_oreb / n_games



            points_conceded_oreb = aggregate_points_by_action(
                dash.games,
                None,
                game_ids,
                conceded=True
            ).get(
                "Reb off",
                0
            )


            avg_points_conceded_oreb = (
                points_conceded_oreb / n_games
            )



            layout.addWidget(
                _build_stat_row(
                    [
                        (
                            f"{avg_points_oreb:.1f}",
                            "Points après rebond offensif"
                        ),

                        (
                            f"{avg_points_conceded_oreb:.1f}",
                            "Points encaissés après rebond offensif (moy./match)"
                        ),
                    ]
                )
            )


            # === Camemberts OREB/DREB : qui capte les rebonds, selon qui tire ===

            fig = Figure(
                figsize=(13, 4.2)
            )


            ax1, ax2, ax3 = fig.subplots(
                1,
                3
            )


            # 1. Quand l'équipe analysée tire : OREB équipe vs DREB adversaires
            _plot_pie_2(
                ax1,
                team_box.oreb,
                opponent_box.dreb,
                f"OREB {dash.team_name}",
                "DREB Adversaires",
                TEAM_COLOR,
                OPPONENT_COLOR,
                f"Quand {dash.team_name} tire",
            )


            # 2. Quand les adversaires tirent : OREB adversaires vs DREB équipe
            _plot_pie_2(
                ax2,
                opponent_box.oreb,
                team_box.dreb,
                "OREB Adversaires",
                f"DREB {dash.team_name}",
                OPPONENT_COLOR,
                TEAM_COLOR,
                "Quand les adversaires tirent",
            )


            # 3. Part globale des rebonds captés (OREB + DREB) par équipe
            _plot_pie_2(
                ax3,
                team_box.oreb + team_box.dreb,
                opponent_box.oreb + opponent_box.dreb,
                dash.team_name,
                "Adversaires",
                TEAM_COLOR,
                OPPONENT_COLOR,
                "Part des rebonds captés",
            )


            fig.tight_layout()


            layout.addWidget(
                _make_canvas(fig)
            )

    # =====================================================
    # Onglet Pertes de balle
    # =====================================================

    def _build_turnovers_tab(self) -> QWidget:


        scroll, outer_layout = _scrollable_tab()

        dash = self.dashboard


        if not dash.games:

            outer_layout.addWidget(
                QLabel(
                    "Aucun match enregistré."
                )
            )

            return scroll



        filters = QHBoxLayout()


        player_filter = MultiSelectFilter(
            "Joueuses",
            [
                (
                    p.id,
                    f"#{p.number} {p.name}"
                )
                for p in dash.players
            ],
        )


        match_filter = MultiSelectFilter(
            "Matchs",
            [
                (
                    g.game.id,
                    f"vs {g.opponent_name}"
                )
                for g in dash.games
            ],
        )


        filters.addWidget(
            player_filter
        )

        filters.addWidget(
            match_filter
        )

        filters.addStretch(
            1
        )


        outer_layout.addLayout(
            filters
        )



        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )


        outer_layout.addWidget(
            content
        )



        def refresh():

            _clear_layout(
                content_layout
            )


            self._populate_turnovers_content(
                content_layout,
                player_filter.selected_ids(),
                match_filter.selected_ids(),
            )



        player_filter.on_change = refresh

        match_filter.on_change = refresh


        refresh()


        return scroll



    def _populate_turnovers_content(
        self,
        layout: QVBoxLayout,
        player_ids: Optional[List[int]],
        game_ids: Optional[List[int]],
    ) -> None:


        dash = self.dashboard


        team_box, opponent_box = aggregate_boxes(
            dash.games,
            game_ids
        )


        layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{team_box.tov_pct:.1f}%",
                        f"TOV% {dash.team_name}"
                    ),

                    (
                        f"{opponent_box.tov_pct:.1f}%",
                        "TOV% adversaire"
                    ),
                ]
            )
        )



        breakdown = aggregate_turnover_breakdown(
            dash.games,
            player_ids,
            game_ids
        )



        if breakdown:

            fig = Figure(
                figsize=(6,4)
            )


            ax = fig.subplots()


            _plot_pie(
                ax,
                breakdown,
                "Répartition des pertes de balle"
            )


            layout.addWidget(
                _make_canvas(fig)
            )


        else:

            layout.addWidget(
                QLabel(
                    "Aucune perte de balle enregistrée."
                )
            )

    # =====================================================
    # Onglet Fautes & lancers francs
    # =====================================================

    def _build_fouls_tab(self) -> QWidget:


        scroll, layout = _scrollable_tab()

        dash = self.dashboard


        if not dash.games:

            layout.addWidget(
                QLabel(
                    "Aucun match enregistré."
                )
            )

            return scroll



        avg_team_fouls = (
            sum(
                g.team_box.fouls
                for g in dash.games
            )
            /
            len(dash.games)
        )


        avg_opponent_fouls = (
            sum(
                g.opponent_box.fouls
                for g in dash.games
            )
            /
            len(dash.games)
        )


        avg_fta = (
            sum(
                g.team_box.fta
                for g in dash.games
            )
            /
            len(dash.games)
        )


        layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{avg_team_fouls:.1f}",
                        f"Fautes / match ({dash.team_name})"
                    ),

                    (
                        f"{avg_opponent_fouls:.1f}",
                        "Fautes / match adversaires"
                    ),

                    (
                        f"{avg_fta:.1f}",
                        "Lancers francs tentés / match"
                    ),

                    (
                        f"{dash.team_totals.ft_pct:.1f}%",
                        "Réussite aux lancers francs"
                    ),
                ]
            )
        )



        labels = [
            f"{dash.team_name}\nvs\n{g.opponent_name}"
            for g in dash.games
        ]


        team_values = [
            g.team_box.fouls
            for g in dash.games
        ]


        opponent_values = [
            g.opponent_box.fouls
            for g in dash.games
        ]



        fig = Figure(
            figsize=(8,3.5)
        )


        ax = fig.subplots()



        _plot_grouped_bar(
            ax,
            labels,
            {
                dash.team_name: team_values,
                "Adversaires": opponent_values,
            },
            "Fautes par match",
            "Nombre de fautes",
            colors=[
                TEAM_COLOR,
                OPPONENT_COLOR,
            ],
        )


        layout.addWidget(
            _make_canvas(fig)
        )



        return scroll

    # =====================================================
    # Onglet Play by play (montages vidéo multi-matchs)
    # =====================================================

    def _build_playbyplay_tab(self) -> QWidget:

        panel = TeamPlayByPlayPanel()
        self.team_playbyplay_panel = panel

        dash = self.dashboard

        if not dash.games:
            return panel

        self._load_playbyplay_data(panel)

        panel.event_seek_requested.connect(self._on_team_seek_requested)
        panel.export_requested.connect(self._on_team_export_requested)

        return panel

    def _load_playbyplay_data(self, panel: TeamPlayByPlayPanel) -> None:

        dash = self.dashboard

        items: List[TeamPlayByPlayEvent] = []
        players: Dict[int, Player] = {p.id: p for p in dash.players}
        team_player_ids = {p.id for p in dash.players}
        games_for_filter: List[Tuple[int, str]] = []

        player_cache: Dict[int, Optional[Player]] = {}

        def get_player(player_id: int) -> Optional[Player]:
            if player_id not in player_cache:
                player_cache[player_id] = self.database.get_player(player_id)
            return player_cache[player_id]

        for game_dash in dash.games:

            game = game_dash.game
            label = f"vs {game_dash.opponent_name} ({game.date})"
            games_for_filter.append((game.id, label))

            for event in self.database.get_events_for_game(game.id):

                if event.player_id not in players:
                    player = get_player(event.player_id)
                    if player is not None:
                        players[player.id] = player

                items.append(TeamPlayByPlayEvent(event, game.id, label))

        self._playbyplay_video_paths = {
            g.game.id: g.game.video_path for g in dash.games
        }

        panel.refresh(items, players, team_player_ids, games_for_filter)

    def _on_team_seek_requested(self, game_id: int, timestamp: float) -> None:
        """Ouvre (ou réactive) la fenêtre d'analyse du match concerné et
        rembobine juste avant l'action, comme le double-clic dans le
        play-by-play d'un match (voir AnalysisWindow._on_seek_from_playbyplay)."""

        from ui.analysis.analysis_window import AnalysisWindow

        window = self._analysis_windows.get(game_id)

        if window is None or not window.isVisible():
            window = AnalysisWindow(
                self.database, game_id, launch_window=self.launch_window
            )
            self._analysis_windows[game_id] = window

        window.show()
        window.raise_()
        window.activateWindow()

        target = max(0.0, timestamp - 5.0)
        window.video_panel.seek(target)
        window.tabs.setCurrentIndex(0)

    def _on_team_export_requested(self, events, before, after) -> None:

        if not events:
            return

        video_paths = {
            game_id: path
            for game_id, path in self._playbyplay_video_paths.items()
            if path
        }

        usable_events = [e for e in events if video_paths.get(e.game_id)]

        if len(usable_events) < len(events):
            QMessageBox.warning(
                self,
                "Vidéo introuvable",
                "Certains événements sélectionnés n'ont pas de vidéo associée "
                "à leur match et seront ignorés du montage."
            )

        if not usable_events:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le montage vidéo", "montage.mp4", "Vidéo MP4 (*.mp4)"
        )

        if not output_path:
            return

        self._export_thread = QThread(self)
        self._export_worker = VideoExportWorker(
            video_path=video_paths,
            events=usable_events,
            before=before,
            after=after,
            output_path=output_path,
        )
        self._export_worker.moveToThread(self._export_thread)

        self._export_progress_dialog = QProgressDialog(
            "Export du montage en cours...", "Annuler", 0, len(usable_events), self
        )
        self._export_progress_dialog.setWindowModality(Qt.WindowModal)

        self._export_thread.started.connect(self._export_worker.run)
        self._export_worker.progress.connect(
            self._on_team_export_progress, Qt.ConnectionType.QueuedConnection
        )
        self._export_worker.finished.connect(self._on_team_export_finished)
        self._export_worker.error.connect(self._on_team_export_error)
        self._export_progress_dialog.canceled.connect(self._export_worker.cancel)
        self._export_worker.finished.connect(self._export_thread.quit)
        self._export_worker.error.connect(self._export_thread.quit)

        self._export_thread.start()

    def _on_team_export_progress(self, done, total) -> None:
        self._export_progress_dialog.setValue(done)

    def _on_team_export_finished(self, output_path) -> None:
        self._export_progress_dialog.close()
        QMessageBox.information(self, "Export terminé", f"Montage enregistré :\n{output_path}")

    def _on_team_export_error(self, message) -> None:
        self._export_progress_dialog.close()
        QMessageBox.critical(self, "Erreur d'export", message)
