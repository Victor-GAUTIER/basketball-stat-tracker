"""Fenêtre de configuration des événements personnalisables : phases de
jeu, systèmes associés, types d'action, niveaux de défense, événements
classiques (avec raccourci clavier), et préférences d'affichage locales
au poste.

Accessible depuis le menu Affichage > Configuration des événements (voir
AnalysisWindow._create_menu). Les modifications de la configuration
partagée (phases, systèmes, types d'action, niveaux de défense,
événements) sont appliquées immédiatement (écriture en base à chaque
action) et se répercutent sans redémarrage sur tous les popups de saisie
(PhasePanel, EventPanel, ShotDetailsDialog, EditEventDialog) grâce au
signal data.event_config.event_config.changed. Les préférences
d'affichage (onglet Fonctionnalités) sont locales au poste (QSettings,
voir ui.feature_flags).
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.event_config import event_config
from ui.feature_flags import feature_flags


class _ManagedListWidget(QWidget):
    """Une liste à cases à cocher (activer/désactiver) avec boutons
    Ajouter / Renommer / Supprimer, réutilisée pour toutes les catégories
    "à plat" (types d'action, niveaux de défense, systèmes d'une phase)."""

    def __init__(
        self,
        title: str,
        get_entries: Callable[[], List],
        on_add: Callable[[str], None],
        on_rename: Callable[[int, str], None],
        on_set_enabled: Callable[[int, bool], None],
        on_delete: Callable[[int], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._get_entries = get_entries
        self._on_add = on_add
        self._on_rename = on_rename
        self._on_set_enabled = on_set_enabled
        self._on_delete = on_delete

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label)

        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        buttons_row = QHBoxLayout()

        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._on_add_clicked)

        rename_btn = QPushButton("Renommer")
        rename_btn.clicked.connect(self._on_rename_clicked)

        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._on_delete_clicked)

        buttons_row.addWidget(add_btn)
        buttons_row.addWidget(rename_btn)
        buttons_row.addWidget(delete_btn)

        layout.addLayout(buttons_row)

        self._suspend_signals = False

        self.refresh()

    def refresh(self) -> None:

        self._suspend_signals = True

        current_id = self._current_entry_id()

        self.list_widget.clear()

        for entry in self._get_entries():

            item = QListWidgetItem(entry.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if entry.enabled else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, entry.id)

            self.list_widget.addItem(item)

            if entry.id == current_id:
                self.list_widget.setCurrentItem(item)

        self._suspend_signals = False

    def _current_entry_id(self) -> Optional[int]:

        item = self.list_widget.currentItem()

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _on_item_changed(self, item: QListWidgetItem) -> None:

        if self._suspend_signals:
            return

        entry_id = item.data(Qt.ItemDataRole.UserRole)
        enabled = item.checkState() == Qt.CheckState.Checked

        self._on_set_enabled(entry_id, enabled)

    def _on_add_clicked(self) -> None:

        name, ok = QInputDialog.getText(self, "Ajouter", "Nom :")

        if not ok or not name.strip():
            return

        self._on_add(name.strip())

    def _on_rename_clicked(self) -> None:

        entry_id = self._current_entry_id()

        if entry_id is None:
            return

        current_name = self.list_widget.currentItem().text()

        name, ok = QInputDialog.getText(
            self, "Renommer", "Nouveau nom :", text=current_name
        )

        if not ok or not name.strip():
            return

        self._on_rename(entry_id, name.strip())

    def _on_delete_clicked(self) -> None:

        entry_id = self._current_entry_id()

        if entry_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Supprimer",
            "Supprimer cette entrée ? Les événements déjà enregistrés "
            "conservent leur valeur actuelle ; seule la liste de choix "
            "future est modifiée."
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._on_delete(entry_id)


class _EventTypesWidget(QWidget):
    """Onglet de gestion des événements classiques (LF+, Rebonds, Passe
    décisive, Perte de balle...) : renommer, changer le raccourci,
    activer/désactiver, ajouter un nouvel événement personnalisé,
    supprimer un événement personnalisé (les événements intégrés, marqués
    "[intégré]", ne peuvent être que renommés/désactivés)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        note = QLabel(
            "Les événements marqués \"[intégré]\" ne peuvent pas être "
            "supprimés (certains déclenchent un comportement spécifique "
            "à la saisie), mais restent renommables, désactivables, et "
            "leur raccourci reste modifiable."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: grey;")
        layout.addWidget(note)

        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        buttons_row = QHBoxLayout()

        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._on_add_clicked)

        rename_btn = QPushButton("Renommer")
        rename_btn.clicked.connect(self._on_rename_clicked)

        shortcut_btn = QPushButton("Changer le raccourci")
        shortcut_btn.clicked.connect(self._on_shortcut_clicked)

        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._on_delete_clicked)

        buttons_row.addWidget(add_btn)
        buttons_row.addWidget(rename_btn)
        buttons_row.addWidget(shortcut_btn)
        buttons_row.addWidget(delete_btn)

        layout.addLayout(buttons_row)

        self._suspend_signals = False

        self.refresh()

    def refresh(self) -> None:

        self._suspend_signals = True

        current_id = self._current_entry_id()

        self.list_widget.clear()

        for entry in event_config.state.event_types:

            builtin_suffix = " [intégré]" if entry["is_builtin"] else ""
            shortcut_suffix = f"  ({entry['shortcut']})" if entry["shortcut"] else ""

            item = QListWidgetItem(
                f"{entry['label']}{shortcut_suffix}{builtin_suffix}"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if entry["enabled"] else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, entry["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, entry["is_builtin"])

            self.list_widget.addItem(item)

            if entry["id"] == current_id:
                self.list_widget.setCurrentItem(item)

        self._suspend_signals = False

    def _current_entry_id(self) -> Optional[int]:

        item = self.list_widget.currentItem()

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _current_is_builtin(self) -> bool:

        item = self.list_widget.currentItem()

        if item is None:
            return False

        return bool(item.data(Qt.ItemDataRole.UserRole + 1))

    def _on_item_changed(self, item: QListWidgetItem) -> None:

        if self._suspend_signals:
            return

        entry_id = item.data(Qt.ItemDataRole.UserRole)
        enabled = item.checkState() == Qt.CheckState.Checked

        event_config.set_event_type_enabled(entry_id, enabled)

    def _on_add_clicked(self) -> None:

        label, ok = QInputDialog.getText(self, "Ajouter un événement", "Nom :")

        if not ok or not label.strip():
            return

        shortcut, ok = QInputDialog.getText(
            self,
            "Raccourci clavier",
            "Raccourci (ex: A, Shift+B, laisser vide si aucun) :",
        )

        if not ok:
            shortcut = ""

        event_config.add_event_type(label.strip(), shortcut.strip())

    def _on_rename_clicked(self) -> None:

        entry_id = self._current_entry_id()

        if entry_id is None:
            return

        current_label = self.list_widget.currentItem().text().split("  (")[0].replace(
            " [intégré]", ""
        )

        label, ok = QInputDialog.getText(
            self, "Renommer", "Nouveau nom :", text=current_label
        )

        if not ok or not label.strip():
            return

        event_config.rename_event_type(entry_id, label.strip())

    def _on_shortcut_clicked(self) -> None:

        entry_id = self._current_entry_id()

        if entry_id is None:
            return

        current_entry = next(
            (e for e in event_config.state.event_types if e["id"] == entry_id),
            None,
        )
        current_shortcut = current_entry["shortcut"] if current_entry else ""

        shortcut, ok = QInputDialog.getText(
            self,
            "Raccourci clavier",
            "Raccourci (ex: A, Shift+B, laisser vide pour aucun) :",
            text=current_shortcut,
        )

        if not ok:
            return

        event_config.set_event_type_shortcut(entry_id, shortcut.strip())

    def _on_delete_clicked(self) -> None:

        entry_id = self._current_entry_id()

        if entry_id is None:
            return

        if self._current_is_builtin():
            QMessageBox.warning(
                self,
                "Impossible de supprimer",
                "Cet événement est intégré à l'application et ne peut "
                "pas être supprimé. Vous pouvez le désactiver à la place."
            )
            return

        reply = QMessageBox.question(
            self,
            "Supprimer",
            "Supprimer cet événement ? Les événements déjà enregistrés "
            "conservent leur valeur actuelle ; seule la liste de choix "
            "future est modifiée."
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        event_config.delete_event_type(entry_id)


class _FeatureFlagsWidget(QWidget):
    """Onglet à cases à cocher pour activer/désactiver des sections
    entières de la saisie (PhasePanel, popup de détails du tir, champs
    individuels de ce popup). Préférence locale au poste (QSettings),
    voir ui.feature_flags."""

    FLAGS = [
        ("phase_panel", "Afficher la sélection de phase de jeu / système"),
        ("shot_details_dialog", "Afficher le popup de détails du tir"),
        ("field_action_type", "  → Champ : type d'action"),
        ("field_defense", "  → Champ : niveau de défense"),
        ("field_prior_oreb", "  → Champ : rebond offensif préalable"),
        ("field_dribbles", "  → Champ : nombre de dribbles"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        note = QLabel(
            "Réglages propres à ce poste (non partagés avec les autres "
            "utilisateurs). Les champs indentés (→) ne s'appliquent que "
            "si le popup de détails du tir est lui-même activé ci-dessus."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: grey;")
        layout.addWidget(note)

        self._checkboxes = {}

        for key, label in self.FLAGS:

            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._on_toggled(k, state)
            )

            self._checkboxes[key] = checkbox

            layout.addWidget(checkbox)

        layout.addStretch(1)

        self.refresh()

    def refresh(self) -> None:

        for key, checkbox in self._checkboxes.items():

            checkbox.blockSignals(True)
            checkbox.setChecked(feature_flags._get(key))
            checkbox.blockSignals(False)

    def _on_toggled(self, key: str, state: int) -> None:

        feature_flags.set_flag(key, state == Qt.CheckState.Checked.value)


class EventConfigDialog(QDialog):
    """Fenêtre principale de configuration, avec un onglet par
    catégorie."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Configuration des événements")
        self.setMinimumSize(640, 480)

        layout = QVBoxLayout(self)

        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        tabs.addTab(self._build_phases_tab(), "Phases & systèmes")
        tabs.addTab(self._build_event_types_tab(), "Événements")
        tabs.addTab(self._build_action_types_tab(), "Types d'action")
        tabs.addTab(self._build_defense_levels_tab(), "Niveaux de défense")
        tabs.addTab(self._build_features_tab(), "Fonctionnalités")

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        event_config.changed.connect(self._refresh_all)

    # =====================================================
    # Onglet Phases & systèmes (deux niveaux)
    # =====================================================

    def _build_phases_tab(self) -> QWidget:

        container = QWidget()
        outer_layout = QHBoxLayout(container)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._phases_list = _ManagedListWidget(
            "Phases",
            get_entries=lambda: event_config.state.phases,
            on_add=lambda name: event_config.add_phase(name),
            on_rename=lambda eid, name: event_config.rename_phase(eid, name),
            on_set_enabled=lambda eid, enabled: event_config.set_phase_enabled(eid, enabled),
            on_delete=lambda eid: event_config.delete_phase(eid),
        )

        self._phases_list.list_widget.currentItemChanged.connect(
            lambda *_: self._systems_list.refresh()
        )

        self._systems_list = _ManagedListWidget(
            "Systèmes de la phase sélectionnée",
            get_entries=self._current_phase_systems,
            on_add=self._add_system_to_current_phase,
            on_rename=lambda eid, name: event_config.rename_system(eid, name),
            on_set_enabled=lambda eid, enabled: event_config.set_system_enabled(eid, enabled),
            on_delete=lambda eid: event_config.delete_system(eid),
        )

        splitter.addWidget(self._phases_list)
        splitter.addWidget(self._systems_list)

        outer_layout.addWidget(splitter)

        return container

    def _current_phase_id(self) -> Optional[int]:

        item = self._phases_list.list_widget.currentItem()

        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _current_phase_systems(self) -> List:

        phase_id = self._current_phase_id()

        if phase_id is None:
            return []

        return event_config.state.systems_by_phase.get(phase_id, [])

    def _add_system_to_current_phase(self, name: str) -> None:

        phase_id = self._current_phase_id()

        if phase_id is None:
            QMessageBox.warning(
                self, "Aucune phase sélectionnée",
                "Sélectionnez une phase avant d'ajouter un système."
            )
            return

        event_config.add_system(phase_id, name)

    # =====================================================
    # Onglet Événements
    # =====================================================

    def _build_event_types_tab(self) -> QWidget:

        self._event_types_widget = _EventTypesWidget()

        return self._event_types_widget

    # =====================================================
    # Onglet Types d'action
    # =====================================================

    def _build_action_types_tab(self) -> QWidget:

        self._action_types_list = _ManagedListWidget(
            "",
            get_entries=lambda: event_config.state.action_types,
            on_add=lambda name: event_config.add_action_type(name),
            on_rename=lambda eid, name: event_config.rename_action_type(eid, name),
            on_set_enabled=lambda eid, enabled: event_config.set_action_type_enabled(eid, enabled),
            on_delete=lambda eid: event_config.delete_action_type(eid),
        )

        return self._action_types_list

    # =====================================================
    # Onglet Niveaux de défense
    # =====================================================

    def _build_defense_levels_tab(self) -> QWidget:

        self._defense_levels_list = _ManagedListWidget(
            "",
            get_entries=lambda: event_config.state.defense_levels,
            on_add=lambda name: event_config.add_defense_level(name),
            on_rename=lambda eid, name: event_config.rename_defense_level(eid, name),
            on_set_enabled=lambda eid, enabled: event_config.set_defense_level_enabled(eid, enabled),
            on_delete=lambda eid: event_config.delete_defense_level(eid),
        )

        return self._defense_levels_list

    # =====================================================
    # Onglet Fonctionnalités (préférences locales)
    # =====================================================

    def _build_features_tab(self) -> QWidget:

        self._features_widget = _FeatureFlagsWidget()

        return self._features_widget

    # =====================================================
    # Rafraîchissement global (après toute modification)
    # =====================================================

    def _refresh_all(self) -> None:

        self._phases_list.refresh()
        self._systems_list.refresh()
        self._event_types_widget.refresh()
        self._action_types_list.refresh()
        self._defense_levels_list.refresh()
        self._features_widget.refresh()
