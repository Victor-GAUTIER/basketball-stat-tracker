from dataclasses import dataclass
from typing import Optional


EVENTS = [
    "2PTS_MADE",
    "2PTS_MISS",
    "3PTS_MADE",
    "3PTS_MISS",
    "REBOND_OFF",
    "REBOND_DEF",
    "PASSE_DEC",
    "PERTE_BALLE",
    "FAUTE",
]


@dataclass
class Player:
    id: Optional[int]
    name: str
    number: int


@dataclass
class Game:
    id: Optional[int]
    name: str
    video_path: str


@dataclass
class Event:
    id: Optional[int]
    game_id: int
    player_id: int
    timestamp: float       # secondes dans la vidéo
    event_type: str        # voir EVENTS
    x: Optional[float] = None   # position terrain (rempli plus tard par le ML)
    y: Optional[float] = None
