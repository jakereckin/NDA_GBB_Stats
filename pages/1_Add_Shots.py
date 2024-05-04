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
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut

@st.cache_resource
def load_data():
    conn = st.connection("gsheets", 
                        type=GSheetsConnection
    )
    players = conn.read(worksheet='players')
    games = conn.read(worksheet='games')
    players['YEAR'] = (players['YEAR'].astype('str')
                                      .str
                                      .replace('.0',
                                               '',
                                               regex=False)
    )
    spots = conn.read(worksheet='spots')
    games['SEASON'] = (games['SEASON'].astype('str')
                                      .str
                                      .replace('.0', 
                                               '', 
                                               regex=False)
    )
    all_plays = conn.read(worksheet='play_event')
    games['LABEL'] = (games['OPPONENT']
                 + ' - '
                 + games['DATE']
    )
    players['LABEL'] = (players['NUMBER'].astype('str')
                        + ' - '
                        + players['FIRST_NAME']
    )
    return conn, players, games, spots, all_plays


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

def get_values_needed(game_val,
                      game):
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

password = st.text_input(label='Password',
                         type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    conn, players, games, spots, all_plays = load_data()
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
    game = get_selected_game(games_season=games_season,
                                game_select=game_select
    )
    with st.form('Play Event', 
                clear_on_submit=False):
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
                            options=['Y', 
                                    'N'],
                            horizontal=True
        )
        shot_defense = st.radio(label='Shot Defense',
                                options=['OPEN', 
                                        'GUARDED', 
                                        'HEAVILY_GUARDED'],
                                horizontal=True
        )
        add = st.form_submit_button("Add Play")
        final_add = st.form_submit_button('Final Submit')
        if add:
            time.sleep(.5)
            player_number, game_val_final = get_values_needed(game_val=game_val,
                                                            game=game
            )
            test_make = np.where(make_miss=='Y',
                                 'Make',
                                 'Miss')
            st.text(f'Submitted {test_make} by {player_number} from {spot_val} with defense {shot_defense}')
            my_df = create_df(game_val_final=game_val_final, 
                            player_number=player_number, 
                            spot_val=spot_val,
                            shot_defense=shot_defense,
                            make_miss=make_miss
            )
            st.session_state.temp_df.append(my_df)
            st.dataframe(my_df)
        if final_add:
            final_temp_df = pd.concat(st.session_state.temp_df,
                                    axis=0
            )
            all_data = (pd.concat([final_temp_df,
                                all_plays])
                        .reset_index(drop=True)
            )
            conn.update(worksheet='play_event',
                        data=all_data
            )
            st.write('Added to DB!')
            time.sleep(.5)
            st.cache_data.clear()
            st.session_state.temp_df = []