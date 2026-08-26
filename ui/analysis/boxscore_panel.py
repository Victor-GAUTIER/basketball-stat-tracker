"""Panneau affichant les statistiques MOYENNES par match de chaque
joueuse, sur l'ensemble des matchs auxquels elle a participé (pas
seulement le match en cours) — complète l'onglet "Statistiques", qui
montre lui les totaux du match en cours."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.models import Player


HEADERS = [
    "Joueuse",
    "MJ",
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "FG (M/A)",
    "FG%",
    "3PT (M/A)",
    "3PT%",
    "FT (M/A)",
    "FT%",
]


class BoxscorePanel(QWidget):
    """Affiche, pour les deux équipes, les moyennes par match de chaque
    joueuse sur l'ensemble de la saison."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:

        super().__init__(parent)

        self.home_title = QLabel("Équipe domicile")
        self.home_title.setStyleSheet("font-weight: bold; font-size: 15px;")

        self.away_title = QLabel("Équipe extérieure")
        self.away_title.setStyleSheet("font-weight: bold; font-size: 15px;")

        self.home_table = QTableWidget(self)
        self.away_table = QTableWidget(self)

        self._configure_table(self.home_table)
        self._configure_table(self.away_table)

        layout = QVBoxLayout(self)

        layout.addWidget(self.home_title)
        layout.addWidget(self.home_table)

        layout.addWidget(self.away_title)
        layout.addWidget(self.away_table)

    def _configure_table(self, table: QTableWidget) -> None:

        table.setColumnCount(len(HEADERS))
        table.setHorizontalHeaderLabels(HEADERS)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)

        # Une ligne sur deux légèrement plus claire, et des lignes de
        # séparation visibles entre chaque ligne/colonne. Couleurs
        # alignées sur le thème sombre déjà utilisé dans
        # TeamAnalysisWindow (CARD_BG / TEXT_COLOR / BORDER_COLOR) : la
        # fenêtre parente force un fond sombre + texte clair sur tous ses
        # widgets, donc un style blanc classique rendrait le texte
        # illisible ici.
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)

        table.setStyleSheet(
            """
            QTableWidget {
                background-color: #252525;
                alternate-background-color: #2f2f2f;
                gridline-color: #555555;
                color: #eeeeee;
                border: 1px solid #555555;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #eeeeee;
                padding: 4px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            """
        )

    # =====================================================
    # Actualisation
    # =====================================================

    def refresh(
        self,
        home_players: List[Player],
        averages: Dict[int, Dict[str, float]],
        home_name: Optional[str] = None,
        away_players: Optional[List[Player]] = None,
        away_name: Optional[str] = None,
    ) -> None:
        """`away_players` est optionnel : laisse-le à None (par défaut)
        pour un usage à une seule équipe (tableau de bord d'équipe), la
        section "équipe extérieure" est alors masquée."""

        if home_name:
            self.home_title.setText(home_name)

        self._fill_table(self.home_table, home_players, averages)

        if away_players:

            self.away_title.setVisible(True)
            self.away_table.setVisible(True)

            if away_name:
                self.away_title.setText(away_name)

            self._fill_table(self.away_table, away_players, averages)

        else:

            self.away_title.setVisible(False)
            self.away_table.setVisible(False)

    def _fill_table(
        self,
        table: QTableWidget,
        players: List[Player],
        averages: Dict[int, Dict[str, float]],
    ) -> None:

        table.setSortingEnabled(False)

        table.clearContents()
        table.setRowCount(len(players))

        for row, player in enumerate(players):

            stats = averages.get(player.id, {})

            if not stats:
                # Aucun match joué (toutes équipes confondues) pour cette
                # joueuse : ligne quasi vide plutôt qu'une division par 0.
                values = [f"#{player.number} {player.name}"] + ["-"] * (len(HEADERS) - 1)

            else:
                values = [
                    f"#{player.number} {player.name}",
                    int(stats["GP"]),
                    f"{stats['PTS']:.1f}",
                    f"{stats['REB']:.1f}",
                    f"{stats['AST']:.1f}",
                    f"{stats['STL']:.1f}",
                    f"{stats['BLK']:.1f}",
                    f"{stats['TOV']:.1f}",
                    f"{stats['PF']:.1f}",
                    f"{int(stats['FGM'])}/{int(stats['FGA'])}",
                    f"{stats['FG_PCT']:.0f}%",
                    f"{int(stats['3PM'])}/{int(stats['3PA'])}",
                    f"{stats['3PT_PCT']:.0f}%",
                    f"{int(stats['FTM'])}/{int(stats['FTA'])}",
                    f"{stats['FT_PCT']:.0f}%",
                ]

            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(str(value)))

        table.setSortingEnabled(True)
        table.resizeColumnsToContents()

        table.setSortingEnabled(True)
        table.resizeColumnsToContents()
