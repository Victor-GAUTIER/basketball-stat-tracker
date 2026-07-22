"""Panneau d'affichage des boxscores des deux équipes."""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


HEADERS = [
    "Joueur",
    "PTS",
    "FG",
    "3PT",
    "eFG%",
    "FT",
    "REB",
    "AST",
    "TO",
    "STL",
    "BLK",
    "OREB",
    "DREB",
    "PF",
]


class StatsPanel(QWidget):
    """Affiche les boxscores des deux équipes, avec une ligne TOTAL toujours visible."""

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:

        super().__init__(parent)


        # =============================
        # Titres
        # =============================

        self.home_title = QLabel(
            "Équipe domicile"
        )

        self.home_title.setStyleSheet(
            "font-weight: bold; font-size: 15px;"
        )


        self.away_title = QLabel(
            "Équipe extérieure"
        )

        self.away_title.setStyleSheet(
            "font-weight: bold; font-size: 15px;"
        )


        # =============================
        # Tableaux joueurs (scrollables)
        # =============================

        self.home_table = QTableWidget(
            self
        )

        self.away_table = QTableWidget(
            self
        )


        self._configure_table(
            self.home_table
        )

        self._configure_table(
            self.away_table
        )


        # =============================
        # Lignes TOTAL (figées, non scrollables)
        # =============================

        self.home_total_table = QTableWidget(
            self
        )

        self.away_total_table = QTableWidget(
            self
        )


        self._configure_total_table(
            self.home_total_table
        )

        self._configure_total_table(
            self.away_total_table
        )


        self._sync_column_widths(
            self.home_table,
            self.home_total_table
        )

        self._sync_column_widths(
            self.away_table,
            self.away_total_table
        )


        # =============================
        # Layout vertical
        # =============================

        layout = QVBoxLayout(
            self
        )


        home_tables = QVBoxLayout()

        home_tables.setSpacing(
            0
        )

        home_tables.addWidget(
            self.home_table
        )

        home_tables.addWidget(
            self.home_total_table
        )


        away_tables = QVBoxLayout()

        away_tables.setSpacing(
            0
        )

        away_tables.addWidget(
            self.away_table
        )

        away_tables.addWidget(
            self.away_total_table
        )


        layout.addWidget(
            self.home_title
        )

        layout.addLayout(
            home_tables
        )


        layout.addWidget(
            self.away_title
        )

        layout.addLayout(
            away_tables
        )


    # =====================================================
    # Configuration tableau joueurs
    # =====================================================

    def _configure_table(
        self,
        table: QTableWidget
    ) -> None:

        table.setColumnCount(
            len(HEADERS)
        )

        table.setHorizontalHeaderLabels(
            HEADERS
        )


        table.verticalHeader().setVisible(
            False
        )


        table.setSortingEnabled(
            True
        )

        table.setFrameShape(
            QFrame.Shape.NoFrame
        )


    # =====================================================
    # Configuration ligne TOTAL figée
    # =====================================================

    def _configure_total_table(
        self,
        table: QTableWidget
    ) -> None:

        table.setColumnCount(
            len(HEADERS)
        )

        table.setRowCount(
            1
        )

        table.horizontalHeader().setVisible(
            False
        )

        table.verticalHeader().setVisible(
            False
        )

        table.setSortingEnabled(
            False
        )

        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )

        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        row_height = table.verticalHeader().defaultSectionSize()

        table.setFixedHeight(
            row_height + 6
        )

        table.setStyleSheet(
            "font-weight: bold; border-top: 2px solid gray;"
        )

        table.setFrameShape(
            QFrame.Shape.NoFrame
        )


    # =====================================================
    # Synchronisation des largeurs de colonnes
    # =====================================================

    def _sync_column_widths(
        self,
        table: QTableWidget,
        total_table: QTableWidget
    ) -> None:

        def sync(index, old_size, new_size):

            total_table.setColumnWidth(
                index,
                new_size
            )

        table.horizontalHeader().sectionResized.connect(
            sync
        )


    # =====================================================
    # Pourcentages
    # =====================================================

    @staticmethod
    def _pct(made: int, att: int) -> str:

        if att == 0:
            return "0%"

        return f"{round(made / att * 100)}%"


    @staticmethod
    def _efg(fg_made: int, three_made: int, fg_att: int) -> int:

        if fg_att == 0:
            return 0

        return round(
            (fg_made + 0.5 * three_made) / fg_att * 100
        )


    # =====================================================
    # Actualisation
    # =====================================================

    def refresh(
        self,
        home_players: List[Player],
        away_players: List[Player],
        stats: Dict[int, Dict[str, Any]],
        home_name: Optional[str] = None,
        away_name: Optional[str] = None
    ) -> None:

        if home_name:

            self.home_title.setText(
                home_name
            )

        if away_name:

            self.away_title.setText(
                away_name
            )


        self._fill_table(
            self.home_table,
            self.home_total_table,
            home_players,
            stats
        )


        self._fill_table(
            self.away_table,
            self.away_total_table,
            away_players,
            stats
        )


    # =====================================================
    # Remplissage boxscore
    # =====================================================

    def _fill_table(
        self,
        table: QTableWidget,
        total_table: QTableWidget,
        players: List[Player],
        stats: Dict[int, Dict[str, Any]]
    ) -> None:


        table.clearContents()


        table.setRowCount(
            len(players)
        )


        totals = {
            "PTS": 0,
            "FG_MADE": 0,
            "FG_ATT": 0,
            "3PT_MADE": 0,
            "3PT_ATT": 0,
            "FT_MADE": 0,
            "FT_ATT": 0,
            "REB": 0,
            "AST": 0,
            "TO": 0,
            "STL": 0,
            "BLK": 0,
            "OREB": 0,
            "DREB": 0,
            "PF": 0,
        }


        for row, player in enumerate(players):

            player_stats = stats.get(
                player.id,
                {}
            )


            pts = (
                player_stats.get("2PTS_MADE", 0) * 2
                +
                player_stats.get("3PTS_MADE", 0) * 3
                +
                player_stats.get("FT_MADE", 0)
            )


            fg_made = (
                player_stats.get("2PTS_MADE", 0)
                +
                player_stats.get("3PTS_MADE", 0)
            )


            fg_att = (
                player_stats.get("2PTS_MADE", 0)
                +
                player_stats.get("2PTS_MISSED", 0)
                +
                player_stats.get("3PTS_MADE", 0)
                +
                player_stats.get("3PTS_MISSED", 0)
            )


            three_made = player_stats.get(
                "3PTS_MADE",
                0
            )


            three_att = (
                player_stats.get("3PTS_MADE", 0)
                +
                player_stats.get("3PTS_MISSED", 0)
            )


            ft_made = player_stats.get(
                "FT_MADE",
                0
            )


            ft_att = (
                player_stats.get("FT_MADE", 0)
                +
                player_stats.get("FT_MISSED", 0)
            )


            oreb = player_stats.get(
                "OFF_REBOUND",
                0
            )


            dreb = player_stats.get(
                "DEF_REBOUND",
                0
            )


            reb = oreb + dreb


            ast = player_stats.get(
                "ASSIST",
                0
            )

            turnover = player_stats.get(
                "TURNOVER",
                0
            )

            steal = player_stats.get(
                "STEAL",
                0
            )

            block = player_stats.get(
                "BLOCK",
                0
            )

            foul = player_stats.get(
                "FOUL",
                0
            )


            fg_pct = self._pct(
                fg_made,
                fg_att
            )

            three_pct = self._pct(
                three_made,
                three_att
            )

            efg = self._efg(
                fg_made,
                three_made,
                fg_att
            )


            values = [
                f"#{player.number} {player.name}",
                pts,
                f"{fg_made}/{fg_att} ({fg_pct})",
                f"{three_made}/{three_att} ({three_pct})",
                f"{efg}%",
                f"{ft_made}/{ft_att}",
                reb,
                ast,
                turnover,
                steal,
                block,
                oreb,
                dreb,
                foul,
            ]


            for col, value in enumerate(values):

                table.setItem(
                    row,
                    col,
                    QTableWidgetItem(
                        str(value)
                    )
                )


            # Mise à jour totaux

            totals["PTS"] += pts

            totals["FG_MADE"] += fg_made
            totals["FG_ATT"] += fg_att

            totals["3PT_MADE"] += three_made
            totals["3PT_ATT"] += three_att

            totals["FT_MADE"] += ft_made
            totals["FT_ATT"] += ft_att

            totals["REB"] += reb
            totals["AST"] += ast
            totals["TO"] += turnover
            totals["STL"] += steal
            totals["BLK"] += block
            totals["OREB"] += oreb
            totals["DREB"] += dreb
            totals["PF"] += foul


        table.resizeColumnsToContents()


        # =============================
        # Ligne total équipe (table figée)
        # =============================

        team_fg_pct = self._pct(
            totals["FG_MADE"],
            totals["FG_ATT"]
        )

        team_three_pct = self._pct(
            totals["3PT_MADE"],
            totals["3PT_ATT"]
        )

        team_efg = self._efg(
            totals["FG_MADE"],
            totals["3PT_MADE"],
            totals["FG_ATT"]
        )


        total_values = [
            "TOTAL",

            totals["PTS"],

            f"{totals['FG_MADE']}/{totals['FG_ATT']} ({team_fg_pct})",

            f"{totals['3PT_MADE']}/{totals['3PT_ATT']} ({team_three_pct})",

            f"{team_efg}%",

            f"{totals['FT_MADE']}/{totals['FT_ATT']}",

            totals["REB"],

            totals["AST"],

            totals["TO"],

            totals["STL"],

            totals["BLK"],

            totals["OREB"],

            totals["DREB"],

            totals["PF"],
        ]


        for col, value in enumerate(total_values):

            item = QTableWidgetItem(
                str(value)
            )

            total_table.setItem(
                0,
                col,
                item
            )

            # Largeur initiale alignée sur la table joueurs, au cas où
            # le signal sectionResized n'aurait pas encore été émis.
            total_table.setColumnWidth(
                col,
                table.columnWidth(col)
            )
