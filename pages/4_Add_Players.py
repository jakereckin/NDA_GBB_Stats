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
save = st.button('Save')
edited_df = st.data_editor(players, 
                           num_rows='dynamic', 
                           key='data_editor')
if save:
    conn.update(worksheet='players',
                data=edited_df
    )
    st.write('Added to DB!')
    st.cache_data.clear()
    st.rerun()