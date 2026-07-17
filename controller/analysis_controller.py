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

    def __init__(
        self,
        database: Database,
        game_id: int
    ) -> None:

        self.database = database
        self.game_id = game_id

        # Quart temps courant pendant la saisie
        self.current_quarter = 1


    # =====================================================
    # Chargement des données du match
    # =====================================================

    def get_game(self) -> Optional[Game]:
        return self.database.get_game(
            self.game_id
        )


    def get_teams(self) -> List[Tuple[Team, bool]]:
        """
        Retourne les équipes du match sous la forme :
        [(équipe, est_domicile)]
        """

        return self.database.get_game_teams(
            self.game_id
        )


    def get_players_for_team(
        self,
        team_id: int
    ) -> List[Player]:

        return self.database.get_game_players(
            self.game_id,
            team_id
        )



    # =====================================================
    # Gestion du quart temps
    # =====================================================

    def set_quarter(
        self,
        quarter: int
    ) -> None:

        self.current_quarter = quarter



    def get_current_quarter(self) -> int:

        return self.current_quarter


    # =====================================================
    # Enregistrement des événements
    # =====================================================

    def record_event(
        self,
        player_id: int,
        timestamp: float,
        event_type: str,
        *,
        phase: Optional[str] = None,
        system: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Event:
        """
        Ajoute un événement dans la base.

        phase et system décrivent la situation de jeu :
        - phase : Contre attaque, Transition, Attaque placée, Touche...
        - system : système associé (Ghost, Flash, Poing...)

        x et y sont utilisés pour les tirs afin de construire
        le shot chart.
        """

        event_id = self.database.add_event(
            game_id=self.game_id,
            player_id=player_id,
            timestamp=timestamp,
            quarter=self.current_quarter,
            event_type=event_type,
            phase=phase,
            system=system,
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
            phase=phase,
            system=system,
            x=x,
            y=y,
        )



    # =====================================================
    # Récupération événements
    # =====================================================

    def get_events(self) -> List[Event]:

        return self.database.get_events_for_game(
            self.game_id
        )



    def get_shots(self) -> List[Event]:
        """
        Retourne uniquement les tirs ayant une position.

        Utilisé pour le shot chart.
        """

        shot_types = (
            "2PTS_MADE",
            "2PTS_MISS",
            "3PTS_MADE",
            "3PTS_MISS",
        )


        return [
            event
            for event in self.get_events()
            if event.event_type in shot_types
            and event.x is not None
            and event.y is not None
        ]



    def get_player_shots(
        self,
        player_id: int
    ) -> List[Event]:
        """
        Retourne les tirs d'un joueur précis.
        """

        return [
            event
            for event in self.get_shots()
            if event.player_id == player_id
        ]



    # =====================================================
    # Statistiques
    # =====================================================

    def get_player_stats(
        self
    ) -> Dict[int, Dict[str, int]]:
        """
        Retourne :

        {
            player_id:
                {
                    event_type: nombre
                }
        }

        Exemple :

        {
            12:
                {
                    "2PTS_MADE": 5,
                    "REB": 3
                }
        }
        """


        stats: Dict[int, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )


        for event in self.get_events():

            stats[event.player_id][event.event_type] += 1



        return {
            player_id: dict(counts)
            for player_id, counts in stats.items()
        }



    def get_team_stats(
        self,
        player_ids: List[int]
    ) -> Dict[str, int]:
        """
        Calcule les stats cumulées d'une équipe.
        """

        totals = defaultdict(int)


        for event in self.get_events():

            if event.player_id in player_ids:

                totals[event.event_type] += 1


        return dict(totals)
