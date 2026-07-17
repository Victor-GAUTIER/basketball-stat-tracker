"""Fenêtre récapitulative du shot chart d'un match.

Reprend le même terrain (forme, rotation) que le terrain de saisie des tirs
(ShotChartWidget), mais en lecture seule : tous les tirs du match y sont
superposés, un rond pour un tir marqué, une croix pour un tir manqué, une
couleur par équipe. Les tirs de chaque équipe sont toujours affichés du même
côté du terrain (les tirs pris après le changement de camp, à partir du 3e
quart-temps, sont symétrisés horizontalement pour rester cohérents avec le
reste du match) : voir AnalysisWindow._compute_shot_markers().
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ShotChartSummaryWidget(QWidget):
    """Terrain (même rendu que le terrain de saisie) avec les tirs du match
    superposés : ronds pour les tirs marqués, croix pour les tirs manqués."""

    HOME_COLOR = QColor(41, 128, 185)    # bleu
    AWAY_COLOR = QColor(230, 126, 34)    # orange

    MARKER_RADIUS = 5

    def __init__(self, svg_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.pixmap = QPixmap(svg_path)

        self.setMinimumSize(500, 260)

        self._markers: List[Dict] = []
        self._home_label = "Domicile"
        self._away_label = "Extérieur"

    def set_team_labels(self, home_label: str, away_label: str) -> None:
        self._home_label = home_label
        self._away_label = away_label
        self.update()

    def set_shots(self, markers: List[Dict]) -> None:
        """markers : liste de dicts {x, y, made, is_home}, x/y normalisés
        (0..1) dans le même repère que le terrain de saisie des tirs."""
        self._markers = markers
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)

        if self.pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Même transformation que le terrain de saisie : rotation 90°,
        # redimensionnement en conservant les proportions, centrage.
        court = self.pixmap.transformed(
            QTransform().rotate(90),
            Qt.TransformationMode.SmoothTransformation,
        )

        court = court.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_offset = (self.width() - court.width()) // 2
        y_offset = (self.height() - court.height()) // 2 + 5

        painter.drawPixmap(x_offset, y_offset, court)

        # Libellés d'équipe au-dessus de chaque moitié.
        half_width = court.width() // 2

        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)

        painter.setPen(self.AWAY_COLOR)
        painter.drawText(
            x_offset, max(0, y_offset - 10), half_width, 18,
            Qt.AlignmentFlag.AlignCenter, self._away_label,
        )
        painter.setPen(self.HOME_COLOR)
        painter.drawText(
            x_offset + half_width, max(0, y_offset - 20), court.width() - half_width, 18,
            Qt.AlignmentFlag.AlignCenter, self._home_label,
        )

        # Tirs : ronds pleins = marqués, croix = manqués.
        for marker in self._markers:

            color = self.HOME_COLOR if marker["is_home"] else self.AWAY_COLOR

            px = x_offset + marker["x"] * court.width()
            py = y_offset + marker["y"] * court.height()

            painter.setPen(QPen(color, 2))

            if marker["made"]:
                painter.setBrush(color)
                r = self.MARKER_RADIUS
                painter.drawEllipse(int(px - r), int(py - r), r * 2, r * 2)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                r = self.MARKER_RADIUS
                painter.drawLine(int(px - r), int(py - r), int(px + r), int(py + r))
                painter.drawLine(int(px - r), int(py + r), int(px + r), int(py - r))


class ShotChartSummaryPanel(QWidget):
    """Panneau (terrain + légende) destiné à être intégré comme onglet,
    au même titre que les onglets Analyse, Statistiques et Play by play."""

    def __init__(self, svg_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.chart = ShotChartSummaryWidget(svg_path, self)
        layout.addWidget(self.chart, stretch=1)

        self.set_team_labels("Domicile", "Extérieur")

    def set_team_labels(self, home_label: str, away_label: str) -> None:
        self.chart.set_team_labels(home_label, away_label)

    def set_shots(self, markers: List[Dict]) -> None:
        self.chart.set_shots(markers)
