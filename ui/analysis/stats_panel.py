"""Panneau affichant les statistiques cumulées, par joueur."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from data.models import Player
from ui.analysis.event_panel import EVENT_TYPES


class StatsPanel(QWidget):
    """Tableau récapitulatif : une ligne par joueur, une colonne par type d'événement."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(EVENT_TYPES) + 1)
        headers = ["Joueur"] + [label for _code, label, _shortcut in EVENT_TYPES]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def refresh(self, players: List[Player], stats: Dict[int, Dict[str, int]]) -> None:
        """Recalcule et réaffiche le tableau des statistiques pour la liste de joueurs donnée."""
        self.table.setRowCount(len(players))
        for row, player in enumerate(players):
            self.table.setItem(row, 0, QTableWidgetItem(f"#{player.number} {player.name}"))
            player_stats = stats.get(player.id, {})
            for col, (code, _label, _shortcut) in enumerate(EVENT_TYPES, start=1):
                count = player_stats.get(code, 0)
                item = QTableWidgetItem(str(count))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
