import streamlit as st
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None


def load_data():
    conn = st.connection('gsheets', 
                         type=GSheetsConnection
    )
    games = conn.read(worksheet='games')
    return conn, games

conn, games = load_data()
save = st.button('Save')
edited_df = st.data_editor(games, 
                           num_rows='dynamic', 
                           key='data_editor'
)
if save:
    conn.update(data=edited_df,
                worksheet='games'
    )
    st.write('Added to DB!')
    time.sleep(2)
    st.rerun()