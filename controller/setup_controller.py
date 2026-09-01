"""Contrôleur de la phase de préparation du match (Setup).

Fait le lien entre la fenêtre de préparation (ui.setup.setup_window) et la
base de données : création du match, des équipes et des joueurs.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from data.database import Database


class SetupController:
    """Orchestre la création d'un match à partir des données saisies par l'utilisateur."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def start_analysis(
        self,
        game_name: str,
        game_date: str,
        video_path: str,
        home_team_name: str,
        home_players: List[Tuple[str, int]],
        home_present_players: List[Tuple[str, int]],
        home_color: str,
        away_team_name: str,
        away_players: List[Tuple[str, int]],
        away_present_players: List[Tuple[str, int]],
        away_color: str,
        season_id: Optional[int] = None,
    ) -> int:
        """Crée le match, les équipes et les joueurs en base de données.

        Args:
            game_name: nom du match.
            game_date: date du match (format "yyyy-MM-dd").
            video_path: chemin vers le fichier vidéo du match.
            home_team_name: nom de l'équipe à domicile.
            home_players: effectif complet (nom, numéro) de l'équipe à domicile.
            home_present_players: sous-ensemble de `home_players` présent à ce match.
            home_color: couleur (hex) de l'équipe à domicile.
            away_team_name: nom de l'équipe à l'extérieur.
            away_players: effectif complet (nom, numéro) de l'équipe à l'extérieur.
            away_present_players: sous-ensemble de `away_players` présent à ce match.
            away_color: couleur (hex) de l'équipe à l'extérieur.
            season_id: saison à laquelle rattacher ce match (None = aucune
                saison, "Sans saison").

        Returns:
            L'identifiant du match nouvellement créé.
        """
        game_id = self.database.create_game(
            game_name, game_date, video_path, season_id=season_id
        )

        home_team_id = self.database.get_or_create_team(home_team_name, home_color)
        away_team_id = self.database.get_or_create_team(away_team_name, away_color)

        self.database.link_game_team(game_id, home_team_id, is_home=True)
        self.database.link_game_team(game_id, away_team_id, is_home=False)

        self._register_players(game_id, home_team_id, home_players, home_present_players)
        self._register_players(game_id, away_team_id, away_players, away_present_players)

        return game_id

    def _register_players(
        self,
        game_id: int,
        team_id: int,
        players: List[Tuple[str, int]],
        present_players: List[Tuple[str, int]],
    ) -> None:
        """Crée (ou réutilise) chaque joueur de l'effectif, et n'associe au
        match que ceux marqués comme présents."""

        present_set = set(present_players)

        for name, number in players:
            player_id = self.database.get_or_create_player(team_id, name, number)
            if (name, number) in present_set:
                self.database.link_game_player(game_id, player_id)
