from typing import Optional

from data.database import Database
from data.models import Player, Game, Event


class GameController:
    """Toute la logique métier passe par ici. L'UI ne touche jamais
    directement à la BDD : elle appelle des méthodes du controller.
    Ça permet de tester la logique sans lancer Qt, et de changer
    l'UI plus tard sans toucher aux règles métier."""

    def __init__(self, db: Database):
        self.db = db
        self.current_game: Optional[Game] = None
        self.current_player: Optional[Player] = None

    # ---------- Setup ----------

    def load_video(self, video_path: str) -> Game:
        self.current_game = self.db.get_or_create_game(video_path)
        return self.current_game

    def set_active_player(self, player: Player):
        self.current_player = player

    def add_player(self, name: str, number: int) -> Player:
        return self.db.add_player(name, number)

    def get_players(self) -> list[Player]:
        return self.db.get_players()

    # ---------- Événements ----------

    def record_event(self, event_type: str, timestamp: float) -> Optional[Event]:
        if self.current_game is None:
            raise ValueError("Aucune vidéo chargée.")
        if self.current_player is None:
            raise ValueError("Aucun joueur sélectionné.")

        return self.db.add_event(
            game_id=self.current_game.id,
            player_id=self.current_player.id,
            timestamp=timestamp,
            event_type=event_type,
        )

    def undo_last_event(self):
        """Supprime le dernier événement enregistré pour la partie en cours."""
        if self.current_game is None:
            return
        events = self.db.get_events(self.current_game.id)
        if events:
            self.db.delete_event(events[-1].id)

    def get_events(self) -> list[Event]:
        if self.current_game is None:
            return []
        return self.db.get_events(self.current_game.id)
