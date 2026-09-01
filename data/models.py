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
    color: str = "#297ffe"


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
    phase: Optional[str] = None
    system: Optional[str] = None
    action_type: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None

    # Détails saisis spécifiquement pour les tirs (voir
    # ui.analysis.shot_details_dialog.ShotDetailsDialog) : niveau de
    # défense subi, tir consécutif à un rebond offensif dans la même
    # possession, nombre de dribbles pris avant le tir. None = non
    # renseigné (événement antérieur à l'ajout de ces champs, ou
    # événement qui n'est pas un tir).
    defense_level: Optional[str] = None
    prior_oreb: Optional[bool] = None
    dribbles: Optional[int] = None


@dataclass
class Season:
    """Représente un groupe de matchs."""

    id: Optional[int]
    name: str
