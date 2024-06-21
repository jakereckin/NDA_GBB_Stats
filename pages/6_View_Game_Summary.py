import numpy as np
import streamlit as st
import sys
import os
import plotly.express as px
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None


list_of_stats = ['LABEL',
                 'OFFENSIVE_EFFICENCY',
                 'EFF_POINTS',
                 'EFG%',
                 '2PPA',
                 '3PPA',
                 'PPA',
                 'POINTS'
]
other_stats = ['OFFENSIVE_EFFICENCY',
                 'EFF_POINTS',
                 'EFG%',
                 '2PPA',
                 '3PPA',
                 'PPA',
                 'POINTS'
]

@st.cache_resource
def get_client():
    uri =  f"mongodb+srv://nda-gbb-admin:{st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client

def get_my_db(client):
    my_db = client['NDA_GBB']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    games = pd.DataFrame(list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(list(players_db.find())).drop(columns=['_id'])
    game_summary = pd.DataFrame(list(game_summary_db.find())).drop(columns=['_id'])
    return games, players, game_summary

@st.cache_resource
def load_data():
    client = get_client()
    games, players, game_summary = get_my_db(client)
    games['SEASON'] = (games['SEASON'].astype('str')
                                      .str
                                      .replace('.0', 
                                               '', 
                                               regex=False)
    )
    players['YEAR'] = (players['YEAR'].astype('str')
                                          .str
                                          .replace('.0',
                                                   '',
                                                   regex=False)
    )
    return players, games, game_summary

@st.cache_data
def get_games(game_summary, games, players):

    game_summary = pd.merge(left=game_summary, right=games, on='GAME_ID')

    game_summary = pd.merge(game_summary,
                            players,
                            left_on=['PLAYER_ID', 'SEASON'],
                            right_on=['NUMBER', 'YEAR']
    )
    game_summary['LABEL'] = (game_summary['OPPONENT']
                             + ' - '
                             + game_summary['DATE']
    )
    game_summary['NAME'] = (game_summary['FIRST_NAME']
                            + ' '
                            + game_summary['LAST_NAME']
    )
    game_summary['FGA'] = (game_summary['TWO_FGA']
                           + game_summary['THREE_FGA']
    )
    game_summary['FGM'] = (game_summary['TWO_FGM']
                           + game_summary['THREE_FGM']
    )
    game_summary['POINTS'] = ((2*game_summary['TWO_FGM'])
                              + (3*game_summary['THREE_FGM'])
                              + (game_summary['FTM'])
    )
    team_data = (game_summary.copy()
                             .groupby(by='LABEL', as_index=False)
                             .sum()
    )
    return game_summary, team_data

def apply_derived(data):

    data['TWO_POINTS_SCORED'] = 2 * data['TWO_FGM']
    data['THREE_POINTS_SCORED'] = 3 * data['THREE_FGM']
    data['TOTAL_POINTS_SCORED'] = (data['TWO_POINTS_SCORED']
                                   + data['THREE_POINTS_SCORED']
    )
    data['OE_NUM'] = data['FGM'] + data['ASSISTS']
    data['OE_DENOM'] = (data['FGA'] 
                        - data['OFFENSIVE_REBOUNDS'] 
                        + data['ASSISTS'] 
                        + data['TURNOVER']
    )
    data['EFG_NUM'] = data['FGM'] + (.5*data['THREE_FGM'])

    data['2PPA'] = np.where(data['TWO_FGA']>0,
                            data['TWO_POINTS_SCORED']/data['TWO_FGA'],
                            0
    )
    data['3PPA'] = np.where(data['THREE_FGA']>0,
                            data['THREE_POINTS_SCORED']/data['THREE_FGA'],
                            0
    )
    data['PPA'] = np.where(data['FGA']>0,
                            data['TOTAL_POINTS_SCORED']/data['FGA'],
                            0
    )
    data['OFFENSIVE_EFFICENCY'] = np.where(data['OE_DENOM']!=0,
                                           data['OE_NUM']/data['OE_DENOM'],
                                           0
    )
    data['EFG%'] = np.where(data['FGA']>0,
                            data['EFG_NUM']/data['FGA'],
                            0
    ) 
    data['EFF_POINTS'] = data['POINTS'] * data['OFFENSIVE_EFFICENCY']

    return data

players, games, game_summary = load_data()

game_summary, team_data = get_games(game_summary=game_summary,
                                    games=games,
                                    players=players
)
season_list = game_summary['SEASON'].unique().tolist()

season = st.multiselect(label='Select Season', options=season_list)

if season_list:

    game_summary_season = (game_summary[game_summary['SEASON'].isin(season)]
                                       .sort_values(by='GAME_ID')
    )
    games_list = game_summary_season['LABEL'].unique().tolist()

    game = st.multiselect(label='Select Games', options=games_list)

    if game != []:
        final_data = game_summary_season[game_summary_season['LABEL'].isin(game)]
        team_data = team_data[team_data['LABEL'].isin(game)]
        team_data = apply_derived(team_data)
        team_data = (team_data[list_of_stats]
                              .rename(columns={'LABEL': 'Opponent'})
                              .round(2)
        )
        present = final_data.groupby(by='NAME', as_index=False).sum()

        present = apply_derived(present).round(2)

        st.text('Team Level Data')
        st.dataframe(team_data, use_container_width=True, hide_index=True)

        data_list = st.radio(label='Select Stat',
                             options=other_stats,
                             horizontal=True
        )

        if data_list:
            fig = px.bar(present, 
                         x=data_list, 
                         y='NAME', 
                         orientation='h',
                         text=data_list
            )
            st.plotly_chart(fig, use_container_width=True)
