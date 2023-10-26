import streamlit as st
import datetime as dt
import sys
import time
import sys
import numpy as np
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut

conn = ut.create_db()
#ut.create_event(conn)
players = ut.select_players(conn)
players = players[players['YEAR']=='2023']
spots = ut.select_spot(conn)
game = ut.select_games(conn)
game['LABEL'] = (game['OPPONENT']
                 + ' - '
                 + game['DATE']
)
players['LABEL'] = (players['NUMBER']
                    + ' - '
                    + players['FIRST_NAME']
)
event_types = ['SHOT_ATTEMPT',
               'ASSIST',
               'BLOCK',
               'O_REBOUND',
               'D_REBOUND',
               'TURNOVER',
               'STEAL',
               'DEFLECTION',
               'HUSTLE_PLAY',
               'SUB_IN',
               'SUB_OUT',
               'DREW FOUL',
               'COMMIT FOUL'

]
half = ['FIRST HALF',
        'SECOND_HALF',
        'OT'
]
mins = (pd.DataFrame(data=[x for x in range(0, 21)],
                    columns=['MINS'])
          .assign(TMP='1')
)
secs = (pd.DataFrame(data=[x for x in range(0, 60)],
                     columns=['SECS'])
          .assign(TMP='1')
)
min_sec = (pd.merge(mins,
                    secs,
                    on='TMP',
                    how='inner')
)
min_sec['MIN_SEC'] = (min_sec['MINS'].astype('str')
                      + ':'
                      + min_sec['SECS'].astype('str')
)
min_sec_20 = (min_sec.head(1201)
                     .drop(columns=['MINS', 
                                    'TMP', 
                                    'SECS'])
)
min_list = min_sec_20['MIN_SEC'].unique().tolist()
st.set_page_config('Game Shots', initial_sidebar_state='expanded')
st.sidebar.header('Add Shots')

with st.form('Play Event', clear_on_submit=True):
    game_val = st.radio(label='Game',
                        options=reversed(game['LABEL']),
                        horizontal=True
    )
    player_val = st.radio(label='Player',
                          options=players['LABEL'],
                          horizontal=True
    )
    half_val = st.radio(label='Half',
                        options=half,
                        horizontal=True
    )
    min_val = st.select_slider(label='Time Left',
                           options=reversed(min_list)
    )
    event_val = st.radio(label='Play Type',
                         options=event_types,
                         horizontal=True
    )
    nda_val = st.slider(label='NDA Score',
                        min_value=0,
                        max_value=120
    )
    opp_val = st.slider(label='Opponent Score',
                        min_value=0,
                        max_value=120
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
    add = st.form_submit_button("Add To DB")
    if add:
        game_val_opp = game_val.split(' - ')[0]
        game_val_date = game_val.split(' - ')[1]
        game_val_this = game[(game['OPPONENT']==game_val_opp)
                             & (game['DATE']==game_val_date)]
        player_number = player_val.split(' - ')[0]
        game_val_final = game_val_this['GAME_ID'].values[0]
        st.text('Submitted!')
        this_data = [game_val_final, 
                     player_number, 
                     min_val,
                     half_val,
                     event_val,
                     nda_val,
                     opp_val,
                     spot_val,
                     shot_defense,
                     make_miss]
        my_df = pd.DataFrame(data=[this_data],
                             columns=['GAME', 
                                      'PLAYER', 
                                      'TIME',
                                      'HALF',
                                      'EVENT_TYPE',
                                      'TEAM_SCORE',
                                      'OPPONENT_SCORE',
                                      'SPOT', 
                                      'SHOT_DEFENSE',
                                      'MAKE_MISS'])
        data = list(zip(my_df['GAME'],
                        my_df['PLAYER'],
                        my_df['TIME'],
                        my_df['HALF'],
                        my_df['EVENT_TYPE'],
                        my_df['TEAM_SCORE'], 
                        my_df['OPPONENT_SCORE'], 
                        my_df['SPOT'],
                        my_df['SHOT_DEFENSE'],
                        my_df['MAKE_MISS'])
        )
        ut.insert_event(conn, data)