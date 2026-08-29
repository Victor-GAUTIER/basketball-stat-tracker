"""Flags de fonctionnalités optionnelles de la saisie (afficher/masquer
PhasePanel, le popup de détails du tir, ou certains de ses champs).

Contrairement aux phases/systèmes/types d'action/événements (partagés
entre tous les utilisateurs via la base de données, car ils affectent la
cohérence des statistiques collectées), ces réglages sont des préférences
d'affichage locales à chaque poste, gérées comme le thème sombre/clair
(voir ui.theme) via QSettings plutôt qu'en base.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QObject, QSettings, Signal


ORG_NAME = "RennesAvenir"
APP_NAME = "BasketballStatTracker"

DEFAULT_FLAGS: Dict[str, bool] = {
    "phase_panel": True,
    "shot_details_dialog": True,
    "field_action_type": True,
    "field_defense": True,
    "field_prior_oreb": True,
    "field_dribbles": True,
}


class _FeatureFlagsManager(QObject):

    changed = Signal()

    def is_phase_panel_enabled(self) -> bool:
        return self._get("phase_panel")

    def is_shot_details_dialog_enabled(self) -> bool:
        return self._get("shot_details_dialog")

    def is_field_enabled(self, field_key: str) -> bool:
        return self._get(f"field_{field_key}")

    def set_flag(self, key: str, enabled: bool) -> None:
        settings = QSettings(ORG_NAME, APP_NAME)
        settings.setValue(f"event_flags/{key}", enabled)
        self.changed.emit()

    def _get(self, key: str) -> bool:
        settings = QSettings(ORG_NAME, APP_NAME)
        default = DEFAULT_FLAGS.get(key, True)
        value = settings.value(f"event_flags/{key}", default)
        # QSettings peut renvoyer une string "true"/"false" selon l'OS
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)


feature_flags = _FeatureFlagsManager()
