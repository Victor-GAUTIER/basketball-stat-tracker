"""Modèles de données (dataclasses) représentant les entités métier.

Ces classes sont de simples conteneurs de données utilisés pour transporter
les informations entre la base de données, les contrôleurs et l'interface.
Elles ne contiennent aucune logique d'accès aux données (voir database.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Team:
    """Représente une équipe."""

    id: Optional[int]
    name: str


@dataclass
class Player:
    """Représente un joueur, rattaché à une équipe."""

    id: Optional[int]
    team_id: int
    name: str
    number: int


@dataclass
class Game:
    """Représente un match."""

    id: Optional[int]
    name: str
    date: str
    video_path: str


@dataclass
class Event:
    """Représente un événement statistique horodaté durant un match."""

    id: Optional[int]
    game_id: int
    player_id: int
    timestamp: float  # position dans la vidéo, en secondes
    quarter: int
    event_type: str
    x: Optional[float] = None
    y: Optional[float] = None
