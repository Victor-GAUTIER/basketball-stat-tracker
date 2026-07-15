"""Boîte de dialogue permettant de saisir un nouveau joueur (nom + numéro)."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)


class PlayerEditorDialog(QDialog):
    """Formulaire modal pour ajouter un joueur à une équipe."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajouter un joueur")
        self.setMinimumWidth(280)

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Nom du joueur")

        self.number_spin = QSpinBox(self)
        self.number_spin.setRange(0, 99)

        form = QFormLayout()
        form.addRow("Nom :", self.name_edit)
        form.addRow("Numéro :", self.number_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        form.addRow(buttons)
        self.setLayout(form)

    def _on_accept(self) -> None:
        # On ne valide que si un nom a été saisi.
        if self.name_edit.text().strip():
            self.accept()

    def get_player(self) -> Optional[Tuple[str, int]]:
        """Retourne (nom, numéro) si le formulaire est valide, sinon None."""
        name = self.name_edit.text().strip()
        if not name:
            return None
        return name, self.number_spin.value()
