# College football conference rankings

A Streamlit app using [College Football Data](https://collegefootballdata.com), defaulting to the 2026 season. View all conferences, choose FBS/FCS/all divisions, search teams, change the ranking metric, and export CSV.

## Run

Python 3.12 is supported. In the prepared cloud environment:

```sh
cd /workspace/college_football
source /workspace/venvs/college-football/bin/activate
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

For another machine, create a virtual environment and run `python -m pip install -r requirements-dev.txt`. Supply `CFBD_API_KEY` securely as an environment secret. In the cloud, allow its HTTPS destination `api.collegefootballdata.com`. Never commit API keys or paste them into source code. No database or Ruby runtime is required.

## Metrics

- Overall and conference wins, losses, and win percentages come from `/records`.
- **Beaten opponents’ conf wins (A):** sum of current conference wins of each conference opponent defeated.
- **Lost-to opponents’ conf losses (B):** sum of current conference losses of each conference opponent that beat the team.
- **Opponent results %:** A / (A + B). A zero denominator is unavailable.
- Conference yards gained and allowed use per-game `totalYards` from `/games/teams`, joined to completed conference games from `/games`. Yard differential is gained minus allowed.
- **Yard differential / game:** conference yard differential divided by completed conference games. Kentucky’s −222 across four games is −55.5. Missing yardage or zero conference games produces an unavailable value.

Only completed conference games count toward the custom opponent and yardage metrics. Every matchup counts; repeated opponents count for each matchup. Opponents’ records update throughout the season. Ties count as half a win for record percentages and contribute neither A nor B.

Missing game data or yardage is unavailable, not zero: totals are blank until coverage matches the recorded conference game count. Coverage shows games with both teams' yardage / expected conference games. Zero completed conference games yields zero yards and an unavailable conference percentage.

Default table order: conference win %, opponent results %, yard differential, overall win %, then team name. The selected primary metric moves to the front of that ordering. Ranks are sequential table positions; they are not official standings and do not encode conference tiebreaker rules.

Requests are cached in memory for 15 minutes. Initial loading makes a records request, regular/postseason game requests, and one stats request per completed conference-game week/season type. API limits and endpoint permissions depend on your account. Refresh uses additional requests. API failures show an actionable message without exposing your credential.

## Verify

```sh
python -m pytest -q
```

The synthetic Kentucky fixture checks the requested example: 5, 1, .833, 3, 1, .750, 3, 1, .750, 1412, 1634, -222. It is an illustrative calculation test, not a hardcoded live ranking.
