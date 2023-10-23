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
games = ut.select_games(conn)
save = st.button('Save')
edited_df = st.data_editor(games, 
                           num_rows='dynamic', 
                           key='data_editor')
data = pd.DataFrame(st.session_state['data_editor']['added_rows'])
if save:
    save_data = list(zip(data['GAME_ID'],
                         data['OPPONENT'],
                         data['LOCATION'],
                         data['DATE'],
                         data['SEASON'])
    )
    ut.insert_games(conn, save_data)
    st.write('Added to DB!')
    st.rerun() 