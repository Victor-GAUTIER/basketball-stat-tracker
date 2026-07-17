from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QComboBox,
)


PHASES = {

    "Contre-attaque": [],

    "Transition": [
        "Stream",
        "Ghost",
        "Flash",
        "Boum",
        "Bas",
    ],

    "Attaque placée": [
        "Poing",
        "2",
        "Maillot",
    ],

    "Touche": [
        "TF1",
        "TF2",
        "TC",
    ],
}


class PhasePanel(QWidget):

    phase_changed = Signal(str, str)


    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QHBoxLayout(self)


        layout.addWidget(
            QLabel("Phase")
        )


        self.phase_combo = QComboBox()

        self.phase_combo.addItems(
            PHASES.keys()
        )


        layout.addWidget(
            self.phase_combo
        )


        layout.addWidget(
            QLabel("Système")
        )


        self.system_combo = QComboBox()


        layout.addWidget(
            self.system_combo
        )


        self.phase_combo.currentTextChanged.connect(
            self.update_systems
        )

        self.system_combo.currentTextChanged.connect(
            self.emit_change
        )


        self.update_systems(
            self.phase_combo.currentText()
        )


    def update_systems(self, phase):

        self.system_combo.clear()

        self.system_combo.addItems(
            PHASES.get(
                phase,
                []
            )
        )

        self.emit_change()


    def emit_change(self):

        self.phase_changed.emit(
            self.phase_combo.currentText(),
            self.system_combo.currentText()
        )


    def current_phase(self):

        return self.phase_combo.currentText()


    def current_system(self):

        return self.system_combo.currentText()
