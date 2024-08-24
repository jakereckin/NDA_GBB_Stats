import streamlit as st
import sys
import time
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from functions import utils as ut
pd.options.mode.chained_assignment = None


# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client


# ----------------------------------------------------------------------------
def get_my_db(client):
    my_db = client['NDA_GBB']
    games_db = my_db['GAMES']
    games = pd.DataFrame(list(games_db.find())).drop(columns=['_id'])
    return games_db, games


# ----------------------------------------------------------------------------
def load_data():

    client = get_client()
    games_db, games = get_my_db(client=client)
    games['SEASON'] = (games['SEASON'].astype('str')
                                      .str
                                      .replace('.0', 
                                               '', 
                                               regex=False)
    )
    return games_db, games


# ----------------------------------------------------------------------------
password = st.text_input(label='Password',type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    games_db, games = load_data()
    save = st.button('Save')
    delete = st.button('Delete Game')
    games.insert(0, "SELECT", False)
    games = games.sort_values(by='GAME_ID').reset_index(drop=True)
    edited_df = st.data_editor(
        games, 
        num_rows='dynamic', 
        key='new_games',
        use_container_width=True,
        hide_index=True,
        column_config={
            "SELECT": st.column_config.CheckboxColumn(required=False)
        }
    )
    if save:
        if st.session_state['new_games'].get('edit_rows') != {}:
            check_spot = pd.merge(games.drop(columns=['SELECT']),
                                  edited_df.drop(columns=['SELECT']),
                                  on=['GAME_ID', 
                                      'OPPONENT', 
                                      'LOCATION', 
                                      'DATE',
                                      'SEASON'],
                                  how='outer',
                                  indicator='exists'
            )
            my_df = (
                check_spot[check_spot['exists']=='right_only']
                .drop(columns=['exists'])
            )
            my_df['_id'] = (
                my_df['GAME_ID'].astype(str).str.replace('.0', '', regex=False)
                + '_' 
                + my_df['OPPONENT']
            )
            data_list = my_df.to_dict('records')
            games_db.insert_many(data_list, bypass_document_validation=True)
            my_games_add = my_df['OPPONENT'].tolist()
            st.write(f'Added {my_games_add} to DB')

    if delete:
        selected_rows = edited_df[edited_df.SELECT]
        if len(selected_rows)==0:
            st.write('Must Select Games to Delete')
        if len(selected_rows) > 1:
            st.write('Can Only Delete One Row at a Time!!!')
        else:
            delete_games = selected_rows.copy().drop(columns=['SELECT'])
            delete_games['_id'] = (
                delete_games['GAME_ID'].astype(str).str.replace('.0', 
                                                                '', 
                                                                regex=False)
                + '_' 
                + delete_games['OPPONENT']
            )
            data_list = delete_games.to_dict('records')[0]
            games_db.delete_many(data_list)
            st.write('Game Deleted')
            time.sleep(.5)
            st.rerun()