from collections import defaultdict

from data.database import Database


def player_summary(db: Database, game_id: int) -> dict[int, dict]:
    """Construit un dict {player_id: {name, number, counts: {event_type: n}, pct_2pts, pct_3pts}}
    à partir des lignes brutes renvoyées par la BDD."""
    rows = db.get_player_stats(game_id)

    summary: dict[int, dict] = {}
    for r in rows:
        pid = r["player_id"]
        if pid not in summary:
            summary[pid] = {
                "name": r["name"],
                "number": r["number"],
                "counts": defaultdict(int),
            }
        summary[pid]["counts"][r["event_type"]] = r["count"]

    for pid, data in summary.items():
        c = data["counts"]
        made2, miss2 = c.get("2PTS_MADE", 0), c.get("2PTS_MISS", 0)
        made3, miss3 = c.get("3PTS_MADE", 0), c.get("3PTS_MISS", 0)

        data["pct_2pts"] = _pct(made2, made2 + miss2)
        data["pct_3pts"] = _pct(made3, made3 + miss3)
        data["points"] = made2 * 2 + made3 * 3
        data["rebonds"] = c.get("REBOND_OFF", 0) + c.get("REBOND_DEF", 0)

    return summary


def _pct(made: int, total: int) -> float:
    return round(100 * made / total, 1) if total else 0.0
