"""Pull completed MLB games from the MLB Stats API.

The dataset builder starts on 2023-03-30 and then asks prop-odds.com for
run-line prices. This script does not call that API. It keeps the same
start date and stops on 2026-11-07, and it writes only final games.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import statsapi

START = "2023-03-30"
THROUGH = "2026-11-07"
COMPLETED = {"Final", "Game Over", "Completed Early"}
GAME_TYPES = {"R", "F", "D", "L", "W"}
OUT = Path(__file__).resolve().parent / "completed_games.csv"


def month_windows(start: str, end: str):
    cursor = datetime.strptime(start, "%Y-%m-%d").date()
    last = datetime.strptime(end, "%Y-%m-%d").date()
    while cursor <= last:
        if cursor.month == 12:
            nxt = cursor.replace(year=cursor.year + 1, month=1, day=1)
        else:
            nxt = cursor.replace(month=cursor.month + 1, day=1)
        chunk_end = min(last, nxt - timedelta(days=1))
        yield cursor.isoformat(), chunk_end.isoformat()
        cursor = chunk_end + timedelta(days=1)


def fetch_range(start: str, end: str, depth: int = 0) -> list:
    try:
        games = statsapi.schedule(start_date=start, end_date=end, sportId=1)
        time.sleep(0.25)
        return games
    except requests.HTTPError as exc:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        end_d = datetime.strptime(end, "%Y-%m-%d").date()
        if depth >= 6 or start_d >= end_d:
            raise
        mid = start_d + (end_d - start_d) // 2
        print(f"split {start}..{end} after HTTP {exc.response.status_code}")
        time.sleep(1.0)
        left = fetch_range(start, mid.isoformat(), depth + 1)
        right = fetch_range((mid + timedelta(days=1)).isoformat(), end, depth + 1)
        return left + right


def main() -> None:
    games = []
    for chunk_start, chunk_end in month_windows(START, THROUGH):
        print(f"fetch {chunk_start} {chunk_end}")
        games.extend(fetch_range(chunk_start, chunk_end))

    rows = []
    seen = set()
    for game in games:
        game_id = game.get("game_id")
        if game_id in seen:
            continue
        if game.get("game_date", "") > THROUGH:
            continue
        if game.get("status") not in COMPLETED:
            continue
        if game.get("game_type") not in GAME_TYPES:
            continue
        if game.get("away_score") is None or game.get("home_score") is None:
            continue
        seen.add(game_id)
        away_score = int(game["away_score"])
        home_score = int(game["home_score"])
        rows.append(
            {
                "game_id": game_id,
                "date": game["game_date"],
                "away": game.get("away_name", ""),
                "home": game.get("home_name", ""),
                "away_score": away_score,
                "home_score": home_score,
                "home_cover": int(home_score - away_score > 1.5),
                "status": game["status"],
                "game_type": game["game_type"],
            }
        )

    frame = pd.DataFrame(rows).sort_values(["date", "game_id"])
    frame.to_csv(OUT, index=False)
    data_min = frame["date"].min()
    data_max = frame["date"].max()
    notes = Path(__file__).resolve().parent / "NOTES.md"
    notes.write_text(
        "This repo predicts whether an MLB team covers the run line, not who wins the game.\n\n"
        "Completed games were pulled from the MLB Stats API. A home cover is labeled when "
        "home score minus away score is greater than 1.5.\n\n"
        f"Minimum date: {data_min}\n"
        f"Maximum date: {data_max}\n"
        f"Row count: {len(frame)}\n\n"
        "mlb_game_predictor features and predictions were not copied.\n",
        encoding="utf-8",
    )
    print(f"min date {data_min}")
    print(f"max date {data_max}")
    print(f"rows {len(frame)}")
    print(f"home_cover {int(frame['home_cover'].sum())}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        notes = Path(__file__).resolve().parent / "NOTES.md"
        notes.write_text(
            "This repo predicts whether an MLB team covers the run line, not who wins the game.\n\n"
            "The MLB Stats API pull failed on 2026-11-07:\n"
            f"{type(exc).__name__}: {exc}\n"
            "mlb_game_predictor features and predictions were not copied. This branch was not pushed.\n",
            encoding="utf-8",
        )
        print(f"FAIL {type(exc).__name__}: {exc}")
        raise SystemExit(1)
