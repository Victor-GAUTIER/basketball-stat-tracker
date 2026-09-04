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
from ui.analysis.filters import MultiSelectFilter

HOME_COLOR = QColor("#e07b00")  # orange
AWAY_COLOR = QColor("#1e6fd9")  # bleu

SHOT_TYPES = ("2PTS_MADE", "2PTS_MISSED", "3PTS_MADE", "3PTS_MISSED")
FT_TYPES = ("FT_MADE", "FT_MISSED")

DEFENSE_EDITABLE_TYPES = SHOT_TYPES
DRIBBLES_EDITABLE_TYPES = SHOT_TYPES
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

# Valeurs spéciales pour le filtre "Équipe" (MultiSelectFilter attend des
# ids entiers, on utilise -1/-2 plutôt que "home"/"away").
TEAM_HOME = -1
TEAM_AWAY = -2


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

    event_defense_changed = Signal(int, str)
    event_dribbles_changed = Signal(int, int)

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # -------------------------
        # Filtres — tous en sélection multiple (voir ui.analysis.filters)
        # -------------------------

        self.team_filter = MultiSelectFilter("Équipe", [], self)
        self.player_filter = MultiSelectFilter("Joueuse", [], self)
        self.event_filter = MultiSelectFilter("Événement", [], self)
        self.phase_filter = MultiSelectFilter("Phase", [], self)
        self.system_filter = MultiSelectFilter("Système", [], self)
        self.action_type_filter = MultiSelectFilter("Type d'action", [], self)

        for combo in (
            self.team_filter,
            self.player_filter,
            self.event_filter,
            self.phase_filter,
            self.system_filter,
            self.action_type_filter,
        ):
            combo.on_change = self._apply_filters

        filters_row_1 = QHBoxLayout()

        filters_row_1.addWidget(self.team_filter)
        filters_row_1.addWidget(self.player_filter)
        filters_row_1.addWidget(self.event_filter)
        filters_row_1.addStretch()

        filters_row_2 = QHBoxLayout()

        filters_row_2.addWidget(self.phase_filter)
        filters_row_2.addWidget(self.system_filter)
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

        # Mapping libellé -> id numérique pour les filtres Phase/Système/
        # Type d'action, dont les valeurs réelles sont des chaînes : voir
        # _string_filter_selection ci-dessous.
        self._phase_ids: Dict[str, int] = {}
        self._system_ids: Dict[str, int] = {}
        self._action_type_ids: Dict[str, int] = {}

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

        self.team_filter.set_items([
            (TEAM_HOME, home_name),
            (TEAM_AWAY, away_name),
        ])


    def _populate_player_filter(
        self,
        home_players: List[Player],
        away_players: List[Player],
        home_name: str,
        away_name: str
    ):
        """Liste plate (MultiSelectFilter ne supporte pas les en-têtes de
        groupe non sélectionnables), le nom d'équipe est donc préfixé au
        libellé de chaque joueuse."""

        items: List[Tuple[int, str]] = [
            (p.id, f"{home_name} — #{p.number} {p.name}")
            for p in sorted(home_players, key=lambda p: p.number)
        ] + [
            (p.id, f"{away_name} — #{p.number} {p.name}")
            for p in sorted(away_players, key=lambda p: p.number)
        ]

        self.player_filter.set_items(items)


    def _populate_other_filters(self):

        # Phase/Système/Type d'action : construits à partir des valeurs
        # RÉELLEMENT présentes dans les événements du match (pas depuis
        # data.event_config), pour ne proposer que des filtres pertinents
        # pour ce match précis.

        event_codes = sorted({
            e.event_type
            for e in self._all_events
        })

        shot_group_options = [
            (SHOTS_MADE, "Tirs réussis (2+3 pts)"),
            (SHOTS_MISSED, "Tirs manqués (2+3 pts)"),
            (SHOTS_ALL, "Tous les tirs (2+3 pts)"),
        ]

        turnover_group_options = [
            (TURNOVERS_ALL, "Pertes de balle (tous types)"),
        ]

        event_options = [
            (code, event_label(code))
            for code in event_codes
        ]

        self.event_filter.set_items(
            shot_group_options + turnover_group_options + event_options
        )

        phase_values = sorted({
            e.phase
            for e in self._all_events
            if e.phase
        })

        system_values = sorted({
            e.system
            for e in self._all_events
            if e.system
        })

        action_type_values = sorted({
            e.action_type
            for e in self._all_events
            if e.action_type
        })

        self._populate_string_filter(
            self.phase_filter, self._phase_ids, phase_values
        )
        self._populate_string_filter(
            self.system_filter, self._system_ids, system_values
        )
        self._populate_string_filter(
            self.action_type_filter, self._action_type_ids, action_type_values
        )

    def _populate_string_filter(
        self,
        widget: MultiSelectFilter,
        id_map: Dict[str, int],
        values: List[str],
    ) -> None:
        """MultiSelectFilter attend des ids entiers ; phase/système/type
        d'action sont des chaînes en base. On leur attribue un id entier
        stable (position dans la liste triée) et on garde le mapping
        inverse pour retrouver la chaîne d'origine dans _apply_filters."""

        id_map.clear()

        items: List[Tuple[int, str]] = []

        for index, value in enumerate(values):
            id_map[value] = index
            items.append((index, value))

        widget.set_items(items)

    def _string_filter_selection(
        self,
        widget: MultiSelectFilter,
        id_map: Dict[str, int],
    ) -> Optional[set]:
        """Retourne l'ensemble des valeurs (chaînes) sélectionnées, ou
        None si aucun filtre n'est actif (tout coché)."""

        selected_ids = widget.selected_ids()

        if selected_ids is None:
            return None

        reverse = {v: k for k, v in id_map.items()}

        return {reverse[i] for i in selected_ids if i in reverse}


    # =====================================================
    # Application des filtres
    # =====================================================

    def _apply_filters(self):

        selected_teams = self.team_filter.selected_ids()
        selected_players = self.player_filter.selected_ids()
        selected_events = self.event_filter.selected_ids()

        selected_phases = self._string_filter_selection(
            self.phase_filter, self._phase_ids
        )
        selected_systems = self._string_filter_selection(
            self.system_filter, self._system_ids
        )
        selected_action_types = self._string_filter_selection(
            self.action_type_filter, self._action_type_ids
        )

        def matches_team(event: Event) -> bool:

            if selected_teams is None:
                return True

            is_home = event.player_id in self._home_player_ids
            is_away = event.player_id in self._away_player_ids

            if TEAM_HOME in selected_teams and is_home:
                return True

            if TEAM_AWAY in selected_teams and is_away:
                return True

            return False

        def matches_player(event: Event) -> bool:

            if selected_players is None:
                return True

            return event.player_id in selected_players

        def matches_event(event: Event) -> bool:

            if selected_events is None:
                return True

            for value in selected_events:

                if value == SHOTS_MADE:
                    if event.event_type in SHOT_TYPES and event.event_type.endswith("_MADE"):
                        return True

                elif value == SHOTS_MISSED:
                    if event.event_type in SHOT_TYPES and event.event_type.endswith("_MISSED"):
                        return True

                elif value == SHOTS_ALL:
                    if event.event_type in SHOT_TYPES:
                        return True

                elif value == TURNOVERS_ALL:
                    if event.event_type.startswith("TO_") or event.event_type == "TURNOVER":
                        return True

                elif event.event_type == value:
                    return True

            return False

        self._events = [
            e
            for e in self._all_events
            if matches_team(e)
            and matches_player(e)
            and matches_event(e)
            and (selected_phases is None or e.phase in selected_phases)
            and (selected_systems is None or e.system in selected_systems)
            and (selected_action_types is None or e.action_type in selected_action_types)
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
            # Défense (éditable directement, pour les tirs de jeu) :
            # niveaux issus de data.event_config, modifiables via le menu
            # Affichage > Configuration des événements.
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

            edit_btn = QPushButton("✏️")

            edit_btn.clicked.connect(
                lambda checked=False, e=event:
                self.event_edit_requested.emit(e.id)
            )

            edit_widget = QWidget()
            edit_layout = QHBoxLayout(edit_widget)
            edit_layout.setContentsMargins(0, 0, 0, 0)
            edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_layout.addWidget(edit_btn)

            self.table.setCellWidget(row, COL_EDIT, edit_widget)


            # -------------------------
            # Bouton supprimer
            # -------------------------

            delete_btn = QPushButton("🗑")

            delete_btn.clicked.connect(
                lambda checked=False, e=event:
                self.event_deleted.emit(e.id)
            )

            delete_widget = QWidget()
            delete_layout = QHBoxLayout(delete_widget)
            delete_layout.setContentsMargins(0, 0, 0, 0)
            delete_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            delete_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, COL_DELETE, delete_widget)


        self.table.resizeColumnsToContents()


    def _on_double_click(
        self,
        row: int,
        column: int
    ):

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
