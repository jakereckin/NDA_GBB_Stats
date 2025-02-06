import numpy as np
import streamlit as st
import plotly.express as px
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None

st.cache_resource.clear()

st.set_page_config(layout='wide')

list_of_stats = [
    'LABEL', 'OFFENSIVE_EFFICENCY', 'EFF_POINTS', 'EFG%', '2PPA', '3PPA',
    'PPA', 'POINTS', 'POSSESSIONS', 'GAME_SCORE'
]
other_stats = [
    'Offensive Efficency', 'Efficent Points Scored', 'Effective FG%',
    '2 Points Per Attempt', '3 Points Per Attempt', 'Points Per Attempt',
    'Points Scored', 'Game Score'
]

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
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    players = players[players['NUMBER'] != 0]
    game_summary = (
        pd.DataFrame(data=list(game_summary_db.find())).drop(columns=['_id'])
    )
    return games, players, game_summary


# ----------------------------------------------------------------------------
@st.cache_resource
def load_data():
    client = get_client()
    games, players, game_summary = get_my_db(client)
    games['SEASON'] = (
        games['SEASON'].astype(dtype='str').str.replace(pat='.0', 
                                                        repl='', 
                                                        regex=False)
    )
    players['YEAR'] = (
        players['YEAR'].astype(dtype='str').str.replace(pat='.0', 
                                                        repl='', 
                                                        regex=False)
    )
    return players, games, game_summary


# ----------------------------------------------------------------------------
@st.cache_data
def get_games(game_summary, games, players):

    game_summary = pd.merge(left=game_summary, right=games, on='GAME_ID')

    game_summary = pd.merge(
        left=game_summary, right=players, left_on=['PLAYER_ID', 'SEASON'],
        right_on=['NUMBER', 'YEAR']
    )
    game_summary['LABEL'] = (
        game_summary['OPPONENT'] + ' - ' + game_summary['DATE']
    )
    game_summary['NAME'] = (
        game_summary['FIRST_NAME'] + ' ' + game_summary['LAST_NAME']
    )
    game_summary['FGA'] = (
        game_summary['TWO_FGA'] + game_summary['THREE_FGA']
    )
    game_summary['FGM'] = (
        game_summary['TWO_FGM'] + game_summary['THREE_FGM']
    )
    game_summary['POINTS'] = (
        (2*game_summary['TWO_FGM']) + (3*game_summary['THREE_FGM'])
        + (game_summary['FTM'])
    )
    game_summary['GAME_SCORE'] = (
        game_summary['POINTS']
        + 0.4*game_summary['FGM'] - 0.7*game_summary['FGA']
        - 0.4*(game_summary['FTA']-game_summary['FTM'])
        + 0.7*game_summary['OFFENSIVE_REBOUNDS']
        + 0.3*game_summary['DEFENSIVE_REBOUNDS'] + game_summary['STEALS']
        + 0.7*game_summary['ASSISTS'] + 0.7*game_summary['BLOCKS']
        - game_summary['TURNOVER']
    )
    team_data = (
        game_summary.copy().groupby(by='LABEL', as_index=False).sum()
    )
    return game_summary, team_data


# ----------------------------------------------------------------------------
def apply_derived(data):

    data['TWO_POINTS_SCORED'] = 2 * data['TWO_FGM']
    data['THREE_POINTS_SCORED'] = 3 * data['THREE_FGM']
    data['TOTAL_POINTS_SCORED'] = (
        data['TWO_POINTS_SCORED'] + data['THREE_POINTS_SCORED']
    )
    data['OE_NUM'] = data['FGM'] + data['ASSISTS']
    data['OE_DENOM'] = (
        data['FGA'] - data['OFFENSIVE_REBOUNDS'] + data['ASSISTS'] 
        + data['TURNOVER']
    )
    data['EFG_NUM'] = data['TWO_FGM'] + (1.5*data['THREE_FGM'])

    data['2PPA'] = np.where(
        data['TWO_FGA'] > 0, data['TWO_POINTS_SCORED'] / data['TWO_FGA'], 0
    )
    data['3PPA'] = np.where(
        data['THREE_FGA'] > 0, 
        data['THREE_POINTS_SCORED'] / data['THREE_FGA'], 
        0
    )
    data['PPA'] = np.where(
        data['FGA'] > 0, data['TOTAL_POINTS_SCORED'] / data['FGA'], 0
    )
    data['OFFENSIVE_EFFICENCY'] = np.where(
        data['OE_DENOM'] != 0, data['OE_NUM'] / data['OE_DENOM'], 0
    )
    data['EFG%'] = np.where(
        data['FGA'] > 0, data['EFG_NUM'] / data['FGA'], 0
    ) 
    data['EFF_POINTS'] = data['POINTS'] * data['OFFENSIVE_EFFICENCY']
    data['POSSESSIONS'] = (
        .96 * (data['FGA'] + data['TURNOVER'] 
               + (.44 * data['FTA']) - data['OFFENSIVE_REBOUNDS'])
    )
    return data


# ============================================================================
players, games, game_summary = load_data()

game_summary, team_data = get_games(
    game_summary=game_summary, games=games, players=players
)
season_list = game_summary['SEASON'].unique().tolist()

season = st.multiselect(label='Select Season', options=season_list)

if season_list:

    game_summary_season = (
        game_summary[game_summary['SEASON'].isin(values=season)]
                    .sort_values(by='GAME_ID')
    )
    games_list = game_summary_season['LABEL'].unique().tolist()

    game = st.multiselect(label='Select Games', options=games_list)

    if game != []:
        final_data = game_summary_season[
            game_summary_season['LABEL'].isin(values=game)
        ]
        team_data = team_data[team_data['LABEL'].isin(values=game)]
        team_data = apply_derived(data=team_data)
        team_data = (
            team_data[list_of_stats]
                     .rename(columns={'LABEL': 'Opponent'}).round(decimals=2)
        )
        player_level = final_data.groupby(by='NAME', as_index=False).sum()

        player_level = apply_derived(data=player_level).round(decimals=2)
        team_data = team_data.rename(
            columns={'OFFENSIVE_EFFICENCY': 'Offensive Efficency',
             'EFF_POINTS': 'Efficent Points Scored',
             'EFG%': 'Effective FG%',
             '2PPA': '2 Points Per Attempt',
             '3PPA': '3 Points Per Attempt',
             'PPA': 'Points Per Attempt',
             'POINTS': 'Points Scored',
             'GAME_SCORE': 'Game Score',
             'POSSESSIONS': 'Possessions'}
        )
        player_level = player_level.rename(
            columns={'OFFENSIVE_EFFICENCY': 'Offensive Efficency',
             'EFF_POINTS': 'Efficent Points Scored',
             'EFG%': 'Effective FG%',
             '2PPA': '2 Points Per Attempt',
             '3PPA': '3 Points Per Attempt',
             'PPA': 'Points Per Attempt',
             'POINTS': 'Points Scored',
             'GAME_SCORE': 'Game Score',
             'POSSESSIONS': 'Possessions'}
        )
        st.text(body='Team Level Data')
        st.dataframe(
            data=team_data, use_container_width=True, hide_index=True
        )

        data = st.radio(
            label='Select Stat', options=other_stats, horizontal=True
        )

        if data:
            fig = px.bar(
                data_frame=player_level, x=data, y='NAME', orientation='h',
                text=data
            )
            st.plotly_chart(figure_or_data=fig, use_container_width=True)
