"""Fenêtre récapitulative du shot chart d'un match.

Reprend le même terrain (forme, rotation) que le terrain de saisie des tirs
(ShotChartWidget), mais en lecture seule : tous les tirs du match y sont
superposés, un rond pour un tir marqué, une croix pour un tir manqué, une
couleur par équipe. Les tirs de chaque équipe sont toujours affichés du même
côté du terrain (les tirs pris après le changement de camp, à partir du 3e
quart-temps, sont symétrisés horizontalement pour rester cohérents avec le
reste du match) : voir AnalysisWindow._compute_shot_markers().

Un bandeau de filtres permet de restreindre l'affichage à une joueuse en
particulier, et/ou de masquer les tirs marqués ou manqués.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from data.models import Player

# Valeur utilisée dans le combo de filtre pour représenter "toutes les joueuses"
ALL_PLAYERS = -1


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
        """markers : liste de dicts {x, y, made, is_home, player_id},
        x/y normalisés (0..1) dans le même repère que le terrain de saisie
        des tirs. Cette liste est déjà filtrée par ShotChartSummaryPanel."""
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
    """Panneau (filtres + terrain + légende) destiné à être intégré comme
    onglet, au même titre que les onglets Analyse, Statistiques et Play by
    play."""

    def __init__(self, svg_path: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # -------------------------
        # Bandeau de filtres
        # -------------------------

        filters_layout = QHBoxLayout()

        filters_layout.addWidget(QLabel("Joueuse :"))

        self.player_combo = QComboBox(self)
        self.player_combo.addItem("Toutes les joueuses", ALL_PLAYERS)
        self.player_combo.currentIndexChanged.connect(self._on_filters_changed)

        filters_layout.addWidget(self.player_combo, stretch=1)

        self.made_checkbox = QCheckBox("Tirs marqués", self)
        self.made_checkbox.setChecked(True)
        self.made_checkbox.stateChanged.connect(self._on_filters_changed)

        self.missed_checkbox = QCheckBox("Tirs manqués", self)
        self.missed_checkbox.setChecked(True)
        self.missed_checkbox.stateChanged.connect(self._on_filters_changed)

        filters_layout.addWidget(self.made_checkbox)
        filters_layout.addWidget(self.missed_checkbox)

        layout.addLayout(filters_layout)

        # -------------------------
        # Terrain
        # -------------------------

        self.chart = ShotChartSummaryWidget(svg_path, self)
        layout.addWidget(self.chart, stretch=1)

        self.set_team_labels("Domicile", "Extérieur")

        self._all_markers: List[Dict] = []

    # =====================================================
    # Equipes / joueuses
    # =====================================================

    def set_team_labels(self, home_label: str, away_label: str) -> None:
        self.chart.set_team_labels(home_label, away_label)

    def set_players(self, players: List[Player]) -> None:
        """Alimente le menu déroulant de filtrage par joueuse.

        À appeler une fois les joueuses du match connues (typiquement au
        chargement du match), avec la liste combinée des deux équipes.
        """

        current_id = self.player_combo.currentData()

        self.player_combo.blockSignals(True)

        self.player_combo.clear()
        self.player_combo.addItem("Toutes les joueuses", ALL_PLAYERS)

        for player in sorted(players, key=lambda p: p.number):
            self.player_combo.addItem(
                f"#{player.number} {player.name}",
                player.id,
            )

        # Restaure la sélection précédente si la joueuse existe toujours
        index = self.player_combo.findData(current_id)
        self.player_combo.setCurrentIndex(index if index >= 0 else 0)

        self.player_combo.blockSignals(False)

        self._apply_filters()

    # =====================================================
    # Tirs
    # =====================================================

    def set_shots(self, markers: List[Dict]) -> None:
        """markers : liste de dicts {x, y, made, is_home, player_id}."""
        self._all_markers = markers
        self._apply_filters()

    # =====================================================
    # Filtrage
    # =====================================================

    def _on_filters_changed(self, *_args) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:

        selected_player_id = self.player_combo.currentData()
        show_made = self.made_checkbox.isChecked()
        show_missed = self.missed_checkbox.isChecked()

        filtered = []

        for marker in self._all_markers:

            if (
                selected_player_id not in (None, ALL_PLAYERS)
                and marker.get("player_id") != selected_player_id
            ):
                continue

            if marker["made"] and not show_made:
                continue

            if not marker["made"] and not show_missed:
                continue

            filtered.append(marker)

        self.chart.set_shots(filtered)
