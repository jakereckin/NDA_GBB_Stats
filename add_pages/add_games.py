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
games = load_data()
games = games.sort_values(by='SEASON', ascending=False).reset_index(drop=True)
seasons = games['SEASON'].unique().tolist()

selected_season = st.radio(
    label='Select Season',
    options=seasons,
    horizontal=True
)

games = (
    games[games['SEASON'] == selected_season]
    .sort_values(by='GAME_ID', ascending=True)
    .reset_index(drop=True)
)

st.write(f'*Last Game in DB for {selected_season}*')
last_game = games.tail(1)
st.write(
    f'{last_game['GAME_ID'].values[0]} - {last_game['OPPONENT'].values[0]}'
)

if selected_season:
    with st.form(key='add_games'):
        left_row_one, right_row_one = st.columns(2)
        left_row_two, middle_row_two, right_row_two = st.columns(3)

        with left_row_one:
            game_id = st.text_input(
                label='Game ID', placeholder='Enter Game ID'
            )
        with right_row_one:
            opponent = st.text_input(
                label='Opponent', placeholder='Enter Opponent'
            )

        with left_row_two:
            location = st.text_input(
                label='Location', placeholder='Enter Home/Away/Neutral'
            )
        
        with middle_row_two:
            date = st.text_input(
                label='Date',
                placeholder='Enter Date (MM/DD/YYYY)',
                value=pd.to_datetime('today').strftime('%m/%d/%Y'),
            )
        with right_row_two:
            season = st.text_input(
                label='Season',
                placeholder='Enter Season',
                value=selected_season
            )

        save_col, delete_col = st.columns(2)
        with save_col:
            save = st.form_submit_button(label='Add Game', key='add_game_btn')
        with delete_col:
            delete = st.form_submit_button(label='Delete Game', key='delete_game_btn')

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
                        str(season),
                    ),
                )
                conn.commit()
            st.success('Game Added')
            st.write(f'Added {opponent} to DB')
            time.sleep(0.5)
            st.rerun()

        if delete:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                st.write(f'Deleting Game {str(game_id)} from DB')
                cursor.execute(
                    sql=sql.delete_game_sql(),
                    parameters=(str(game_id),),
                )
                conn.commit()
            st.success('Game Deleted')
            time.sleep(0.5)
            st.rerun()
