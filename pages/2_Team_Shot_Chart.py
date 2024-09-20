from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import plotly.graph_objects as go
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
    plays = pd.DataFrame(list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(list(games_db.find())).drop(columns=['_id'])
    plays = plays[plays['PLAYER_ID'] != 0]
    return plays, spots, games


# ----------------------------------------------------------------------------
@st.cache_data
def load_frames():
     client = get_client()
     play_event, spot, games = get_my_db(client)
     spot = spot[spot['SPOT'] != 'FREE_THROW1']
     return play_event, spot, games


# ----------------------------------------------------------------------------
@st.cache_data
def get_game_data(play_event, spot, games):
     team_data = (
          play_event.merge(spot, left_on='SHOT_SPOT', right_on='SPOT')
                    .merge(games, on='GAME_ID')
     )
     team_data['GAME'] = team_data['OPPONENT'] + ' ' + team_data['DATE']

     team_data['MAKE'] = np.where(team_data['MAKE_MISS'] == 'Y', 1, 0)

     team_data['HEAVILY_GUARDED'] = np.where(
          team_data['SHOT_DEFENSE'] == 'HEAVILY_GUARDED', 1, 0
     )
     team_data['ATTEMPT'] = 1
     return team_data


# ----------------------------------------------------------------------------
@st.cache_data
def filter_team_data(team_data):
     team_data_filtered = team_data[['GAME',
                              'GAME_ID',
                              'OPPONENT',
                              'DATE',
                              'SHOT_SPOT',
                              'MAKE',
                              'ATTEMPT',
                              'XSPOT',
                              'YSPOT',
                              'HEAVILY_GUARDED'
     ]]
     team_data_filtered = team_data_filtered.sort_values(
          by='GAME_ID', ascending=False
     )
     team_data_filtered['U_ID'] = (
          team_data_filtered['OPPONENT'] + ' - ' + team_data_filtered['DATE']
     )
     return team_data_filtered


# ----------------------------------------------------------------------------
def get_selected_games(games_selected, team_data_filtered):
     data_from_game_selected = pd.DataFrame(games_selected, columns=['U_ID'])
     data_from_game_selected['OPP'] = (
          data_from_game_selected['U_ID'].str.split(' - ').str[0]
     )
     data_from_game_selected['DATE'] = (
          data_from_game_selected['U_ID'].str.split(' - ').str[1]
     )
     opponents = data_from_game_selected['OPP'].unique().tolist()

     dates = data_from_game_selected['DATE'].unique().tolist()

     this_game = team_data_filtered[
          (team_data_filtered['OPPONENT'].isin(opponents))
          & (team_data_filtered['DATE'].isin(dates))
     ]
     return this_game


# ----------------------------------------------------------------------------
def format_selected_games(this_game):
     totals = (this_game.groupby(by=['SHOT_SPOT', 'XSPOT', 'YSPOT'], 
                                 as_index=False)
                         [['MAKE', 
                           'ATTEMPT', 
                           'HEAVILY_GUARDED']]
                         .sum()
     )
     totals['POINT_VALUE'] = (
          totals['SHOT_SPOT'].str.strip().str[-1].astype('int64')
     )
     totals['MAKE_PERCENT'] = totals['MAKE'] / totals['ATTEMPT'].replace(0, 1)

     totals['HG_PERCENT'] = (
          totals['HEAVILY_GUARDED'] / totals['ATTEMPT'].replace(0, 1)
     )
     totals['POINTS_PER_ATTEMPT'] = (
          (totals['MAKE'] * totals['POINT_VALUE']) 
          / totals['ATTEMPT'].replace(0, 1)
     )
     totals_sorted = totals.sort_values(
          by=['POINTS_PER_ATTEMPT', 'ATTEMPT'], ascending=False
     )
     totals_sorted = totals_sorted[totals_sorted['ATTEMPT'] > 1]
     totals_sorted = totals_sorted[['SHOT_SPOT',
                                   'MAKE',
                                   'ATTEMPT',
                                   'MAKE_PERCENT',
                                   'POINTS_PER_ATTEMPT',
                                   'HG_PERCENT']].round(3)
     return totals, totals_sorted

play_event, spot, games = load_frames()

team_data = get_game_data(play_event=play_event, spot=spot, games=games)

team_data_filtered = filter_team_data(team_data=team_data)


games = team_data_filtered['U_ID'].unique()
games_selected = st.multiselect('Choose Games', games)

this_game = get_selected_games(
     games_selected=games_selected, team_data_filtered=team_data_filtered
)

# ----------------------------------------------------------------------------
if games_selected:
    totals, totals_sorted = format_selected_games(this_game=this_game)
    fig = ut.load_shot_chart_team(totals, team_selected=games_selected)
    st.markdown(
         "<h1 style='text-align: center; color: black;'>Shot Chart</h1>", 
         unsafe_allow_html=True
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
         "<h1 style='text-align: center; color: black;'>Top 5 Spots</h1>", 
         unsafe_allow_html=True
    )
    st.dataframe(
         totals_sorted.head(5), use_container_width=True, hide_index=True
    )
