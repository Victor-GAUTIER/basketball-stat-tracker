import csv

from data.models import Event, Player


def export_events(events: list[Event], players: dict[int, Player], path: str):
    """Écrit tous les événements d'un match dans un CSV, en résolvant les
    noms de joueurs (plutôt que de stocker un CSV brut à chaque clic
    comme dans la v1)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["timestamp_s", "joueur", "numero", "evenement"])
        for e in events:
            p = players.get(e.player_id)
            name = p.name if p else "?"
            number = p.number if p else "?"
            writer.writerow([round(e.timestamp, 2), name, number, e.event_type])
