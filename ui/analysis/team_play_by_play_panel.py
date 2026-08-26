"""Panneau play-by-play agrégé pour le tableau de bord d'équipe.

Reprend le principe du play-by-play match par match (voir
ui.analysis.play_by_play_panel), mais sur l'ensemble des matchs d'une
équipe : permet de filtrer une situation de jeu à travers plusieurs
matchs, puis d'exporter un montage vidéo combinant les extraits
correspondants, quel que soit leur match d'origine.

Les filtres sont répartis sur plusieurs lignes (un filtre "Matchs"
s'ajoute aux filtres habituels du play-by-play, et l'espace disponible
dans le tableau de bord d'équipe est plus contraint que dans la fenêtre
d'analyse d'un match).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Event, Player
from ui.analysis.event_labels import event_label
from ui.analysis.filters import MultiSelectFilter
from ui.analysis.play_by_play_panel import (
    SHOT_TYPES,
    SHOTS_ALL,
    SHOTS_MADE,
    SHOTS_MISSED,
    TURNOVERS_ALL,
)


TEAM_COLOR = QColor("#297ffe")
OPPONENT_COLOR = QColor("#b0b0b0")


class TeamPlayByPlayEvent:
    """Associe un événement à son match d'origine (libellé affiché dans la
    colonne "Match", et clé de regroupement pour l'export vidéo)."""

    __slots__ = ("event", "game_id", "game_label")

    def __init__(self, event: Event, game_id: int, game_label: str) -> None:
        self.event = event
        self.game_id = game_id
        self.game_label = game_label


class TeamPlayByPlayPanel(QWidget):
    """Play-by-play agrégé sur plusieurs matchs, pour la création de
    montages vidéo d'une situation type."""

    # (game_id, timestamp)
    event_seek_requested = Signal(int, float)

    # (events, before, after) — chaque Event conserve son game_id, le
    # regroupement par match/vidéo se fait côté fenêtre appelante.
    export_requested = Signal(list, float, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # -------------------------
        # Filtres (plusieurs lignes pour ne pas déborder de la fenêtre)
        # -------------------------

        self.match_filter = MultiSelectFilter("Matchs", [], self)
        self.match_filter.on_change = self._apply_filters

        self.player_filter = QComboBox(self)
        self.event_filter = QComboBox(self)
        self.phase_filter = QComboBox(self)
        self.system_filter = QComboBox(self)
        self.action_type_filter = QComboBox(self)

        for combo in (
            self.player_filter,
            self.event_filter,
            self.phase_filter,
            self.system_filter,
            self.action_type_filter,
        ):
            combo.currentIndexChanged.connect(self._apply_filters)

        filters_row_1 = QHBoxLayout()
        filters_row_1.addWidget(QLabel("Matchs :"))
        filters_row_1.addWidget(self.match_filter)
        filters_row_1.addWidget(QLabel("Joueuse :"))
        filters_row_1.addWidget(self.player_filter)
        filters_row_1.addStretch()

        filters_row_2 = QHBoxLayout()
        filters_row_2.addWidget(QLabel("Événement :"))
        filters_row_2.addWidget(self.event_filter)
        filters_row_2.addWidget(QLabel("Phase :"))
        filters_row_2.addWidget(self.phase_filter)
        filters_row_2.addStretch()

        filters_row_3 = QHBoxLayout()
        filters_row_3.addWidget(QLabel("Système :"))
        filters_row_3.addWidget(self.system_filter)
        filters_row_3.addWidget(QLabel("Type d'action :"))
        filters_row_3.addWidget(self.action_type_filter)
        filters_row_3.addStretch()

        filters_column = QVBoxLayout()
        filters_column.addLayout(filters_row_1)
        filters_column.addLayout(filters_row_2)
        filters_column.addLayout(filters_row_3)

        # -------------------------
        # Tableau
        # -------------------------

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Match", "Temps", "QT", "Joueuse",
            "Événement", "Phase", "Système", "Type d'action",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.cellDoubleClicked.connect(self._on_double_click)

        # -------------------------
        # Export vidéo
        # -------------------------

        self.export_before_spin = QDoubleSpinBox(self)
        self.export_before_spin.setRange(0.0, 30.0)
        self.export_before_spin.setValue(3.0)
        self.export_before_spin.setSuffix(" s avant")
        self.export_before_spin.setSingleStep(0.5)

        self.export_after_spin = QDoubleSpinBox(self)
        self.export_after_spin.setRange(0.0, 30.0)
        self.export_after_spin.setValue(2.0)
        self.export_after_spin.setSuffix(" s après")
        self.export_after_spin.setSingleStep(0.5)

        self.export_btn = QPushButton("🎬 Exporter le montage (tous matchs)")
        self.export_btn.clicked.connect(self._on_export_clicked)

        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("Durée des segments :"))
        export_row.addWidget(self.export_before_spin)
        export_row.addWidget(self.export_after_spin)
        export_row.addStretch()
        export_row.addWidget(self.export_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(filters_column)
        layout.addWidget(self.table)
        layout.addLayout(export_row)

        self._all_items: List[TeamPlayByPlayEvent] = []
        self._items: List[TeamPlayByPlayEvent] = []
        self._players: Dict[int, Player] = {}
        self._team_player_ids: Set[int] = set()

    # =====================================================
    # Chargement des données
    # =====================================================

    def refresh(
        self,
        items: List[TeamPlayByPlayEvent],
        players: Dict[int, Player],
        team_player_ids: Set[int],
        games: List[Tuple[int, str]],
    ) -> None:
        """`games` : liste (game_id, libellé), dans l'ordre d'affichage
        souhaité pour le filtre "Matchs"."""

        self._all_items = list(reversed(items))
        self._players = players
        self._team_player_ids = set(team_player_ids)

        self.match_filter.set_items(games)

        self._populate_player_filter(players, team_player_ids)
        self._populate_other_filters()

        self._apply_filters()

    def _populate_player_filter(
        self, players: Dict[int, Player], team_player_ids: Set[int]
    ) -> None:

        combo = self.player_filter
        previous = combo.currentData()

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Toutes les joueuses", None)

        for player in sorted(
            (p for p in players.values() if p.id in team_player_ids),
            key=lambda p: p.number,
        ):
            combo.addItem(f"#{player.number} {player.name}", player.id)

        index = combo.findData(previous)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _populate_other_filters(self) -> None:

        event_codes = sorted({it.event.event_type for it in self._all_items})

        shot_group_options = [
            ("Tirs réussis (2+3 pts)", SHOTS_MADE),
            ("Tirs manqués (2+3 pts)", SHOTS_MISSED),
            ("Tous les tirs (2+3 pts)", SHOTS_ALL),
        ]
        turnover_group_options = [
            ("Pertes de balle (tous types)", TURNOVERS_ALL),
        ]
        event_options = [(event_label(code), code) for code in event_codes]

        phase_values = sorted({it.event.phase for it in self._all_items if it.event.phase})
        system_values = sorted({it.event.system for it in self._all_items if it.event.system})
        action_type_values = sorted({
            it.event.action_type for it in self._all_items if it.event.action_type
        })

        self._populate_combo(
            self.event_filter, "Tous les événements",
            shot_group_options + turnover_group_options + event_options,
        )
        self._populate_combo(
            self.phase_filter, "Toutes les phases", [(v, v) for v in phase_values]
        )
        self._populate_combo(
            self.system_filter, "Tous les systèmes", [(v, v) for v in system_values]
        )
        self._populate_combo(
            self.action_type_filter, "Tous les types d'action",
            [(v, v) for v in action_type_values],
        )

    def _populate_combo(self, combo: QComboBox, placeholder: str, options) -> None:

        previous = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder, None)
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(previous)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    # =====================================================
    # Filtrage
    # =====================================================

    def _apply_filters(self) -> None:

        game_ids = self.match_filter.selected_ids()
        player_id = self.player_filter.currentData()
        event_type = self.event_filter.currentData()
        phase = self.phase_filter.currentData()
        system = self.system_filter.currentData()
        action_type = self.action_type_filter.currentData()

        def matches_event(event: Event) -> bool:

            if event_type is None:
                return True
            if event_type == SHOTS_MADE:
                return event.event_type in SHOT_TYPES and event.event_type.endswith("_MADE")
            if event_type == SHOTS_MISSED:
                return event.event_type in SHOT_TYPES and event.event_type.endswith("_MISSED")
            if event_type == SHOTS_ALL:
                return event.event_type in SHOT_TYPES
            if event_type == TURNOVERS_ALL:
                return event.event_type.startswith("TO_") or event.event_type == "TURNOVER"
            return event.event_type == event_type

        self._items = [
            it
            for it in self._all_items
            if (game_ids is None or it.game_id in game_ids)
            and (player_id is None or it.event.player_id == player_id)
            and matches_event(it.event)
            and (phase is None or it.event.phase == phase)
            and (system is None or it.event.system == system)
            and (action_type is None or it.event.action_type == action_type)
        ]

        self._render_table()

    # =====================================================
    # Affichage
    # =====================================================

    def _render_table(self) -> None:

        self.table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):

            event = item.event
            player = self._players.get(event.player_id)
            player_name = f"#{player.number} {player.name}" if player else "Inconnue"

            minutes = int(event.timestamp // 60)
            seconds = int(event.timestamp % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"

            values = [
                item.game_label,
                time_str,
                str(event.quarter),
                player_name,
                event_label(event.event_type),
                event.phase or "",
                event.system or "",
                event.action_type or "",
            ]

            for col, value in enumerate(values):

                cell = QTableWidgetItem(str(value))

                if col in (1, 2):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if col == 3:
                    cell.setForeground(
                        TEAM_COLOR
                        if event.player_id in self._team_player_ids
                        else OPPONENT_COLOR
                    )

                self.table.setItem(row, col, cell)

        self.table.resizeColumnsToContents()

    def _on_double_click(self, row: int, column: int) -> None:

        if 0 <= row < len(self._items):
            item = self._items[row]
            self.event_seek_requested.emit(item.game_id, item.event.timestamp)

    def _on_export_clicked(self) -> None:

        if not self._items:
            return

        before = self.export_before_spin.value()
        after = self.export_after_spin.value()

        self.export_requested.emit([it.event for it in self._items], before, after)
