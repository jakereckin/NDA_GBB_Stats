import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
import polars as pl
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
    plays = pl.DataFrame(list(plays_db.find())).drop(['_id'])
    spots = pl.DataFrame(list(spots_db.find())).drop(['_id'])
    games = pl.DataFrame(list(games_db.find())).drop(['_id'])
    players = pl.DataFrame(list(players_db.find())).drop(['_id'])
    players = players.filter(pl.col('YEAR') == 2024)
    game_summary = (
        pl.DataFrame(list(game_summary_db.find())).drop(['_id'])
    )
    return plays, spots, games, players, game_summary


#-----------------------------------------------------------------------------
def load_data():
    client = get_client()
    play_event, spot, games, players, game_summary = get_my_db(client=client)
    return play_event, spot, games, players, game_summary


#-----------------------------------------------------------------------------
def format_data(spot, games, players, game_summary_data, play_event):
    '''
    Format data to count makes and misses.
    '''
    player_data = (
        play_event.join(other=spot, left_on='SHOT_SPOT', right_on='SPOT')
                  .join(games, on=['GAME_ID'])
                  .join(players, left_on=['PLAYER_ID'], right_on=['NUMBER'])
    )
    game_summary = game_summary_data.join(games, on='GAME_ID')

    game_summary = game_summary.filter(pl.col('SEASON') == 2024)
    game_summary = (
        game_summary.with_columns(
            (pl.col('OPPONENT') + ' - ' + pl.col('DATE'))
            .alias('LABEL')
        )
    )
    player_data = (
        player_data.with_columns(
            (pl.col('OPPONENT') + ' - ' + pl.col('DATE'))
            .alias('LABEL'),
            (pl.col('FIRST_NAME') + ' ' + pl.col('LAST_NAME'))
            .alias('NAME'),
            pl.when(pl.col('MAKE_MISS') == 'Y')
              .then(1)
              .otherwise(0)
              .alias('MAKE'),
            pl.lit(1).alias('ATTEMPT'),
            pl.col('DATE').str.to_datetime(strict=False, format='%m/%d/%Y').alias('DATE_DTTM')

        )
    )
    player_data = player_data.sort(by='DATE_DTTM')
    player_data2 = player_data.select(
        ['NAME', 'SHOT_SPOT', 'MAKE', 'ATTEMPT', 'SHOT_DEFENSE']
    )
    return player_data, player_data2, game_summary


#-------------------------------------------------------------------------------
def get_games_data(player_data, game_summary, game):
    '''
    Get game data for selected game
    '''
    t_game = player_data.filter(pl.col('LABEL') == game)
    game_data = (
        game_summary.filter(pl.col('LABEL') == game)
                    .with_columns(
                        pl.col('DATE')
                          .str
                          .to_datetime(strict=False, format='%m/%d/%Y')
                          .alias('DATE_DTTM')
                    )
                    .sort(by='DATE')
    )
    return t_game, game_data


#-------------------------------------------------------------------------------
def get_grouped_all_spots(player_data2, spot):
    #spot = spot.to_pandas()
    grouped = (
        player_data2.group_by(['NAME', 'SHOT_SPOT', 'SHOT_DEFENSE'])
                    .agg([pl.col('ATTEMPT').sum().alias('ATTEMPTS'),
                          pl.col('MAKE').sum().alias('MAKES')])
    )
    # Basically counting for divison by 0
    # If denom (attempts) is 0, return 0, else get percent
    grouped = (
        grouped.with_columns(
            (pl.when(pl.col('ATTEMPTS') > 0)
               .then(pl.col('MAKES') / pl.col('ATTEMPTS'))
               .otherwise(0))
            .alias('MAKE_PERCENT')
        )
    )
    all_spots = spot.clone()
    all_spots = (
        all_spots.with_columns(
            (pl.col('SPOT').str.slice(-1,1).cast(int).alias('POINT_VALUE'))
        )
    )
    # Spot name final character is point value.. easy fix is putting this into DB
    # TODO: add to DB instead of here.
    #all_spots['POINT_VALUE'] = (
   #     all_spots['SPOT'].str.strip().str[-1].astype('int64')
   # )
    grouped_all_spots = all_spots.join(  
        grouped, left_on=['SPOT'], right_on=['SHOT_SPOT'], how='left'
    )
    grouped_all_spots = (
        grouped_all_spots.with_columns(
            (pl.col('POINT_VALUE') * pl.col('MAKE_PERCENT'))
            .alias('EXPECTED_VALUE')
        )
    )
    # Expected value = point value * percent make (accounting for defense)
    grouped_all_spots = (
        grouped_all_spots.drop(['XSPOT', 'YSPOT', 'MAKES', 'ATTEMPTS'])
                         .rename({'SPOT': 'SHOT_SPOT'})
    )
    return grouped_all_spots


#-------------------------------------------------------------------------------
def get_team_data(t_game, grouped_all_spots):
    '''
    Get expected points, but on team level instead of individual
    '''
    t_game = t_game.to_pandas()
    grouped_all_spots = grouped_all_spots.to_pandas()
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


#-------------------------------------------------------------------------------
@st.cache_data(allow_output_mutation=True)
def get_data():
    play_event, spot, games, players, gs_data = load_data()
    player_data, player_data2, game_summary_cleaned = format_data(
        spot=spot, 
        games=games, 
        players=players, 
        game_summary_data=gs_data, 
        play_event=play_event
    )
    games_list = player_data['LABEL'].unique()
    return (player_data, 
            player_data2, 
            game_summary_cleaned, 
            games_list, 
            spot, 
            play_event)



#-------------------------------------------------------------------------------
(player_data,
 player_data2, 
 game_summary_cleaned, 
 games_list, 
 spot, 
 play_event) = get_data()
game = st.radio(label='Select Game', options=games_list, horizontal=True)

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

    # ========== EXPECTED ==========
    expected_fg = this_game['EXPECTED_POINTS'].sum()
    total_expected = expected_fg
    
    # ========== ACTUAL ==========
    actual_fg = this_game['ACTUAL_POINTS'].sum()
    total_actual = actual_fg

    st.metric(
        value=np.round(total_expected, 2), label='TOTAL EXPECTED POINTS'
    )
    st.metric(value=total_actual, label='ACTUAL POINTS')
    st.dataframe(
        this_game, use_container_width=True, hide_index=True
    )