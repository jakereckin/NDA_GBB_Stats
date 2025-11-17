import streamlit as st
import time
import pandas as pd
import sqlitecloud
from py import sql, data_source
pd.options.mode.chained_assignment = None


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

# ----------------------------------------------------------------------------
def load_data():
    players = data_source.run_query(
        sql=sql.get_players_sql(), connection=sql_lite_connect
    )
    return players

players = load_data()
seasons = players['YEAR'].unique().tolist()
selected_season = st.selectbox(
    label='Select Season',
    placeholder='Enter Season',
    options=seasons
)
add_new_season = st.text_input('Or Add New Season')

if add_new_season != '':
    selected_season = add_new_season
players = players[players['YEAR'] == selected_season]
st.write(f'Players in DB for {selected_season}')
st.dataframe(data=players, use_container_width=True)
if selected_season:

    with st.form(key='player_form'):
        left, middle, right = st.columns(3)

        with left:
            number = st.text_input(
                label='Player Number',
                placeholder='Enter Player Number'
            )
        
        with middle:
            first_name = st.text_input(
                label='First Name',
                placeholder='Enter First Name'
            )
        
        with right:
            last_name = st.text_input(
                label='Last Name',
                placeholder='Enter Last Name'
            )
        save_col, delete_col = st.columns(spec=2)
        with save_col:
            save = st.form_submit_button(label='Add Player', key='add_player')
        with delete_col:
            delete = st.form_submit_button(label='Delete Player', key='delete_player')
        if save:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.insert_player_sql(),
                    parameters=(
                        str(number),
                        str(first_name),
                        str(last_name),
                        str(selected_season)
                    )
                )
                conn.commit()
            st.write('Players Added') 
            st.write(f'Added {last_name} to DB')
            time.sleep(.5)
            st.write('Reloading...')
            st.rerun()

        if delete:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.delete_player_sql(),
                    parameters=(
                        str(number),
                        str(selected_season)
                    )
                )
                conn.commit()
            st.write('Player Deleted')
            time.sleep(.5)
            st.rerun()
