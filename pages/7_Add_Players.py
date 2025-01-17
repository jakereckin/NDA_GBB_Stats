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
    players_db = my_db['PLAYERS']
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    return players_db, players


# ----------------------------------------------------------------------------
def load_data():
    client = get_client()
    players_db, players = get_my_db(client)
    players = (
        players.sort_values(by=['YEAR', 'NUMBER']).reset_index(drop=True)
    )
    return players_db, players


password = st.text_input(label='Password', type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    players_db, players = load_data()
    save = st.button(label='Save')
    delete = st.button(label='Delete Game')
    players.insert(loc=0, column='SELECT', value=False)
    players[['YEAR', 'NUMBER']] = (
        players[['YEAR', 'NUMBER']].astype(dtype='int32')
    )
    edited_df = st.data_editor(
        data=players, num_rows='dynamic', key='new_players',
        use_container_width=True, hide_index=True,
        column_config={
            'SELECT': st.column_config.CheckboxColumn(required=False)
        } 
    )
    if save:
        if st.session_state['new_players'].get('edit_rows') != {}:
            check_player = pd.merge(
                left=players.drop(columns=['SELECT']),
                right=edited_df.drop(columns=['SELECT']),
                on=['NUMBER', 'FIRST_NAME', 'LAST_NAME', 'YEAR'],
                how='outer', indicator='exists'
            )
            my_df = (
                check_player[check_player['exists'] == 'right_only']
                            .drop(columns=['exists'])
            )
            my_df['_id'] = (
                my_df['FIRST_NAME'].astype(dtype=str).str.replace(pat='.0',
                                                                  repl='',
                                                                  regex=False)
                + '_' + my_df['LAST_NAME'] + '_'
                + my_df['YEAR'].astype(dtype=str).str.replace(pat='.0',
                                                                          repl='',
                                                                          regex=False)
            )
            data_list = my_df.to_dict(orient='records')
            players_db.insert_many(
                documents=data_list, bypass_document_validation=True
            )
            my_players_add = my_df['LAST_NAME'].tolist()
            st.write(f'Added {my_players_add} to DB')

    if delete:
        selected_rows = edited_df[edited_df.SELECT]
        if len(selected_rows)==0:
            st.write('Must Select Player to Delete')
        if len(selected_rows) > 1:
            st.write('Can Only Delete One Row at a Time!!!')
        else:
            delete_player = selected_rows.copy().drop(columns=['SELECT'])
            delete_player['_id'] = (
                delete_player['FIRST_NAME'].astype(dtype=str).str.replace(pat='.0',
                                                                          repl='',
                                                                          regex=False)
                + '_' + delete_player['LAST_NAME'] + '_'
                + delete_player['YEAR'].astype(dtype=str).str.replace(pat='.0',
                                                                          repl='',
                                                                          regex=False)
            )
            data_list = delete_player.to_dict(orient='records')[0]
            players_db.delete_many(filter=data_list)
            st.write('Player Deleted')
            time.sleep(.5)
            st.rerun()