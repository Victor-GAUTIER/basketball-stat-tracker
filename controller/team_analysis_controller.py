"""Agrégation des statistiques d'une équipe sur l'ensemble de ses matchs.

Reproduit en Python les calculs faits dans le notebook R d'analyse
(points par action, TOV%, Four Factors, rebonds offensifs, etc.), afin
d'alimenter le tableau de bord PySide6 (voir
ui/analysis/team_analysis_window.py).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data.database import Database
from data.models import Event, Game, Player


SHOT_TYPES = ("2PTS_MADE", "2PTS_MISSED", "3PTS_MADE", "3PTS_MISSED")
FT_TYPES = ("FT_MADE", "FT_MISSED")

POINTS_BY_EVENT = {
    "FT_MADE": 1,
    "2PTS_MADE": 2,
    "3PTS_MADE": 3,
}


def _points(event_type: str) -> int:
    return POINTS_BY_EVENT.get(event_type, 0)


def _is_turnover(event_type: str) -> bool:
    return event_type == "TURNOVER" or event_type.startswith("TO_")


def _is_foul(event_type: str) -> bool:
    return "FOUL" in event_type


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# =====================================================
# Dataclasses
# =====================================================

@dataclass
class TeamBoxScore:
    """Statistiques agrégées d'une équipe (ou d'un joueur) sur un ou
    plusieurs matchs."""

    points: int = 0
    fgm: int = 0        # tirs 2pts+3pts réussis
    fga: int = 0        # tirs 2pts+3pts tentés
    fga2: int = 0
    fga3: int = 0
    p3m: int = 0         # 3pts réussis
    fta: int = 0
    ftm: int = 0
    oreb: int = 0
    dreb: int = 0
    tov: int = 0
    fouls: int = 0

    @property
    def fgm2(self) -> int:
        return self.fgm - self.p3m

    @property
    def reb(self) -> int:
        return self.oreb + self.dreb

    @property
    def efg_pct(self) -> float:
        if self.fga == 0:
            return 0.0
        return (self.fgm + 0.5 * self.p3m) / self.fga * 100

    @property
    def two_pt_pct(self) -> float:
        return (self.fgm2 / self.fga2 * 100) if self.fga2 else 0.0

    @property
    def three_pt_pct(self) -> float:
        return (self.p3m / self.fga3 * 100) if self.fga3 else 0.0

    @property
    def ft_pct(self) -> float:
        return (self.ftm / self.fta * 100) if self.fta else 0.0

    @property
    def tov_pct(self) -> float:
        denom = self.fga + 0.44 * self.fta + self.tov
        if denom == 0:
            return 0.0
        return self.tov / denom * 100

    @property
    def ft_rate(self) -> float:
        if self.fga == 0:
            return 0.0
        return self.fta / self.fga * 100

    @property
    def possessions(self) -> float:
        return self.fga + 0.44 * self.fta + self.tov

    @property
    def points_per_shot(self) -> float:
        return (self.points / self.fga) if self.fga else 0.0

    @property
    def points_per_possession(self) -> float:
        poss = self.possessions
        return (self.points / poss) if poss else 0.0

    def oreb_pct(self, opponent_dreb: int) -> float:
        denom = self.oreb + opponent_dreb
        return (self.oreb / denom * 100) if denom else 0.0

    def dreb_pct(self, opponent_oreb: int) -> float:
        denom = self.dreb + opponent_oreb
        return (self.dreb / denom * 100) if denom else 0.0

    def reb_pct(self, opponent_box: "TeamBoxScore") -> float:
        denom = self.reb + opponent_box.reb
        return (self.reb / denom * 100) if denom else 0.0


def sum_boxes(boxes: List[TeamBoxScore]) -> TeamBoxScore:
    total = TeamBoxScore()
    for b in boxes:
        total.points += b.points
        total.fgm += b.fgm
        total.fga += b.fga
        total.fga2 += b.fga2
        total.fga3 += b.fga3
        total.p3m += b.p3m
        total.fta += b.fta
        total.ftm += b.ftm
        total.oreb += b.oreb
        total.dreb += b.dreb
        total.tov += b.tov
        total.fouls += b.fouls
    return total


def _apply_event_to_box(box: TeamBoxScore, event: Event, points: int) -> None:

    box.points += points

    if event.event_type in SHOT_TYPES:
        box.fga += 1
        if event.event_type.startswith("3PTS"):
            box.fga3 += 1
        else:
            box.fga2 += 1
        if event.event_type.endswith("_MADE"):
            box.fgm += 1
            if event.event_type.startswith("3PTS"):
                box.p3m += 1

    if event.event_type in FT_TYPES:
        box.fta += 1
        if event.event_type == "FT_MADE":
            box.ftm += 1

    if event.event_type == "OFF_REBOUND":
        box.oreb += 1

    if event.event_type == "DEF_REBOUND":
        box.dreb += 1

    if _is_turnover(event.event_type):
        box.tov += 1

    if _is_foul(event.event_type):
        box.fouls += 1


@dataclass
class Shot:
    """Un tir individuel, avec assez de contexte pour être filtré."""

    x: float
    y: float
    made: bool
    is_3pt: bool
    player_id: int
    team_id: int
    team_name: str
    game_id: int
    quarter: int


@dataclass
class GameDashboard:
    """Données agrégées pour un seul match de l'équipe analysée."""

    game: Game
    opponent_name: str
    team_box: TeamBoxScore
    opponent_box: TeamBoxScore
    result: str = "N"  # "V", "D" ou "N" (nul)

    # (index de l'événement dans le match, score cumulé équipe, score cumulé adversaire)
    score_evolution: List[Tuple[int, int, int]] = field(default_factory=list)

    points_by_action: Dict[str, int] = field(default_factory=dict)
    points_conceded_by_action: Dict[str, int] = field(default_factory=dict)
    fga_by_action: Dict[str, int] = field(default_factory=dict)

    diff_by_quarter: Dict[int, int] = field(default_factory=dict)

    player_boxes: Dict[int, TeamBoxScore] = field(default_factory=dict)
    player_points_by_action: Dict[int, Dict[str, int]] = field(default_factory=dict)
    player_fga_by_action: Dict[int, Dict[str, int]] = field(default_factory=dict)
    player_turnovers: Dict[int, Dict[str, int]] = field(default_factory=dict)


@dataclass
class TeamDashboard:
    """Données agrégées sur l'ensemble des matchs d'une équipe."""

    team_name: str
    team_id: int = -1
    games: List[GameDashboard] = field(default_factory=list)

    points_by_action: Dict[str, int] = field(default_factory=dict)
    points_conceded_by_action: Dict[str, int] = field(default_factory=dict)
    points_per_possession: Dict[str, float] = field(default_factory=dict)
    points_per_shot_by_action: Dict[str, float] = field(default_factory=dict)

    turnover_breakdown: Dict[str, int] = field(default_factory=dict)

    shots: List[Shot] = field(default_factory=list)

    reb_off_pct_team: float = 0.0
    reb_off_pct_opp: float = 0.0

    team_totals: TeamBoxScore = field(default_factory=TeamBoxScore)
    opponent_totals: TeamBoxScore = field(default_factory=TeamBoxScore)

    wins: int = 0
    losses: int = 0

    avg_possessions: float = 0.0
    avg_points_per_shot: float = 0.0
    avg_points_per_possession: float = 0.0

    diff_by_quarter: Dict[int, float] = field(default_factory=dict)

    teams_faced: List[Tuple[int, str]] = field(default_factory=list)
    players: List[Player] = field(default_factory=list)

    @property
    def record(self) -> str:
        return f"{self.wins}-{self.losses}"


# =====================================================
# Calcul principal
# =====================================================

def compute_team_dashboard(database: Database, team_id: int) -> TeamDashboard:
    """Calcule toutes les statistiques agrégées d'une équipe, tous matchs confondus."""

    teams = {t.id: t for t in database.get_teams()}
    team = teams.get(team_id)
    team_name = team.name if team else "Équipe inconnue"

    dashboard = TeamDashboard(team_name=team_name, team_id=team_id)

    games = database.get_games_for_team(team_id)

    player_cache: Dict[int, Optional[Player]] = {}

    def get_player(player_id: int) -> Optional[Player]:
        if player_id not in player_cache:
            player_cache[player_id] = database.get_player(player_id)
        return player_cache[player_id]

    points_by_action: Dict[str, int] = defaultdict(int)
    points_conceded_by_action: Dict[str, int] = defaultdict(int)
    fga_by_action: Dict[str, int] = defaultdict(int)
    tov_by_action: Dict[str, int] = defaultdict(int)
    fta_by_action: Dict[str, int] = defaultdict(int)
    oreb_by_action: Dict[str, int] = defaultdict(int)

    turnover_breakdown: Dict[str, int] = defaultdict(int)

    shots: List[Shot] = []
    teams_faced_set = {(team_id, team_name)}

    total_team_oreb = 0
    total_team_dreb = 0
    total_opp_oreb = 0
    total_opp_dreb = 0

    for game in games:

        events = database.get_events_for_game(game.id)
        game_teams = database.get_game_teams(game.id)

        opponent_team = next(
            (t for t, _is_home in game_teams if t.id != team_id),
            None
        )
        opponent_name = opponent_team.name if opponent_team else "Adversaire"

        if opponent_team is not None:
            teams_faced_set.add((opponent_team.id, opponent_team.name))

        team_box = TeamBoxScore()
        opponent_box = TeamBoxScore()

        score_evolution: List[Tuple[int, int, int]] = []
        team_cum = 0
        opp_cum = 0

        game_points_by_action: Dict[str, int] = defaultdict(int)
        game_points_conceded_by_action: Dict[str, int] = defaultdict(int)
        game_fga_by_action: Dict[str, int] = defaultdict(int)
        game_player_boxes: Dict[int, TeamBoxScore] = {}
        game_player_points_by_action: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        game_player_fga_by_action: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        game_player_turnovers: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        quarter_points_team: Dict[int, int] = defaultdict(int)
        quarter_points_opp: Dict[int, int] = defaultdict(int)

        for index, event in enumerate(events, start=1):

            player = get_player(event.player_id)
            is_team_event = player is not None and player.team_id == team_id

            box = team_box if is_team_event else opponent_box
            pts = _points(event.event_type)

            _apply_event_to_box(box, event, pts)

            team_cum += pts if is_team_event else 0
            opp_cum += pts if not is_team_event else 0
            score_evolution.append((index, team_cum, opp_cum))

            if is_team_event:
                quarter_points_team[event.quarter] += pts
            else:
                quarter_points_opp[event.quarter] += pts

            action = event.action_type or "Non renseigné"

            if is_team_event:

                p_box = game_player_boxes.setdefault(player.id, TeamBoxScore())
                _apply_event_to_box(p_box, event, pts)

                if pts > 0:
                    points_by_action[action] += pts
                    game_points_by_action[action] += pts
                    game_player_points_by_action[player.id][action] += pts

                if event.event_type in SHOT_TYPES:
                    fga_by_action[action] += 1
                    game_fga_by_action[action] += 1
                    game_player_fga_by_action[player.id][action] += 1

                if _is_turnover(event.event_type):
                    tov_by_action[action] += 1
                    to_label = (
                        event.event_type.replace("TO_", "")
                        if event.event_type.startswith("TO_")
                        else "AUTRE"
                    )
                    turnover_breakdown[to_label] += 1
                    game_player_turnovers[player.id][to_label] += 1

                if event.event_type in FT_TYPES:
                    fta_by_action[action] += 1

                if event.event_type == "OFF_REBOUND":
                    oreb_by_action[action] += 1

                if (
                    event.event_type in SHOT_TYPES
                    and event.x is not None
                    and event.y is not None
                ):
                    shots.append(Shot(
                        x=event.x,
                        y=event.y,
                        made=event.event_type.endswith("_MADE"),
                        is_3pt=event.event_type.startswith("3PTS"),
                        player_id=player.id,
                        team_id=team_id,
                        team_name=team_name,
                        game_id=game.id,
                        quarter=event.quarter,
                    ))

            else:

                if pts > 0:
                    points_conceded_by_action[action] += pts
                    game_points_conceded_by_action[action] += pts

                if (
                    event.event_type in SHOT_TYPES
                    and event.x is not None
                    and event.y is not None
                    and opponent_team is not None
                ):
                    shots.append(Shot(
                        x=event.x,
                        y=event.y,
                        made=event.event_type.endswith("_MADE"),
                        is_3pt=event.event_type.startswith("3PTS"),
                        player_id=event.player_id,
                        team_id=opponent_team.id,
                        team_name=opponent_team.name,
                        game_id=game.id,
                        quarter=event.quarter,
                    ))

        result = (
            "V" if team_box.points > opponent_box.points
            else "D" if team_box.points < opponent_box.points
            else "N"
        )

        game_diff_by_quarter = {
            q: quarter_points_team.get(q, 0) - quarter_points_opp.get(q, 0)
            for q in sorted(set(quarter_points_team) | set(quarter_points_opp))
        }

        dashboard.games.append(GameDashboard(
            game=game,
            opponent_name=opponent_name,
            team_box=team_box,
            opponent_box=opponent_box,
            result=result,
            score_evolution=score_evolution,
            points_by_action=dict(game_points_by_action),
            points_conceded_by_action=dict(game_points_conceded_by_action),
            fga_by_action=dict(game_fga_by_action),
            diff_by_quarter=game_diff_by_quarter,
            player_boxes=game_player_boxes,
            player_points_by_action={
                pid: dict(d) for pid, d in game_player_points_by_action.items()
            },
            player_fga_by_action={
                pid: dict(d) for pid, d in game_player_fga_by_action.items()
            },
            player_turnovers={
                pid: dict(d) for pid, d in game_player_turnovers.items()
            },
        ))

        total_team_oreb += team_box.oreb
        total_team_dreb += team_box.dreb
        total_opp_oreb += opponent_box.oreb
        total_opp_dreb += opponent_box.dreb

    points_per_possession: Dict[str, float] = {}
    points_per_shot_by_action: Dict[str, float] = {}

    for action, pts in points_by_action.items():
        possessions = (
            fga_by_action.get(action, 0)
            + tov_by_action.get(action, 0)
            + 0.44 * fta_by_action.get(action, 0)
            + oreb_by_action.get(action, 0)
        )
        points_per_possession[action] = (pts / possessions) if possessions > 0 else 0.0

        fga_only = fga_by_action.get(action, 0)
        points_per_shot_by_action[action] = (pts / fga_only) if fga_only > 0 else 0.0

    dashboard.points_by_action = dict(points_by_action)
    dashboard.points_conceded_by_action = dict(points_conceded_by_action)
    dashboard.points_per_possession = points_per_possession
    dashboard.points_per_shot_by_action = points_per_shot_by_action
    dashboard.turnover_breakdown = dict(turnover_breakdown)
    dashboard.shots = shots

    dashboard.reb_off_pct_team = (
        total_team_oreb / (total_team_oreb + total_opp_dreb) * 100
        if (total_team_oreb + total_opp_dreb) > 0 else 0.0
    )
    dashboard.reb_off_pct_opp = (
        total_opp_oreb / (total_opp_oreb + total_team_dreb) * 100
        if (total_opp_oreb + total_team_dreb) > 0 else 0.0
    )

    dashboard.team_totals = sum_boxes([g.team_box for g in dashboard.games])
    dashboard.opponent_totals = sum_boxes([g.opponent_box for g in dashboard.games])

    dashboard.wins = sum(1 for g in dashboard.games if g.result == "V")
    dashboard.losses = sum(1 for g in dashboard.games if g.result == "D")

    dashboard.avg_possessions = _avg([g.team_box.possessions for g in dashboard.games])
    dashboard.avg_points_per_shot = _avg([g.team_box.points_per_shot for g in dashboard.games])
    dashboard.avg_points_per_possession = _avg(
        [g.team_box.points_per_possession for g in dashboard.games]
    )

    quarter_diffs: Dict[int, List[int]] = defaultdict(list)
    for g in dashboard.games:
        for q, diff in g.diff_by_quarter.items():
            quarter_diffs[q].append(diff)
    dashboard.diff_by_quarter = {q: _avg(v) for q, v in quarter_diffs.items()}

    dashboard.teams_faced = sorted(teams_faced_set, key=lambda t: t[1])
    dashboard.players = database.get_players_by_team(team_id)

    return dashboard


# =====================================================
# Fonctions de filtrage/agrégation (utilisées par la fenêtre PySide6)
# =====================================================

def aggregate_boxes(
    games: List[GameDashboard],
    game_ids: Optional[List[int]] = None,
) -> Tuple[TeamBoxScore, TeamBoxScore]:
    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]
    return (
        sum_boxes([g.team_box for g in selected]),
        sum_boxes([g.opponent_box for g in selected]),
    )


def aggregate_player_box(
    games: List[GameDashboard],
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
) -> TeamBoxScore:
    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]
    boxes = [
        box for g in selected for pid, box in g.player_boxes.items()
        if player_ids is None or pid in player_ids
    ]
    return sum_boxes(boxes)


def filter_shots(
    shots: List[Shot],
    team_ids: Optional[List[int]] = None,
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
) -> List[Shot]:
    return [
        s for s in shots
        if (team_ids is None or s.team_id in team_ids)
        and (player_ids is None or s.player_id in player_ids)
        and (game_ids is None or s.game_id in game_ids)
    ]


def aggregate_turnover_breakdown(
    games: List[GameDashboard],
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
) -> Dict[str, int]:
    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]
    result: Dict[str, int] = defaultdict(int)
    for g in selected:
        for pid, breakdown in g.player_turnovers.items():
            if player_ids is not None and pid not in player_ids:
                continue
            for label, count in breakdown.items():
                result[label] += count
    return dict(result)


def aggregate_points_by_action(
    games: List[GameDashboard],
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
    conceded: bool = False,
) -> Dict[str, int]:
    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]
    result: Dict[str, int] = defaultdict(int)
    for g in selected:
        if conceded:
            for action, pts in g.points_conceded_by_action.items():
                result[action] += pts
        elif player_ids is None:
            for action, pts in g.points_by_action.items():
                result[action] += pts
        else:
            for pid, actions in g.player_points_by_action.items():
                if pid not in player_ids:
                    continue
                for action, pts in actions.items():
                    result[action] += pts
    return dict(result)


def aggregate_fga_by_action(
    games: List[GameDashboard],
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
) -> Dict[str, int]:
    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]
    result: Dict[str, int] = defaultdict(int)
    for g in selected:
        if player_ids is None:
            for action, n in g.fga_by_action.items():
                result[action] += n
        else:
            for pid, actions in g.player_fga_by_action.items():
                if pid not in player_ids:
                    continue
                for action, n in actions.items():
                    result[action] += n
    return dict(result)


def win_pct_by_shooting_comparison(
    games: List[GameDashboard],
    game_ids: Optional[List[int]] = None,
) -> Tuple[Optional[float], Optional[float], int, int]:
    """Retourne (win% quand eFG% > adversaire, win% quand eFG% < adversaire,
    nb de matchs dans chaque cas)."""

    selected = games if game_ids is None else [g for g in games if g.game.id in game_ids]

    better = [g for g in selected if g.team_box.efg_pct > g.opponent_box.efg_pct]
    worse = [g for g in selected if g.team_box.efg_pct < g.opponent_box.efg_pct]

    def _win_pct(subset: List[GameDashboard]) -> Optional[float]:
        if not subset:
            return None
        wins = sum(1 for g in subset if g.result == "V")
        return wins / len(subset) * 100

    return _win_pct(better), _win_pct(worse), len(better), len(worse)
