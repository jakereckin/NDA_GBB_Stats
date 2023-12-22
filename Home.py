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
pd.options.mode.chained_assignment = None


st.session_state.temp_df = []
st.header('NDA GBB Statcast')
st.subheader('Created by Jake Reckin')
st.caption('Jake is the VP of Deep Basketball Analytics/4th Grade Coach/Katelyn\'s Boyfriend (title pending)')