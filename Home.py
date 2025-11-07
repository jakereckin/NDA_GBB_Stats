import streamlit as st
import pandas as pd
from py import sql, data_source
from PIL import Image
import sqlitecloud
pd.options.mode.chained_assignment = None


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

st.set_page_config(page_title='NDA GBB Analytics')
st.session_state.temp_df = []
users = data_source.run_query(sql.get_users(), sql_lite_connect)


st.markdown(
    body="<h1 style='text-align: center; color: blue;'>NDA GBB Analytics</h1>", 
    unsafe_allow_html=True
)
#st.header(body='', divider='blue')
image = Image.open(fp='NDA_LOGO.jpg')
col1, col2, col3 = st.columns(3)
with col2:
    st.image(image=image)