"""Libellés lisibles pour les codes d'événements internes.

Les événements sont stockés en base avec des codes techniques (ex :
"2PTS_MADE", "FOUL"). Ce module centralise leur traduction en texte lisible
pour l'affichage (play-by-play, dialogue d'édition...), afin d'avoir une
seule source de vérité partagée entre les différents écrans plutôt que des
libellés dupliqués (et potentiellement incohérents) un peu partout.

Les événements "classiques" (LF+, Rebonds, Passe décisive, Perte de
balle...) ont un libellé personnalisable via data.event_config (menu
Affichage > Configuration des événements). event_label() les résout en
priorité depuis cette configuration, avec repli sur les libellés statiques
ci-dessous pour les codes qui n'en dépendent pas (tirs, sous-types de
perte de balle) ou pour un événement enregistré avec un ancien libellé
avant renommage.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from data.event_config import event_config

# (code interne, libellé affiché) pour les codes qui ne dépendent PAS de
# la configuration personnalisable : tirs (zone détectée automatiquement
# sur le terrain) et sous-types de perte de balle (voir
# ui.analysis.turnover_dialog.TURNOVER_TYPES).
STATIC_EVENT_CHOICES: List[Tuple[str, str]] = [
    ("2PTS_MADE", "2 points marqués"),
    ("2PTS_MISSED", "2 points manqués"),
    ("3PTS_MADE", "3 points marqués"),
    ("3PTS_MISSED", "3 points manqués"),
    ("TO_PASS", "Perte de balle (passe)"),
    ("TO_DRIBBLE", "Perte de balle (dribble)"),
    ("TO_VIOLATION", "Perte de balle (violation)"),
    ("TO_SORTIE", "Perte de balle (sortie)"),
    ("TO_FAUTE", "Perte de balle (faute)"),
    ("TO_TEMPS", "Perte de balle (temps)"),
    ("TO_AUTRE", "Perte de balle (autre)"),
]

STATIC_EVENT_LABELS: Dict[str, str] = dict(STATIC_EVENT_CHOICES)


def event_label(code: str) -> str:
    """Retourne le libellé lisible d'un code d'événement.

    Cherche d'abord dans la configuration personnalisable des événements
    classiques (actifs ou non, pour rester lisible même si un événement a
    depuis été désactivé ou supprimé), puis dans les libellés statiques
    (tirs, sous-types de perte de balle). Si le code n'est reconnu nulle
    part, retourne le code brut tel quel plutôt que de lever une erreur :
    un affichage un peu moins joli vaut mieux qu'un plantage de
    l'interface.
    """

    dynamic_label = event_config.event_label_by_code(code)

    if dynamic_label is not None:
        return dynamic_label

    return STATIC_EVENT_LABELS.get(code, code)


def get_event_choices() -> List[Tuple[str, str]]:
    """Liste complète (code, libellé) pour peupler un menu déroulant de
    sélection d'événement (voir EditEventDialog) : événements classiques
    actifs (configuration personnalisable) + tirs + sous-types de perte
    de balle."""

    active_classic = [
        (code, label)
        for code, label, _shortcut in event_config.active_event_types()
    ]

    return active_classic + STATIC_EVENT_CHOICES


# Conservé pour compatibilité ascendante avec d'éventuels imports
# existants ; préférer get_event_choices() pour une liste à jour.
EVENT_CHOICES = STATIC_EVENT_CHOICES
EVENT_LABELS = STATIC_EVENT_LABELS
