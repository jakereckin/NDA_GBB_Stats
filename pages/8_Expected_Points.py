import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None

@st.cache_data
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    play_event = conn.read(worksheet='play_event')
    spot = conn.read(worksheet='spots')
    games = conn.read(worksheet='games')
    players = conn.read(worksheet='players')
    players = players[players['YEAR']==2024]
    game_summary_data = conn.read(worksheet='game_summary')
    return play_event, spot, games, players, game_summary_data

@st.cache_data
def get_ft_values(game_summary_data,
                  games):
    game_summary = pd.merge(left=game_summary_data,
                            right=games,
                            on='GAME_ID'
    )
    game_summary = game_summary[game_summary['SEASON']==2024]
    game_summary['LABEL'] = (game_summary['OPPONENT']
                                + ' - '
                                + game_summary['DATE']
    )
    ft_percent = (game_summary.groupby(by=['PLAYER_ID'], as_index=False)
                            .agg(FTA=('FTA', np.sum),
                                FTM=('FTM', np.sum))
    )
    mean_ft_percent = ft_percent['FTM'].sum()/ft_percent['FTA'].sum()
    ft_percent['FT_PERCENT'] = np.where(ft_percent['FTA']==0,
                                        mean_ft_percent,
                                        ft_percent['FTM']/ft_percent['FTA'])
    ft_percent_keep = ft_percent[['PLAYER_ID',
                                'FT_PERCENT']]
    return game_summary, ft_percent_keep

@st.cache_data
def format_data(spot,
                games,
                players):
    player_data = (play_event.merge(spot,
                                left_on=['SHOT_SPOT'],
                                right_on=['SPOT'])
                         .merge(games,
                                on=['GAME_ID'])
                         .merge(players,
                                left_on=['PLAYER_ID'],
                                right_on=['NUMBER'])
    )
    player_data['LABEL'] = (player_data['OPPONENT']
                                + ' - '
                                + player_data['DATE']
    )
    player_data['NAME'] = (player_data['FIRST_NAME']
                        + ' '
                        + player_data['LAST_NAME']
    )
    player_data['MAKE'] = np.where(player_data['MAKE_MISS']=='Y',
                                1,
                                0
    )
    player_data['WAS_ASSIST'] = np.where(player_data['ASSISTED']=='Y',
                                1,
                                0
    )
    player_data['HEAVILY_GUARDED'] = np.where(player_data['SHOT_DEFENSE']=='HEAVILY_GUARDED',
                                1,
                                0
    )
    player_data['ATTEMPT'] = 1
    player_data2 = player_data[['NAME',
                                'SHOT_SPOT',
                                'MAKE',
                                'ATTEMPT',
                                'SHOT_DEFENSE'
    ]]
    return player_data, player_data2

def get_games_data(player_data,
                   game_summary,
                   game):
    t_game = player_data[player_data['LABEL']==game]
    game_data = game_summary[game_summary['LABEL']==game]
    game_data = game_data.merge(ft_percent_keep,
                                on=['PLAYER_ID']
    )
    return t_game, game_data

def get_grouped_all_spots(player_data2,
                          spot):
    grouped = (player_data2.groupby(by=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'],
                        as_index=False)
                .agg(ATTEMPTS=('ATTEMPT', np.sum),
                    MAKES=('MAKE', np.sum))
    )
    grouped['MAKE_PERCENT'] = np.where(grouped['ATTEMPTS']>0,
                                    grouped['MAKES']/grouped['ATTEMPTS'],
                                    0
    )
    all_spots = spot.copy()
    all_spots['POINT_VALUE'] = (all_spots['SPOT'].str
                                                    .strip()
                                                    .str[-1]
                                                    .astype('int64')
    )
    grouped_all_spots = (pd.merge(all_spots,
                                grouped,
                                left_on=['SPOT'],
                                right_on=['SHOT_SPOT'],
                                how='left')
    )
    grouped_all_spots['EXPECTED_VALUE'] = (grouped_all_spots['POINT_VALUE']
                                *grouped_all_spots['MAKE_PERCENT']
    )
    grouped_all_spots = grouped_all_spots.drop(columns=['SPOT',
                                        'XSPOT',
                                        'YSPOT',
                                        'MAKES',
                                        'ATTEMPTS'])
    return grouped_all_spots

def get_team_data(t_game,
                  grouped_all_spots):
    this_game = (t_game.groupby(by=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'],
                        as_index=False)
                .agg(ATTEMPTS=('ATTEMPT', np.sum),
                    MAKES=('MAKE', np.sum))
                .merge(grouped_all_spots,
                        on=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'])
    )
    this_game['EXPECTED_POINTS'] = this_game['ATTEMPTS']*this_game['EXPECTED_VALUE']
    this_game['ACTUAL_POINTS'] = this_game['MAKES']*this_game['POINT_VALUE']
    return this_game

play_event, spot, games, players, game_summary_data = load_data()
game_summary, ft_percent_keep = get_ft_values(game_summary_data=game_summary_data,
                                              games=games
)
player_data, player_data2 = format_data(spot=spot,
                                        games=games,
                                        players=players
)

games_list = (player_data['LABEL'].unique()
                                  .tolist()
)
game = st.selectbox(label='Select Games',
                      options=games_list
)
if game != []:
    t_game, game_data = get_games_data(player_data=player_data,
                                       game_summary=game_summary,
                                       game=game
    )
    grouped_all_spots = get_grouped_all_spots(player_data2=player_data2,
                                              spot=spot
    )
    this_game = get_team_data(t_game=t_game,
                              grouped_all_spots=grouped_all_spots
    )
    # EXPECTED ====
    expected_fg = this_game['EXPECTED_POINTS'].sum()
    expected_ft = (game_data['FTA']*game_data['FT_PERCENT']).sum()
    total_expected = expected_fg+expected_ft
    # ACTUAL ====
    actual_fg = this_game['ACTUAL_POINTS'].sum()
    actual_ft = game_data['FTM'].sum()
    total_actual = actual_fg+actual_ft
    st.metric(value=total_expected,
            label='TOTAL EXPECTED POINTS')
    st.metric(value=total_actual,
            label='ACTUAL POINTS')
    st.dataframe(this_game, use_container_width=True, hide_index=True)
    st.dataframe(grouped_all_spots, use_container_width=True, hide_index=True)
    st.dataframe(ft_percent_keep, use_container_width=True, hide_index=True)