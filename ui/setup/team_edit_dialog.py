"""Dialogue de modification du nom et de la couleur d'une équipe déjà
enregistrée en base."""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data.models import Team


class TeamEditDialog(QDialog):
    """Permet de renommer une équipe et/ou de changer sa couleur."""

    def __init__(self, team: Team, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Modifier l'équipe")
        self.setMinimumWidth(320)

        self._color = team.color

        self.name_edit = QLineEdit(team.name, self)

        self.color_swatch = QLabel(self)
        self.color_swatch.setFixedSize(24, 24)
        self._update_swatch()

        color_button = QPushButton("Couleur...", self)
        color_button.clicked.connect(self._on_pick_color)

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_swatch)
        color_row.addWidget(color_button)
        color_row.addStretch(1)

        form = QFormLayout()
        form.addRow("Nom :", self.name_edit)
        form.addRow("Couleur :", color_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _update_swatch(self) -> None:
        self.color_swatch.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888;"
        )

    def _on_pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Couleur de l'équipe")
        if color.isValid():
            self._color = color.name()
            self._update_swatch()

    def team_name(self) -> str:
        return self.name_edit.text().strip()

    def team_color(self) -> str:
        return self._color
