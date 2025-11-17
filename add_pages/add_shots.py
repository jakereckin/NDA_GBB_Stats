import streamlit as st
import sqlitecloud
import pandas as pd
from PIL import Image
from py import utils, data_source, sql
import time
import numpy as np
from plotly import graph_objs as go
from streamlit_plotly_events import plotly_events

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
    shot_spots = data_source.run_query(
        sql=sql.get_shot_spots_sql(), connection=sql_lite_connect
    )
    player_game = data_source.run_query(
        sql=sql.get_player_game_sql(), connection=sql_lite_connect
    )
    return shot_spots, player_game

# ----------------------------------------------------------------------------
def load_pbp_data(game_id):
    my_sql = sql.get_play_sql().replace('?', game_id)
    pbp_data = data_source.run_query(
        sql=my_sql, connection=sql_lite_connect
    )
    return pbp_data

# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(
        player_game: pd.DataFrame, season: int
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
    games_season = player_game[player_game['SEASON'] == season].copy()
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
        make_miss,
        spot_x,
        spot_y
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
        game_val_final, player_number, spot_val, shot_defense, make_miss, spot_x, spot_y
    ]
    col_names = [
        'GAME_ID', 'NUMBER', 'SPOT', 'SHOT_DEFENSE', 'MAKE_MISS', 'XSPOT', 'YSPOT'
    ]
    my_df = pd.DataFrame(data=[this_data], columns=col_names)
    return my_df


st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
# Load or create shot data
left, right = st.columns(2)
_shot_defenses = ["OPEN", "GUARDED", "HEAVILY_GUARDED"]
shot_spots, player_game = load_data()
games = player_game.sort_values(by="SEASON", ascending=False).reset_index(drop=True)
season_list = games["SEASON"].unique().tolist()

col1, col2 = st.columns(2)
with left:
    season = st.radio(label="Select Season", options=season_list, horizontal=True)

games_season = get_season_data(player_game=games, season=season)
game_list = games_season["GAME_LABEL"].unique().tolist()[::-1]

with right:
    game_select = st.selectbox(label="Select Game", options=game_list, width='stretch')

game = get_selected_game(games_season=games_season, game_select=game_select)

fig = utils.build_blank_shot_chart()

if "shots" not in st.session_state:
    st.session_state.shots = []

# Add invisible scatter trace of capture points
@st.cache_data(show_spinner=False)
def make_grid(xmin, xmax, ymin, ymax, spacing):
    xs = np.arange(xmin, xmax + 1, spacing)
    ys = np.arange(ymin, ymax + 1, spacing)
    xx, yy = np.meshgrid(xs, ys)
    return xx.ravel().tolist(), yy.ravel().tolist()

# --- Chart ranges (match your utils court)
opacity = 1
spacing = 20
marker_size = 1
X_MIN, X_MAX = -250, 250
Y_MIN, Y_MAX = -50, 450

capture_x, capture_y = make_grid(X_MIN, X_MAX, Y_MIN, Y_MAX, spacing)

fig.update_layout(
    xaxis=dict(range=[X_MIN, X_MAX], showgrid=False, zeroline=False),
    yaxis=dict(range=[Y_MIN, Y_MAX], showgrid=False, zeroline=False, scaleanchor="x"),
    width=350,
    height=400,
    margin=dict(l=20, r=20, t=20, b=20),
    plot_bgcolor="white",
    clickmode="event+select",
)
fig.add_trace(
    go.Scatter(
        x=capture_x,
        y=capture_y,
        mode="markers",
        marker=dict(opacity=opacity, size=marker_size, color="white"),
    )
)

col3, col4 = st.columns(2)
with col3:
    clicked = plotly_events(fig, click_event=True, key="shot-capture")

if clicked:
    ev = clicked[0]
    x_click = ev.get("x")
    y_click = ev.get("y")
    shot_spot = utils.get_nearest_spot(x_click, y_click, shot_spots)
    spot_val = shot_spot.get("spot")
    if spot_val:
        with col4:
            st.write(f"Adding shot at {spot_val}")
            with st.form(key="shot_form", clear_on_submit=False):
                font_size_px = 10
                game_val = game["GAME_LABEL"].values[0]
                players_season = games_season.sort_values(by="NUMBER")
                games_season["NUMBER_INT"] = games_season["NUMBER"].astype(int)
                unique_players = games_season.sort_values(by="NUMBER_INT")["PLAYER_LABEL"].unique()
                pbp_data = load_pbp_data(game_val)
                player_val = st.radio(label="Player", options=unique_players, horizontal=True)

                c2, c3, c4 = st.columns(3)
                with c2:
                    free_throw = st.radio(label="Free Throw", options=["N", "Y"], horizontal=True)
                with c4:
                    make_miss = st.radio(label="Make/Miss", options=["N", "Y"], horizontal=True)
                with c3:
                    shot_defense = st.radio(label="Shot Defense", options=_shot_defenses, horizontal=True)

                add = st.form_submit_button(label="Add Play")
                if add:
                    time.sleep(0.5)
                    player_number, game_val_final = get_values_needed(
                        game_val=game_val, game=game, player_val=player_val
                    )
                    player_number = int(player_number)

                    if free_throw == "Y":
                        spot_val = "FREE_THROW1"
                        x_click = 0
                        y_click = 150

                    test_make = "Make" if make_miss == "Y" else "Miss"

                    my_df = create_df(
                        game_val_final=game_val_final,
                        player_number=player_number,
                        spot_val=spot_val,
                        shot_defense=shot_defense,
                        make_miss=make_miss,
                        spot_x=x_click,
                        spot_y=y_click,
                    )
                    my_df = my_df.merge(shot_spots.drop(columns=['XSPOT', 'YSPOT']), on='SPOT')
                    all_data_game = pbp_data
                    #games_season[games_season["GAME_ID"] == game_val_final]
                    if len(all_data_game) == 0:
                        my_df["PLAY_NUM"] = 0
                    else:
                        current_play = len(all_data_game)
                        my_df["PLAY_NUM"] = current_play

                    with sqlitecloud.connect(sql_lite_connect) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            sql=sql.insert_plays_sql(),
                            parameters=(
                                str(game_val_final),
                                str(player_number),
                                str(spot_val),
                                str(shot_defense),
                                str(make_miss),
                                str(my_df["PLAY_NUM"].values[0]),
                                str(x_click),
                                str(y_click),
                            ),
                        )
                        conn.commit()

                    current_game = pd.concat(
                        objs=[all_data_game.reset_index(drop=True), my_df.reset_index(drop=True)],
                        ignore_index=True,
                    )
                    current_game["ACTUAL_POINTS"] = np.where(
                        current_game["MAKE_MISS"] == "Y", current_game["POINTS"], 0
                    )
                    current_game['NUMBER'] = current_game['NUMBER'].astype(int)
                    my_len = len(current_game)
                    st.text(
                        f"Submitted {test_make} by player {player_number} from spot {spot_val} with defense {shot_defense} for game {game_val_final}"
                    )
                    st.write(f"Added to DB, {my_len} shots in DB for game {game_val_final}")

                    nda_points = current_game[current_game["NUMBER"] != 0]
                    opp_points = current_game[current_game["NUMBER"] == 0]
                    nda_points_val = int(nda_points.ACTUAL_POINTS.sum())
                    opp_points_val = int(opp_points.ACTUAL_POINTS.sum())
                    st.write(f"NDA Points: {nda_points_val}")
                    st.write(f"Opp Points: {opp_points_val}")
                    simple_data = current_game[['NUMBER', 'SPOT', 'SHOT_DEFENSE', 'MAKE_MISS', 'PLAY_NUM']]
                    simple_data = simple_data.sort_values(by=['PLAY_NUM'], ascending=False).head(10)
                    st.write(f'Previous 10 shots')
                    st.dataframe(simple_data)