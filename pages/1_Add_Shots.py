import streamlit as st
import time
import sys
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    """
    Establishes a connection to the MongoDB server using credentials
    stored in Streamlit secrets.

    Returns:
        MongoClient: A MongoClient instance connected to the
        specified MongoDB server.
    """
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client

# ----------------------------------------------------------------------------
def get_my_db(client):
    """
    Retrieves various collections from the MongoDB database and
    converts them to pandas DataFrames.

    Parameters:
        client (MongoClient): A MongoClient instance connected
        to the MongoDB server.

    Returns:
        tuple: A tuple containing DataFrames for plays, spots,
        games, players, and the plays collection.
    """
    my_db = client['NDA_GBB']
    plays_db = my_db['PLAYS']
    spots_db = my_db['SPOTS']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    plays = pd.DataFrame(data=list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(data=list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    return plays, spots, games, players, plays_db


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
    client = get_client()
    all_plays, spots, games, players, plays_db = get_my_db(client=client)


    def clean_column(column):
        new_col = (
            column.astype(dtype='str')
                  .str
                  .replace(pat='.0', repl='', regex=False)
        )
        return new_col

    players['YEAR'] = clean_column(column=players['YEAR'])
    games['SEASON'] = clean_column(column=games['SEASON'])
    games['LABEL'] = games['OPPONENT'] + ' - ' + games['DATE']

    players['LABEL'] = (
        players['NUMBER'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False) 
        + ' - '
        + players['FIRST_NAME']
    )
    return plays_db, players, games, spots, all_plays


# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(
    games: pd.DataFrame, players: pd.DataFrame, season: int
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
    games_season = games[games['SEASON'] == season].copy()
    games_season['DATE_DTTM'] = pd.to_datetime(games_season['DATE'])
    games_season = games_season.sort_values(by='DATE_DTTM')
    players_season = players[players['YEAR'] == season].copy()
    games_season['LABEL'] = (
        games_season['OPPONENT'] + ' - ' + games_season['DATE']
    )
    return games_season, players_season


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


# ----------------------------------------------------------------------------
password = st.text_input(label='Password', type='password')
if password == st.secrets['page_password']['PAGE_PASSWORD']:
    #image = Image.open(fp='SHOT_CHART.jpg')
    #st.image(image=image)
    _shot_defenses = ['OPEN', 'GUARDED', 'HEAVILY_GUARDED']
    col1, col2 = st.columns(spec=2)
    plays_db, players, games, spots, all_plays = load_data()
    games = (
        games.sort_values(by='SEASON', ascending=False).reset_index(drop=True)
    )
    season_list = games['SEASON'].unique().tolist()

    with col1:
        season = st.radio(
            label='Select Season', options=season_list, horizontal=True
        )

    games_season, players_season = get_season_data(
        games=games, players=players, season=season
    )

    game_list = games_season['LABEL'].unique().tolist()
    game_list = game_list[::-1]

    with col2:
        game_select = st.selectbox(label='Select Game', options=game_list)
    game = get_selected_game(
        games_season=games_season, game_select=game_select
    )
    with st.form(key='Play Event', clear_on_submit=False):
        game_val = game['LABEL'].values[0]
        players_season = players_season.sort_values(by='NUMBER')
        spots = spots.sort_values(by=['POINTS', 'SPOT'])
        col1, col2 = st.columns(spec=2)
        with col1:
            player_val = st.radio(
            label='Player', options=players_season['LABEL'], horizontal=True
            )

        with col2:
            spot_val = st.radio(
            label='Shot Spot', options=spots['SPOT'], horizontal=True
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
                game_val_final=game_val_final, player_number=player_number,
                spot_val=spot_val, shot_defense=shot_defense,
                make_miss=make_miss
            )
            all_data_game = all_plays[all_plays['GAME_ID'] == game_val_final]
            if len(all_data_game) == 0:
                my_df['PLAY_NUM'] = 0
            else:
                current_play = len(all_data_game)
                my_df['PLAY_NUM'] = current_play
            
            current_game = pd.concat(objs=[all_data_game, my_df])
            current_play_dict = my_df.to_dict(orient='records')
            plays_db.insert_many(
                documents=current_play_dict, bypass_document_validation=True
            )
            current_game_merge = current_game.merge(
                right=spots, left_on='SHOT_SPOT', right_on='SPOT'
            )
            current_game_merge['ACTUAL_POINTS'] = np.where(
                current_game_merge['MAKE_MISS'] == 'Y',
                current_game_merge['POINTS'], 
                0
            )
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
            nda_points = current_game_merge[
                current_game_merge['PLAYER_ID'] != 0
            ]
            opp_points = current_game_merge[
                current_game_merge['PLAYER_ID'] == 0
            ]
            nda_points_val = nda_points.ACTUAL_POINTS.sum().astype(int)
            opp_points_val = opp_points.ACTUAL_POINTS.sum().astype(int)
            st.write(f'NDA Points: {nda_points_val}')
            st.write(f'Opp Points: {opp_points_val}')
