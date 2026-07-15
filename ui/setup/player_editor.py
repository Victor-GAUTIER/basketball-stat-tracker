"""Boîte de dialogue permettant d'ajouter ou modifier une joueuse."""

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
    """Formulaire modal pour ajouter ou modifier une joueuse."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        player: Optional[Tuple[str, int]] = None,
    ) -> None:

        super().__init__(parent)

        self.setMinimumWidth(280)


        if player is None:
            self.setWindowTitle("Ajouter une joueuse")
        else:
            self.setWindowTitle("Modifier la joueuse")


        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Nom de la joueuse")


        self.number_spin = QSpinBox(self)
        self.number_spin.setRange(0, 99)


        # Si on modifie une joueuse existante,
        # on recharge ses informations
        if player is not None:
            name, number = player
            self.name_edit.setText(name)
            self.number_spin.setValue(number)


        form = QFormLayout()

        form.addRow(
            "Nom :",
            self.name_edit
        )

        form.addRow(
            "Numéro :",
            self.number_spin
        )


        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )


        buttons.accepted.connect(
            self._on_accept
        )

        buttons.rejected.connect(
            self.reject
        )


        form.addRow(
            buttons
        )


        self.setLayout(
            form
        )


    def _on_accept(self) -> None:
        """Valide uniquement si un nom existe."""

        if self.name_edit.text().strip():
            self.accept()


    def get_player(self) -> Optional[Tuple[str, int]]:
        """Retourne (nom, numéro)."""

        name = self.name_edit.text().strip()

        if not name:
            return None

        return (
            name,
            self.number_spin.value()
        )
