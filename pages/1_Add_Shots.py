import streamlit as st
import datetime as dt
import sys
import time
import sys
import numpy as np
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
pd.options.mode.chained_assignment = None
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from functions import utils as ut

@st.cache_resource
def get_client():
    uri =  f"mongodb+srv://nda-gbb-admin:{st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client

def get_my_db(client):
    my_db = client['NDA_GBB']
    plays_db = my_db['PLAYS']
    spots_db = my_db['SPOTS']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    plays = pd.DataFrame(list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(list(players_db.find())).drop(columns=['_id'])
    players = players[players['YEAR']==2024]
    return plays, spots, games, players, plays_db

def load_data():
    client = get_client()
    all_plays, spots, games, players, plays_db = get_my_db(client=client)
    players['YEAR'] = (players['YEAR'].astype('str')
                                      .str
                                      .replace('.0',
                                               '',
                                               regex=False)
    )
    games['SEASON'] = (games['SEASON'].astype('str')
                                      .str
                                      .replace('.0', 
                                               '', 
                                               regex=False)
    )
    games['LABEL'] = games['OPPONENT'] + ' - ' + games['DATE']

    players['LABEL'] = (players['NUMBER'].astype('str')
                        + ' - '
                        + players['FIRST_NAME']
    )
    return plays_db, players, games, spots, all_plays


@st.cache_data
def get_season_data(games, players, season):
    games_season = games[games['SEASON']==season]
    games_season['DATE_DTTM'] = pd.to_datetime(games_season['DATE'])
    games_season = games_season.sort_values(by='DATE_DTTM')
    players_season = players[players['YEAR']==season]
    games_season['LABEL'] = (games_season['OPPONENT']
                            + ' - '
                            + games_season['DATE']
    )
    return games_season, players_season

@st.cache_data
def get_selected_game(games_season, game_select):
    game_val_opp = game_select.split(' - ')[0]
    game_val_date = game_select.split(' - ')[1]
    this_game = games_season[(games_season['OPPONENT']==game_val_opp)
                             & (games_season['DATE']==game_val_date)]
    return this_game

def get_values_needed(game_val, game):
    game_val_opp = game_val.split(' - ')[0]
    game_val_date = game_val.split(' - ')[1]
    game_val_this = game[(game['OPPONENT']==game_val_opp)
                         & (game['DATE']==game_val_date)]
    player_number = player_val.split(' - ')[0]
    game_val_final = game_val_this['GAME_ID'].values[0]
    return player_number, game_val_final

def create_df(game_val_final, 
              player_number, 
              spot_val, 
              shot_defense, 
              make_miss):
    this_data = [game_val_final, 
                 player_number, 
                 spot_val,
                 shot_defense,
                 make_miss
    ]
    my_df = pd.DataFrame(data=[this_data],
                         columns=['GAME_ID', 
                                  'PLAYER_ID', 
                                  'SHOT_SPOT', 
                                  'SHOT_DEFENSE',
                                  'MAKE_MISS']
    )
    return my_df

password = st.text_input(label='Password', type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    plays_db, players, games, spots, all_plays = load_data()

    season_list = games['SEASON'].unique().tolist()

    season = st.selectbox(label='Select Season', options=season_list)

    games_season, players_season = get_season_data(games=games,
                                                players=players,
                                                season=season
    )

    game_list = games_season['LABEL'].unique().tolist()
    game_select = st.selectbox(label='Select Game', options=game_list)
    game = get_selected_game(games_season=games_season,
                                game_select=game_select
    )
    with st.form('Play Event', clear_on_submit=False):
        game_val = game['LABEL'].values[0]
        player_val = st.radio(label='Player',
                            options=players_season['LABEL'],
                            horizontal=True
        )
        spot_val = st.radio(label='Shot Spot',
                            options=spots['SPOT'],
                            horizontal=True
        )
        make_miss = st.radio(label='Make/Miss',
                            options=['Y', 'N'],
                            horizontal=True
        )
        shot_defense = st.radio(label='Shot Defense',
                                options=['OPEN', 
                                        'GUARDED', 
                                        'HEAVILY_GUARDED'],
                                horizontal=True
        )
        add = st.form_submit_button('Add Play')
        if add:
            time.sleep(.5)
            player_number, game_val_final = get_values_needed(game_val=game_val,
                                                            game=game
            )
            test_make = np.where(make_miss=='Y', 'Make', 'Miss')
            st.text(f'Submitted {test_make} by {player_number} from {spot_val} with defense {shot_defense} for {game_val_final}')
            my_df = create_df(game_val_final=game_val_final, 
                            player_number=player_number, 
                            spot_val=spot_val,
                            shot_defense=shot_defense,
                            make_miss=make_miss
            )
            all_data_game = all_plays[all_plays['GAME_ID']==game_val_final]
            if len(all_data_game)==0:
                my_df['PLAY_NUM'] = 1
            else:
                current_play = len(all_data_game)
                my_df['PLAY_NUM'] = current_play
            
            current_game = pd.concat([all_data_game, my_df])
            current_play_dict = my_df.to_dict('records')
            plays_db.insert_many(current_play_dict, bypass_document_validation=True)
            st.write(f'Added to DB, {len(current_game)} shots in DB for game {game_val_final}')
            #conn.update(worksheet='play_event',
            #            data=all_data
            #)
            #st.write('Added to DB!')
            #time.sleep(.5)
            #st.cache_data.clear()
            #st.session_state.temp_df = []