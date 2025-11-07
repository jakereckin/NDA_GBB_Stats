import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from PIL import Image
from py import utils, data_source, sql
import os
import time
import numpy as np


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
def load_data():
    """
    Loads and cleans data from the database.
    This function connects to the database, retrieves various
    datasets, and performs cleaning operations on specific
    columns to ensure data consistency.
    Returns:
        tuple: A tuple containing the following elements:
            - plays_db (DataFrame): The plays database.
            - players (DataFrame): The players data with cleaned
                'YEAR' and 'LABEL' columns.
            - games (DataFrame): The games data with cleaned
                'SEASON' and 'LABEL' columns.
            - spots (DataFrame): The spots data.
            - all_plays (DataFrame): All plays data.
    """
    pbp_data = data_source.run_query(
        sql=sql.get_play_sql(), connection=sql_lite_connect
    )
    return pbp_data

# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(
    pbp_data: pd.DataFrame, season: int
    ):
    """
    Extracts and processes game and player data for a specific season.

    Args:
        games (pd.DataFrame): DataFrame containing game data
            with at least 'SEASON', 'DATE', and 'OPPONENT' columns.
        players (pd.DataFrame): DataFrame containing player data
            with at least a 'YEAR' column.
        season (int): The season year to filter the data.

    Returns:
        tuple: A tuple containing two DataFrames:
            - games_season (pd.DataFrame): Filtered and processed
                game data for the specified season.
            - players_season (pd.DataFrame): Filtered player
                data for the specified season.
    """
    games_season = pbp_data[pbp_data['SEASON'] == season].copy()
    games_season['DATE_DTTM'] = pd.to_datetime(games_season['DATE'])
    return games_season


# ----------------------------------------------------------------------------
@st.cache_data
def get_selected_game(games_season, game_select):
    """
    Retrieve a specific game from the season's games
    based on the selected game.

    Args:
        games_season (pd.DataFrame): DataFrame containing
            the season's games data.
        game_select (str): A string in the format
            'Opponent Name - Game Date' used to select the game.

    Returns:
        pd.DataFrame: A DataFrame containing the
            data for the selected game.
    """
    opponent_name, game_date = game_select.split(' - ')
    this_game = games_season[
        (games_season['OPPONENT'] == opponent_name)
        & (games_season['DATE'] == game_date)
    ]
    return this_game


# ----------------------------------------------------------------------------
def get_values_needed(game_val, game, player_val):
    """
    Extracts and returns the player number and game ID
    based on the provided game and player values.

    Args:
        game_val (str): A string containing the opponent name
            and game date separated by ' - '.
        game (pd.DataFrame): A DataFrame containing game data
            with columns 'OPPONENT', 'DATE', and 'GAME_ID'.
        player_val (str): A string containing the player number
            and other player details separated by ' - '.

    Returns:
        tuple: A tuple containing the player number (str) and the game ID (int).
    """
    opponent_name, game_val_date = game_val.split(' - ')
    game_val_this = game[
        (game['OPPONENT'] == opponent_name) & (game['DATE'] == game_val_date)
    ]
    player_number = player_val.split(' - ')[0]
    game_val_final = game_val_this['GAME_ID'].values[0]
    return player_number, game_val_final


# ----------------------------------------------------------------------------
def create_df(
        game_val_final,
        player_number,
        spot_val,
        shot_defense,
        make_miss
        ) -> pd.DataFrame:
    """
        Creates a pandas DataFrame with the given shot data.

        Parameters:
        game_val_final (int or str): The game identifier.
        player_number (int or str): The player's identifier.
        spot_val (int or str): The shot spot identifier.
        shot_defense (int or str): The shot defense identifier.
        make_miss (int or str): Indicator if the shot was made or missed.

        Returns:
        pandas.DataFrame: 
            A DataFrame containing the shot data with columns 
            ['GAME_ID', 'PLAYER_ID', 'SHOT_SPOT', 
             'SHOT_DEFENSE', 'MAKE_MISS'].
    """
    this_data = [
        game_val_final, player_number, spot_val, shot_defense, make_miss
    ]
    col_names = [
        'GAME_ID', 'PLAYER_ID', 'SHOT_SPOT', 'SHOT_DEFENSE', 'MAKE_MISS'
    ]
    my_df = pd.DataFrame(data=[this_data], columns=col_names)
    return my_df


st.set_page_config(layout="wide")
# Load or create shot data
password = st.text_input(label='Password', type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    _shot_defenses = ['OPEN', 'GUARDED', 'HEAVILY_GUARDED']
    col1, col2 = st.columns(spec=2)
    pbp_data = load_data()
    games = (
        pbp_data.sort_values(by='SEASON', ascending=False).reset_index(drop=True)
    )
    season_list = games['SEASON'].unique().tolist()

    with col1:
        season = st.radio(
            label='Select Season', options=season_list, horizontal=True
        )

    games_season = get_season_data(pbp_data=pbp_data, season=season)

    game_list = games_season['GAME_LABEL'].unique().tolist()
    game_list = game_list[::-1]

    with col2:
        game_select = st.selectbox(label='Select Game', options=game_list)
    game = get_selected_game(
        games_season=games_season, game_select=game_select
    )
    shot_df = pd.DataFrame(columns=["x", "y", "result"], data=[[1, 1, 'Make']])
    image = Image.open('SHOT_CHART.png')
    #img_array = np.array(image)
    #img_array = np.array(image)
    if "clear_canvas" not in st.session_state:
        st.session_state.clear_canvas = False

    # Display court image
    st.subheader("Click on the court to log a shot")
    #st.image(img_array)
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",  # orange
        stroke_width=1,
        stroke_color="#000000",
        background_image=image,  # halfcourt image
        update_streamlit=True,
        height = image.height,
        width = image.width,
        #height=600 * (470 + 2 * 10) / (500 + 2 * 10),
        #width=700,
        drawing_mode="point",
        key="canvas",
        initial_drawing=[] if st.session_state.clear_canvas else None
    )
    # Handle new clicks
    if canvas_result.json_data['objects'] != []:
        objects = canvas_result.json_data["objects"]
        with st.form(key='Play Event', clear_on_submit=False):
            game_val = game['GAME_LABEL'].values[0]
            new_obj = objects[-1]
            x, y = new_obj["left"], new_obj["top"]
            st.write(x, y)
            players_season = games_season.sort_values(by='NUMBER')
            spots = games_season.sort_values(by=['POINTS', 'SPOT'])
            unique_players = (
                games_season.sort_values(by='NUMBER')['PLAYER_LABEL'].unique()
            )
            unique_spots = (
                games_season.sort_values(by=['POINTS', 'SPOT'])['SPOT'].unique()
            )
            col1, col2 = st.columns(spec=2)
            with col1:
                player_val = st.radio(
                label='Player', options=unique_players, horizontal=True
                )

            with col2:
                spot_val = st.radio(
                label='Shot Spot', options=unique_spots, horizontal=True
            )
            st.divider()
            col1, col2 = st.columns(spec=2)

            with col1:
                make_miss = st.radio(
                label='Make/Miss', options=['Y', 'N'], horizontal=True
            )
            
            with col2:
                shot_defense = st.radio(
                    label='Shot Defense', options=_shot_defenses, horizontal=True
            )
            add = st.form_submit_button(label='Add Play')
            if add:
                time.sleep(.5)
                player_number, game_val_final = get_values_needed(
                    game_val=game_val, game=game, player_val=player_val
                )
                player_number = int(player_number)
                test_make = np.where(make_miss == 'Y', 'Make', 'Miss')
                my_df = create_df(
                    game_val_final=game_val_final,
                    player_number=player_number,
                    spot_val=spot_val,
                    shot_defense=shot_defense,
                    make_miss=make_miss
                )

                all_data_game = games_season[games_season['GAME_ID'] == game_val_final]
                if len(all_data_game) == 0:
                    my_df['PLAY_NUM'] = 0
                else:
                    current_play = len(all_data_game)
                    my_df['PLAY_NUM'] = current_play
                #with sqlitecloud.connect(sql_lite_connect) as conn:
                #    cursor = conn.cursor()
                #    cursor.execute(
                #        sql=sql.insert_plays_sql(),
                #        parameters=(
                #            str(game_val_final),
                #            str(player_number),
                #            str(spot_val),
                #            str(shot_defense),
                #            str(make_miss),
                #            str(my_df['PLAY_NUM'].values[0])
                #            )
                #        )
                #    conn.commit()
                current_game = pd.concat(
                    objs=[
                        all_data_game.reset_index(drop=True), 
                        my_df.reset_index(drop=True)
                    ],
                    ignore_index=True
                )
                current_game['ACTUAL_POINTS'] = np.where(
                    current_game['MAKE_MISS'] == 'Y',
                    current_game['POINTS'], 
                    0
                )
                st.write(current_game)
                my_len = len(current_game)
                st.text(
                    body=f'Submitted {test_make}\
                        by player {player_number}\
                        from spot {spot_val}\
                        with defense {shot_defense}\
                        for game {game_val_final}'
                )
                st.write(f'Added to DB, {my_len}\
                        shots in DB for game {game_val_final}'
                )
                nda_points = current_game[
                    current_game['NUMBER'] != '0'
                ]
                opp_points = current_game[
                    current_game['NUMBER'] == '0'
                ]
                nda_points_val = nda_points.ACTUAL_POINTS.sum().astype(int)
                opp_points_val = opp_points.ACTUAL_POINTS.sum().astype(int)
                st.write(f'NDA Points: {nda_points_val}')
                st.write(f'Opp Points: {opp_points_val}')



