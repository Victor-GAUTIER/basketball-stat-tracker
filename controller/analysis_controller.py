"""Contrôleur de la phase d'analyse vidéo.

Fait le lien entre la fenêtre d'analyse (ui.analysis.analysis_window) et la
base de données : enregistrement des événements et calcul des statistiques
affichées en direct.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from data.database import Database
from data.models import Event, Game, Player, Team


class AnalysisController:
    """Orchestre l'enregistrement des événements pendant l'analyse d'un match."""

    def __init__(self, database: Database, game_id: int) -> None:
        self.database = database
        self.game_id = game_id
        self.current_quarter = 1

    # ------------------------------------------------------------------
    # Chargement des données du match
    # ------------------------------------------------------------------
    def get_game(self) -> Optional[Game]:
        return self.database.get_game(self.game_id)

    def get_teams(self) -> List[Tuple[Team, bool]]:
        """Retourne les deux équipes du match sous la forme (équipe, est_domicile)."""
        return self.database.get_game_teams(self.game_id)

    def get_players_for_team(self, team_id: int) -> List[Player]:
        return self.database.get_game_players(self.game_id, team_id)

    # ------------------------------------------------------------------
    # Enregistrement des événements
    # ------------------------------------------------------------------
    def record_event(
        self,
        player_id: int,
        timestamp: float,
        event_type: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Event:
        """Enregistre un nouvel événement au timestamp vidéo courant."""
        event_id = self.database.add_event(
            game_id=self.game_id,
            player_id=player_id,
            timestamp=timestamp,
            quarter=self.current_quarter,
            event_type=event_type,
            x=x,
            y=y,
        )
        return Event(
            id=event_id,
            game_id=self.game_id,
            player_id=player_id,
            timestamp=timestamp,
            quarter=self.current_quarter,
            event_type=event_type,
            x=x,
            y=y,
        )

    def undo_last_event(self) -> Optional[Event]:
        """Supprime le dernier événement enregistré pour ce match."""
        last_event = self.database.get_last_event_for_game(self.game_id)
        if last_event is None or last_event.id is None:
            return None
        self.database.delete_event(last_event.id)
        return last_event

    def set_quarter(self, quarter: int) -> None:
        self.current_quarter = quarter

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------
    def get_events(self) -> List[Event]:
        return self.database.get_events_for_game(self.game_id)

    def get_player_stats(self) -> Dict[int, Dict[str, int]]:
        """Retourne, pour chaque joueur, le nombre d'occurrences par type
        d'événement. Structure : {player_id: {event_type: count}}.
        """
        stats: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for event in self.get_events():
            stats[event.player_id][event.event_type] += 1
        return {player_id: dict(counts) for player_id, counts in stats.items()}
