"""Couche d'accès à la base de données SQLite.

Toute l'interaction avec SQLite est centralisée ici : création du schéma,
opérations CRUD sur les équipes, joueurs, matchs et événements. Le reste de
l'application ne doit jamais exécuter de requêtes SQL directement, mais
passer par les méthodes de la classe Database.
"""

from __future__ import annotations

import os
import sys
import sqlite3
from typing import Dict, List, Optional, Tuple

from data.models import Event, Game, Player, Team


def get_default_db_path() -> str:
    """Retourne un chemin fixe et propre à l'utilisateur pour la base de
    données, indépendant du dossier depuis lequel l'app est lancée."""

    app_name = "BasketballStatTracker"

    if sys.platform == "win32":
        base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        base_dir = os.path.expanduser("~/.local/share")

    app_dir = os.path.join(base_dir, app_name)
    os.makedirs(app_dir, exist_ok=True)

    return os.path.join(app_dir, "basketball_stats.db")


# Couleur par défaut attribuée à une équipe qui n'en a pas encore choisi une
# (équipes créées avant l'ajout de cette fonctionnalité, par exemple).
DEFAULT_TEAM_COLOR = "#297ffe"


# Schéma complet de la base. `IF NOT EXISTS` permet de relancer l'application
# sur une base déjà existante sans erreur.
SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    color TEXT
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
    number    INTEGER,
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

    phase       TEXT,
    system      TEXT,
    action_type TEXT,

    x          REAL,
    y          REAL,

    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_phases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_systems (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id   INTEGER NOT NULL,
    name       TEXT NOT NULL,
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (phase_id) REFERENCES event_phases (id) ON DELETE CASCADE,
    UNIQUE (phase_id, name)
);

CREATE TABLE IF NOT EXISTS event_action_types (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_defense_levels (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    enabled    INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    """Gère la connexion SQLite et toutes les opérations CRUD de l'application."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or get_default_db_path()
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
        self._migrate_schema()
        self._seed_event_config()

    def _migrate_schema(self) -> None:
        """Ajoute les colonnes manquantes sur une base déjà existante.

        SQLite ne supporte pas `ADD COLUMN IF NOT EXISTS`, donc on vérifie
        manuellement la présence des colonnes via PRAGMA table_info avant
        de les ajouter.
        """
        assert self._connection is not None

        cur = self._connection.execute("PRAGMA table_info(events)")
        existing_columns = {row["name"] for row in cur.fetchall()}

        if "action_type" not in existing_columns:
            self._connection.execute(
                "ALTER TABLE events ADD COLUMN action_type TEXT"
            )
            self._connection.commit()

        if "defense_level" not in existing_columns:
            self._connection.execute(
                "ALTER TABLE events ADD COLUMN defense_level TEXT"
            )
            self._connection.commit()

        if "prior_oreb" not in existing_columns:
            self._connection.execute(
                "ALTER TABLE events ADD COLUMN prior_oreb INTEGER"
            )
            self._connection.commit()

        if "dribbles" not in existing_columns:
            self._connection.execute(
                "ALTER TABLE events ADD COLUMN dribbles INTEGER"
            )
            self._connection.commit()

        cur = self._connection.execute("PRAGMA table_info(game_players)")
        existing_game_player_columns = {row["name"] for row in cur.fetchall()}

        if "number" not in existing_game_player_columns:
            self._connection.execute(
                "ALTER TABLE game_players ADD COLUMN number INTEGER"
            )
            self._connection.commit()

        _defense_code_to_label = {
            "OUVERT": "Ouvert",
            "PEU_DEFENDU": "Un peu défendu",
            "TRES_DEFENDU": "Très défendu",
        }
        for code, label in _defense_code_to_label.items():
            self._connection.execute(
                "UPDATE events SET defense_level = ? WHERE defense_level = ?",
                (label, code),
            )
        self._connection.commit()

        # Index (non contraignant) sur (team_id, name), pour accélérer la
        # recherche d'une joueuse par son identité (voir get_or_create_player).
        # Volontairement PAS de contrainte UNIQUE : une base déjà existante
        # peut contenir des doublons de nom hérités de l'ancien système
        # d'identification par numéro, et on ne veut pas faire planter la
        # migration pour ça.
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_players_team_name "
            "ON players (team_id, name)"
        )
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
    def get_or_create_team(
        self, name: str, color: Optional[str] = None
    ) -> int:
        """Retourne l'id de l'équipe portant ce nom, en la créant si besoin.

        Si l'équipe existe déjà et qu'une couleur est fournie, elle est mise
        à jour (permet de changer la couleur d'une équipe existante depuis
        l'écran de création de match).
        """
        cur = self.connection.execute("SELECT id FROM teams WHERE name = ?", (name,))
        row = cur.fetchone()
        if row is not None:
            if color is not None:
                self.connection.execute(
                    "UPDATE teams SET color = ? WHERE id = ?", (color, row["id"])
                )
                self.connection.commit()
            return int(row["id"])
        cur = self.connection.execute(
            "INSERT INTO teams (name, color) VALUES (?, ?)",
            (name, color or DEFAULT_TEAM_COLOR),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def get_teams(self) -> List[Team]:
        cur = self.connection.execute(
            "SELECT id, name, color FROM teams ORDER BY name"
        )
        return [
            Team(id=r["id"], name=r["name"], color=r["color"] or DEFAULT_TEAM_COLOR)
            for r in cur.fetchall()
        ]

    def get_team(self, team_id: int) -> Optional[Team]:
        cur = self.connection.execute(
            "SELECT id, name, color FROM teams WHERE id = ?", (team_id,)
        )
        r = cur.fetchone()
        if r is None:
            return None
        return Team(id=r["id"], name=r["name"], color=r["color"] or DEFAULT_TEAM_COLOR)

    def update_team(
        self, team_id: int, name: str, color: Optional[str] = None
    ) -> None:
        """Modifie le nom et/ou la couleur d'une équipe.

        `color` à None laisse la couleur actuelle inchangée.
        """
        if color is None:
            self.connection.execute(
                "UPDATE teams SET name = ? WHERE id = ?", (name, team_id)
            )
        else:
            self.connection.execute(
                "UPDATE teams SET name = ?, color = ? WHERE id = ?",
                (name, color, team_id),
            )
        self.connection.commit()

    def delete_team(self, team_id: int) -> None:
        """Supprime une équipe (et en cascade ses joueurs et ses liens aux matchs)."""
        self.connection.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        self.connection.commit()

    # ------------------------------------------------------------------
    # Joueurs
    # ------------------------------------------------------------------
    def get_or_create_player(self, team_id: int, name: str, number: int) -> int:
        """Retourne l'id du joueur (team_id, name), en le créant si besoin.

        L'identité d'une joueuse est définie par son ÉQUIPE et son NOM, et
        non plus par son numéro de maillot : le numéro peut changer d'un
        match (voire d'une saison) à l'autre, alors que le nom, lui, reste
        stable. Se baser sur le numéro exposait à un bug sérieux : créer
        une nouvelle joueuse avec le numéro d'une joueuse déjà existante
        renommait silencieusement cette dernière (même id, donc même
        historique de stats) au lieu de créer une entrée distincte.

        Si une joueuse portant ce nom existe déjà dans cette équipe, son
        numéro est mis à jour (au cas où il aurait changé) et son id est
        réutilisé, ce qui conserve tout son historique d'événements.
        Sinon, une nouvelle joueuse est créée.
        """
        cur = self.connection.execute(
            "SELECT id FROM players WHERE team_id = ? AND name = ?",
            (team_id, name),
        )
        row = cur.fetchone()
        if row is not None:
            self.connection.execute(
                "UPDATE players SET number = ? WHERE id = ?", (number, row["id"])
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
        """Modifie le nom et le numéro par défaut d'une joueuse (utilisé
        pour tout match ne définissant pas de numéro spécifique)."""

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

    def update_game(
        self, game_id: int, name: str, date: str, video_path: str
    ) -> None:
        """Modifie les informations générales d'un match déjà enregistré
        (nom, date, chemin de la vidéo)."""

        self.connection.execute(
            "UPDATE games SET name = ?, date = ?, video_path = ? WHERE id = ?",
            (name, date, video_path, game_id),
        )
        self.connection.commit()

    def get_games(self) -> List[Game]:
        cur = self.connection.execute(
            "SELECT id, name, date, video_path FROM games ORDER BY date DESC"
        )
        return [
            Game(id=r["id"], name=r["name"], date=r["date"], video_path=r["video_path"])
            for r in cur.fetchall()
        ]

    def get_games_for_team(self, team_id: int) -> List[Game]:
        """Retourne tous les matchs auxquels une équipe a participé."""
        cur = self.connection.execute(
            "SELECT g.id, g.name, g.date, g.video_path FROM games g "
            "JOIN game_teams gt ON gt.game_id = g.id "
            "WHERE gt.team_id = ? ORDER BY g.date",
            (team_id,),
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
            "SELECT t.id, t.name, t.color, gt.is_home FROM teams t "
            "JOIN game_teams gt ON gt.team_id = t.id "
            "WHERE gt.game_id = ? ORDER BY gt.is_home DESC",
            (game_id,),
        )
        return [
            (
                Team(id=r["id"], name=r["name"], color=r["color"] or DEFAULT_TEAM_COLOR),
                bool(r["is_home"]),
            )
            for r in cur.fetchall()
        ]

    def link_game_player(
        self,
        game_id: int,
        player_id: int,
        number: Optional[int] = None,
    ) -> None:
        """Associe une joueuse à un match, avec un numéro de maillot
        optionnel propre à CE match (None = numéro par défaut de l'équipe).

        Si la joueuse est déjà liée à ce match, son numéro est mis à jour.
        """
        self.connection.execute(
            "INSERT INTO game_players (game_id, player_id, number) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(game_id, player_id) DO UPDATE SET number = excluded.number",
            (game_id, player_id, number),
        )
        self.connection.commit()

    def unlink_game_player(self, game_id: int, player_id: int) -> None:
        """Retire un joueur de la liste des présents pour ce match."""
        self.connection.execute(
            "DELETE FROM game_players WHERE game_id = ? AND player_id = ?",
            (game_id, player_id),
        )
        self.connection.commit()

    def set_game_players(
        self,
        game_id: int,
        player_ids: List[int],
        numbers: Optional[Dict[int, int]] = None,
    ) -> None:
        """Remplace la liste des joueurs présents à un match par `player_ids`.

        `numbers`, optionnel, associe player_id -> numéro de maillot propre
        à CE match ; une joueuse absente de ce dict garde le numéro par
        défaut de son équipe (voir get_game_players).

        À utiliser depuis l'écran de création/édition de match, une fois que
        l'utilisateur a coché les joueuses présentes des deux équipes.
        """
        numbers = numbers or {}

        self.connection.execute(
            "DELETE FROM game_players WHERE game_id = ?", (game_id,)
        )
        self.connection.executemany(
            "INSERT INTO game_players (game_id, player_id, number) VALUES (?, ?, ?)",
            [
                (game_id, player_id, numbers.get(player_id))
                for player_id in player_ids
            ],
        )
        self.connection.commit()

    def update_game_player_number(
        self,
        game_id: int,
        player_id: int,
        number: Optional[int],
    ) -> None:
        """Modifie le numéro de maillot d'une joueuse pour CE match
        uniquement (le numéro par défaut de l'équipe n'est pas touché).
        `number` à None réinitialise sur le numéro par défaut de l'équipe.
        """
        self.connection.execute(
            "UPDATE game_players SET number = ? WHERE game_id = ? AND player_id = ?",
            (number, game_id, player_id),
        )
        self.connection.commit()

    def get_game_players(self, game_id: int, team_id: int) -> List[Player]:
        """Retourne les joueuses d'une équipe présentes à ce match, avec
        leur numéro de maillot pour CE match (numéro par défaut de
        l'équipe si aucun numéro spécifique n'a été défini pour ce match)."""
        cur = self.connection.execute(
            "SELECT p.id, p.team_id, p.name, p.number AS default_number, "
            "gp.number AS match_number "
            "FROM players p "
            "JOIN game_players gp ON gp.player_id = p.id "
            "WHERE gp.game_id = ? AND p.team_id = ? "
            "ORDER BY COALESCE(gp.number, p.number)",
            (game_id, team_id),
        )
        return [
            Player(
                id=r["id"],
                team_id=r["team_id"],
                name=r["name"],
                number=(
                    r["match_number"]
                    if r["match_number"] is not None
                    else r["default_number"]
                ),
            )
            for r in cur.fetchall()
        ]

    # ------------------------------------------------------------------
    # Configuration des événements (phases, systèmes, types d'action,
    # niveaux de défense) — voir data.event_config
    # ------------------------------------------------------------------

    def _seed_event_config(self) -> None:
        """Peuple les tables de configuration avec les valeurs
        historiques codées en dur, uniquement si elles sont vides
        (première utilisation, ou base créée avant l'ajout de cette
        fonctionnalité)."""

        from data.event_config import (
            DEFAULT_ACTION_TYPES,
            DEFAULT_DEFENSE_LEVELS,
            DEFAULT_PHASES,
        )

        cur = self.connection.execute("SELECT COUNT(*) AS n FROM event_phases")
        if cur.fetchone()["n"] > 0:
            return

        for order, (phase_name, systems) in enumerate(DEFAULT_PHASES.items()):
            cur = self.connection.execute(
                "INSERT INTO event_phases (name, sort_order) VALUES (?, ?)",
                (phase_name, order),
            )
            phase_id = cur.lastrowid
            for s_order, system_name in enumerate(systems):
                self.connection.execute(
                    "INSERT INTO event_systems (phase_id, name, sort_order) "
                    "VALUES (?, ?, ?)",
                    (phase_id, system_name, s_order),
                )

        for order, name in enumerate(DEFAULT_ACTION_TYPES):
            self.connection.execute(
                "INSERT INTO event_action_types (name, sort_order) VALUES (?, ?)",
                (name, order),
            )

        for order, name in enumerate(DEFAULT_DEFENSE_LEVELS):
            self.connection.execute(
                "INSERT INTO event_defense_levels (name, sort_order) VALUES (?, ?)",
                (name, order),
            )

        self.connection.commit()

    def get_event_config_state(self):

        from data.event_config import ConfigEntry, EventConfigState

        phases_rows = self.connection.execute(
            "SELECT id, name, enabled FROM event_phases ORDER BY sort_order, name"
        ).fetchall()
        phases = [
            ConfigEntry(id=r["id"], name=r["name"], enabled=bool(r["enabled"]))
            for r in phases_rows
        ]

        systems_by_phase = {}
        for phase in phases:
            rows = self.connection.execute(
                "SELECT id, name, enabled FROM event_systems "
                "WHERE phase_id = ? ORDER BY sort_order, name",
                (phase.id,),
            ).fetchall()
            systems_by_phase[phase.id] = [
                ConfigEntry(id=r["id"], name=r["name"], enabled=bool(r["enabled"]))
                for r in rows
            ]

        action_rows = self.connection.execute(
            "SELECT id, name, enabled FROM event_action_types ORDER BY sort_order, name"
        ).fetchall()
        action_types = [
            ConfigEntry(id=r["id"], name=r["name"], enabled=bool(r["enabled"]))
            for r in action_rows
        ]

        defense_rows = self.connection.execute(
            "SELECT id, name, enabled FROM event_defense_levels ORDER BY sort_order, name"
        ).fetchall()
        defense_levels = [
            ConfigEntry(id=r["id"], name=r["name"], enabled=bool(r["enabled"]))
            for r in defense_rows
        ]

        return EventConfigState(
            phases=phases,
            systems_by_phase=systems_by_phase,
            action_types=action_types,
            defense_levels=defense_levels,
        )

    # -- Phases --

    def add_event_phase(self, name: str) -> int:
        cur = self.connection.execute(
            "INSERT INTO event_phases (name, sort_order) VALUES (?, "
            "(SELECT COALESCE(MAX(sort_order), -1) + 1 FROM event_phases))",
            (name,),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def rename_event_phase(self, phase_id: int, name: str) -> None:
        self.connection.execute(
            "UPDATE event_phases SET name = ? WHERE id = ?", (name, phase_id)
        )
        self.connection.commit()

    def set_event_phase_enabled(self, phase_id: int, enabled: bool) -> None:
        self.connection.execute(
            "UPDATE event_phases SET enabled = ? WHERE id = ?", (int(enabled), phase_id)
        )
        self.connection.commit()

    def delete_event_phase(self, phase_id: int) -> None:
        self.connection.execute("DELETE FROM event_phases WHERE id = ?", (phase_id,))
        self.connection.commit()

    # -- Systèmes --

    def add_event_system(self, phase_id: int, name: str) -> int:
        cur = self.connection.execute(
            "INSERT INTO event_systems (phase_id, name, sort_order) VALUES (?, ?, "
            "(SELECT COALESCE(MAX(sort_order), -1) + 1 FROM event_systems "
            "WHERE phase_id = ?))",
            (phase_id, name, phase_id),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def rename_event_system(self, system_id: int, name: str) -> None:
        self.connection.execute(
            "UPDATE event_systems SET name = ? WHERE id = ?", (name, system_id)
        )
        self.connection.commit()

    def set_event_system_enabled(self, system_id: int, enabled: bool) -> None:
        self.connection.execute(
            "UPDATE event_systems SET enabled = ? WHERE id = ?", (int(enabled), system_id)
        )
        self.connection.commit()

    def delete_event_system(self, system_id: int) -> None:
        self.connection.execute("DELETE FROM event_systems WHERE id = ?", (system_id,))
        self.connection.commit()

    # -- Types d'action --

    def add_event_action_type(self, name: str) -> int:
        cur = self.connection.execute(
            "INSERT INTO event_action_types (name, sort_order) VALUES (?, "
            "(SELECT COALESCE(MAX(sort_order), -1) + 1 FROM event_action_types))",
            (name,),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def rename_event_action_type(self, entry_id: int, name: str) -> None:
        self.connection.execute(
            "UPDATE event_action_types SET name = ? WHERE id = ?", (name, entry_id)
        )
        self.connection.commit()

    def set_event_action_type_enabled(self, entry_id: int, enabled: bool) -> None:
        self.connection.execute(
            "UPDATE event_action_types SET enabled = ? WHERE id = ?",
            (int(enabled), entry_id),
        )
        self.connection.commit()

    def delete_event_action_type(self, entry_id: int) -> None:
        self.connection.execute("DELETE FROM event_action_types WHERE id = ?", (entry_id,))
        self.connection.commit()

    # -- Niveaux de défense --

    def add_event_defense_level(self, name: str) -> int:
        cur = self.connection.execute(
            "INSERT INTO event_defense_levels (name, sort_order) VALUES (?, "
            "(SELECT COALESCE(MAX(sort_order), -1) + 1 FROM event_defense_levels))",
            (name,),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def rename_event_defense_level(self, entry_id: int, name: str) -> None:
        self.connection.execute(
            "UPDATE event_defense_levels SET name = ? WHERE id = ?", (name, entry_id)
        )
        self.connection.commit()

    def set_event_defense_level_enabled(self, entry_id: int, enabled: bool) -> None:
        self.connection.execute(
            "UPDATE event_defense_levels SET enabled = ? WHERE id = ?",
            (int(enabled), entry_id),
        )
        self.connection.commit()

    def delete_event_defense_level(self, entry_id: int) -> None:
        self.connection.execute(
            "DELETE FROM event_defense_levels WHERE id = ?", (entry_id,)
        )
        self.connection.commit()

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
        action_type: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        defense_level: Optional[str] = None,
        prior_oreb: Optional[bool] = None,
        dribbles: Optional[int] = None,
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
                action_type,
                x,
                y,
                defense_level,
                prior_oreb,
                dribbles
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                player_id,
                timestamp,
                quarter,
                event_type,
                phase,
                system,
                action_type,
                x,
                y,
                defense_level,
                None if prior_oreb is None else int(prior_oreb),
                dribbles,
            ),
        )

        self.connection.commit()

        return int(cur.lastrowid)

    def delete_event(self, event_id: int) -> None:
        self.connection.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.connection.commit()

    def update_event(
        self,
        event_id: int,
        player_id: int,
        event_type: str,
        quarter: int,
        phase: Optional[str] = None,
        system: Optional[str] = None,
        action_type: Optional[str] = None,
        defense_level: Optional[str] = None,
        prior_oreb: Optional[bool] = None,
        dribbles: Optional[int] = None,
    ) -> None:
        """Corrige la joueuse, le type, le quart-temps, la phase, le système,
        le type d'action et/ou les détails de tir (défense, rebond offensif
        préalable, nombre de dribbles) d'un événement.

        Le timestamp n'est pas modifié : il reste lié
        au moment réel où l'action a été cliquée pendant l'analyse vidéo.
        """
        self.connection.execute(
            "UPDATE events SET player_id = ?, event_type = ?, quarter = ?, "
            "phase = ?, system = ?, action_type = ?, defense_level = ?, "
            "prior_oreb = ?, dribbles = ? WHERE id = ?",
            (
                player_id,
                event_type,
                quarter,
                phase,
                system,
                action_type,
                defense_level,
                None if prior_oreb is None else int(prior_oreb),
                dribbles,
                event_id,
            ),
        )
        self.connection.commit()

    def update_events_quarter(self, event_ids: List[int], quarter: int) -> None:
        """Modifie le quart-temps de plusieurs événements en une seule fois
        (édition groupée depuis le Play by play), sans toucher aux autres
        champs de ces événements."""

        self.connection.executemany(
            "UPDATE events SET quarter = ? WHERE id = ?",
            [(quarter, event_id) for event_id in event_ids],
        )
        self.connection.commit()

    def get_events_for_player(self, player_id: int) -> List[Event]:
        """Retourne tous les événements d'un joueur, tous matchs confondus
        (utilisé pour calculer des moyennes saison)."""
        cur = self.connection.execute(
            "SELECT id, game_id, player_id, timestamp, quarter, event_type, "
            "phase, system, action_type, x, y, defense_level, prior_oreb, dribbles "
            "FROM events WHERE player_id = ? ORDER BY game_id, timestamp",
            (player_id,),
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
                action_type=r["action_type"],
                x=r["x"],
                y=r["y"],
                defense_level=r["defense_level"],
                prior_oreb=None if r["prior_oreb"] is None else bool(r["prior_oreb"]),
                dribbles=r["dribbles"],
            )
            for r in cur.fetchall()
        ]

    def get_games_played_count(self, player_id: int) -> int:
        """Nombre de matchs auxquels ce joueur est associé (game_players)."""
        cur = self.connection.execute(
            "SELECT COUNT(*) AS n FROM game_players WHERE player_id = ?",
            (player_id,),
        )
        row = cur.fetchone()
        return int(row["n"]) if row else 0

    def get_events_for_game(self, game_id: int) -> List[Event]:
        cur = self.connection.execute(
            "SELECT id, game_id, player_id, timestamp, quarter, event_type, "
            "phase, system, action_type, x, y, defense_level, prior_oreb, dribbles "
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
                action_type=r["action_type"],
                x=r["x"],
                y=r["y"],
                defense_level=r["defense_level"],
                prior_oreb=None if r["prior_oreb"] is None else bool(r["prior_oreb"]),
                dribbles=r["dribbles"],
            )
            for r in cur.fetchall()
        ]

    def get_last_event_for_game(self, game_id: int) -> Optional[Event]:
        cur = self.connection.execute(
            "SELECT id, game_id, player_id, timestamp, quarter, event_type, "
            "phase, system, action_type, x, y, defense_level, prior_oreb, dribbles "
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
            action_type=r["action_type"],
            x=r["x"],
            y=r["y"],
            defense_level=r["defense_level"],
            prior_oreb=None if r["prior_oreb"] is None else bool(r["prior_oreb"]),
            dribbles=r["dribbles"],
        )

    def delete_game(self, game_id: int) -> None:
        """Supprime un match (et en cascade ses liens équipes/joueurs et ses événements)."""
        self.connection.execute("DELETE FROM games WHERE id = ?", (game_id,))
        self.connection.commit()

    def swap_home_away(self, game_id: int) -> None:
        """Inverse le statut domicile/extérieur des deux équipes d'un match."""
        self.connection.execute(
            "UPDATE game_teams SET is_home = 1 - is_home WHERE game_id = ?",
            (game_id,),
        )
        self.connection.commit()
