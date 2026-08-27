"""Onglet de comparaison des deux équipes, façon tableau de bord d'équipe
(voir ui.analysis.team_analysis_window), mais pour un seul match.

Structure en 5 sous-onglets :
- Overview : score par quart-temps, Four Factors, comparaison tête-à-tête
  complète, meneuses.
- Adresse : eFG%/2PT/3PT, points marqués par action, points par tir.
- Rebonds : répartition OREB/DREB.
- Pertes de balle : TOV% et répartition par type.
- Fautes : fautes, lancers francs.

Pour ne pas ralentir la saisie vidéo (refresh() est appelé après CHAQUE
événement enregistré), la reconstruction des graphiques matplotlib de
chaque sous-onglet est différée : seul l'onglet actuellement visible est
reconstruit immédiatement, les autres sont simplement marqués comme
"à reconstruire" et ne le seront qu'au moment où l'utilisateur les
consulte.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data.models import Player

from ui.theme import get_chart_colors, theme_manager

DEFAULT_HOME_COLOR = "#2980b9"
DEFAULT_AWAY_COLOR = "#e67e22"

# Couleurs des figures/cartes, dépendantes du thème actif — voir
# _refresh_theme_colors(), rappelée à chaque changement de thème.
FIGURE_BG_COLOR = ""
FIGURE_TEXT_COLOR = ""


def _refresh_theme_colors() -> None:

    global FIGURE_BG_COLOR, FIGURE_TEXT_COLOR

    colors = get_chart_colors()

    FIGURE_BG_COLOR = colors["card"]
    FIGURE_TEXT_COLOR = colors["text"]


_refresh_theme_colors()

# Statistiques affichées comme barres de comparaison tête-à-tête, dans
# l'onglet Overview (clé_dans_team_stats, libellé, "pct" ou "count").
BAR_STATS = [
    ("FG", "Tirs réussis", "pct"),
    ("2PTS", "Tirs à 2 points", "pct"),
    ("3PTS", "Tirs à 3 points", "pct"),
    ("FT", "Lancers francs", "pct"),
    ("REB", "Rebonds", "count"),
    ("AST", "Passes décisives", "count"),
    ("STL", "Interceptions", "count"),
    ("BLK", "Contres", "count"),
    ("TO", "Pertes de balle", "count"),
    ("PF", "Fautes", "count"),
]

_ACTION_COLOR_PALETTE = [
    "#297ffe", "#e51f1f", "#2ecc71", "#f1c40f", "#9b59b6",
    "#e67e22", "#1abc9c", "#e84393", "#7f8c8d", "#3498db",
]

# =====================================================
# Fonctions utilitaires (mise en page)
# =====================================================


def _scrollable() -> Tuple[QScrollArea, QVBoxLayout]:

    inner = QWidget()
    layout = QVBoxLayout(inner)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setWidget(inner)

    return scroll, layout


def _clear_layout(layout: QVBoxLayout) -> None:

    while layout.count():

        item = layout.takeAt(0)
        widget = item.widget()

        if widget:
            widget.deleteLater()


def _style_axes(ax) -> None:
    """Applique le style sombre (fond gris, texte blanc) à un axe
    matplotlib : fond, titre, labels d'axes, ticks et bordures."""

    ax.set_facecolor(FIGURE_BG_COLOR)

    ax.title.set_color(FIGURE_TEXT_COLOR)
    ax.xaxis.label.set_color(FIGURE_TEXT_COLOR)
    ax.yaxis.label.set_color(FIGURE_TEXT_COLOR)

    ax.tick_params(colors=FIGURE_TEXT_COLOR)

    for spine in ax.spines.values():
        spine.set_color(FIGURE_TEXT_COLOR)


def _make_canvas(figure: Figure) -> QWidget:

    figure.patch.set_facecolor(FIGURE_BG_COLOR)

    canvas = FigureCanvas(figure)
    canvas.setStyleSheet(f"background: {FIGURE_BG_COLOR};")

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(canvas)

    container.setMinimumHeight(
        int(figure.get_size_inches()[1] * figure.dpi)
    )

    return container


def _build_stat_row(stats: List[Tuple[str, str, Optional[str]]]) -> QWidget:
    """Cartes statistiques : (valeur, libellé, couleur optionnelle)."""

    row = QWidget()
    row_layout = QHBoxLayout(row)

    for value, label, color in stats:

        card = QWidget()
        card.setStyleSheet(
            f"QWidget {{ background-color: {FIGURE_BG_COLOR}; border-radius: 10px; }}"
        )

        card_layout = QVBoxLayout(card)

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(
            f"color:{color or FIGURE_TEXT_COLOR}; font-size:20px; font-weight:bold;"
        )

        caption_label = QLabel(label)
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_label.setWordWrap(True)
        caption_label.setStyleSheet(f"color:{FIGURE_TEXT_COLOR}; font-size:11px;")

        card_layout.addWidget(value_label)
        card_layout.addWidget(caption_label)

        row_layout.addWidget(card)

    return row


def _build_action_color_map(*data_dicts: Dict[str, float]) -> Dict[str, str]:
    """Attribue une couleur fixe à chaque type d'action, identique quel
    que soit le graphique où elle apparaît (domicile / extérieur, points
    marqués / pertes de balle...). Les actions sont triées par ordre
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


def _plot_pie(ax, data: Dict[str, float], title: str, color_map: Optional[Dict[str, str]] = None) -> None:

    _style_axes(ax)

    if not data:
        ax.set_title(title, color=FIGURE_TEXT_COLOR)
        ax.axis("off")
        return

    # Tri par taille de secteur décroissante (voir team_analysis_window._plot_pie).
    sorted_items = sorted(data.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    colors = (
        [color_map.get(label) for label in labels]
        if color_map
        else None
    )

    ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.0f%%",
        textprops={"fontsize": 8, "color": FIGURE_TEXT_COLOR},
    )

    ax.set_title(title, fontsize=10, fontweight="bold", color=FIGURE_TEXT_COLOR)


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

    _style_axes(ax)

    total = val1 + val2

    if total <= 0:
        ax.set_title(title, color=FIGURE_TEXT_COLOR)
        ax.axis("off")
        return

    colors = [color1, color2]

    wedges, texts, autotexts = ax.pie(
        [val1, val2],
        labels=[label1, label2],
        colors=colors,
        autopct="%1.0f%%",
        pctdistance=0.6,
        textprops={"fontweight": "bold"},
    )

    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")
        autotext.set_fontsize(13)

    # Les libellés (noms d'équipes) restent dans la couleur de l'équipe
    # correspondante pour rester lisibles sur fond gris et garder
    # l'association visuelle avec les couleurs domicile/extérieur.
    for text, color in zip(texts, colors):
        text.set_color(color)
        text.set_fontweight("bold")

    ax.set_title(title, fontsize=11, fontweight="bold", color=FIGURE_TEXT_COLOR)


def _plot_grouped_bar(
    ax,
    labels: List[str],
    series: Dict[str, List[float]],
    title: str,
    ylabel: str,
    colors: Optional[List[str]] = None,
) -> None:

    _style_axes(ax)

    if not labels:
        ax.set_title(title, fontsize=10, color=FIGURE_TEXT_COLOR)
        ax.axis("off")
        return

    n_series = len(series)
    x = list(range(len(labels)))
    width = 0.8 / max(n_series, 1)

    for i, (name, values) in enumerate(series.items()):

        offset = (i - (n_series - 1) / 2) * width
        positions = [xi + offset for xi in x]

        color = colors[i] if colors and i < len(colors) else None

        bars = ax.bar(positions, values, width=width, label=name, color=color)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=FIGURE_TEXT_COLOR,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8, color=FIGURE_TEXT_COLOR)
    ax.set_title(title, fontsize=10, fontweight="bold", color=FIGURE_TEXT_COLOR)
    ax.set_ylabel(ylabel, color=FIGURE_TEXT_COLOR)

    legend = ax.legend(fontsize=8)
    legend.get_frame().set_facecolor(FIGURE_BG_COLOR)
    for text in legend.get_texts():
        text.set_color(FIGURE_TEXT_COLOR)


# =====================================================
# Barre de comparaison tête-à-tête (onglet Overview)
# =====================================================


class ComparisonBarWidget(QWidget):
    """Une ligne de comparaison tête-à-tête pour une statistique donnée :
    barre colorée équipe domicile partant de la gauche, barre équipe
    extérieure partant de la droite, libellé de la statistique au centre."""

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._label = label
        self._home_text = "0"
        self._away_text = "0"
        self._home_ratio = 0.0
        self._away_ratio = 0.0

        self._home_color = QColor(DEFAULT_HOME_COLOR)
        self._away_color = QColor(DEFAULT_AWAY_COLOR)

        self.setMinimumHeight(34)

    def set_colors(self, home_color: str, away_color: str) -> None:
        self._home_color = QColor(home_color)
        self._away_color = QColor(away_color)
        self.update()

    def set_values(
        self,
        home_text: str,
        away_text: str,
        home_ratio: float,
        away_ratio: float,
    ) -> None:
        """ratio : proportion 0..1 de la longueur de la barre dans sa moitié."""
        self._home_text = home_text
        self._away_text = away_text
        self._home_ratio = max(0.0, min(1.0, home_ratio))
        self._away_ratio = max(0.0, min(1.0, away_ratio))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802

        from PySide6.QtGui import QPainter, QFont as _QFont

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid = w // 2

        bar_h = 14
        bar_y = h // 2 - bar_h // 2

        home_len = int(mid * self._home_ratio)
        painter.fillRect(mid - home_len, bar_y, home_len, bar_h, self._home_color)

        away_len = int((w - mid) * self._away_ratio)
        painter.fillRect(mid, bar_y, away_len, bar_h, self._away_color)

        font = _QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(0, 0, w, bar_y, Qt.AlignmentFlag.AlignCenter, self._label)

        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)

        painter.setPen(QColor(60, 60, 60))
        painter.drawText(
            0, bar_y, mid - 8, bar_h,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self._home_text,
        )

        painter.setPen(QColor(60, 60, 60))
        painter.drawText(
            mid + 8, bar_y, w - mid - 8, bar_h,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._away_text,
        )


# =====================================================
# Panneau principal
# =====================================================


class TeamComparisonPanel(QWidget):
    """Panneau complet à onglets : Overview, Adresse, Rebonds, Pertes de
    balle, Fautes — pour le match en cours."""

    TAB_OVERVIEW = 0
    TAB_ADRESSE = 1
    TAB_REBONDS = 2
    TAB_TURNOVERS = 3
    TAB_FOULS = 4

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Dernières données reçues via refresh(), utilisées pour la
        # reconstruction différée des onglets non visibles.
        self._latest: Optional[dict] = None
        self._dirty_tabs = {
            self.TAB_OVERVIEW,
            self.TAB_ADRESSE,
            self.TAB_REBONDS,
            self.TAB_TURNOVERS,
            self.TAB_FOULS,
        }

        layout = QVBoxLayout(self)

        # -------------------------
        # En-têtes équipes
        # -------------------------

        self.home_title = QLabel("Domicile")
        self.home_title.setStyleSheet(
            f"font-weight: bold; font-size: 16px; color: {DEFAULT_HOME_COLOR};"
        )

        self.away_title = QLabel("Extérieur")
        self.away_title.setStyleSheet(
            f"font-weight: bold; font-size: 16px; color: {DEFAULT_AWAY_COLOR};"
        )
        self.away_title.setAlignment(Qt.AlignmentFlag.AlignRight)

        titles_row = QHBoxLayout()
        titles_row.addWidget(self.home_title)
        titles_row.addWidget(self.away_title)
        layout.addLayout(titles_row)

        # -------------------------
        # Onglets
        # -------------------------

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # --- Overview ---
        self.overview_scroll, self.overview_layout = _scrollable()

        self.quarter_table = QTableWidget(self)
        self.quarter_table.setRowCount(2)
        self.quarter_table.verticalHeader().setVisible(False)
        self.quarter_table.setMaximumHeight(90)
        self.quarter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quarter_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.overview_layout.addWidget(self.quarter_table)

        self._four_factors_container = QWidget()
        self._four_factors_layout = QVBoxLayout(self._four_factors_container)
        self._four_factors_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_layout.addWidget(self._four_factors_container)

        self._bars: Dict[str, ComparisonBarWidget] = {}
        bars_title = QLabel("Comparaison détaillée")
        bars_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.overview_layout.addWidget(bars_title)

        for key, label, _kind in BAR_STATS:
            bar = ComparisonBarWidget(label, self)
            self._bars[key] = bar
            self.overview_layout.addWidget(bar)

        leaders_title = QLabel("Meneuses")
        leaders_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.overview_layout.addWidget(leaders_title)

        self.leader_labels: Dict[str, Tuple[QLabel, QLabel]] = {}

        for key, label in (("PTS", "Points"), ("REB", "Rebonds"), ("AST", "Passes décisives")):

            row = QHBoxLayout()

            home_label = QLabel("-")
            stat_label = QLabel(label)
            stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_label.setMinimumWidth(120)
            away_label = QLabel("-")
            away_label.setAlignment(Qt.AlignmentFlag.AlignRight)

            row.addWidget(home_label)
            row.addWidget(stat_label)
            row.addWidget(away_label)

            self.overview_layout.addLayout(row)

            self.leader_labels[key] = (home_label, away_label)

        self.overview_layout.addStretch(1)

        self.tabs.addTab(self.overview_scroll, "Overview")

        # --- Adresse ---
        self.adresse_scroll, self.adresse_layout = _scrollable()
        self.tabs.addTab(self.adresse_scroll, "Adresse")

        # --- Rebonds ---
        self.rebonds_scroll, self.rebonds_layout = _scrollable()
        self.tabs.addTab(self.rebonds_scroll, "Rebonds")

        # --- Pertes de balle ---
        self.turnovers_scroll, self.turnovers_layout = _scrollable()
        self.tabs.addTab(self.turnovers_scroll, "Pertes de balle")

        # --- Fautes ---
        self.fouls_scroll, self.fouls_layout = _scrollable()
        self.tabs.addTab(self.fouls_scroll, "Fautes")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        theme_manager.theme_changed.connect(self._on_theme_changed)

    # =====================================================
    # Rafraîchissement
    # =====================================================

    def refresh(
        self,
        home_name: str,
        away_name: str,
        home_color: str,
        away_color: str,
        quarter_scores: Dict[int, Tuple[int, int]],
        home_stats: Dict[str, int],
        away_stats: Dict[str, int],
        home_leaders: Dict[str, Optional[Tuple[Player, int]]],
        away_leaders: Dict[str, Optional[Tuple[Player, int]]],
        comparison_data: TeamComparisonData,
    ) -> None:

        self.home_title.setText(home_name)
        self.home_title.setStyleSheet(
            f"font-weight: bold; font-size: 16px; color: {home_color};"
        )

        self.away_title.setText(away_name)
        self.away_title.setStyleSheet(
            f"font-weight: bold; font-size: 16px; color: {away_color};"
        )

        self._latest = {
            "home_name": home_name,
            "away_name": away_name,
            "home_color": home_color,
            "away_color": away_color,
            "quarter_scores": quarter_scores,
            "home_stats": home_stats,
            "away_stats": away_stats,
            "home_leaders": home_leaders,
            "away_leaders": away_leaders,
            "data": comparison_data,
        }

        # Le tableau des scores par quart-temps et les barres tête-à-tête
        # sont peu coûteux : on les met à jour à chaque refresh, quel que
        # soit l'onglet visible.
        self._refresh_quarter_table(home_name, away_name, quarter_scores)
        self._refresh_bars(home_color, away_color, home_stats, away_stats)
        self._refresh_leaders(home_leaders, away_leaders)

        self._dirty_tabs = {
            self.TAB_OVERVIEW,
            self.TAB_ADRESSE,
            self.TAB_REBONDS,
            self.TAB_TURNOVERS,
            self.TAB_FOULS,
        }

        self._rebuild_tab(self.tabs.currentIndex())

    def _on_tab_changed(self, index: int) -> None:

        if index in self._dirty_tabs and self._latest is not None:
            self._rebuild_tab(index)

    def _on_theme_changed(self, theme: str) -> None:
        """Reconstruit les graphiques de l'onglet actuellement visible
        avec les couleurs du nouveau thème ; les autres onglets seront
        reconstruits à la volée dès qu'ils redeviennent visibles (même
        mécanisme que le rafraîchissement différé habituel)."""

        _refresh_theme_colors()

        self._dirty_tabs = {
            self.TAB_OVERVIEW,
            self.TAB_ADRESSE,
            self.TAB_REBONDS,
            self.TAB_TURNOVERS,
            self.TAB_FOULS,
        }

        if self._latest is not None:
            self._rebuild_tab(self.tabs.currentIndex())


    def _rebuild_tab(self, index: int) -> None:

        if self._latest is None:
            return

        if index == self.TAB_OVERVIEW:
            self._populate_four_factors()
        elif index == self.TAB_ADRESSE:
            self._populate_adresse()
        elif index == self.TAB_REBONDS:
            self._populate_rebonds()
        elif index == self.TAB_TURNOVERS:
            self._populate_turnovers()
        elif index == self.TAB_FOULS:
            self._populate_fouls()

        self._dirty_tabs.discard(index)

    @staticmethod
    def _bold_font() -> QFont:
        font = QFont()
        font.setBold(True)
        return font

    # =====================================================
    # Score par quart-temps
    # =====================================================

    def _refresh_quarter_table(
        self,
        home_name: str,
        away_name: str,
        quarter_scores: Dict[int, Tuple[int, int]],
    ) -> None:

        has_overtime = any(q >= 5 for q in quarter_scores)

        quarters = [1, 2, 3, 4] + ([5] if has_overtime else [])
        headers = [f"Q{q}" if q <= 4 else "OT" for q in quarters] + ["TOTAL"]

        self.quarter_table.setColumnCount(len(headers))
        self.quarter_table.setHorizontalHeaderLabels(headers)
        self.quarter_table.setVerticalHeaderLabels([home_name, away_name])

        home_total = 0
        away_total = 0

        for col, quarter in enumerate(quarters):

            home_pts, away_pts = quarter_scores.get(quarter, (0, 0))

            home_total += home_pts
            away_total += away_pts

            self.quarter_table.setItem(0, col, QTableWidgetItem(str(home_pts)))
            self.quarter_table.setItem(1, col, QTableWidgetItem(str(away_pts)))

        total_col = len(quarters)

        home_total_item = QTableWidgetItem(str(home_total))
        home_total_item.setFont(self._bold_font())
        self.quarter_table.setItem(0, total_col, home_total_item)

        away_total_item = QTableWidgetItem(str(away_total))
        away_total_item.setFont(self._bold_font())
        self.quarter_table.setItem(1, total_col, away_total_item)

        self.quarter_table.resizeColumnsToContents()

    # =====================================================
    # Barres tête-à-tête
    # =====================================================

    def _refresh_bars(
        self,
        home_color: str,
        away_color: str,
        home_stats: Dict[str, int],
        away_stats: Dict[str, int],
    ) -> None:

        for key, _label, kind in BAR_STATS:

            bar = self._bars[key]
            bar.set_colors(home_color, away_color)

            if kind == "pct":

                home_made = home_stats.get(f"{key}_MADE", 0)
                home_att = home_stats.get(f"{key}_ATT", 0)
                away_made = away_stats.get(f"{key}_MADE", 0)
                away_att = away_stats.get(f"{key}_ATT", 0)

                home_pct = (home_made / home_att * 100) if home_att else 0.0
                away_pct = (away_made / away_att * 100) if away_att else 0.0

                bar.set_values(
                    f"{home_made}/{home_att} ({round(home_pct)}%)",
                    f"{away_made}/{away_att} ({round(away_pct)}%)",
                    home_pct / 100,
                    away_pct / 100,
                )

            else:

                home_value = home_stats.get(key, 0)
                away_value = away_stats.get(key, 0)

                max_value = max(home_value, away_value, 1)

                bar.set_values(
                    str(home_value),
                    str(away_value),
                    home_value / max_value,
                    away_value / max_value,
                )

    # =====================================================
    # Meneuses
    # =====================================================

    def _refresh_leaders(
        self,
        home_leaders: Dict[str, Optional[Tuple[Player, int]]],
        away_leaders: Dict[str, Optional[Tuple[Player, int]]],
    ) -> None:

        for key, (home_label, away_label) in self.leader_labels.items():
            home_label.setText(self._format_leader(home_leaders.get(key)))
            away_label.setText(self._format_leader(away_leaders.get(key)))

    @staticmethod
    def _format_leader(entry: Optional[Tuple[Player, int]]) -> str:

        if entry is None:
            return "-"

        player, value = entry
        return f"#{player.number} {player.name} ({value})"

    # =====================================================
    # Overview : Four Factors
    # =====================================================

    def _populate_four_factors(self) -> None:

        _clear_layout(self._four_factors_layout)

        assert self._latest is not None
        home_name = self._latest["home_name"]
        away_name = self._latest["away_name"]
        home_color = self._latest["home_color"]
        away_color = self._latest["away_color"]
        data: TeamComparisonData = self._latest["data"]

        home_box = data.home_box
        away_box = data.away_box

        factors = ["eFG%", "TOV%", "Reb. Off %", "FT Rate"]

        home_values = [
            home_box.efg_pct,
            home_box.tov_pct,
            home_box.oreb_pct(away_box.dreb),
            home_box.ft_rate,
        ]

        away_values = [
            away_box.efg_pct,
            away_box.tov_pct,
            away_box.oreb_pct(home_box.dreb),
            away_box.ft_rate,
        ]

        fig = Figure(figsize=(7, 3.2))
        ax = fig.subplots()

        _plot_grouped_bar(
            ax,
            factors,
            {home_name: home_values, away_name: away_values},
            "Four Factors",
            "%",
            colors=[home_color, away_color],
        )

        fig.tight_layout()

        self._four_factors_layout.addWidget(_make_canvas(fig))

        self._four_factors_layout.addWidget(
            _build_stat_row(
                [
                    (f"{home_box.possessions:.1f}", f"Possessions {home_name}", home_color),
                    (f"{away_box.possessions:.1f}", f"Possessions {away_name}", away_color),
                    (f"{home_box.points_per_shot:.2f}", "Points / tir (domicile)", home_color),
                    (f"{away_box.points_per_shot:.2f}", "Points / tir (extérieur)", away_color),
                ]
            )
        )

    # =====================================================
    # Adresse
    # =====================================================

    def _populate_adresse(self) -> None:

        _clear_layout(self.adresse_layout)

        assert self._latest is not None
        home_name = self._latest["home_name"]
        away_name = self._latest["away_name"]
        home_color = self._latest["home_color"]
        away_color = self._latest["away_color"]
        data: TeamComparisonData = self._latest["data"]

        home_box = data.home_box
        away_box = data.away_box

        self.adresse_layout.addWidget(
            _build_stat_row(
                [
                    (f"{home_box.efg_pct:.1f}%", f"eFG% {home_name}", home_color),
                    (f"{away_box.efg_pct:.1f}%", f"eFG% {away_name}", away_color),
                ]
            )
        )

        self.adresse_layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{home_box.fgm2}/{home_box.fga2} ({home_box.two_pt_pct:.0f}%)",
                        f"2 points {home_name}", home_color,
                    ),
                    (
                        f"{home_box.p3m}/{home_box.fga3} ({home_box.three_pt_pct:.0f}%)",
                        f"3 points {home_name}", home_color,
                    ),
                    (
                        f"{away_box.fgm2}/{away_box.fga2} ({away_box.two_pt_pct:.0f}%)",
                        f"2 points {away_name}", away_color,
                    ),
                    (
                        f"{away_box.p3m}/{away_box.fga3} ({away_box.three_pt_pct:.0f}%)",
                        f"3 points {away_name}", away_color,
                    ),
                ]
            )
        )

        action_colors = _build_action_color_map(
            data.home_points_by_action,
            data.away_points_by_action,
        )

        fig = Figure(figsize=(8, 3.5))
        ax1, ax2 = fig.subplots(1, 2)

        _plot_pie(ax1, data.home_points_by_action, f"Points marqués — {home_name}", action_colors)
        _plot_pie(ax2, data.away_points_by_action, f"Points marqués — {away_name}", action_colors)

        fig.tight_layout()
        self.adresse_layout.addWidget(_make_canvas(fig))

        # Points par tir selon l'action, comparés tête-à-tête.
        actions = sorted(
            {
                a for a in list(data.home_fga_by_action) + list(data.away_fga_by_action)
                if a.lower() != "non renseigné"
            }
        )

        home_pps = []
        away_pps = []
        used_actions = []

        for action in actions:

            home_fga = data.home_fga_by_action.get(action, 0)
            away_fga = data.away_fga_by_action.get(action, 0)

            if home_fga < 2 and away_fga < 2:
                continue

            used_actions.append(action)

            home_pts = data.home_points_by_action.get(action, 0)
            away_pts = data.away_points_by_action.get(action, 0)

            home_pps.append((home_pts / home_fga) if home_fga else 0.0)
            away_pps.append((away_pts / away_fga) if away_fga else 0.0)

        if used_actions:

            fig2 = Figure(figsize=(8, 3.2))
            ax3 = fig2.subplots()

            _plot_grouped_bar(
                ax3,
                used_actions,
                {home_name: home_pps, away_name: away_pps},
                "Points par tir selon l'action",
                "Points / tir",
                colors=[home_color, away_color],
            )

            fig2.tight_layout()
            self.adresse_layout.addWidget(_make_canvas(fig2))

        self.adresse_layout.addStretch(1)

    # =====================================================
    # Rebonds
    # =====================================================

    def _populate_rebonds(self) -> None:

        _clear_layout(self.rebonds_layout)

        assert self._latest is not None
        home_name = self._latest["home_name"]
        away_name = self._latest["away_name"]
        home_color = self._latest["home_color"]
        away_color = self._latest["away_color"]
        data: TeamComparisonData = self._latest["data"]

        home_box = data.home_box
        away_box = data.away_box

        self.rebonds_layout.addWidget(
            _build_stat_row(
                [
                    (
                        str(data.home_points_by_action.get("Reb off", 0)),
                        f"Points après rebond offensif — {home_name}",
                        home_color,
                    ),
                    (
                        str(data.away_points_by_action.get("Reb off", 0)),
                        f"Points après rebond offensif — {away_name}",
                        away_color,
                    ),
                ]
            )
        )

        fig = Figure(figsize=(11, 4))
        ax1, ax2, ax3 = fig.subplots(1, 3)

        _plot_pie_2(
            ax1,
            home_box.oreb,
            away_box.dreb,
            f"OREB {home_name}",
            f"DREB {away_name}",
            home_color,
            away_color,
            f"Quand {home_name} tire",
        )

        _plot_pie_2(
            ax2,
            away_box.oreb,
            home_box.dreb,
            f"OREB {away_name}",
            f"DREB {home_name}",
            away_color,
            home_color,
            f"Quand {away_name} tire",
        )

        _plot_pie_2(
            ax3,
            home_box.oreb + home_box.dreb,
            away_box.oreb + away_box.dreb,
            home_name,
            away_name,
            home_color,
            away_color,
            "Part des rebonds captés",
        )

        fig.tight_layout()
        self.rebonds_layout.addWidget(_make_canvas(fig))

        self.rebonds_layout.addStretch(1)

    # =====================================================
    # Pertes de balle
    # =====================================================

    def _populate_turnovers(self) -> None:

        _clear_layout(self.turnovers_layout)

        assert self._latest is not None
        home_name = self._latest["home_name"]
        away_name = self._latest["away_name"]
        home_color = self._latest["home_color"]
        away_color = self._latest["away_color"]
        data: TeamComparisonData = self._latest["data"]

        home_box = data.home_box
        away_box = data.away_box

        self.turnovers_layout.addWidget(
            _build_stat_row(
                [
                    (f"{home_box.tov_pct:.1f}%", f"TOV% {home_name}", home_color),
                    (f"{away_box.tov_pct:.1f}%", f"TOV% {away_name}", away_color),
                ]
            )
        )

        if data.home_turnover_breakdown or data.away_turnover_breakdown:

            turnover_colors = _build_action_color_map(
                data.home_turnover_breakdown,
                data.away_turnover_breakdown,
            )

            fig = Figure(figsize=(9, 3.8))
            ax1, ax2 = fig.subplots(1, 2)

            _plot_pie(ax1, data.home_turnover_breakdown, f"Pertes de balle — {home_name}", turnover_colors)
            _plot_pie(ax2, data.away_turnover_breakdown, f"Pertes de balle — {away_name}", turnover_colors)

            fig.tight_layout()
            self.turnovers_layout.addWidget(_make_canvas(fig))

        else:

            self.turnovers_layout.addWidget(
                QLabel("Aucune perte de balle enregistrée pour l'instant.")
            )

        self.turnovers_layout.addStretch(1)

    # =====================================================
    # Fautes
    # =====================================================

    def _populate_fouls(self) -> None:

        _clear_layout(self.fouls_layout)

        assert self._latest is not None
        home_name = self._latest["home_name"]
        away_name = self._latest["away_name"]
        home_color = self._latest["home_color"]
        away_color = self._latest["away_color"]
        data: TeamComparisonData = self._latest["data"]

        home_box = data.home_box
        away_box = data.away_box

        self.fouls_layout.addWidget(
            _build_stat_row(
                [
                    (str(home_box.fouls), f"Fautes {home_name}", home_color),
                    (str(away_box.fouls), f"Fautes {away_name}", away_color),
                ]
            )
        )

        self.fouls_layout.addWidget(
            _build_stat_row(
                [
                    (
                        f"{home_box.ftm}/{home_box.fta} ({home_box.ft_pct:.0f}%)",
                        f"Lancers francs {home_name}", home_color,
                    ),
                    (
                        f"{away_box.ftm}/{away_box.fta} ({away_box.ft_pct:.0f}%)",
                        f"Lancers francs {away_name}", away_color,
                    ),
                ]
            )
        )

        self.fouls_layout.addStretch(1)
