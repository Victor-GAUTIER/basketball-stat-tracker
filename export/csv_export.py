"""Fonctions d'export des données du match vers différents formats.

Ce module ne contient pour l'instant que l'export CSV. Il est conçu pour
accueillir facilement, plus tard, des fonctions export_events_to_excel ou
export_events_to_pdf sans modifier le reste de l'application.
"""

from __future__ import annotations

import csv
from typing import Dict, List

from data.models import Event, Player


def export_events_to_csv(path: str, events: List[Event], players_by_id: Dict[int, Player]) -> None:
    """Exporte la liste des événements d'un match vers un fichier CSV.

    Args:
        path: chemin du fichier CSV à créer.
        events: liste des événements à exporter, triés par timestamp.
        players_by_id: dictionnaire {id joueur: Player}, pour résoudre noms et numéros.
    """
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["timestamp_s", "quarter", "player_number", "player_name", "event_type", "x", "y"]
        )
        for event in events:
            player = players_by_id.get(event.player_id)
            writer.writerow(
                [
                    f"{event.timestamp:.2f}",
                    event.quarter,
                    player.number if player else "",
                    player.name if player else "",
                    event.event_type,
                    event.x if event.x is not None else "",
                    event.y if event.y is not None else "",
                ]
            )
