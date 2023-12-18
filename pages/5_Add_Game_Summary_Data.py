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

conn = st.connection("gsheets", type=GSheetsConnection)
players = conn.read(worksheet='players')
games = conn.read(worksheet='games')
game_summary_data = conn.read(worksheet='game_summary')

season = st.selectbox(label='Select Season',
                      options=games['SEASON'].unique().tolist()
)
games_season = games[games['SEASON']==season]
players_season = players[players['YEAR']==season]
games_season['LABEL'] = (games_season['OPPONENT']
                         + ' - '
                         + games_season['DATE']
)
game_select = st.selectbox(label='Select Game',
                           options=games_season['LABEL'].unique().tolist()
)
game_val_opp = game_select.split(' - ')[0]
game_val_date = game_select.split(' - ')[1]
game_val_this = games_season[(games_season['OPPONENT']==game_val_opp)
                             & (games_season['DATE']==game_val_date)]

data_columns = game_summary_data.columns.tolist()
player_values = players_season['NUMBER'].tolist()

if game_val_this['GAME_ID'].values[0] in (game_summary_data['GAME_ID'].unique().tolist()):
    update_frame = game_summary_data[game_summary_data['GAME_ID']==game_val_this['GAME_ID'].values[0]]
else:
    update_frame = pd.DataFrame(columns=data_columns)
    update_frame['PLAYER_ID'] = player_values
    update_frame['GAME_ID'] = game_val_this['GAME_ID'].values[0]

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