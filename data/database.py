import sqlite3
from pathlib import Path
from typing import Optional

from data.models import Player, Game, Event


SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    video_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    x REAL,
    y REAL,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (player_id) REFERENCES players (id)
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER,
    tracking_id INTEGER,
    timestamp REAL NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games (id),
    FOREIGN KEY (player_id) REFERENCES players (id)
);
"""


class Database:
    """Wrapper simple autour de sqlite3. Une instance = une connexion à un
    fichier .db. Toutes les méthodes renvoient des objets du module models,
    jamais des tuples bruts, pour garder l'UI découplée du SQL."""

    def __init__(self, path: str = "basket_scout.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- Players ----------

    def add_player(self, name: str, number: int) -> Player:
        cur = self.conn.execute(
            "INSERT INTO players (name, number) VALUES (?, ?)", (name, number)
        )
        self.conn.commit()
        return Player(id=cur.lastrowid, name=name, number=number)

    def get_players(self) -> list[Player]:
        rows = self.conn.execute("SELECT * FROM players ORDER BY number").fetchall()
        return [Player(id=r["id"], name=r["name"], number=r["number"]) for r in rows]

    def delete_player(self, player_id: int):
        self.conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
        self.conn.commit()

    # ---------- Games ----------

    def add_game(self, name: str, video_path: str) -> Game:
        cur = self.conn.execute(
            "INSERT INTO games (name, video_path) VALUES (?, ?)", (name, video_path)
        )
        self.conn.commit()
        return Game(id=cur.lastrowid, name=name, video_path=video_path)

    def get_or_create_game(self, video_path: str) -> Game:
        row = self.conn.execute(
            "SELECT * FROM games WHERE video_path = ?", (video_path,)
        ).fetchone()
        if row:
            return Game(id=row["id"], name=row["name"], video_path=row["video_path"])
        name = Path(video_path).stem
        return self.add_game(name, video_path)

    # ---------- Events ----------

    def add_event(
        self,
        game_id: int,
        player_id: int,
        timestamp: float,
        event_type: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Event:
        cur = self.conn.execute(
            """INSERT INTO events (game_id, player_id, timestamp, event_type, x, y)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (game_id, player_id, timestamp, event_type, x, y),
        )
        self.conn.commit()
        return Event(
            id=cur.lastrowid,
            game_id=game_id,
            player_id=player_id,
            timestamp=timestamp,
            event_type=event_type,
            x=x,
            y=y,
        )

    def delete_event(self, event_id: int):
        self.conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.conn.commit()

    def get_events(self, game_id: int) -> list[Event]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE game_id = ? ORDER BY timestamp", (game_id,)
        ).fetchall()
        return [
            Event(
                id=r["id"],
                game_id=r["game_id"],
                player_id=r["player_id"],
                timestamp=r["timestamp"],
                event_type=r["event_type"],
                x=r["x"],
                y=r["y"],
            )
            for r in rows
        ]

    # ---------- Stats agrégées ----------

    def get_player_stats(self, game_id: int) -> list[sqlite3.Row]:
        """Renvoie, par joueur, le nombre d'occurrences de chaque type
        d'événement (pivot fait côté Python dans stats.py)."""
        return self.conn.execute(
            """SELECT p.id AS player_id, p.name, p.number,
                      e.event_type, COUNT(*) AS count
               FROM events e
               JOIN players p ON p.id = e.player_id
               WHERE e.game_id = ?
               GROUP BY p.id, e.event_type""",
            (game_id,),
        ).fetchall()

    def close(self):
        self.conn.close()
