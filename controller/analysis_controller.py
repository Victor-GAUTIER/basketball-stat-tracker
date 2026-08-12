"""Contrôleur de la phase d'analyse vidéo.

Fait le lien entre la fenêtre d'analyse (ui.analysis.analysis_window) et la
base de données : enregistrement des événements et calcul des statistiques
affichées en direct.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from data.database import Database
from data.models import Event, Game, Player, Team

# Réutilisation des briques de calcul déjà utilisées pour le tableau de
# bord d'équipe (team_analysis_controller), afin d'éviter de dupliquer la
# logique d'agrégation des statistiques "boxscore".
from controller.team_analysis_controller import (
    TeamBoxScore,
    _apply_event_to_box,
    _is_turnover,
    _points,
)


SHOT_TYPES = ("2PTS_MADE", "2PTS_MISSED", "3PTS_MADE", "3PTS_MISSED")


@dataclass
class TeamComparisonData:
    """Statistiques détaillées des deux équipes pour le match en cours,
    utilisées par l'onglet "Comparaison" (TeamComparisonPanel)."""

    home_box: TeamBoxScore = field(default_factory=TeamBoxScore)
    away_box: TeamBoxScore = field(default_factory=TeamBoxScore)

    home_points_by_action: Dict[str, int] = field(default_factory=dict)
    away_points_by_action: Dict[str, int] = field(default_factory=dict)

    home_fga_by_action: Dict[str, int] = field(default_factory=dict)
    away_fga_by_action: Dict[str, int] = field(default_factory=dict)

    home_turnover_breakdown: Dict[str, int] = field(default_factory=dict)
    away_turnover_breakdown: Dict[str, int] = field(default_factory=dict)


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
            action_type: Optional[str] = None,
            x: Optional[float] = None,
            y: Optional[float] = None,
            defense_level: Optional[str] = None,
            prior_oreb: Optional[bool] = None,
            dribbles: Optional[int] = None,
        ) -> Event:
            """
            Ajoute un événement dans la base.

            phase et system décrivent la situation de jeu :
            - phase : Contre attaque, Transition, Attaque placée, Touche...
            - system : système associé (Ghost, Flash, Poing...)
            action_type décrit le type d'action individuelle :
            Jeu rapide, Pick and roll, Drive, Poste bas, Coupe,
            Rebond off, Écran non porteur, Mouvement de balle.

            x et y sont utilisés pour les tirs afin de construire
            le shot chart.

            defense_level, prior_oreb et dribbles sont des détails saisis
            spécifiquement pour les tirs (voir ShotDetailsDialog) : niveau
            de défense subi, tir consécutif à un rebond offensif dans la
            même possession, nombre de dribbles pris avant le tir.
            """

            event_id = self.database.add_event(
                game_id=self.game_id,
                player_id=player_id,
                timestamp=timestamp,
                quarter=self.current_quarter,
                event_type=event_type,
                phase=phase,
                system=system,
                action_type=action_type,
                x=x,
                y=y,
                defense_level=defense_level,
                prior_oreb=prior_oreb,
                dribbles=dribbles,
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
                action_type=action_type,
                x=x,
                y=y,
                defense_level=defense_level,
                prior_oreb=prior_oreb,
                dribbles=dribbles,
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

    # =====================================================
    # Statistiques détaillées pour l'onglet "Comparaison"
    # =====================================================

    def get_team_comparison_data(
        self,
        home_player_ids: Set[int],
        away_player_ids: Set[int],
    ) -> TeamComparisonData:
        """Calcule, pour le match en cours, les statistiques "boxscore"
        détaillées (four factors, points par action, tirs par action,
        répartition des pertes de balle) des deux équipes.

        Réutilise la même logique d'agrégation que le tableau de bord
        d'équipe (controller.team_analysis_controller), mais appliquée à un
        seul match plutôt qu'à l'historique complet d'une équipe.
        """

        data = TeamComparisonData()

        home_points_by_action: Dict[str, int] = defaultdict(int)
        away_points_by_action: Dict[str, int] = defaultdict(int)

        home_fga_by_action: Dict[str, int] = defaultdict(int)
        away_fga_by_action: Dict[str, int] = defaultdict(int)

        home_turnover_breakdown: Dict[str, int] = defaultdict(int)
        away_turnover_breakdown: Dict[str, int] = defaultdict(int)

        for event in self.get_events():

            is_home = event.player_id in home_player_ids

            box = data.home_box if is_home else data.away_box

            points_by_action = (
                home_points_by_action if is_home else away_points_by_action
            )
            fga_by_action = (
                home_fga_by_action if is_home else away_fga_by_action
            )
            turnover_breakdown = (
                home_turnover_breakdown if is_home else away_turnover_breakdown
            )

            pts = _points(event.event_type)

            _apply_event_to_box(box, event, pts)

            action = event.action_type or "Non renseigné"

            if pts > 0:
                points_by_action[action] += pts

            if event.event_type in SHOT_TYPES:
                fga_by_action[action] += 1

            if _is_turnover(event.event_type):
                to_label = (
                    event.event_type.replace("TO_", "")
                    if event.event_type.startswith("TO_")
                    else "AUTRE"
                )
                turnover_breakdown[to_label] += 1

        data.home_points_by_action = dict(home_points_by_action)
        data.away_points_by_action = dict(away_points_by_action)

        data.home_fga_by_action = dict(home_fga_by_action)
        data.away_fga_by_action = dict(away_fga_by_action)

        data.home_turnover_breakdown = dict(home_turnover_breakdown)
        data.away_turnover_breakdown = dict(away_turnover_breakdown)

        return data
