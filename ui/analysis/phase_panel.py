"""Widget de sélection de la phase de jeu et du système, pendant la
saisie d'un événement.

Les phases, systèmes, types d'action et niveaux de défense affichés ici
(et dans ShotDetailsDialog / EditEventDialog) ne sont plus codés en dur :
ils viennent de la configuration persistante gérée par
data.event_config.event_config, modifiable depuis le menu
Affichage > Configuration des événements (voir ui.event_config_dialog).
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from data.event_config import event_config


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

    def __init__(self, parent=None):

        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._current_phase = None
        self._current_system = None

        self._phase_buttons = {}
        self._system_buttons = {}

        # -------------------------
        # Ligne Phase
        # -------------------------

        self.phase_row = QHBoxLayout()
        self.phase_row.addWidget(QLabel("Phase"))

        self._phase_buttons_container = QWidget()
        self._phase_buttons_layout = QHBoxLayout(self._phase_buttons_container)
        self._phase_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.phase_row.addWidget(self._phase_buttons_container)
        self.phase_row.addStretch()

        main_layout.addLayout(self.phase_row)

        # -------------------------
        # Ligne Système
        # -------------------------

        self.system_row = QHBoxLayout()
        self.system_row.addWidget(QLabel("Système"))

        self._system_buttons_container = QWidget()
        self._system_buttons_layout = QHBoxLayout(self._system_buttons_container)
        self._system_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.system_row.addWidget(self._system_buttons_container)
        self.system_row.addStretch()

        main_layout.addLayout(self.system_row)

        event_config.changed.connect(self.refresh_from_config)

        self.refresh_from_config()

    # =====================================================
    # Construction bouton
    # =====================================================

    def _make_button(self, text):

        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet(BUTTON_STYLE)

        return btn

    # =====================================================
    # (Re)construction depuis la configuration
    # =====================================================

    def refresh_from_config(self):
        """Reconstruit entièrement les boutons de phase (et de système
        pour la phase actuellement sélectionnée) à partir de la
        configuration active. Appelé au démarrage et à chaque
        modification de la configuration (ajout/suppression/activation)."""

        while self._phase_buttons_layout.count():
            item = self._phase_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._phase_buttons = {}

        phases = event_config.active_phase_names()

        for phase in phases:

            btn = self._make_button(phase)

            btn.clicked.connect(
                lambda checked=False, p=phase: self._on_phase_clicked(p)
            )

            self._phase_buttons[phase] = btn

            self._phase_buttons_layout.addWidget(btn)

        # Conserve la phase actuellement choisie si elle existe toujours,
        # sinon retombe sur la première phase active disponible.
        if self._current_phase not in phases:
            self._current_phase = phases[0] if phases else None

        if self._current_phase is not None:
            self._select_phase(self._current_phase, emit=False)
        else:
            self._rebuild_system_buttons(None)

    # =====================================================
    # Phase
    # =====================================================

    def _on_phase_clicked(self, phase):

        self._select_phase(phase)

    def _select_phase(self, phase, emit: bool = True):

        for p, btn in self._phase_buttons.items():

            btn.setChecked(p == phase)

        self._current_phase = phase

        self._rebuild_system_buttons(phase)

        if emit:
            self.emit_change()

    def _rebuild_system_buttons(self, phase):

        while self._system_buttons_layout.count():

            item = self._system_buttons_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        self._system_buttons = {}

        self._current_system = None

        systems = event_config.active_system_names(phase) if phase else []

        for system in systems:

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
