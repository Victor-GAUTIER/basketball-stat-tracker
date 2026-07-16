from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    )

from data.models import Event, Player


class PlayByPlayPanel(QWidget):

    event_deleted = Signal(int)
    event_seek_requested = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.table = QTableWidget(self)

        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Temps",
            "QT",
            "Joueuse",
            "Événement",
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

        layout.addWidget(self.table)

        self._events: List[Event] = []

    def refresh(
        self,
        events: List[Event],
        players: Dict[int, Player]
    ):

        self._events = list(reversed(events))

        self.table.setRowCount(len(self._events))

        for row, event in enumerate(self._events):

            player = players.get(event.player_id)

            player_name = (
                f"#{player.number} {player.name}"
                if player else "Inconnue"
            )

            minutes = int(event.timestamp // 60)
            seconds = int(event.timestamp % 60)

            time_str = f"{minutes:02d}:{seconds:02d}"

            values = [
                time_str,
                str(event.quarter),
                player_name,
                event.event_type,
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(value)

                if col in (0, 1):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row, col, item)

            # Bouton modifier (placeholder)
            edit_btn = QPushButton("✏️")
            edit_btn.setEnabled(False)

            edit_widget = QWidget()
            edit_layout = QHBoxLayout(edit_widget)
            edit_layout.setContentsMargins(0, 0, 0, 0)
            edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_layout.addWidget(edit_btn)

            self.table.setCellWidget(row, 4, edit_widget)

            # Bouton supprimer
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

            self.table.setCellWidget(row, 5, delete_widget)

        self.table.resizeColumnsToContents()

    def _on_double_click(self, row: int, column: int):

        if 0 <= row < len(self._events):

            event = self._events[row]

            self.event_seek_requested.emit(event.timestamp)
