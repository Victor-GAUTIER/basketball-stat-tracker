"""Panneau d'affichage des boxscores des deux équipes."""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


class StatsPanel(QWidget):
    """Affiche les boxscores des deux équipes."""

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
        # Tableaux
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
        # Layout vertical
        # =============================

        layout = QVBoxLayout(
            self
        )


        layout.addWidget(
            self.home_title
        )

        layout.addWidget(
            self.home_table
        )


        layout.addWidget(
            self.away_title
        )

        layout.addWidget(
            self.away_table
        )


    # =====================================================
    # Configuration tableau
    # =====================================================

    def _configure_table(
        self,
        table: QTableWidget
    ) -> None:

        headers = [
            "Joueur",
            "PTS",
            "FG",
            "3PT",
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


        table.setColumnCount(
            len(headers)
        )

        table.setHorizontalHeaderLabels(
            headers
        )


        table.verticalHeader().setVisible(
            False
        )


        table.setSortingEnabled(
            True
        )


    # =====================================================
    # Actualisation
    # =====================================================

    def refresh(
        self,
        home_players: List[Player],
        away_players: List[Player],
        stats: Dict[int, Dict[str, Any]]
    ) -> None:


        self._fill_table(
            self.home_table,
            home_players,
            stats
        )


        self._fill_table(
            self.away_table,
            away_players,
            stats
        )


    # =====================================================
    # Remplissage boxscore
    # =====================================================

    def _fill_table(
        self,
        table: QTableWidget,
        players: List[Player],
        stats: Dict[int, Dict[str, Any]]
    ) -> None:


        table.clearContents()


        # +1 pour la ligne TOTAL
        table.setRowCount(
            len(players) + 1
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
                player_stats.get("2PTS_MISS", 0)
                +
                player_stats.get("3PTS_MADE", 0)
                +
                player_stats.get("3PTS_MISS", 0)
            )


            three_made = player_stats.get(
                "3PTS_MADE",
                0
            )


            three_att = (
                player_stats.get("3PTS_MADE", 0)
                +
                player_stats.get("3PTS_MISS", 0)
            )


            ft_made = player_stats.get(
                "FT_MADE",
                0
            )


            ft_att = (
                player_stats.get("FT_MADE", 0)
                +
                player_stats.get("FT_MISS", 0)
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


            values = [
                f"#{player.number} {player.name}",
                pts,
                f"{fg_made}/{fg_att}",
                f"{three_made}/{three_att}",
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



        # =============================
        # Ligne total équipe
        # =============================

        total_values = [
            "TOTAL",

            totals["PTS"],

            f"{totals['FG_MADE']}/{totals['FG_ATT']}",

            f"{totals['3PT_MADE']}/{totals['3PT_ATT']}",

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


        total_row = len(players)


        for col, value in enumerate(total_values):

            item = QTableWidgetItem(
                str(value)
            )

            table.setItem(
                total_row,
                col,
                item
            )


        table.resizeColumnsToContents()
