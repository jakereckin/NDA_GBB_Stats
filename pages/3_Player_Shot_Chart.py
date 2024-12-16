import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None

st.cache_data.clear()

# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(host=uri, server_api=ServerApi(version='1'))
    return client


# ----------------------------------------------------------------------------
def get_my_db(client):
    my_db = client['NDA_GBB']
    plays_db = my_db['PLAYS']
    spots_db = my_db['SPOTS']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    plays = pd.DataFrame(data=list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(data=list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    players = players[players['FIRST_NAME'] != 'OPPONENT']
    return plays, spots, games, players


# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
     client = get_client()
     play_event, spot, games, players = get_my_db(client=client)
     spot = spot[spot['SPOT'] != 'FREE_THROW1']
     return play_event, spot, games, players


# ----------------------------------------------------------------------------
@st.cache_data
def get_player_data(play_event, spot, games, players, season):
     players = players[players['YEAR'] == season]
     games = games[games['SEASON'] == season]
     player_data = (
          play_event.merge(spot, left_on='SHOT_SPOT', right_on='SPOT')
                    .merge(games, on='GAME_ID')
                    .merge(players, left_on='PLAYER_ID', right_on='NUMBER')
     )
     player_data['NAME'] = (
          player_data['FIRST_NAME']  + ' ' + player_data['LAST_NAME']
     )
     player_data['MAKE'] = np.where(player_data['MAKE_MISS'] == 'Y', 1, 0)

     player_data['HEAVILY_GUARDED'] = np.where(
          player_data['SHOT_DEFENSE'] == 'HEAVILY_GUARDED', 1, 0
     )
     player_data['ATTEMPT'] = 1
     player_data = player_data[[
          'FIRST_NAME', 'LAST_NAME', 'NAME', 'SHOT_SPOT', 'MAKE', 'ATTEMPT',
          'XSPOT', 'YSPOT', 'HEAVILY_GUARDED'
     ]]
     player_data['U_ID'] = (
          player_data['FIRST_NAME'] + ' ' + player_data['LAST_NAME']
     )
     return player_data

# ----------------------------------------------------------------------------
def format_visual_data(this_game):
     totals = (
          this_game.groupby(by=['NAME', 'SHOT_SPOT', 'XSPOT', 'YSPOT'], 
                            as_index=False)
                   [['MAKE', 'ATTEMPT', 'HEAVILY_GUARDED']].sum()
     )
     totals['POINT_VALUE'] = (
          totals['SHOT_SPOT'].str.strip().str[-1].astype('int64')
     )
     totals['MAKE_PERCENT'] = (
          totals['MAKE'] / totals['ATTEMPT'].replace(0, 1)
     )
     totals['HG_PERCENT'] = (
          totals['HEAVILY_GUARDED'] / totals['ATTEMPT'].replace(0, 1)
     )
     totals['POINTS_PER_ATTEMPT'] = (
          (totals['MAKE']*totals['POINT_VALUE'])
          / totals['ATTEMPT'].replace(0, 1)
     )
     totals_sorted = totals.sort_values(
          by=['POINTS_PER_ATTEMPT', 'ATTEMPT'], ascending=False
     )
     totals_sorted = totals_sorted[totals_sorted['ATTEMPT'] > 1]
     totals_sorted = totals_sorted[[
          'SHOT_SPOT', 'MAKE', 'ATTEMPT', 'MAKE_PERCENT',
          'POINTS_PER_ATTEMPT', 'HG_PERCENT'
     ]].round(3)
     return totals, totals_sorted


# ----------------------------------------------------------------------------
@st.cache_data
def filter_player_data(players_selected, player_data):
     first_name = players_selected.split(' ')[0]
     last_name = players_selected.split(' ')[1]
     this_game = player_data[
          (player_data['FIRST_NAME']==first_name)
          & (player_data['LAST_NAME']==last_name)
     ]
     return this_game

play_event, spot, games, players = load_data()

season_list = players[players['YEAR'] > 2023].YEAR.unique().tolist()

season = st.radio(label='Select Season', options=season_list, horizontal=True)

if season:
     player_data = get_player_data(
          play_event=play_event, spot=spot, games=games, players=players, 
          season=season
     )


     player_names = player_data['U_ID'].unique()
     players_selected = st.radio(
          label='Choose Player', options=player_names, horizontal=True
     )

     this_game = filter_player_data(
          players_selected=players_selected, player_data=player_data
     )
     if players_selected:
          totals, totals_sorted = format_visual_data(this_game=this_game)
          fig = ut.load_shot_chart_player(
               totals=totals, players_selected=players_selected
               )
          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Shot Chart for {players_selected}</h1>", 
               unsafe_allow_html=True
          )

          st.plotly_chart(figure_or_data=fig, use_container_width=True)

          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Top 5 Spots for {players_selected}</h1>", 
               unsafe_allow_html=True
          )

          st.dataframe(
               data=totals_sorted.head(5), use_container_width=True, hide_index=True
          )