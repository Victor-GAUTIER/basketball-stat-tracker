"""Couche d'accès à la base de données SQLite.

Toute l'interaction avec SQLite est centralisée ici : création du schéma,
opérations CRUD sur les équipes, joueurs, matchs et événements. Le reste de
l'application ne doit jamais exécuter de requêtes SQL directement, mais
passer par les méthodes de la classe Database.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from data.models import Event, Game, Player, Team


# Schéma complet de la base. `IF NOT EXISTS` permet de relancer l'application
# sur une base déjà existante sans erreur.
SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS players (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name    TEXT NOT NULL,
    number  INTEGER NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS games (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    date       TEXT NOT NULL,
    video_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_teams (
    game_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    is_home INTEGER NOT NULL,
    PRIMARY KEY (game_id, team_id),
    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_players (
    game_id   INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, player_id),
    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id    INTEGER NOT NULL,
    player_id  INTEGER NOT NULL,
    timestamp  REAL NOT NULL,
    quarter    INTEGER NOT NULL,
    event_type TEXT NOT NULL,

    phase      TEXT,
    system     TEXT,

    x          REAL,
    y          REAL,

    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
);
"""


class Database:
    """Gère la connexion SQLite et toutes les opérations CRUD de l'application."""

    def __init__(self, db_path: str = "basketball_stats.db") -> None:
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_schema()

    # ------------------------------------------------------------------
    # Connexion / schéma
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def _create_schema(self) -> None:
        assert self._connection is not None
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        assert self._connection is not None
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # ------------------------------------------------------------------
    # Equipes
    # ------------------------------------------------------------------
    def get_or_create_team(self, name: str) -> int:
        """Retourne l'id de l'équipe portant ce nom, en la créant si besoin."""
        cur = self.connection.execute("SELECT id FROM teams WHERE name = ?", (name,))
        row = cur.fetchone()
        if row is not None:
            return int(row["id"])
        cur = self.connection.execute("INSERT INTO teams (name) VALUES (?)", (name,))
        self.connection.commit()
        return int(cur.lastrowid)

    def get_teams(self) -> List[Team]:
        cur = self.connection.execute("SELECT id, name FROM teams ORDER BY name")
        return [Team(id=r["id"], name=r["name"]) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Joueurs
    # ------------------------------------------------------------------
    def get_or_create_player(self, team_id: int, name: str, number: int) -> int:
        """Retourne l'id du joueur (team_id, number), en le créant si besoin.

        Si le joueur existe déjà (même équipe, même numéro), son nom est mis
        à jour au cas où il aurait changé.
        """
        cur = self.connection.execute(
            "SELECT id FROM players WHERE team_id = ? AND number = ?",
            (team_id, number),
        )
        row = cur.fetchone()
        if row is not None:
            self.connection.execute(
                "UPDATE players SET name = ? WHERE id = ?", (name, row["id"])
            )
            self.connection.commit()
            return int(row["id"])
        cur = self.connection.execute(
            "INSERT INTO players (team_id, name, number) VALUES (?, ?, ?)",
            (team_id, name, number),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def get_players_by_team(self, team_id: int) -> List[Player]:
        cur = self.connection.execute(
            "SELECT id, team_id, name, number FROM players "
            "WHERE team_id = ? ORDER BY number",
            (team_id,),
        )
        return [
            Player(id=r["id"], team_id=r["team_id"], name=r["name"], number=r["number"])
            for r in cur.fetchall()
        ]

    def get_player(self, player_id: int) -> Optional[Player]:
        cur = self.connection.execute(
            "SELECT id, team_id, name, number FROM players WHERE id = ?",
            (player_id,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return Player(id=r["id"], team_id=r["team_id"], name=r["name"], number=r["number"])

    def update_player(
        self,
        player_id: int,
        name: str,
        number: int
    ) -> None:
        """Modifie le nom et le numéro d'une joueuse."""

        self.connection.execute(
            """
            UPDATE players
            SET name = ?, number = ?
            WHERE id = ?
            """,
            (name, number, player_id)
        )

        self.connection.commit()

    # ------------------------------------------------------------------
    # Matchs
    # ------------------------------------------------------------------
    def create_game(self, name: str, date: str, video_path: str) -> int:
        cur = self.connection.execute(
            "INSERT INTO games (name, date, video_path) VALUES (?, ?, ?)",
            (name, date, video_path),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def get_game(self, game_id: int) -> Optional[Game]:
        cur = self.connection.execute(
            "SELECT id, name, date, video_path FROM games WHERE id = ?", (game_id,)
        )
        r = cur.fetchone()
        if r is None:
            return None
        return Game(id=r["id"], name=r["name"], date=r["date"], video_path=r["video_path"])

    def get_games(self) -> List[Game]:
        cur = self.connection.execute(
            "SELECT id, name, date, video_path FROM games ORDER BY date DESC"
        )
        return [
            Game(id=r["id"], name=r["name"], date=r["date"], video_path=r["video_path"])
            for r in cur.fetchall()
        ]

    def link_game_team(self, game_id: int, team_id: int, is_home: bool) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO game_teams (game_id, team_id, is_home) "
            "VALUES (?, ?, ?)",
            (game_id, team_id, int(is_home)),
        )
        self.connection.commit()

    def get_game_teams(self, game_id: int) -> List[Tuple[Team, bool]]:
        """Retourne les deux équipes associées à un match, avec leur statut domicile/extérieur."""
        cur = self.connection.execute(
            "SELECT t.id, t.name, gt.is_home FROM teams t "
            "JOIN game_teams gt ON gt.team_id = t.id "
            "WHERE gt.game_id = ? ORDER BY gt.is_home DESC",
            (game_id,),
        )
        return [
            (Team(id=r["id"], name=r["name"]), bool(r["is_home"]))
            for r in cur.fetchall()
        ]

    def link_game_player(self, game_id: int, player_id: int) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO game_players (game_id, player_id) VALUES (?, ?)",
            (game_id, player_id),
        )
        self.connection.commit()

    def get_game_players(self, game_id: int, team_id: int) -> List[Player]:
        """Retourne les joueurs d'une équipe qui participent effectivement à ce match."""
        cur = self.connection.execute(
            "SELECT p.id, p.team_id, p.name, p.number FROM players p "
            "JOIN game_players gp ON gp.player_id = p.id "
            "WHERE gp.game_id = ? AND p.team_id = ? ORDER BY p.number",
            (game_id, team_id),
        )
        return [
            Player(id=r["id"], team_id=r["team_id"], name=r["name"], number=r["number"])
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------
    # Evénements
    # ------------------------------------------------------------------
    def add_event(
        self,
        game_id: int,
        player_id: int,
        timestamp: float,
        quarter: int,
        event_type: str,
        phase: Optional[str] = None,
        system: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> int:

        cur = self.connection.execute(
            """
            INSERT INTO events (
                game_id,
                player_id,
                timestamp,
                quarter,
                event_type,
                phase,
                system,
                x,
                y
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                player_id,
                timestamp,
                quarter,
                event_type,
                phase,
                system,
                x,
                y,
            ),
        )

        self.connection.commit()

        return int(cur.lastrowid)

    def delete_event(self, event_id: int) -> None:
        self.connection.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.connection.commit()

    def update_event(self, event_id: int, player_id: int, event_type: str) -> None:
        """Corrige la joueuse et/ou le type d'un événement déjà enregistré.

        Le timestamp, le quart-temps et les coordonnées x/y ne sont pas
        modifiés : seule une erreur de saisie (mauvaise joueuse ou mauvais
        type d'action) est corrigée ici, pas le moment de l'action.
        """
        self.connection.execute(
            "UPDATE events SET player_id = ?, event_type = ? WHERE id = ?",
            (player_id, event_type, event_id),
        )
        self.connection.commit()

    def get_events_for_game(self, game_id: int) -> List[Event]:
        cur = self.connection.execute(
            "SELECT id, game_id, player_id, timestamp, quarter, event_type, phase, system, x, y "
            "FROM events WHERE game_id = ? ORDER BY timestamp",
            (game_id,),
        )
        return [
            Event(
                id=r["id"],
                game_id=r["game_id"],
                player_id=r["player_id"],
                timestamp=r["timestamp"],
                quarter=r["quarter"],
                event_type=r["event_type"],
                phase=r["phase"],
                system=r["system"],
                x=r["x"],
                y=r["y"],
            )
            for r in cur.fetchall()
        ]

    def get_last_event_for_game(self, game_id: int) -> Optional[Event]:
        cur = self.connection.execute(
            "SELECT id, game_id, player_id, timestamp, quarter, event_type, phase, system, x, y "
            "FROM events WHERE game_id = ? ORDER BY id DESC LIMIT 1",
            (game_id,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return Event(
            id=r["id"],
            game_id=r["game_id"],
            player_id=r["player_id"],
            timestamp=r["timestamp"],
            quarter=r["quarter"],
            event_type=r["event_type"],
            phase=r["phase"],
            system=r["system"],
            x=r["x"],
            y=r["y"],
        )
