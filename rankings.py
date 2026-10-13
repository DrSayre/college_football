"""Conference rankings from CFBD records, completed games and per-game yards."""
from collections import defaultdict

import pandas as pd


def percentage(wins, losses, ties=0):
    played = wins + losses + ties
    return (wins + ties / 2) / played if played else None


def total_yards(team):
    for stat in team.get("stats", []):
        if stat.get("category") == "totalYards":
            try:
                value = int(str(stat["stat"]).replace(",", ""))
                return value if value >= 0 else None
            except (ValueError, TypeError, KeyError):
                return None
    return None


def build_rankings(records, games, statistics):
    """Use season records for W/L and opponents' current conference records.

    Only completed conference games contribute to opponent results and yards.
    Missing yards never become zero or misleading partial season totals.
    """
    records_by_id = {r["teamId"]: r for r in records}
    stats_by_id = {g["id"]: g for g in statistics}
    conference_games = defaultdict(list)
    seen = set()
    for game in games:
        if game["id"] in seen:
            continue
        seen.add(game["id"])
        if not game.get("completed") or not game.get("conferenceGame"):
            continue
        conference_games[game["homeId"]].append((game, game["awayId"], True))
        conference_games[game["awayId"]].append((game, game["homeId"], False))

    rows = []
    for team_id, record in records_by_id.items():
        overall = record["total"]
        conf = record["conferenceGames"]
        beaten_wins = lost_to_losses = yards_for = yards_against = coverage = 0
        opponents_complete = True
        team_games = conference_games[team_id]
        for game, opponent_id, home in team_games:
            own_score = game.get("homePoints" if home else "awayPoints")
            other_score = game.get("awayPoints" if home else "homePoints")
            opponent = records_by_id.get(opponent_id)
            if own_score is None or other_score is None or opponent is None:
                opponents_complete = False
            elif own_score > other_score:
                beaten_wins += opponent["conferenceGames"]["wins"]
            elif own_score < other_score:
                lost_to_losses += opponent["conferenceGames"]["losses"]
            stats = stats_by_id.get(game["id"], {})
            by_team = {t["teamId"]: t for t in stats.get("teams", [])}
            own_yards = total_yards(by_team.get(team_id, {}))
            other_yards = total_yards(by_team.get(opponent_id, {}))
            if own_yards is not None and other_yards is not None:
                coverage += 1
                yards_for += own_yards
                yards_against += other_yards

        expected = conf["wins"] + conf["losses"] + conf.get("ties", 0)
        games_complete = len(team_games) == expected
        yards_complete = games_complete and coverage == expected
        opponents_complete = opponents_complete and games_complete
        rows.append({
            "Team": record["team"],
            "Conference": record.get("conference") or "Independent",
            "Classification": record.get("classification") or "unknown",
            "Wins": overall["wins"], "Losses": overall["losses"],
            "Win %": percentage(overall["wins"], overall["losses"], overall.get("ties", 0)),
            "Conf wins": conf["wins"], "Conf losses": conf["losses"],
            "Conf %": percentage(conf["wins"], conf["losses"], conf.get("ties", 0)),
            "Beaten opponents’ conf wins": beaten_wins if opponents_complete else None,
            "Lost-to opponents’ conf losses": lost_to_losses if opponents_complete else None,
            "Opponent results %": percentage(beaten_wins, lost_to_losses) if opponents_complete else None,
            "Conf yards": yards_for if yards_complete else None,
            "Conf yards allowed": yards_against if yards_complete else None,
            "Yard differential": yards_for - yards_against if yards_complete else None,
            "Yardage coverage": f"{coverage}/{expected}",
            "Complete": games_complete and yards_complete and opponents_complete,
        })
    return pd.DataFrame(rows)


def rank_conference(frame, primary="Conf %"):
    keys = list(dict.fromkeys([primary, "Conf %", "Opponent results %", "Yard differential", "Win %"]))
    ranked = frame.sort_values(keys + ["Team"], ascending=[False] * len(keys) + [True], na_position="last").copy()
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked
