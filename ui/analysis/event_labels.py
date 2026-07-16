"""Libellés lisibles pour les codes d'événements internes.

Les événements sont stockés en base avec des codes techniques (ex :
"2PTS_MADE", "FOUL"). Ce module centralise leur traduction en texte lisible
pour l'affichage (play-by-play, dialogue d'édition...), afin d'avoir une
seule source de vérité partagée entre les différents écrans plutôt que des
libellés dupliqués (et potentiellement incohérents) un peu partout.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (code interne, libellé affiché) pour tous les types d'événements que
# l'application peut enregistrer : tirs (terrain de tir, avec zone détectée
# automatiquement) + événements classiques (panneau de boutons).
EVENT_CHOICES: List[Tuple[str, str]] = [
    ("2PTS_MADE", "2 points marqués"),
    ("2PTS_MISSED", "2 points manqués"),
    ("3PTS_MADE", "3 points marqués"),
    ("3PTS_MISSED", "3 points manqués"),
    ("FT_MADE", "Lancer franc marqué"),
    ("FT_MISSED", "Lancer franc manqué"),
    ("OFF_REBOUND", "Rebond offensif"),
    ("DEF_REBOUND", "Rebond défensif"),
    ("ASSIST", "Passe décisive"),
    ("TURNOVER", "Perte de balle"),
    ("STEAL", "Interception"),
    ("BLOCK", "Contre"),
    ("FOUL", "Faute"),
]

EVENT_LABELS: Dict[str, str] = dict(EVENT_CHOICES)


def event_label(code: str) -> str:
    """Retourne le libellé lisible d'un code d'événement.

    Si le code n'est pas reconnu, on retourne le code brut tel quel plutôt
    que de lever une erreur : un affichage un peu moins joli vaut mieux
    qu'un plantage de l'interface.
    """
    return EVENT_LABELS.get(code, code)
