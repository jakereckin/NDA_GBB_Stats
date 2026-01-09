import streamlit as st
import numpy as np
import pandas as pd
import ast
import plotly.express as px
import polars as pl
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from py import sql, data_source
pd.options.mode.chained_assignment = None

st.cache_resource.clear()
st.set_page_config(layout='wide')

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

_PLAYER_LINEUPS_MAP_NAMES = {
    'TOTAL_MIN': 'Total Minutes Played',
    'POITNS_SCORED_PER_GAME': 'Points Scored per Game',
    'POINTS_PER_MINUTE': 'Points per Minute Played',
    'OPP_POINTS_PER_MINUTE': 'Points Allowed per Minute Played',
    'PLUS_MINUS_PER_MINUTE': 'Plus/Minus per Minute Played',
    'GAME_COUNT': 'Games Played'
}

_PLAYER_MAP_NAMES = {
    'GAME_COUNT': 'Games Played',
    'POINTS_PER_MINUTE': 'Team Points while Playing per Minute',
    'OPP_POINTS_PER_MINUTE': 'Points Allowed while Playing per Minute',
    'PLUS_MINUS_PER_MINUTE': 'Plus/Minus per Minute Played',
    'MINUTES_PER_GAME': 'Minutes per Game Played'
}

# ----------------------------------------------------------------------------
@st.cache_data
def get_data():
    minute_data = data_source.run_query(
        sql=sql.view_minutes_sql(), connection=sql_lite_connect
    )
    return minute_data

# ----------------------------------------------------------------------------
@st.cache_data
def build_lineup_intervals(minutes_data, game_end_sec=36*60):
    out_rows = []
    for game_id, grp in minutes_data.groupby('GAME_ID'):
        grp = grp.reset_index(drop=True)
        # unique event times: all IN_SEC and OUT_SEC clipped to [0, game_end_sec]
        times = np.unique(np.clip(np.concatenate([grp['TIME_IN'].values, grp['TIME_OUT'].values]), 0, game_end_sec))
        times = np.sort(times)
        # ensure we include start 0 and final end
        if times[0] != 0:
            times = np.insert(times, 0, 0)
        if times[-1] != game_end_sec:
            times = np.append(times, game_end_sec)
        times = list(reversed(times))
            # iterate intervals
        for i in range(len(times) - 1):
            start = int(times[i])
            end = int(times[i + 1])
            duration = start - end
            if duration <= 0:
                continue
            present = grp[(grp['TIME_IN'] >= start) & (grp['TIME_OUT'] <= end)]
            score_in_frame = grp[(grp['TIME_IN'] == start)]
            score_out_frame = grp[(grp['TIME_OUT'] == end)]
            my_frame = pd.DataFrame()
            my_lineup_players = present['PLAYER_ID'].astype(int).tolist()
            score_in = score_in_frame['TEAM_POINT_IN'].drop_duplicates().min()
            score_out = score_out_frame['TEAM_POINT_OUT'].drop_duplicates().min()
            opp_score_in = score_in_frame['OPP_POINT_IN'].drop_duplicates().min()
            opp_score_out = score_out_frame['OPP_POINT_OUT'].drop_duplicates().min()
            my_times = (start, end)
            lineup_key = tuple(sorted(my_lineup_players))
            lineup_start, lineup_end = my_times
            my_dict = {
                'TIME_IN': lineup_start,
                'TIME_OUT': lineup_end,
                'LINEUP_KEY': str(lineup_key),
                'SCORE_IN': score_in,
                'SCORE_OUT': score_out,
                'OPP_SCORE_IN': opp_score_in,
                'OPP_SCORE_OUT': opp_score_out,
                'GAME_ID': game_id
            }
            out_rows.append(my_dict)
    clean_lineups = pd.DataFrame(out_rows)

    clean_lineups['SECONDS_PLAYED'] = (
        clean_lineups['TIME_IN'] - clean_lineups['TIME_OUT']
    )
    clean_lineups['MIN_PLAYED'] = (
        clean_lineups['SECONDS_PLAYED'] / 60
    )
    clean_lineups['MIN_PLAYED'] = np.where(
        clean_lineups['MIN_PLAYED'] < 1, 1, clean_lineups['MIN_PLAYED']
    )
    clean_lineups['POINTS_SCORED'] = (
        clean_lineups['SCORE_OUT'] - clean_lineups['SCORE_IN']
    )
    clean_lineups['OPP_POINTS_SCORED'] = (
        clean_lineups['OPP_SCORE_OUT'] - clean_lineups['OPP_SCORE_IN']
    )
    return clean_lineups

def build_player_only(minute_data):
    minute_data['SECONDS_PLAYED'] = (
        minute_data['TIME_IN'] - minute_data['TIME_OUT']
    )
    minute_data['MIN_PLAYED'] = (
        minute_data['SECONDS_PLAYED'] / 60
    )
    minute_data['POINTS_SCORED'] = (
        minute_data['TEAM_POINT_OUT'] - minute_data['TEAM_POINT_IN']
    )
    minute_data['OPP_POINTS_SCORED'] = (
        minute_data['OPP_POINT_OUT'] - minute_data['OPP_POINT_IN']
    )
    return minute_data

def group_data(clean_lineups, game_dict):
    grouped_line_data = (
        clean_lineups.groupby(by=['LINEUP_KEY', 'GAME_ID'], as_index=False)
                     .agg(TOTAL_MIN=('MIN_PLAYED', 'sum'),
                          POINTS_SCORED=('POINTS_SCORED', 'sum'),
                          OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum'))
    )
    grouped_line_data['OPPONENT'] = grouped_line_data['GAME_ID'].map(game_dict)
    return grouped_line_data

def get_game_player_info(minutes_data):
    games_info = minutes_data[['GAME_ID', 'GAME_DATE']].drop_duplicates()
    player_info = minutes_data[['GAME_ID', 'PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()
    return games_info, player_info

def get_unique_lineups(grouped_lineups, player_info):
    unique_player_lineups = {}
    unique_lineups = grouped_lineups['LINEUP_KEY'].unique().tolist()
    unique_lineups = [ast.literal_eval(lineup) for lineup in unique_lineups]
    my_players = player_info['PLAYER_ID'].unique().tolist()
    my_players = [int(player) for player in my_players]
    for player in my_players:
        player_lineups = []
        for lineup in unique_lineups:
            if player in lineup:
                player_lineups.append(lineup)
        unique_player_lineups[player] = player_lineups
    return unique_player_lineups, my_players

def get_lineup_level_data(data):
    lineup_level = (
        data.groupby(by=['LINEUP_KEY'], as_index=False)
            .agg(
                GAME_COUNT=('OPPONENT', 'count'),
                TOTAL_MIN=('TOTAL_MIN', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    lineup_level['POINTS_SCORED_PER_GAME'] = (
        lineup_level['POINTS_SCORED'] / lineup_level['GAME_COUNT']
    )
    lineup_level['POINTS_PER_MINUTE'] = (
        lineup_level['POINTS_SCORED'] / lineup_level['TOTAL_MIN']
    )
    lineup_level['OPP_POINTS_PER_MINUTE'] = (
        lineup_level['OPP_POINTS_SCORED'] / lineup_level['TOTAL_MIN']
    )
    lineup_level['PLUS_MINUS_PER_MINUTE'] = (
        lineup_level['POINTS_PER_MINUTE'] - lineup_level['OPP_POINTS_PER_MINUTE']
    )
    lineup_level = (
        lineup_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return lineup_level

def get_player_level(data):
    player_level = (
        data.groupby(by=['PLAYER_NAME'], as_index=False)
            .agg(
                GAME_COUNT=('GAME_DATE', 'nunique'),
                TOTAL_MIN=('MIN_PLAYED', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    player_level['POINTS_SCORED_PER_GAME'] = (
        player_level['POINTS_SCORED'] / player_level['GAME_COUNT']
    )
    player_level['POINTS_PER_MINUTE'] = (
        player_level['POINTS_SCORED'] / player_level['TOTAL_MIN']
    )
    player_level['OPP_POINTS_PER_MINUTE'] = (
        player_level['OPP_POINTS_SCORED'] / player_level['TOTAL_MIN']
    )
    player_level['PLUS_MINUS_PER_MINUTE'] = (
        player_level['POINTS_PER_MINUTE'] - player_level['OPP_POINTS_PER_MINUTE']
    )
    player_level['MINUTES_PER_GAME'] = (
        player_level['TOTAL_MIN'] / player_level['GAME_COUNT']
    )
    player_level = (
        player_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return player_level

def get_game_level(data):
    game_level = (
        data.groupby(by=['LINEUP_KEY', 'OPPONENT'], as_index=False)
            .agg(
                TOTAL_MIN=('TOTAL_MIN', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    game_level['POINTS_PER_MINUTE'] = (
        game_level['POINTS_SCORED'] / game_level['TOTAL_MIN']
    )
    game_level['OPP_POINTS_PER_MINUTE'] = (
        game_level['OPP_POINTS_SCORED'] / game_level['TOTAL_MIN']
    )
    game_level['PLUS_MINUS_PER_MINUTE'] = (
        game_level['POINTS_PER_MINUTE'] - game_level['OPP_POINTS_PER_MINUTE']
    )
    game_level = (
        game_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return game_level

season, players = st.columns(2)

minute_data = get_data()
years = minute_data['SEASON'].sort_values(ascending=False).drop_duplicates().tolist()

with season:
    select_season = st.radio('Select Season', options=years, horizontal=True)
minute_data = minute_data[minute_data['SEASON'] == select_season]
clean_lineups = build_lineup_intervals(minutes_data=minute_data)
games_info, player_info = get_game_player_info(minutes_data=minute_data)
games_info_dict = dict(zip(games_info['GAME_ID'], games_info['GAME_DATE']))
grouped_lineups = group_data(clean_lineups=clean_lineups, game_dict=games_info_dict)
unique_player_lineups, my_players = get_unique_lineups(grouped_lineups=grouped_lineups, player_info=player_info)
player_map = dict(zip(player_info['PLAYER_NAME'], player_info['PLAYER_ID'].astype(int)))

lineup_analysis = clean_lineups.groupby('GAME_ID').apply(
    lambda x: x.sort_values('TIME_IN', ascending=False).reset_index(drop=True)
).reset_index(drop=True)

lineup_analysis['RANK'] = lineup_analysis.groupby('GAME_ID').cumcount() + 1
player_ids = player_info['PLAYER_ID'].astype(int).drop_duplicates().tolist()

with players:
    select_players = st.multiselect('Select Players to View', options=player_ids)

lineup_analysis["LINEUP_SET"] = lineup_analysis["LINEUP_KEY"].apply(lambda x: set(ast.literal_eval(x)))
these_players = lineup_analysis[ lineup_analysis["LINEUP_SET"].apply(lambda s: set(select_players).issubset(s)) ]
# Sort to ensure correct ordering
df = these_players.sort_values(["GAME_ID", "RANK"])

# --- STEP 1: Build transitions BEFORE filtering ---

# Build graph
G = nx.DiGraph()

# Add all nodes first
for lineup in df["LINEUP_KEY"].unique():
    G.add_node(lineup)

# Add edges based on sequential RANK within GAME_ID
for game_id, group in df.groupby("GAME_ID"):
    group = group.sort_values("RANK")

    # Create next-rank mapping
    group["NEXT_LINEUP"] = group["LINEUP_KEY"].shift(-1)

    # Only valid transitions
    transitions = group.dropna(subset=["NEXT_LINEUP"])

    for _, row in transitions.iterrows():
        u = row["LINEUP_KEY"]
        v = row["NEXT_LINEUP"]

        if u == v:
            continue  # prevent self-loops

        if G.has_edge(u, v):
            G[u][v]["weight"] += 1
        else:
            G.add_edge(u, v, weight=1)

# --- STEP 2: Apply filtering AFTER transitions are built ---

if select_players:
    valid_nodes = set(
        df[df["LINEUP_SET"].apply(lambda s: set(select_players).issubset(s))]["LINEUP_KEY"]
    )

    # Remove nodes not matching filter
    nodes_to_remove = [n for n in G.nodes() if n not in valid_nodes]
    G.remove_nodes_from(nodes_to_remove)

# --- STEP 3: Compute PM/min only for remaining nodes ---

df["PLUS_MINUS"] = df["POINTS_SCORED"] - df["OPP_POINTS_SCORED"]
df["PM_PER_MIN"] = df["PLUS_MINUS"] / df["MIN_PLAYED"]

pm_map = df.groupby("LINEUP_KEY")["PM_PER_MIN"].mean().to_dict()

# --- DRAW GRAPH ---

fig = plt.figure(figsize=(50, 25))
pos = nx.spring_layout(G, k=2, seed=13)

weights = [G[u][v]["weight"] for u, v in G.edges()]
node_colors = ["red" if pm_map.get(n, 0) < 0 else "green" for n in G.nodes()]

nx.draw_networkx_nodes(G, pos, node_size=900, node_color=node_colors)
nx.draw_networkx_edges(G, pos, width=weights, arrowsize=20, arrowstyle="-|>")

# Labels with stroke
for node, (x, y) in pos.items():
    plt.text(
        x, y,
        node,
        fontsize=14,
        fontweight="bold",
        ha="center",
        va="center",
        path_effects=[pe.withStroke(linewidth=3, foreground="white")]
    )

plt.title("Lineup Transition Graph", fontsize=24)
plt.axis("off")

st.pyplot(fig)
