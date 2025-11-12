import streamlit as st
import numpy as np
import pandas as pd
import ast
import polars as pl
from py import sql, data_source
pd.options.mode.chained_assignment = None

st.cache_resource.clear()

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

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
    clean_lineups['POINTS_SCORED'] = (
        clean_lineups['SCORE_OUT'] - clean_lineups['SCORE_IN']
    )
    clean_lineups['OPP_POINTS_SCORED'] = (
        clean_lineups['OPP_SCORE_OUT'] - clean_lineups['OPP_SCORE_IN']
    )
    return clean_lineups

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

minute_data = get_data()
clean_lineups = build_lineup_intervals(minutes_data=minute_data)
games_info, player_info = get_game_player_info(minutes_data=minute_data)
games_info_dict = dict(zip(games_info['GAME_ID'], games_info['GAME_DATE']))
grouped_lineups = group_data(clean_lineups=clean_lineups, game_dict=games_info_dict)

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

select_player = st.selectbox(label='Select Player', options=my_players)
if select_player:
    that_player_lineups = unique_player_lineups.get(select_player)
    df = pd.DataFrame(
        data=that_player_lineups, 
        columns=['PLAYER_1', 'PLAYER_2', 'PLAYER_3', 'PLAYER_4', 'PLAYER_5']
    )
    df['LINEUP_KEY'] = tuple(
        zip(
            df['PLAYER_1'], 
            df['PLAYER_2'], 
            df['PLAYER_3'], 
            df['PLAYER_4'],
            df['PLAYER_5']
        )
    )
    df['LINEUP_KEY'] = df['LINEUP_KEY'].astype(str)
    merged = pd.merge(df, grouped_lineups, on=['LINEUP_KEY'])
    game_level = merged[[
        'LINEUP_KEY', 'TOTAL_MIN', 'POINTS_SCORED', 'OPP_POINTS_SCORED', 'OPPONENT'
    ]]
    lineup_level = (
        merged.groupby(by=['LINEUP_KEY'], as_index=False)
              .agg(GAME_COUNT=('OPPONENT', 'count'),
                   TOTAL_MIN=('TOTAL_MIN', 'sum'),
                   POINTS_SCORED=('POINTS_SCORED', 'sum'),
                   OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum'))
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
    lineup_level = lineup_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False).reset_index(drop=True)

    min_threshold = st.number_input(label='Minimum minutes to consider', step=1)

    if min_threshold:
        lineup_level = lineup_level[lineup_level['TOTAL_MIN'] >= min_threshold]
    st.write(lineup_level)
    #st.write(that_player_lineups)
