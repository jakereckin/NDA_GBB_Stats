import streamlit as st
import datetime as dt
import sys
import time
import sys
import numpy as np
import os
import pandas as pd
import sqlite3 as sql
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None

@st.cache_data
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    players = conn.read(worksheet='players')
    players = players.sort_values(by=['YEAR', 'NUMBER'])
    return conn, players

conn, players = load_data()
save = st.button('Save')
edited_df = st.data_editor(players, 
                           num_rows='dynamic', 
                           key='data_editor'
)
if save:
    conn.update(worksheet='players',
                data=edited_df
    )
    st.write('Added to DB!')
    time.sleep(2)
    st.rerun()