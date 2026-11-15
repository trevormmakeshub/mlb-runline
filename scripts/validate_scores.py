"""Check the completed-game file. This does not download."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "completed_games.csv"


def main() -> int:
    with PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    dates = [row["date"] for row in rows]
    ids = [row["game_id"] for row in rows]
    problems = 0
    if len(ids) != len(set(ids)):
        print("fail duplicate game_id")
        problems += 1
    if max(dates) > date.today().isoformat():
        print("fail future date")
        problems += 1
    bad = 0
    for row in rows:
        margin = int(row["home_score"]) - int(row["away_score"])
        expected = "1" if margin > 1.5 else "0"
        if row["home_cover"] != expected:
            bad += 1
    if bad:
        print(f"fail {bad} home_cover labels")
        problems += 1
    print(f"rows {len(rows)} min {min(dates)} max {max(dates)}")
    if problems:
        return 1
    print("validation pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
