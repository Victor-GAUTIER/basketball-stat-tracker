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

        layout.addWidget(
            self.table
        )

        self._events: List[Event] = []


    def refresh(
        self,
        events: List[Event],
        players: Dict[int, Player]
    ):

        self._events = list(reversed(events))

        self.table.setRowCount(
            len(self._events)
        )

        for row, event in enumerate(self._events):

            player = players.get(
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
