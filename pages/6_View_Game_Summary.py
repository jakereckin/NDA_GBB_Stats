from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import sys
import os
import plotly.express as px
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut

#st.set_page_config(initial_sidebar_state='expanded')

from streamlit_gsheets import GSheetsConnection
from functions import utils as ut

conn = st.connection("gsheets", type=GSheetsConnection)
players = conn.read(worksheet='players')
games = conn.read(worksheet='games')
game_summary = conn.read(worksheet='game_summary')

@st.cache_data
def get_games(game_summary, games):
    game_summary = pd.merge(left=game_summary,
                            right=games,
                            on='GAME_ID'
    )
    game_summary = pd.merge(game_summary,
                            players,
                            left_on=['PLAYER_ID',
                                     'SEASON'],
                            right_on=['NUMBER',
                                      'YEAR']
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
    team_data = game_summary.copy().groupby(by='LABEL', as_index=False).sum()
    return game_summary, team_data

def apply_derived(data):
    def get_ppa_two(row):
        total_points = 2 * row['TWO_FGM']
        total_attempts = row['TWO_FGA']
        if total_attempts > 0:
            return total_points / total_attempts
        else:
            return 0

    def get_ppa_three(row):
        total_points = 3 * row['THREE_FGM']
        total_attempts = row['THREE_FGA']
        if total_attempts > 0:
            return total_points / total_attempts
        else:
            return 0

    def get_total_ppa(row):
        total_points = 2 * row['TWO_FGM'] + 3 * row['THREE_FGM']
        total_attempts = row['FGA']
        if total_attempts > 0:
            return total_points / total_attempts
        else:
            return 0

    def offensive_efficiency(row):
        num = row['FGM'] + row['ASSITS']
        denom = row['FGA'] - row['OFFENSIVE_REBOUNDS'] + row['ASSITS'] + row['TURNOVER']
        if denom != 0:
            return num / denom
        else:
            return 0

    def efficient_offense(row):
        val = row['POINTS'] * row['OFFENSIVE_EFFICENCY']
        return val

    def effective_fgp(row):
        num = row['FGM'] + (.5 * row['THREE_FGM'])
        denom = row['FGA']
        if denom > 0:
            return num / denom
        else:
            return 0
        
    data['OFFENSIVE_EFFICENCY'] = data.apply(offensive_efficiency, 
                                             axis='columns'
    )
    data['EFF_POINTS'] = data.apply(efficient_offense, 
                                                    axis='columns'
    )
    data['EFG%'] = data.apply(effective_fgp, 
                                            axis='columns'
    )
    data['2PPA'] = data.apply(get_ppa_two, 
                                            axis='columns'
    )
    data['3PPA'] = data.apply(get_ppa_three, 
                                            axis='columns'
    )
    data['PPA'] = data.apply(get_total_ppa, 
                                            axis='columns'
    )
    return data

game_summary, team_data = get_games(game_summary=game_summary,
                                    games=games
)
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
season_list = game_summary['SEASON'].unique().tolist()
season = st.multiselect(label='Select Season',
                        options=season_list
)
if season_list:
    game_summary_season = game_summary[game_summary['SEASON'].isin(season)]
    games_list = game_summary_season['LABEL'].unique().tolist()
    game = st.multiselect(label='Select Games',
                          options=games_list
    )
    if game != []:
        final_data = game_summary_season[game_summary_season['LABEL'].isin(game)]
        team_data = team_data[team_data['LABEL'].isin(game)]
        team_data = apply_derived(team_data)
        team_data = team_data[list_of_stats]
        team_data = team_data.rename(columns={'LABEL': 'Opponent'})
        team_data = team_data.round(2)
        present = final_data.groupby(by='NAME', 
                                     as_index=False).sum()
        present = apply_derived(present).round(2)
        st.text('Team Level Data')
        st.dataframe(team_data, 
                     use_container_width=True, 
                     hide_index=True
                     )
        data_list = st.radio(label='Select Stat',
                             options=other_stats,
                             horizontal=True
        )
        if data_list:
            #final_data[other_stats] = final_data[other_stats].round(2)
            fig = px.bar(present, 
                         x=data_list, 
                         y='NAME', 
                         orientation='h',
                         text=data_list
            )
            st.plotly_chart(fig, use_container_width=True)
