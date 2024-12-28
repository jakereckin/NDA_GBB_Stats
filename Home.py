import streamlit as st
import pandas as pd
from PIL import Image
pd.options.mode.chained_assignment = None


st.session_state.temp_df = []
st.header(body='NDA GBB Analytics', divider='blue')
image = Image.open(fp='NDA_LOGO.jpg')
st.image(image=image)