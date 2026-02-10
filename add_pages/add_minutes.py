import streamlit as st
import pandas as pd
import time
import numpy as np
import sqlitecloud
from py import sql, data_source, utils as ut
pd.options.mode.chained_assignment = None

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

# ----------------------------------------------------------------------------
@st.cache_resource
def load_data():
    players = data_source.run_query(
        sql=sql.get_players_sql(), connection=sql_lite_connect
    )
    players = players[players['NUMBER'] != '0']
    games = data_source.run_query(
        sql=sql.get_games_sql(), connection=sql_lite_connect
    )
    return players, games

# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(games, players, season):

    games_season = games[games['SEASON'] == season]
    players_season = players[players['YEAR'] == season]

    games_season['LABEL'] = (
        games_season['OPPONENT'] + ' - ' + games_season['DATE']
    )
    games_season['DATE_DTTM'] = pd.to_datetime(games_season['DATE'])
    games_season = games_season.sort_values(by='DATE_DTTM', ascending=False)
    return games_season, players_season

# ----------------------------------------------------------------------------
@st.cache_data
def get_selected_game(games_season, game_select):
    game_val_opp = game_select.split(' - ')[0]
    game_val_date = game_select.split(' - ')[1]
    this_game = games_season[
        (games_season['OPPONENT']==game_val_opp)
        & (games_season['DATE']==game_val_date)
    ]
    return this_game

# ----------------------------------------------------------------------------

players, games = load_data()

my_season_options = (
        games['SEASON'].sort_values(ascending=False).unique().tolist()
    )
st.title("⏱️ Add Minutes Played")
with st.form(key='minutes_form', clear_on_submit=False):
    season_col, game_col = st.columns(2)

    with season_col:
        season = st.radio(
            label='Select Season',
            options=my_season_options,
            horizontal=True,
        )

    games_season, players_season = get_season_data(
        games=games, players=players, season=season
    )
    players_season = players_season[players_season['NUMBER'] != 0]
    my_game_options = games_season['LABEL'].unique().tolist()

    with game_col:
        game_select = st.selectbox(
            label='Select Game', options=my_game_options
        )

    this_game = get_selected_game(
        games_season=games_season, game_select=game_select
    )
    player_values = (
        players_season['NUMBER'].astype(int).sort_values().tolist()
    )
    game_list = this_game['GAME_ID'].unique().tolist()

    player_val = st.radio(
        label='Select Player', options=player_values, horizontal=True
    )

    half_col, min_col, sec_col, team_score_in, opp_score_in = st.columns(5)
    with half_col:
        half = st.radio(
            label='Select Half Subbed In', options=[1, 2], horizontal=True
        )
    with min_col:
        minutes = st.number_input(
            label='Minutes Subbed In',
            min_value=0,
            max_value=18,
            value=0,
            step=1,
        )
    with sec_col:
        seconds = st.number_input(
            label='Seconds Subbed In',
            min_value=0,
            max_value=59,
            value=0,
            step=1,
        )
    with team_score_in:
        points_in = st.number_input(
            label='Team Points When Subbed In', min_value=0, value=0, step=1
        )
    with opp_score_in:
        opp_points_in = st.number_input(
            label='Opponent Points When Subbed In',
            min_value=0,
            value=0,
            step=1
        )
    second_half_col, second_min_col, second_sec_col, team_score_out, opp_score_out = st.columns(5)
    with second_half_col:
        half_out = st.radio(
            label='Select Half Subbed Out', options=[1, 2], horizontal=True
        )
    with second_min_col:
        minutes_out = st.number_input(
            label='Minutes Subbed Out',
            min_value=0,
            max_value=18,
            value=0,
            step=1,
        )
    with second_sec_col:
        seconds_out = st.number_input(
            label='Seconds Subbed Out',
            min_value=0,
            max_value=59,
            value=0,
            step=1,
        )

    with team_score_out:
        points_out = st.number_input(
            label='Team Points When Subbed Out', min_value=0, value=0, step=1
        )
    with opp_score_out:
        opp_points_out = st.number_input(
            label='Opponent Points When Subbed Out',
            min_value=0,
            value=0,
            step=1
        )


    add_minutes = st.form_submit_button(label='Add Minutes')
    if add_minutes:
        half_time = 18 * 60
        if half == 2:
            time_in = minutes * 60 + seconds
        else:
            half_time_in = minutes * 60 + seconds
            time_in = half_time + half_time_in

        if half_out == 2:
            time_out = minutes_out * 60 + seconds_out
        else:
            half_time_out = minutes_out * 60 + seconds_out
            time_out = half_time + half_time_out
        with sqlitecloud.connect(sql_lite_connect) as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql=sql.insert_minutes_sql(),
                parameters=(
                    str(game_list[0]),
                    str(player_val),
                    int(time_in),
                    int(time_out),
                    int(points_in),
                    int(points_out),
                    int(opp_points_in),
                    int(opp_points_out),
                ),
            )
            conn.commit()
        st.success(
            f'Minutes Added for Player {player_val} in Game {game_list[0]} '\
            f'from {time_in} seconds to {time_out} seconds with '\
            f'team points {points_in} to {points_out} and opponent points {opp_points_in} to {opp_points_out}.'
        )
