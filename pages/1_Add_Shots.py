import streamlit as st
import datetime as dt
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut

conn = ut.create_db()
players = ut.select_players(conn)
spots = ut.select_spot(conn)
game = ut.select_games(conn)

st.set_page_config('Game Shots', initial_sidebar_state='expanded')
st.sidebar.header('Add Shots')

with st.form('Player Shot', clear_on_submit=True):
    game_val = st.radio(label='Game',
            options=game['OPPONENT'])
    player_val = st.radio(label='Player',
            options=players['NUMBER'])
    spot_val = st.radio(label='Shot Spot',
            options=spots['SPOT'])
    make_miss = st.radio(label='Make/Miss',
                         options=['Y', 'N'])
    add = st.form_submit_button("Add To DB")
    if add:
        st.text('Submitted!')
        this_data = [game_val, player_val, spot_val, make_miss]
        my_df = pd.DataFrame(data=[this_data],
                             columns=['GAME', 'PLAYER', 'SPOT', 'MAKE_MISS'])
        data = list(zip(my_df['GAME'], 
                        my_df['PLAYER'], 
                        my_df['SPOT'], 
                        my_df['MAKE_MISS'])
        )
        print(data)
        ut.insert_player_shot_spot(conn, data)