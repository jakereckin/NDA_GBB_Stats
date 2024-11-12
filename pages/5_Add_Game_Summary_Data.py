import streamlit as st
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None


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
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    game_summary = (
        pd.DataFrame(data=list(game_summary_db.find())).drop(columns=['_id'])
    )
    return games, players, game_summary, game_summary_db


# ----------------------------------------------------------------------------
def load_data():
    client = get_client()
    games, players, game_summary, game_summary_db = get_my_db(client=client)
    games['SEASON'] = (
        games['SEASON'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False)
    )
    players['YEAR'] = (
        players['YEAR'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False)
    )
    games = games.dropna(subset=['SEASON'])
    return players, games, game_summary, game_summary_db


# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(games, players, season):

    games_season = games[games['SEASON'] == season]
    players_season = players[players['YEAR'] == season]

    games_season['LABEL'] = (
        games_season['OPPONENT'] + ' - ' + games_season['DATE']
    )

    return games_season, players_season


# ----------------------------------------------------------------------------
@st.cache_data
def get_selected_game(games_season, game_select):
    game_val_opp = game_select.split(' - ')[0]
    game_val_date = game_select.split(' - ')[1]
    this_game = games_season[
        (games_season['OPPONENT']==game_val_opp)
        & (games_season['DATE']==game_val_date)
    ]
    return this_game


# ----------------------------------------------------------------------------
password = st.text_input(label='Password', type='password')

if password == st.secrets['page_password']['PAGE_PASSWORD']:

    players, games, game_summary_data, game_summary_db = load_data()

    my_season_options = games['SEASON'].unique().tolist()

    season = st.selectbox(label='Select Season', options=my_season_options)

    games_season, players_season = get_season_data(
        games=games, players=players, season=season
    )

    my_game_options = games_season['LABEL'].unique().tolist()
    game_select = st.selectbox(label='Select Game', options=my_game_options)
    
    this_game = get_selected_game(
        games_season=games_season, game_select=game_select
    )

    data_columns = game_summary_data.columns.tolist()
    player_values = players_season['NUMBER'].tolist()
    game_list = game_summary_data['GAME_ID'].unique().tolist()

    if this_game['GAME_ID'].values[0] in game_list:
        update_frame = game_summary_data[
            game_summary_data['GAME_ID'] == this_game['GAME_ID'].values[0]
        ]
    else:
        update_frame = pd.DataFrame(columns=data_columns)
        update_frame['PLAYER_ID'] = player_values
        update_frame['GAME_ID'] = this_game['GAME_ID'].values[0]

    update_frame = update_frame.reset_index(drop=True)
    save = st.button(label='Save')
    update = st.button(label='Update')
    edited_df = st.data_editor(
        data=update_frame,  num_rows='dynamic', key='game_summary_editor',
        hide_index=True, use_container_width=True
    )
    data = edited_df.copy()
    if save:
        data = data.fillna(0)
        game_summary_ids = pd.DataFrame(data=list(game_summary_db.find()))
        game_summary_ids_list = game_summary_ids['_id'].unique().tolist()
        data['_id'] = (
            data['PLAYER_ID'].astype(str).str.replace('.0', '', regex=False)
            + '_' 
            + data['GAME_ID'].astype(str).str.replace('.0', '', regex=False)
        )
        new_data = data[~data['_id'].isin(game_summary_ids_list)]
        if len(new_data) > 0:
            data_list = new_data.to_dict('records')
            game_summary_db.insert_many(
                documents=data_list, bypass_document_validation=True
            )
        update_data = data[data['_id'].isin(game_summary_ids_list)]
        data_list = update_data.to_dict('records')
        for doc in data_list:
            game_summary_db.update_one(
                filter={'_id': doc['_id']}, update={"$set": doc}, upsert=True
            )    
        st.write('Added to DB!')
        time.sleep(2)
        st.rerun()