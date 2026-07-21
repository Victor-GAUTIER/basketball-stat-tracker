from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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


class PlayByPlayPanel(QWidget):

    event_deleted = Signal(int)
    event_edit_requested = Signal(int)
    event_seek_requested = Signal(float)

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # -------------------------
        # Filtres
        # -------------------------

        self.player_filter = QComboBox(self)
        self.event_filter = QComboBox(self)
        self.phase_filter = QComboBox(self)
        self.system_filter = QComboBox(self)

        for combo in (
            self.player_filter,
            self.event_filter,
            self.phase_filter,
            self.system_filter,
        ):

            combo.currentIndexChanged.connect(
                self._apply_filters
            )

        filters_row = QHBoxLayout()

        filters_row.addWidget(
            QLabel("Joueuse :")
        )

        filters_row.addWidget(
            self.player_filter
        )

        filters_row.addWidget(
            QLabel("Événement :")
        )

        filters_row.addWidget(
            self.event_filter
        )

        filters_row.addWidget(
            QLabel("Phase :")
        )

        filters_row.addWidget(
            self.phase_filter
        )

        filters_row.addWidget(
            QLabel("Système :")
        )

        filters_row.addWidget(
            self.system_filter
        )

        # -------------------------
        # Tableau
        # -------------------------

        self.table = QTableWidget(self)

        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([
            "Temps",
            "QT",
            "Joueuse",
            "Événement",
            "Phase",
            "Système",
            "Modifier",
            "Supprimer",
        ])

        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.cellDoubleClicked.connect(
            self._on_double_click
        )

        layout = QVBoxLayout(self)

        layout.addLayout(
            filters_row
        )

        layout.addWidget(
            self.table
        )

        # Tous les événements du match, indépendamment des filtres actifs
        self._all_events: List[Event] = []

        # Sous-ensemble actuellement affiché, après filtrage
        self._events: List[Event] = []

        self._players: Dict[int, Player] = {}


    # =====================================================
    # Chargement des données
    # =====================================================

    def refresh(
        self,
        events: List[Event],
        players: Dict[int, Player],
        home_players: Optional[List[Player]] = None,
        away_players: Optional[List[Player]] = None,
        home_name: str = "Domicile",
        away_name: str = "Extérieur"
    ):

        self._all_events = list(reversed(events))

        self._players = players

        self._populate_player_filter(
            home_players or [],
            away_players or [],
            home_name,
            away_name
        )

        self._populate_other_filters()

        self._apply_filters()


    # =====================================================
    # Construction des filtres
    # =====================================================

    def _populate_player_filter(
        self,
        home_players: List[Player],
        away_players: List[Player],
        home_name: str,
        away_name: str
    ):

        combo = self.player_filter

        previous = combo.currentData()

        combo.blockSignals(True)

        combo.clear()

        combo.addItem(
            "Toutes les joueuses",
            None
        )

        def add_group(label, players):

            if not players:
                return

            combo.insertSeparator(
                combo.count()
            )

            header_index = combo.count()

            combo.addItem(
                label,
                None
            )

            combo.model().item(
                header_index
            ).setEnabled(False)

            for player in sorted(
                players,
                key=lambda p: p.number
            ):

                combo.addItem(
                    f"#{player.number} {player.name}",
                    player.id
                )

        add_group(
            home_name,
            home_players
        )

        add_group(
            away_name,
            away_players
        )

        index = combo.findData(
            previous
        )

        combo.setCurrentIndex(
            index if index >= 0 else 0
        )

        combo.blockSignals(False)


    def _populate_other_filters(self):

        event_codes = sorted({
            e.event_type
            for e in self._all_events
        })

        event_options = [
            (event_label(code), code)
            for code in event_codes
        ]

        phase_values = sorted({
            e.phase
            for e in self._all_events
            if e.phase
        })

        phase_options = [
            (value, value)
            for value in phase_values
        ]

        system_values = sorted({
            e.system
            for e in self._all_events
            if e.system
        })

        system_options = [
            (value, value)
            for value in system_values
        ]

        self._populate_combo(
            self.event_filter,
            "Tous les événements",
            event_options
        )

        self._populate_combo(
            self.phase_filter,
            "Toutes les phases",
            phase_options
        )

        self._populate_combo(
            self.system_filter,
            "Tous les systèmes",
            system_options
        )


    def _populate_combo(
        self,
        combo: QComboBox,
        placeholder: str,
        options: List[Tuple[str, object]]
    ):

        previous = combo.currentData()

        combo.blockSignals(True)

        combo.clear()

        combo.addItem(
            placeholder,
            None
        )

        for label, value in options:

            combo.addItem(
                label,
                value
            )

        index = combo.findData(
            previous
        )

        combo.setCurrentIndex(
            index if index >= 0 else 0
        )

        combo.blockSignals(False)


    # =====================================================
    # Application des filtres
    # =====================================================

    def _apply_filters(self):

        player_id = self.player_filter.currentData()

        event_type = self.event_filter.currentData()

        phase = self.phase_filter.currentData()

        system = self.system_filter.currentData()

        self._events = [
            e
            for e in self._all_events
            if (player_id is None or e.player_id == player_id)
            and (event_type is None or e.event_type == event_type)
            and (phase is None or e.phase == phase)
            and (system is None or e.system == system)
        ]

        self._render_table()


    # =====================================================
    # Affichage
    # =====================================================

    def _render_table(self):

        self.table.setRowCount(
            len(self._events)
        )

        for row, event in enumerate(self._events):

            player = self._players.get(
                event.player_id
            )

            player_name = (
                f"#{player.number} {player.name}"
                if player
                else "Inconnue"
            )


            minutes = int(
                event.timestamp // 60
            )

            seconds = int(
                event.timestamp % 60
            )

            time_str = (
                f"{minutes:02d}:{seconds:02d}"
            )


            values = [
                time_str,
                str(event.quarter),
                player_name,
                event_label(event.event_type),
                event.phase or "",
                event.system or "",
            ]


            for col, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                if col in (0, 1):

                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.table.setItem(
                    row,
                    col,
                    item
                )


            # -------------------------
            # Bouton modifier
            # -------------------------

            edit_btn = QPushButton(
                "✏️"
            )

            edit_btn.clicked.connect(
                lambda checked=False, e=event:
                self.event_edit_requested.emit(e.id)
            )


            edit_widget = QWidget()

            edit_layout = QHBoxLayout(
                edit_widget
            )

            edit_layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            edit_layout.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            edit_layout.addWidget(
                edit_btn
            )


            self.table.setCellWidget(
                row,
                6,
                edit_widget
            )


            # -------------------------
            # Bouton supprimer
            # -------------------------

            delete_btn = QPushButton(
                "🗑"
            )

            delete_btn.clicked.connect(
                lambda checked=False, e=event:
                self.event_deleted.emit(e.id)
            )


            delete_widget = QWidget()

            delete_layout = QHBoxLayout(
                delete_widget
            )

            delete_layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            delete_layout.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            delete_layout.addWidget(
                delete_btn
            )


            self.table.setCellWidget(
                row,
                7,
                delete_widget
            )


        self.table.resizeColumnsToContents()



    def _on_double_click(
        self,
        row: int,
        column: int
    ):

        if 0 <= row < len(self._events):

            event = self._events[row]

            self.event_seek_requested.emit(
                event.timestamp
            )
