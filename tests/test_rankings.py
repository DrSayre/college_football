import pandas as pd
import pytest

from rankings import build_rankings, rank_conference


def record(team_id, name, wins, losses, conf_wins, conf_losses):
    return {"teamId": team_id, "team": name, "conference": "SEC", "classification": "fbs",
            "total": {"wins": wins, "losses": losses},
            "conferenceGames": {"wins": conf_wins, "losses": conf_losses}}


@pytest.fixture
def kentucky():
    records = [record(96, "Kentucky", 5, 1, 3, 1),
               record(1, "Texas A&M", 1, 1, 1, 1),
               record(2, "South Carolina", 1, 1, 1, 1),
               record(3, "LSU", 1, 1, 1, 1),
               record(4, "Alabama", 2, 1, 2, 1)]
    games, stats = [], []
    for i, (opponent, home_points, away_points, yards, allowed) in enumerate([
        (1, 24, 10, 350, 400), (2, 31, 14, 400, 450),
        (3, 20, 17, 362, 384), (4, 7, 28, 300, 400),
    ], 1):
        games.append({"id": i, "completed": True, "conferenceGame": True,
                      "homeId": 96, "awayId": opponent,
                      "homePoints": home_points, "awayPoints": away_points})
        stats.append({"id": i, "teams": [
            {"teamId": 96, "stats": [{"category": "totalYards", "stat": str(yards)}]},
            {"teamId": opponent, "stats": [{"category": "totalYards", "stat": str(allowed)}]}]})
    return records, games, stats


def team_row(data):
    return build_rankings(*data).set_index("Team").loc["Kentucky"]


def test_kentucky_example(kentucky):
    row = team_row(kentucky)
    assert [row[c] for c in ["Wins", "Losses", "Conf wins", "Conf losses",
                            "Beaten opponents’ conf wins", "Lost-to opponents’ conf losses",
                            "Conf yards", "Conf yards allowed", "Yard differential"]] == [5, 1, 3, 1, 3, 1, 1412, 1634, -222]
    assert row["Win %"] == pytest.approx(5 / 6)
    assert row["Conf %"] == .75
    assert row["Opponent results %"] == .75
    assert row["Yardage coverage"] == "4/4"
    assert row["Yard differential / game"] == -55.5


def test_missing_yards_never_become_partial_totals(kentucky):
    kentucky[2].pop()
    row = team_row(kentucky)
    assert pd.isna(row["Conf yards"])
    assert pd.isna(row["Yard differential"])
    assert pd.isna(row["Yard differential / game"])
    assert row["Opponent results %"] == .75
    assert row["Yardage coverage"] == "3/4"


def test_unfinished_and_nonconference_games_ignored(kentucky):
    kentucky[1].extend([
        {"id": 10, "completed": False, "conferenceGame": True},
        {"id": 11, "completed": True, "conferenceGame": False},
        kentucky[1][0],  # duplicate game must not inflate totals
    ])
    assert team_row(kentucky)["Conf yards"] == 1412


def test_away_team_and_missing_opponent(kentucky):
    g = kentucky[1][0]
    g["homeId"], g["awayId"] = g["awayId"], g["homeId"]
    g["homePoints"], g["awayPoints"] = g["awayPoints"], g["homePoints"]
    assert team_row(kentucky)["Opponent results %"] == .75
    kentucky[0].pop(1)
    assert pd.isna(team_row(kentucky)["Opponent results %"])


def test_no_conference_games():
    frame = build_rankings([record(96, "Kentucky", 1, 0, 0, 0)], [], [])
    row = frame.iloc[0]
    assert pd.isna(row["Conf %"])
    assert pd.isna(row["Opponent results %"])
    assert row["Conf yards"] == 0
    assert pd.isna(row["Yard differential / game"])
    assert row["Complete"]


def test_missing_game_makes_derived_metrics_unavailable(kentucky):
    kentucky[1].pop()
    row = team_row(kentucky)
    assert pd.isna(row["Opponent results %"])
    assert pd.isna(row["Conf yards"])
    assert not row["Complete"]


def test_rank_sort_and_ties_are_deterministic():
    frame = pd.DataFrame([
        {"Team": name, "Conf %": conf, "Opponent results %": opp,
         "Yard differential": yards, "Win %": .8}
        for name, conf, opp, yards in [("B", .75, .5, 10), ("A", .75, .5, 10),
                                      ("C", .75, .6, -10), ("D", None, None, 0)]])
    ranked = rank_conference(frame)
    assert ranked["Team"].tolist() == ["C", "A", "B", "D"]
    assert ranked["Rank"].tolist() == [1, 2, 3, 4]
