from datetime import datetime, timezone

import streamlit as st

from cfbd import DataError, load_season
from rankings import build_rankings, rank_conference

st.set_page_config(page_title="Conference Rankings", page_icon="🏈", layout="wide")
st.title("College football conference rankings")
st.caption("Season records, opponent results, and conference yardage · College Football Data")


@st.cache_data(ttl=900, show_spinner=False)
def season_data(year):
    records, games, stats = load_season(year)
    return build_rankings(records, games, stats), datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


with st.sidebar:
    st.header("Season & rankings")
    year = st.number_input("Season", min_value=2000, max_value=2100, value=2026, step=1)
    level = st.selectbox("Division", ["FBS", "FCS", "All divisions"])
    primary = st.selectbox("Rank first by", ["Conf %", "Opponent results %", "Yard differential", "Yard differential / game", "Win %", "Conf wins"])
    if st.button("Refresh API data", width="stretch"):
        season_data.clear()
    st.caption("Data is cached for 15 minutes. Refreshing uses your API request allowance.")

try:
    with st.spinner(f"Loading {year} records and conference game statistics…"):
        frame, fetched_at = season_data(int(year))
except DataError as error:
    st.error(str(error))
    st.stop()

if frame.empty:
    st.info(f"No season records are available for {year} yet.")
    st.stop()
if level != "All divisions":
    frame = frame[frame["Classification"].str.lower() == level.lower()]
if frame.empty:
    st.info("No teams are available for this division and season.")
    st.stop()

conferences = sorted(frame["Conference"].unique())
division_frame = frame.copy()
selected = st.sidebar.multiselect("Conferences", conferences, default=conferences)
frame = frame[frame["Conference"].isin(selected)]
search = st.sidebar.text_input("Find a team", placeholder="Kentucky")
st.caption(f"{year} season · Last fetched {fetched_at}")
a, b, c = st.columns(3)
a.metric("Conferences", len(selected))
b.metric("Teams", len(frame))
c.metric("Teams with complete conference data", f"{int(frame['Complete'].sum())} / {len(frame)}")

with st.expander("How the rankings work"):
    st.markdown("""
**Opponent results %** = defeated conference opponents’ conference wins ÷
(those wins + conference losses of opponents that beat your team).
Opponent records reflect the selected season so far. Each matchup counts once;
repeat opponents count for each matchup. A zero denominator is shown as unavailable.

Conference yards include only completed conference games. Yards allowed are the
opponent’s total yards in those games. Differential = yards gained − yards allowed.
Differential per game = differential ÷ completed conference games.
For FBS independents (Notre Dame and UConn), all conference-style columns use
completed games against the Big Ten, SEC, ACC, and Big 12 instead. Opponent wins
and losses still use those opponents’ actual conference records. These matchups
do not count as conference games for the Power Four opponent.
Missing statistics show blank totals, with coverage indicating how many games have
both teams’ yardage. Teams with no conference games have zero yards and no conference win %.

Rankings sort by your selected metric, then conference win %, opponent results %,
yard differential, overall win %, and team name. Unavailable values sort last;
rank numbers are table positions, not official standings or shared tie ranks.
If ties occur, win % counts each tie as half a win. Conference membership is supplied by the API.
""")

if not frame.empty and not frame["Complete"].all():
    st.warning("Some teams have incomplete conference games or yardage data. Blank values are unavailable, not zero.")
if search:
    frame = frame[frame["Team"].str.contains(search, case=False, regex=False)]

columns = ["Rank", "Team", "Wins", "Losses", "Win %", "Conf wins", "Conf losses", "Conf %",
           "Beaten opponents’ conf wins", "Lost-to opponents’ conf losses", "Opponent results %",
           "Conf yards", "Conf yards allowed", "Yard differential", "Yard differential / game", "Yardage coverage"]
exports = []
for conference in selected:
    # Rank the full conference before applying a team search.
    ranked = rank_conference(division_frame[division_frame["Conference"] == conference], primary)
    exports.append(ranked)
    if search:
        ranked = ranked[ranked["Team"].str.contains(search, case=False, regex=False)]
    if ranked.empty:
        continue
    st.subheader(conference)
    config = {name: st.column_config.NumberColumn(name, format="%.3f")
              for name in ["Win %", "Conf %", "Opponent results %"]}
    config["Yard differential / game"] = st.column_config.NumberColumn("Yard differential / game", format="%.1f")
    for name in ["Wins", "Losses", "Conf wins", "Conf losses", "Beaten opponents’ conf wins",
                 "Lost-to opponents’ conf losses", "Conf yards", "Conf yards allowed", "Yard differential"]:
        config[name] = st.column_config.NumberColumn(name, format="%d")
    st.dataframe(ranked[columns], hide_index=True, width="stretch",
                 column_config=config, height="content")

if search and frame.empty:
    st.info("No teams match your search in the selected conferences.")
if exports:
    import pandas as pd
    csv = pd.concat(exports)[["Conference"] + columns].to_csv(index=False).encode("utf-8")
    st.download_button("Download conference rankings (CSV)", csv,
                       file_name=f"conference-rankings-{year}.csv", mime="text/csv")
