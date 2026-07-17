import sqlite3
con = sqlite3.connect("basketball_stats.db")
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT event_type, phase, system, x, y FROM events "
    "WHERE event_type LIKE '2PTS_%' OR event_type LIKE '3PTS_%' "
    "ORDER BY id DESC LIMIT 5"
).fetchall()
for r in rows:
    print(dict(r))
