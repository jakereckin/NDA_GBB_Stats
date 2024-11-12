import streamlit as st
import datetime as dt
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pages.functions import utils as ut
from PIL import Image
import streamlit as st
pd.options.mode.chained_assignment = None


st.session_state.temp_df = []
st.header(body='NDA GBB Analytics', divider='blue')
image = Image.open(fp='NDA_LOGO.jpg')
st.image(image=image)