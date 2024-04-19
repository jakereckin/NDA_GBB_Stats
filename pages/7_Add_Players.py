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

SELECT_PLAYERS = """
SELECT *
  FROM PLAYERS
"""
INSERT_PLAYERS = """
INSERT OR REPLACE INTO PLAYERS VALUES(?, ?, ?, ?) 
"""

DELETE_PLAYERS = """
DELETE FROM PLAYERS 
WHERE NUMBER = ?
AND YEAR = ?
"""
#conn = st.connection("gsheets", type=GSheetsConnection)
#players = conn.read(worksheet='players')
my_db = ut.create_db()

with sql.connect(my_db) as nda_db:
    players = pd.read_sql(SELECT_PLAYERS, con=nda_db)

players = players.sort_values(by=['YEAR', 'NUMBER'])
save = st.button('Save')
edited_df = st.data_editor(players, 
                           num_rows='dynamic', 
                           key='data_editor')
if save:
    check_both = pd.merge(players,
                          edited_df,
                          on=['NUMBER',
                              'FIRST_NAME',
                              'LAST_NAME',
                              'YEAR'],
                          how='outer',
                          indicator='exists')
    delete = check_both[check_both['exists']=='left_only']
    add_to = check_both[check_both['exists']=='right_only']
    st.write(check_both)
    with sql.connect(my_db) as nda_db:
        cursor = nda_db.cursor()
        if len(add_to) > 0:
            st.write(add_to)
            player_tuple = list(zip(add_to['NUMBER'].astype(str).values,
                            add_to['FIRST_NAME'].values, 
                            add_to['LAST_NAME'].values,
                            add_to['YEAR'].astype(str).values)
            )
            cursor.executemany(INSERT_PLAYERS, player_tuple)
        if len(delete) > 0:
            delete_tuple = list(zip(delete['NUMBER'],
                                    delete['YEAR'])
            )
            cursor.executemany(DELETE_PLAYERS, delete_tuple)
        if (len(delete)>0)|(len(add_to)>0):
            nda_db.commit()
   # print(edited_df.)
   # st.cache_data.clear()
    st.write('Added to DB!')
    time.sleep(5)
    st.rerun()