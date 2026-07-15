"""Panneau listant les derniers événements enregistrés pendant l'analyse.

Affiché dans la fenêtre d'analyse à la place d'un tableau de statistiques
(celui-ci est désormais disponible séparément dans StatsWindow), pour
permettre à l'utilisateur de vérifier rapidement ses dernières saisies.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from data.models import Event, Player
from ui.analysis.event_panel import EVENT_TYPES

# Dictionnaire code interne -> libellé lisible, construit une fois pour toutes.
_EVENT_LABELS: Dict[str, str] = {code: label for code, label, _shortcut in EVENT_TYPES}


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


class RecentEventsPanel(QWidget):
    """Affiche les événements enregistrés, du plus récent au plus ancien."""

    def __init__(self, parent: Optional[QWidget] = None, max_rows: int = 50) -> None:
        super().__init__(parent)
        self.max_rows = max_rows

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Temps", "Q-T", "Joueur", "Événement"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def refresh(self, events: List[Event], players_by_id: Dict[int, Player]) -> None:
        """Réaffiche les `max_rows` événements les plus récents en tête de liste."""
        recent_events = list(reversed(events))[: self.max_rows]
        self.table.setRowCount(len(recent_events))
        for row, event in enumerate(recent_events):
            player = players_by_id.get(event.player_id)
            player_label = f"#{player.number} {player.name}" if player else "?"
            event_label = _EVENT_LABELS.get(event.event_type, event.event_type)

            self.table.setItem(row, 0, QTableWidgetItem(_format_timestamp(event.timestamp)))
            self.table.setItem(row, 1, QTableWidgetItem(str(event.quarter)))
            self.table.setItem(row, 2, QTableWidgetItem(player_label))
            self.table.setItem(row, 3, QTableWidgetItem(event_label))
