import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from functions import utils as ut
pd.options.mode.chained_assignment = None

st.cache_data.clear()

# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client


# ----------------------------------------------------------------------------
def get_my_db(client):
    my_db = client['NDA_GBB']
    plays_db = my_db['PLAYS']
    spots_db = my_db['SPOTS']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    plays = pd.DataFrame(list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(list(players_db.find())).drop(columns=['_id'])
    players = players[players['YEAR'] == 2024]
    game_summary = (
        pd.DataFrame(list(game_summary_db.find())).drop(columns=['_id'])
    )
    return plays, spots, games, players, game_summary


#-----------------------------------------------------------------------------
def load_data():
    client = get_client()
    play_event, spot, games, players, game_summary = get_my_db(client=client)

    return play_event, spot, games, players, game_summary


#-----------------------------------------------------------------------------
def format_data(spot, games, players, game_summary_data):
    '''
    Format data to count makes and misses.
    '''
    player_data = (
        play_event.merge(spot, left_on=['SHOT_SPOT'], right_on=['SPOT'])
                  .merge(games, on=['GAME_ID'])
                  .merge(players, left_on=['PLAYER_ID'], right_on=['NUMBER'])
    )
    game_summary = pd.merge(left=game_summary_data, right=games, on='GAME_ID')

    game_summary = game_summary[game_summary['SEASON'] == 2024]
    game_summary['LABEL'] = (
        game_summary['OPPONENT'] + ' - ' + game_summary['DATE']
    )
    player_data['LABEL'] = (
        player_data['OPPONENT'] + ' - ' + player_data['DATE']
    )
    player_data['NAME'] = (
        player_data['FIRST_NAME'] + ' ' + player_data['LAST_NAME']
    )
    player_data['MAKE'] = np.where(player_data['MAKE_MISS'] == 'Y', 1, 0)

    player_data['ATTEMPT'] = 1
    player_data['DATE_DTTM'] = pd.to_datetime(player_data['DATE'])
    player_data = (
        player_data.sort_values(by='DATE_DTTM').reset_index(drop=True)
    )
    player_data2 = player_data[['NAME',
                                'SHOT_SPOT',
                                'MAKE',
                                'ATTEMPT',
                                'SHOT_DEFENSE'
    ]]
    return player_data, player_data2, game_summary


#-------------------------------------------------------------------------------
def get_games_data(player_data, game_summary, game):
    '''
    Get game data for selected game
    '''
    t_game = player_data[player_data['LABEL'] == game]
    game_data = game_summary[game_summary['LABEL'] == game]
    game_data['DATE_DTTM'] = pd.to_datetime(game_data['DATE'])
    game_data = game_data.sort_values(by='DATE_DTTM')
    return t_game, game_data


#-------------------------------------------------------------------------------
def get_grouped_all_spots(player_data2, spot):
    grouped = (player_data2.groupby(by=['NAME', 'SHOT_SPOT', 'SHOT_DEFENSE'],
                                    as_index=False)
                           .agg(ATTEMPTS=('ATTEMPT', np.sum),
                                MAKES=('MAKE', np.sum))
    )
    # Basically counting for divison by 0
    # If denom (attempts) is 0, return 0, else get percent
    grouped['MAKE_PERCENT'] = np.where(grouped['ATTEMPTS']>0,
                                       grouped['MAKES']/grouped['ATTEMPTS'],
                                       0
    )
    all_spots = spot.copy()
    # Spot name final character is point value.. easy fix is putting this into DB
    # TODO: add to DB instead of here.
    all_spots['POINT_VALUE'] = (
        all_spots['SPOT'].str.strip().str[-1].astype('int64')
    )
    grouped_all_spots = pd.merge(all_spots,
                                 grouped,
                                 left_on=['SPOT'],
                                 right_on=['SHOT_SPOT'],
                                 how='left'
    )
    # Expected value = point value * percent make (accounting for defense)
    grouped_all_spots['EXPECTED_VALUE'] = (
        grouped_all_spots['POINT_VALUE'] * grouped_all_spots['MAKE_PERCENT']
    )
    grouped_all_spots['EXPECTED_VALUE'] = (
        grouped_all_spots.fillna(grouped_all_spots['OPP_EXPECTED'])
    )
    grouped_all_spots = grouped_all_spots.drop(columns=['SPOT',
                                                        'XSPOT',
                                                        'YSPOT',
                                                        'MAKES',
                                                        'ATTEMPTS']
    )
    return grouped_all_spots


#-------------------------------------------------------------------------------
def get_team_data(t_game, grouped_all_spots):
    '''
    Get expected points, but on team level instead of individual
    '''
    this_game = (t_game.groupby(by=['NAME', 'SHOT_SPOT', 'SHOT_DEFENSE'],
                                as_index=False)
                       .agg(ATTEMPTS=('ATTEMPT', np.sum),
                            MAKES=('MAKE', np.sum))
                       .merge(grouped_all_spots,
                              on=['NAME', 'SHOT_SPOT', 'SHOT_DEFENSE'])
    )
    this_game['EXPECTED_POINTS'] = (
        this_game['ATTEMPTS'] * this_game['EXPECTED_VALUE']
    )
    this_game['ACTUAL_POINTS'] = (
        this_game['MAKES'] * this_game['POINT_VALUE']
    )
    return this_game


play_event, spot, games, players, gs_data = load_data()
player_data, player_data2, game_summary_cleaned = format_data(
    spot=spot, games=games, players=players, game_summary_data=gs_data
)

games_list = player_data['LABEL'].unique().tolist()

game = st.selectbox(label='Select Game', options=games_list)

if game != []:
    t_game, game_data = get_games_data(
        player_data=player_data, game_summary=game_summary_cleaned, game=game
    )
    grouped_all_spots = get_grouped_all_spots(
        player_data2=player_data2, spot=spot
    )
    this_game = get_team_data(
        t_game=t_game, grouped_all_spots=grouped_all_spots
    )

    # ========== EXPECTED TRITONS ==========
    tritons = this_game[this_game['NAME'] != 'OPPONENT TEAM']
    expected_fg = tritons['EXPECTED_POINTS'].sum()
    total_expected = expected_fg
    
    # ========== ACTUAL TRITONS ==========
    actual_fg = tritons['ACTUAL_POINTS'].sum()
    total_actual = actual_fg

    # ========== EXPECTED OPP ==========
    opp = this_game[this_game['NAME'] == 'OPPONENT TEAM']
    expected_fg_opp = opp['EXPECTED_POINTS'].sum()

    # ========== ACTUAL OPP ==========
    actual_fg_opp = opp['ACTUAL_POINTS'].sum()

    st.metric(
        value=np.round(total_expected, 2), label='TOTAL TRITON EXPECTED POINTS'
    )
    st.metric(value=total_actual, label='ACTUAL TRITON POINTS')

    st.metric(
        value=np.round(expected_fg_opp, 2), label='TOTAL OPPONENT EXPECTED POINTS'
    )
    st.metric(value=actual_fg_opp, label='ACTUAL OPPONENT POINTS')

    st.dataframe(
        this_game, use_container_width=True, hide_index=True
    )