from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
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


ACTION_TYPES = [
    "Jeu rapide",
    "PnR",
    "Drive",
    "Poste bas",
    "Coupe",
    "Reb off",
    "Écran non porteur",
    "Mouvement de balle",
]


BUTTON_STYLE = """
QPushButton {
    padding: 3px 10px;
    border: 1px solid #999;
    border-radius: 4px;
    background: #f0f0f0;
    color: black;
}
QPushButton:checked {
    background: #3f7fd1;
    color: white;
    border: 1px solid #3f7fd1;
}
"""


class PhasePanel(QWidget):

    phase_changed = Signal(str, str)
    action_type_changed = Signal(str)

    def __init__(self, parent=None):

        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._current_phase = None
        self._current_system = None
        self._current_action_type = None

        self._system_buttons = {}

        # -------------------------
        # Ligne Phase
        # -------------------------

        self.phase_row = QHBoxLayout()
        self.phase_row.addWidget(QLabel("Phase"))

        self._phase_buttons = {}

        for phase in PHASES:

            btn = self._make_button(phase)

            btn.clicked.connect(
                lambda checked=False, p=phase: self._on_phase_clicked(p)
            )

            self._phase_buttons[phase] = btn

            self.phase_row.addWidget(btn)

        self.phase_row.addStretch()

        main_layout.addLayout(self.phase_row)

        # -------------------------
        # Ligne Système
        # -------------------------

        self.system_row = QHBoxLayout()
        self.system_row.addWidget(QLabel("Système"))

        self._system_buttons_container = QWidget()

        self._system_buttons_layout = QHBoxLayout(
            self._system_buttons_container
        )

        self._system_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.system_row.addWidget(self._system_buttons_container)
        self.system_row.addStretch()

        main_layout.addLayout(self.system_row)

        # -------------------------
        # Ligne Type d'action
        # -------------------------

        self.action_row = QHBoxLayout()
        self.action_row.addWidget(QLabel("Type d'action"))

        self._action_buttons = {}

        for action in ACTION_TYPES:

            btn = self._make_button(action)

            btn.clicked.connect(
                lambda checked=False, a=action: self._on_action_clicked(a)
            )

            self._action_buttons[action] = btn

            self.action_row.addWidget(btn)

        self.action_row.addStretch()

        main_layout.addLayout(self.action_row)

        # Sélection initiale : première phase de la liste
        first_phase = next(iter(PHASES))

        self._select_phase(first_phase)

    # =====================================================
    # Construction bouton
    # =====================================================

    def _make_button(self, text):

        btn = QPushButton(text)

        btn.setCheckable(True)

        btn.setStyleSheet(BUTTON_STYLE)

        return btn

    # =====================================================
    # Phase
    # =====================================================

    def _on_phase_clicked(self, phase):

        self._select_phase(phase)

    def _select_phase(self, phase):

        for p, btn in self._phase_buttons.items():

            btn.setChecked(p == phase)

        self._current_phase = phase

        self._rebuild_system_buttons(phase)

        self.emit_change()

    def _rebuild_system_buttons(self, phase):

        while self._system_buttons_layout.count():

            item = self._system_buttons_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        self._system_buttons = {}

        self._current_system = None

        for system in PHASES.get(phase, []):

            btn = self._make_button(system)

            btn.clicked.connect(
                lambda checked=False, s=system: self._on_system_clicked(s)
            )

            self._system_buttons[system] = btn

            self._system_buttons_layout.addWidget(btn)

    def _on_system_clicked(self, system):

        # Reclic sur le système déjà sélectionné : désélection
        if self._current_system == system:

            self._current_system = None

            self._system_buttons[system].setChecked(False)

        else:

            for s, btn in self._system_buttons.items():

                btn.setChecked(s == system)

            self._current_system = system

        self.emit_change()

    # =====================================================
    # Type d'action
    # =====================================================

    def _on_action_clicked(self, action):

        if self._current_action_type == action:

            self._current_action_type = None

            self._action_buttons[action].setChecked(False)

        else:

            for a, btn in self._action_buttons.items():

                btn.setChecked(a == action)

            self._current_action_type = action

        self.action_type_changed.emit(self._current_action_type or "")

    # =====================================================
    # Accès externe
    # =====================================================

    def emit_change(self):

        self.phase_changed.emit(
            self._current_phase or "",
            self._current_system or "",
        )

    def current_phase(self):

        return self._current_phase or ""

    def current_system(self):

        return self._current_system

    def current_action_type(self):

        return self._current_action_type
