from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.event_config import event_config
from data.models import Event, Player
from ui.analysis.event_labels import event_label

HOME_COLOR = QColor("#e07b00")  # orange
AWAY_COLOR = QColor("#1e6fd9")  # bleu

SHOT_TYPES = ("2PTS_MADE", "2PTS_MISSED", "3PTS_MADE", "3PTS_MISSED")
FT_TYPES = ("FT_MADE", "FT_MISSED")

# Défense et dribbles n'ont de sens que pour les tirs de jeu (pas les
# lancers francs, voir ShotDetailsDialog show_defense=False/show_dribbles=False).
DEFENSE_EDITABLE_TYPES = SHOT_TYPES
DRIBBLES_EDITABLE_TYPES = SHOT_TYPES

# Le rebond offensif préalable, lui, a un sens pour les tirs ET les
# lancers francs.
OREB_APPLICABLE_TYPES = SHOT_TYPES + FT_TYPES

TURNOVER_TYPES = (
    "TO_PASS",
    "TO_DRIBBLE",
    "TO_VIOLATION",
    "TO_SORTIE",
    "TO_FAUTE",
    "TO_TEMPS",
    "TO_AUTRE",
    "TURNOVER",
)

# Valeurs spéciales pour le filtre "Événement", représentant des tirs
# regroupés (2 et 3 points confondus) ou des pertes de balle regroupées
# (tous types confondus) plutôt qu'un event_type unique.
SHOTS_MADE = "__SHOTS_MADE__"
SHOTS_MISSED = "__SHOTS_MISSED__"
SHOTS_ALL = "__SHOTS_ALL__"
TURNOVERS_ALL = "__TURNOVERS_ALL__"


# Index des colonnes du tableau, centralisés pour éviter les nombres
# magiques disséminés dans le code.
COL_TIME = 0
COL_QUARTER = 1
COL_PLAYER = 2
COL_EVENT = 3
COL_PHASE = 4
COL_SYSTEM = 5
COL_ACTION_TYPE = 6
COL_DEFENSE = 7
COL_OREB = 8
COL_DRIBBLES = 9
COL_EDIT = 10
COL_DELETE = 11

COLUMN_HEADERS = [
    "Temps",
    "QT",
    "Joueuse",
    "Événement",
    "Phase",
    "Système",
    "Type d'action",
    "Défense",
    "Reb. off.",
    "Dribbles",
    "Modifier",
    "Supprimer",
]


class PlayByPlayPanel(QWidget):

    event_deleted = Signal(int)
    event_edit_requested = Signal(int)
    event_seek_requested = Signal(float)

    export_requested = Signal(list, float, float)

    bulk_quarter_edit_requested = Signal(list, int)

    # Édition directe depuis le tableau, sans passer par EditEventDialog :
    # (event_id, nouvelle valeur). Chaîne vide = défense non renseignée.
    event_defense_changed = Signal(int, str)
    event_dribbles_changed = Signal(int, int)

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # -------------------------
        # Filtres
        # -------------------------

        self.team_filter = QComboBox(self)
        self.player_filter = QComboBox(self)
        self.event_filter = QComboBox(self)
        self.phase_filter = QComboBox(self)
        self.system_filter = QComboBox(self)
        self.action_type_filter = QComboBox(self)

        for combo in (
            self.team_filter,
            self.player_filter,
            self.event_filter,
            self.phase_filter,
            self.system_filter,
            self.action_type_filter,
        ):

            combo.currentIndexChanged.connect(
                self._apply_filters
            )

        filters_row_1 = QHBoxLayout()

        filters_row_1.addWidget(QLabel("Équipe :"))
        filters_row_1.addWidget(self.team_filter)
        filters_row_1.addWidget(QLabel("Joueuse :"))
        filters_row_1.addWidget(self.player_filter)
        filters_row_1.addWidget(QLabel("Événement :"))
        filters_row_1.addWidget(self.event_filter)
        filters_row_1.addStretch()

        filters_row_2 = QHBoxLayout()

        filters_row_2.addWidget(QLabel("Phase :"))
        filters_row_2.addWidget(self.phase_filter)
        filters_row_2.addWidget(QLabel("Système :"))
        filters_row_2.addWidget(self.system_filter)
        filters_row_2.addWidget(QLabel("Type d'action :"))
        filters_row_2.addWidget(self.action_type_filter)
        filters_row_2.addStretch()

        filters_column = QVBoxLayout()
        filters_column.addLayout(filters_row_1)
        filters_column.addLayout(filters_row_2)

        # -------------------------
        # Tableau
        # -------------------------

        self.table = QTableWidget(self)

        self.table.setColumnCount(len(COLUMN_HEADERS))

        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)

        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.table.cellDoubleClicked.connect(
            self._on_double_click
        )

        layout = QVBoxLayout(self)


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

        self.export_btn = QPushButton("🎬 Exporter le montage")
        self.export_btn.clicked.connect(self._on_export_clicked)

        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("Durée des segments :"))
        export_row.addWidget(self.export_before_spin)
        export_row.addWidget(self.export_after_spin)
        export_row.addStretch()
        export_row.addWidget(self.export_btn)


        # -------------------------
        # Édition groupée (sélection multiple)
        # -------------------------

        self.bulk_quarter_btn = QPushButton("Modifier le quart-temps de la sélection")
        self.bulk_quarter_btn.clicked.connect(self._on_bulk_quarter_edit_clicked)

        bulk_edit_row = QHBoxLayout()
        bulk_edit_row.addWidget(self.bulk_quarter_btn)
        bulk_edit_row.addStretch()

        layout.addLayout(
            filters_column
        )

        layout.addWidget(
            self.table
        )

        layout.addLayout(bulk_edit_row)

        layout.addLayout(export_row)

        # Tous les événements du match, indépendamment des filtres actifs
        self._all_events: List[Event] = []

        # Sous-ensemble actuellement affiché, après filtrage
        self._events: List[Event] = []

        self._players: Dict[int, Player] = {}

        # Ids des joueuses par équipe, pour le filtre et la coloration
        self._home_player_ids: set[int] = set()
        self._away_player_ids: set[int] = set()

        self._home_name = "Domicile"
        self._away_name = "Extérieur"

        self._home_color = HOME_COLOR
        self._away_color = AWAY_COLOR

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

        home_players = home_players or []
        away_players = away_players or []

        self._home_player_ids = {
            p.id
            for p in home_players
        }

        self._away_player_ids = {
            p.id
            for p in away_players
        }

        self._home_name = home_name

        self._away_name = away_name

        self._populate_team_filter(
            home_name,
            away_name
        )

        self._populate_player_filter(
            home_players,
            away_players,
            home_name,
            away_name
        )

        self._populate_other_filters()

        self._apply_filters()

    def set_team_colors(self, home_color: str, away_color: str) -> None:
            """Met à jour les couleurs utilisées pour distinguer les deux
            équipes dans le tableau (au lieu du bleu/orange par défaut)."""

            self._home_color = QColor(home_color)
            self._away_color = QColor(away_color)

            self._render_table()

    # =====================================================
    # Construction des filtres
    # =====================================================

    def _populate_team_filter(
        self,
        home_name: str,
        away_name: str
    ):

        combo = self.team_filter

        previous = combo.currentData()

        combo.blockSignals(True)

        combo.clear()

        combo.addItem(
            "Toutes les équipes",
            None
        )

        combo.addItem(
            home_name,
            "home"
        )

        combo.addItem(
            away_name,
            "away"
        )

        index = combo.findData(
            previous
        )

        combo.setCurrentIndex(
            index if index >= 0 else 0
        )

        combo.blockSignals(False)


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

        shot_group_options = [
            ("Tirs réussis (2+3 pts)", SHOTS_MADE),
            ("Tirs manqués (2+3 pts)", SHOTS_MISSED),
            ("Tous les tirs (2+3 pts)", SHOTS_ALL),
        ]

        turnover_group_options = [
            ("Pertes de balle (tous types)", TURNOVERS_ALL),
        ]

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

        action_type_values = sorted({
            e.action_type
            for e in self._all_events
            if e.action_type
        })

        action_type_options = [
            (value, value)
            for value in action_type_values
        ]

        self._populate_combo(
            self.event_filter,
            "Tous les événements",
            shot_group_options + turnover_group_options + event_options
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

        self._populate_combo(
            self.action_type_filter,
            "Tous les types d'action",
            action_type_options
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

        team = self.team_filter.currentData()

        player_id = self.player_filter.currentData()

        event_type = self.event_filter.currentData()

        phase = self.phase_filter.currentData()

        system = self.system_filter.currentData()

        action_type = self.action_type_filter.currentData()

        def matches_team(event: Event) -> bool:

            if team is None:
                return True

            if team == "home":
                return event.player_id in self._home_player_ids

            if team == "away":
                return event.player_id in self._away_player_ids

            return True

        def matches_event(event: Event) -> bool:

            if event_type is None:
                return True

            if event_type == SHOTS_MADE:
                return (
                    event.event_type in SHOT_TYPES
                    and event.event_type.endswith("_MADE")
                )

            if event_type == SHOTS_MISSED:
                return (
                    event.event_type in SHOT_TYPES
                    and event.event_type.endswith("_MISSED")
                )

            if event_type == SHOTS_ALL:
                return event.event_type in SHOT_TYPES

            if event_type == TURNOVERS_ALL:
                return event.event_type.startswith("TO_") or event.event_type == "TURNOVER"

            return event.event_type == event_type

        self._events = [
            e
            for e in self._all_events
            if matches_team(e)
            and (player_id is None or e.player_id == player_id)
            and matches_event(e)
            and (phase is None or e.phase == phase)
            and (system is None or e.system == system)
            and (action_type is None or e.action_type == action_type)
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

            values = {
                COL_TIME: time_str,
                COL_QUARTER: str(event.quarter),
                COL_PLAYER: player_name,
                COL_EVENT: event_label(event.event_type),
                COL_PHASE: event.phase or "",
                COL_SYSTEM: event.system or "",
                COL_ACTION_TYPE: event.action_type or "",
            }

            for col, value in values.items():

                item = QTableWidgetItem(
                    str(value)
                )

                if col in (COL_TIME, COL_QUARTER):

                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                if col == COL_PLAYER:

                    if event.player_id in self._home_player_ids:

                        item.setForeground(
                            self._home_color
                        )

                    elif event.player_id in self._away_player_ids:

                        item.setForeground(
                            self._away_color
                        )

                self.table.setItem(
                    row,
                    col,
                    item
                )


            # -------------------------
            # Défense (éditable directement, pour les tirs de jeu)
            # -------------------------

            self.table.removeCellWidget(row, COL_DEFENSE)

            if event.event_type in DEFENSE_EDITABLE_TYPES:

                defense_combo = QComboBox()
                defense_combo.addItem("", "")

                for label in event_config.active_defense_level_names():
                    defense_combo.addItem(label, label)

                current_index = defense_combo.findData(event.defense_level or "")

                defense_combo.blockSignals(True)
                defense_combo.setCurrentIndex(
                    current_index if current_index >= 0 else 0
                )
                defense_combo.blockSignals(False)

                defense_combo.currentIndexChanged.connect(
                    lambda _index, e=event, c=defense_combo:
                    self.event_defense_changed.emit(e.id, c.currentData())
                )

                self.table.setCellWidget(row, COL_DEFENSE, defense_combo)

            else:

                self.table.setItem(row, COL_DEFENSE, QTableWidgetItem("-"))


            # -------------------------
            # Rebond offensif préalable (affichage seul)
            # -------------------------

            if event.event_type in OREB_APPLICABLE_TYPES:
                oreb_text = "Oui" if event.prior_oreb else "Non"
            else:
                oreb_text = ""

            oreb_item = QTableWidgetItem(oreb_text)
            oreb_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, COL_OREB, oreb_item)


            # -------------------------
            # Dribbles (éditable directement, pour les tirs de jeu)
            # -------------------------

            self.table.removeCellWidget(row, COL_DRIBBLES)

            if event.event_type in DRIBBLES_EDITABLE_TYPES:

                dribbles_spin = QSpinBox()
                dribbles_spin.setRange(0, 15)

                dribbles_spin.blockSignals(True)
                dribbles_spin.setValue(event.dribbles or 0)
                dribbles_spin.blockSignals(False)

                # editingFinished (perte de focus / Entrée) plutôt que
                # valueChanged, pour éviter de recharger tout le tableau à
                # chaque clic sur les flèches (ce qui détruirait le widget
                # en cours d'utilisation).
                dribbles_spin.editingFinished.connect(
                    lambda e=event, s=dribbles_spin:
                    self.event_dribbles_changed.emit(e.id, s.value())
                )

                self.table.setCellWidget(row, COL_DRIBBLES, dribbles_spin)

            else:

                self.table.setItem(row, COL_DRIBBLES, QTableWidgetItem("-"))


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
                COL_EDIT,
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
                COL_DELETE,
                delete_widget
            )


        self.table.resizeColumnsToContents()



    def _on_double_click(
        self,
        row: int,
        column: int
    ):

        # Ne pas déclencher le seek si le double-clic tombe sur un widget
        # interactif (combo défense, spinbox dribbles, boutons).
        if column in (COL_DEFENSE, COL_DRIBBLES, COL_EDIT, COL_DELETE):
            return

        if 0 <= row < len(self._events):

            event = self._events[row]

            self.event_seek_requested.emit(
                event.timestamp
            )

    def _on_export_clicked(self):

        if not self._events:
            return

        before = self.export_before_spin.value()
        after = self.export_after_spin.value()

        self.export_requested.emit(
            list(self._events),
            before,
            after
        )

    def _on_bulk_quarter_edit_clicked(self):

        selected_rows = sorted({
            index.row()
            for index in self.table.selectedIndexes()
        })

        if not selected_rows:
            return

        selected_events = [
            self._events[row]
            for row in selected_rows
            if 0 <= row < len(self._events)
        ]

        if not selected_events:
            return

        quarter, ok = QInputDialog.getInt(
            self,
            "Modifier le quart-temps",
            f"Nouveau quart-temps pour {len(selected_events)} événement(s) :",
            value=selected_events[0].quarter,
            minValue=1,
            maxValue=5,
        )

        if not ok:
            return

        self.bulk_quarter_edit_requested.emit(
            [e.id for e in selected_events],
            quarter,
        )
