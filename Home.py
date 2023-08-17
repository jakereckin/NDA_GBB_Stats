import streamlit as st
import datetime as dt
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pages.functions import utils as ut
import streamlit as st


conn = ut.create_db()
st.header('WELCOME EVERYONE')
st.dataframe(ut.select_players(conn),
             use_container_width=True,
             hide_index=True)
#conn.ad