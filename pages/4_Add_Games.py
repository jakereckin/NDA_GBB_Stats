import streamlit as st
import time
import pandas as pd
import sqlitecloud
from py import sql, data_source
pd.options.mode.chained_assignment = None


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
def load_data():
    games = data_source.run_query(
        sql=sql.get_games_sql(), connection=sql_lite_connect
    )
    return games


# ----------------------------------------------------------------------------
password = st.text_input(label='Password',type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    games = load_data()
    games = games.sort_values(by='SEASON', ascending=False).reset_index(drop=True)
    seasons = games['SEASON'].unique().tolist()
    selected_season = st.selectbox(
        label='Select Season',
        options=seasons
    )
    games = (
        games[games['SEASON'] == selected_season]
             .sort_values(by='GAME_ID', ascending=True)
             .reset_index(drop=True)
    )
    st.write(f'Games in DB for {selected_season}')
    st.dataframe(data=games, use_container_width=True)
    if selected_season:
        game_id = st.text_input(
            label='Game ID',
            placeholder='Enter Game ID'
        )
        opponent = st.text_input(
            label='Opponent',
            placeholder='Enter Opponent'
        )
        location = st.text_input(
            label='Location',
            placeholder='Enter Home/Away/Neutral'
        )
        date = st.text_input(
            label='Date',
            placeholder='Enter Date (MM/DD/YYYY)',
            value=pd.to_datetime('today').strftime('%m/%d/%Y')
        )
        season = st.text_input(
            label='Season',
            placeholder='Enter Season',
            value=selected_season
        )
        save_col, delete_col = st.columns(spec=2)
        with save_col:
            save = st.button(label='Add Game')
        with delete_col:
            delete = st.button(label='Delete Game')
        if save:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.insert_game_sql(),
                    parameters=(
                        str(game_id),
                        str(opponent),
                        str(location),
                        str(date),
                        str(season)
                        )
                    )
                conn.commit()
            st.write('Games Added') 
            st.write(f'Added {opponent} to DB')
            time.sleep(.5)
            st.write('Reloading...')
            st.rerun()

    if delete:
        with sqlitecloud.connect(sql_lite_connect) as conn:
            cursor = conn.cursor()
            st.write(f'Deleting Game {str(game_id)} from DB')
            cursor.execute(
                sql=sql.delete_game_sql(),
                parameters=(
                    str(game_id)
                )
            )
            conn.commit()
        st.write('Game Deleted')
        time.sleep(.5)
        st.rerun()