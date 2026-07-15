"""Contrôleur de la phase de préparation du match (Setup).

Fait le lien entre la fenêtre de préparation (ui.setup.setup_window) et la
base de données : création du match, des équipes et des joueurs.
"""

from __future__ import annotations

from typing import List, Tuple

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
        away_team_name: str,
        away_players: List[Tuple[str, int]],
    ) -> int:
        """Crée le match, les équipes et les joueurs en base de données.

        Args:
            game_name: nom du match.
            game_date: date du match (format "yyyy-MM-dd").
            video_path: chemin vers le fichier vidéo du match.
            home_team_name: nom de l'équipe à domicile.
            home_players: liste de tuples (nom, numéro) des joueurs à domicile.
            away_team_name: nom de l'équipe à l'extérieur.
            away_players: liste de tuples (nom, numéro) des joueurs à l'extérieur.

        Returns:
            L'identifiant du match nouvellement créé.
        """
        game_id = self.database.create_game(game_name, game_date, video_path)

        home_team_id = self.database.get_or_create_team(home_team_name)
        away_team_id = self.database.get_or_create_team(away_team_name)

        self.database.link_game_team(game_id, home_team_id, is_home=True)
        self.database.link_game_team(game_id, away_team_id, is_home=False)

        self._register_players(game_id, home_team_id, home_players)
        self._register_players(game_id, away_team_id, away_players)

        return game_id

    def _register_players(
        self, game_id: int, team_id: int, players: List[Tuple[str, int]]
    ) -> None:
        """Crée (ou réutilise) chaque joueur et l'associe au match."""
        for name, number in players:
            player_id = self.database.get_or_create_player(team_id, name, number)
            self.database.link_game_player(game_id, player_id)
