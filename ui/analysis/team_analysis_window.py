"""Fenêtre de tableau de bord d'analyse d'une équipe.

Agrège les statistiques de tous les matchs enregistrés pour une équipe et
les affiche sous forme de graphiques, avec des filtres interactifs.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


from controller.team_analysis_controller import (
    TeamDashboard,
    aggregate_boxes,
    aggregate_fga_by_action,
    aggregate_player_box,
    aggregate_points_by_action,
    aggregate_turnover_breakdown,
    compute_team_dashboard,
    win_pct_by_shooting_comparison,
)

from data.database import Database

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



def _plot_pie(
    ax,
    data: Dict[str, float],
    title: str
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


    labels = list(
        data.keys()
    )

    values = list(
        data.values()
    )


    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
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
            "Points marqués par action"
        )


        _plot_pie(
            ax2,
            points_against,
            "Points encaissés par action"
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
    # Fin
    # =====================================================
