"""Configuration personnalisable des phases de jeu, systèmes, types
d'action et niveaux de défense.

Ces listes étaient auparavant codées en dur dans ui.analysis.phase_panel.
Elles sont maintenant stockées en base et modifiables depuis le menu
Affichage > Configuration des événements (voir ui.event_config_dialog),
pour permettre à chacun d'ajouter, renommer, activer ou désactiver une
entrée sans toucher au code.

Un singleton `event_config` centralise l'état en mémoire (chargé une fois
au démarrage, mis à jour à chaque modification) et émet un signal
`changed` pour que les widgets persistants (PhasePanel) se
resynchronisent ; les popups reconstruits à chaque ouverture
(ShotDetailsDialog, EditEventDialog) lisent simplement l'état courant à
leur construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal


# Valeurs par défaut, utilisées uniquement pour peupler la base la
# première fois qu'elle est créée (voir Database._seed_event_config).
DEFAULT_PHASES: Dict[str, List[str]] = {
    "Contre-attaque": [],
    "Transition": ["Stream", "Ghost", "Flash", "Boum", "Bas"],
    "Attaque placée": ["Poing", "2", "Maillot"],
    "Touche": ["TF1", "TF2", "TC"],
}

DEFAULT_ACTION_TYPES: List[str] = [
    "Jeu rapide", "PnR", "Drive", "Poste bas", "Coupe",
    "Reb off", "Écran non porteur", "Mouvement de balle",
]

DEFAULT_DEFENSE_LEVELS: List[str] = ["Ouvert", "Un peu défendu", "Très défendu"]


@dataclass
class ConfigEntry:
    id: int
    name: str
    enabled: bool


@dataclass
class EventConfigState:
    phases: List[ConfigEntry] = field(default_factory=list)
    systems_by_phase: Dict[int, List[ConfigEntry]] = field(default_factory=dict)
    action_types: List[ConfigEntry] = field(default_factory=list)
    defense_levels: List[ConfigEntry] = field(default_factory=list)


class _EventConfigManager(QObject):
    """Singleton applicatif : un seul exemplaire, importé partout où la
    configuration des événements est nécessaire."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._db = None
        self.state = EventConfigState()

    # -----------------------------------------------------
    # Chargement
    # -----------------------------------------------------

    def load(self, database) -> None:
        self._db = database
        self.reload()

    def reload(self) -> None:
        if self._db is None:
            return
        self.state = self._db.get_event_config_state()
        self.changed.emit()

    # -----------------------------------------------------
    # Accès en lecture (entrées actives uniquement), pour les widgets
    # de saisie (PhasePanel, ShotDetailsDialog, EditEventDialog).
    # -----------------------------------------------------

    def active_phase_names(self) -> List[str]:
        return [p.name for p in self.state.phases if p.enabled]

    def active_system_names(self, phase_name: str) -> List[str]:
        phase = next((p for p in self.state.phases if p.name == phase_name), None)
        if phase is None:
            return []
        systems = self.state.systems_by_phase.get(phase.id, [])
        return [s.name for s in systems if s.enabled]

    def active_action_type_names(self) -> List[str]:
        return [a.name for a in self.state.action_types if a.enabled]

    def active_defense_level_names(self) -> List[str]:
        return [d.name for d in self.state.defense_levels if d.enabled]

    # -----------------------------------------------------
    # Écriture (déléguée à la base, puis rechargement du cache)
    # -----------------------------------------------------

    def add_phase(self, name: str) -> None:
        self._db.add_event_phase(name)
        self.reload()

    def rename_phase(self, phase_id: int, name: str) -> None:
        self._db.rename_event_phase(phase_id, name)
        self.reload()

    def set_phase_enabled(self, phase_id: int, enabled: bool) -> None:
        self._db.set_event_phase_enabled(phase_id, enabled)
        self.reload()

    def delete_phase(self, phase_id: int) -> None:
        self._db.delete_event_phase(phase_id)
        self.reload()

    def add_system(self, phase_id: int, name: str) -> None:
        self._db.add_event_system(phase_id, name)
        self.reload()

    def rename_system(self, system_id: int, name: str) -> None:
        self._db.rename_event_system(system_id, name)
        self.reload()

    def set_system_enabled(self, system_id: int, enabled: bool) -> None:
        self._db.set_event_system_enabled(system_id, enabled)
        self.reload()

    def delete_system(self, system_id: int) -> None:
        self._db.delete_event_system(system_id)
        self.reload()

    def add_action_type(self, name: str) -> None:
        self._db.add_event_action_type(name)
        self.reload()

    def rename_action_type(self, entry_id: int, name: str) -> None:
        self._db.rename_event_action_type(entry_id, name)
        self.reload()

    def set_action_type_enabled(self, entry_id: int, enabled: bool) -> None:
        self._db.set_event_action_type_enabled(entry_id, enabled)
        self.reload()

    def delete_action_type(self, entry_id: int) -> None:
        self._db.delete_event_action_type(entry_id)
        self.reload()

    def add_defense_level(self, name: str) -> None:
        self._db.add_event_defense_level(name)
        self.reload()

    def rename_defense_level(self, entry_id: int, name: str) -> None:
        self._db.rename_event_defense_level(entry_id, name)
        self.reload()

    def set_defense_level_enabled(self, entry_id: int, enabled: bool) -> None:
        self._db.set_event_defense_level_enabled(entry_id, enabled)
        self.reload()

    def delete_defense_level(self, entry_id: int) -> None:
        self._db.delete_event_defense_level(entry_id)
        self.reload()


event_config = _EventConfigManager()
