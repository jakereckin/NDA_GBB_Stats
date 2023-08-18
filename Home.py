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

st.header('NDA GBB Statcast')
st.subheader('Created by Jake Reckin')
st.caption('Jake is the VP of Deep Basketball Analytics (title pending)')
conn = ut.create_db()
spots = ['LB2', 
         'RB2', 
         'ML2', 
         'FT2', 
         'LE2', 
         'RE2', 
         'LMR2', 
         'RMR2', 
         'LC3', 
         'RC3', 
         'LW3', 
         'RW3', 
         'TK3']
x = [65, 
     -65,
     0, 
     0, 
     65, 
     -65,
    95, 
    -95, 
    -225, 
    225, 
    -150, 
    150, 
    0
]
y = [0, 
     0, 
     30, 
     150, 
     150, 
     150, 
     75, 
     75, 
     0, 
     0, 
     175, 
     175, 
     225
]
data = pd.DataFrame(list(zip(spots, x, y)), columns=['SPOTS', 'XSPOT', 'YSPOT'])
data_row = list(zip(data['SPOTS'], data['XSPOT'], data['YSPOT']))
ut.drop_spots(conn)
ut.create_shot_spots(conn)
ut.insert_spot(conn, data_row)
df = ut.select_spot(conn)
print(df)
#conn.ad