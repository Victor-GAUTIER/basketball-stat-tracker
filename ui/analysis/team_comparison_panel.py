"""Onglet de comparaison des deux équipes, façon page 'Game Stats' FIBA.

Affiche :
- le score par quart-temps
- des barres de comparaison tête-à-tête (tirs, rebonds, passes, pertes...)
- les meneuses de chaque équipe (points, rebonds, passes)
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


HOME_COLOR = QColor(41, 128, 185)    # bleu, même couleur que le shot chart
AWAY_COLOR = QColor(230, 126, 34)    # orange, même couleur que le shot chart


# Statistiques affichées comme barres de comparaison, dans l'ordre.
# (clé_dans_team_stats, libellé, "pct" ou "count")
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


class ComparisonBarWidget(QWidget):
    """Une ligne de comparaison tête-à-tête pour une statistique donnée :
    barre bleue (domicile) partant de la gauche, barre orange (extérieur)
    partant de la droite, libellé de la statistique au centre."""

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._label = label
        self._home_text = "0"
        self._away_text = "0"
        self._home_ratio = 0.0
        self._away_ratio = 0.0

        self.setMinimumHeight(34)

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

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid = w // 2

        bar_h = 14
        bar_y = h // 2 - bar_h // 2

        # Barre domicile : grandit vers le centre depuis la gauche.
        home_len = int(mid * self._home_ratio)
        painter.fillRect(mid - home_len, bar_y, home_len, bar_h, HOME_COLOR)

        # Barre extérieur : grandit vers le centre depuis la droite.
        away_len = int((w - mid) * self._away_ratio)
        painter.fillRect(mid, bar_y, away_len, bar_h, AWAY_COLOR)

        # Libellé de la statistique, centré au-dessus des barres.
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(0, 0, w, bar_y, Qt.AlignmentFlag.AlignCenter, self._label)

        # Valeurs, de part et d'autre du centre.
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(0, bar_y, mid - 8, bar_h, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._home_text)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(mid + 8, bar_y, w - mid - 8, bar_h, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._away_text)


class TeamComparisonPanel(QWidget):
    """Panneau complet : score par quart-temps, barres de comparaison,
    meneuses de chaque équipe."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # -------------------------
        # En-têtes équipes
        # -------------------------

        self.home_title = QLabel("Domicile")
        self.home_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {HOME_COLOR.name()};")

        self.away_title = QLabel("Extérieur")
        self.away_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {AWAY_COLOR.name()};")
        self.away_title.setAlignment(Qt.AlignmentFlag.AlignRight)

        titles_row = QHBoxLayout()
        titles_row.addWidget(self.home_title)
        titles_row.addWidget(self.away_title)
        layout.addLayout(titles_row)

        # -------------------------
        # Score par quart-temps
        # -------------------------

        self.quarter_table = QTableWidget(self)
        self.quarter_table.setRowCount(2)
        self.quarter_table.verticalHeader().setVisible(False)
        self.quarter_table.setMaximumHeight(90)
        self.quarter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quarter_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        layout.addWidget(self.quarter_table)

        # -------------------------
        # Barres de comparaison
        # -------------------------

        self._bars: Dict[str, ComparisonBarWidget] = {}

        for key, label, _kind in BAR_STATS:
            bar = ComparisonBarWidget(label, self)
            self._bars[key] = bar
            layout.addWidget(bar)

        # -------------------------
        # Meneuses
        # -------------------------

        leaders_title = QLabel("Meneuses")
        leaders_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(leaders_title)

        self.leader_labels: Dict[str, Tuple[QLabel, QLabel]] = {}

        for key, label in (("PTS", "Points"), ("REB", "Rebonds"), ("AST", "Passes décisives")):

            row = QHBoxLayout()

            home_label = QLabel("-")
            home_label.setStyleSheet(f"color: {HOME_COLOR.name()};")

            stat_label = QLabel(label)
            stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_label.setMinimumWidth(120)

            away_label = QLabel("-")
            away_label.setStyleSheet(f"color: {AWAY_COLOR.name()};")
            away_label.setAlignment(Qt.AlignmentFlag.AlignRight)

            row.addWidget(home_label)
            row.addWidget(stat_label)
            row.addWidget(away_label)

            layout.addLayout(row)

            self.leader_labels[key] = (home_label, away_label)

        layout.addStretch(1)

    # =====================================================
    # Actualisation
    # =====================================================

    def refresh(
        self,
        home_name: str,
        away_name: str,
        quarter_scores: Dict[int, Tuple[int, int]],
        home_stats: Dict[str, int],
        away_stats: Dict[str, int],
        home_leaders: Dict[str, Optional[Tuple[Player, int]]],
        away_leaders: Dict[str, Optional[Tuple[Player, int]]],
    ) -> None:

        self.home_title.setText(home_name)
        self.away_title.setText(away_name)

        self._refresh_quarter_table(home_name, away_name, quarter_scores)
        self._refresh_bars(home_stats, away_stats)
        self._refresh_leaders(home_leaders, away_leaders)

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

    @staticmethod
    def _bold_font() -> QFont:
        font = QFont()
        font.setBold(True)
        return font

    # =====================================================
    # Barres de comparaison
    # =====================================================

    def _refresh_bars(self, home_stats: Dict[str, int], away_stats: Dict[str, int]) -> None:

        for key, _label, kind in BAR_STATS:

            bar = self._bars[key]

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
