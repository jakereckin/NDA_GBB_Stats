import streamlit as st
import time
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None


# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(host=uri, server_api=ServerApi(version='1'))
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
    games['SEASON'] = (
        games['SEASON'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False)
    )
    return games_db, games


# ----------------------------------------------------------------------------
password = st.text_input(label='Password',type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    games_db, games = load_data()
    save = st.button(label='Save')
    delete = st.button(label='Delete Game')
    games.insert(loc=0, column="SELECT", value=False)
    games = games.sort_values(by='GAME_ID').reset_index(drop=True)
    games['SEASON'] = games['SEASON'].astype(dtype='int64')
    edited_df = st.data_editor(
        data=games, num_rows='dynamic', key='new_games',
        use_container_width=True, hide_index=True,
        column_config={
            "SELECT": st.column_config.CheckboxColumn(required=False)
        }
    )
    if save:
        if st.session_state['new_games'].get('edit_rows') != {}:
            check_spot = pd.merge(
                left=games.drop(columns=['SELECT']),
                right=edited_df.drop(columns=['SELECT']),
                on=['GAME_ID', 'OPPONENT', 'LOCATION', 'DATE', 'SEASON'],
                how='outer', indicator='exists'
            )
            my_df = (
                check_spot[check_spot['exists'] == 'right_only']
                .drop(columns=['exists'])
            )
            my_df['_id'] = (
                my_df['GAME_ID'].astype(dtype=str).str.replace(pat='.0', 
                                                               repl='', 
                                                               regex=False)
                + '_' + my_df['OPPONENT']
            )
            data_list = my_df.to_dict(orient='records')
            games_db.insert_many(
                documents=data_list, bypass_document_validation=True
            )
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
                delete_games['GAME_ID'].astype(dtype=str).str.replace(pat='.0', 
                                                                      repl='', 
                                                                      regex=False)
                + '_' 
                + delete_games['OPPONENT']
            )
            data_list = delete_games.to_dict(orient='records')[0]
            games_db.delete_many(filter=data_list)
            st.write('Game Deleted')
            time.sleep(.5)
            st.rerun()
