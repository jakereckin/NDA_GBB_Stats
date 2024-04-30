import streamlit as st
import datetime as dt
import sys
import time
import sys
import numpy as np
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None

@st.cache_resource()
def load_data():
    conn = st.connection("gsheets", 
                        type=GSheetsConnection
    )
    players = conn.read(worksheet='players')
    games = conn.read(worksheet='games')
    games['SEASON'] = (games['SEASON'].astype('str')
                                      .str
                                      .replace('.0', 
                                               '', 
                                               regex=False)
    )
    players['SEASON'] = (players['SEASON'].astype('str')
                                          .str
                                          .replace('.0',
                                                   '',
                                                   regex=False)
    )
    game_summary_data = conn.read(worksheet='game_summary')
    return conn, players, games, game_summary_data

@st.cache_data
def get_season_data(games,
                    players,
                    season):
    games_season = games[games['SEASON']==season]
    players_season = players[players['YEAR']==season]
    games_season['LABEL'] = (games_season['OPPONENT']
                            + ' - '
                            + games_season['DATE']
    )
    return games_season, players_season

@st.cache_data
def get_selected_game(games_season,
                      game_select):
    game_val_opp = game_select.split(' - ')[0]
    game_val_date = game_select.split(' - ')[1]
    this_game = games_season[(games_season['OPPONENT']==game_val_opp)
                                & (games_season['DATE']==game_val_date)]
    return this_game

password = st.text_input(label='Password',
                         type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    conn, players, games, game_summary_data = load_data()

    season = st.selectbox(label='Select Season',
                        options=games['SEASON'].unique().tolist()
    )
    games_season, players_season = get_season_data(games=games,
                                                players=players,
                                                season=season
    )
    game_select = st.selectbox(label='Select Game',
                            options=games_season['LABEL'].unique().tolist()
    )
    this_game = get_selected_game(games_season=games_season,
                                game_select=game_select
    )

    data_columns = game_summary_data.columns.tolist()
    player_values = players_season['NUMBER'].tolist()

    if this_game['GAME_ID'].values[0] in (game_summary_data['GAME_ID'].unique().tolist()):
        update_frame = game_summary_data[game_summary_data['GAME_ID']==this_game['GAME_ID'].values[0]]
    else:
        update_frame = pd.DataFrame(columns=data_columns)
        update_frame['PLAYER_ID'] = player_values
        update_frame['GAME_ID'] = this_game['GAME_ID'].values[0]

    edited_df = st.data_editor(update_frame, 
                            num_rows='dynamic', 
                            key='data_editor'
    )
    data = edited_df.copy()
    save = st.button('Save')
    if save:
        data = data.fillna(0)
        all_data = (pd.concat([game_summary_data,
                            data])
                    .drop_duplicates(subset=['PLAYER_ID',
                                            'GAME_ID'],
                                    keep='last')
                    .reset_index(drop=True)
        )
        conn.update(worksheet='game_summary',
                    data=all_data)          
        st.write('Added to DB!')
        st.cache_data.clear()
        st.rerun()