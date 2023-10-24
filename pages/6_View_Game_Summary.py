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

conn = ut.create_db()
game_summary = ut.select_game_summary(conn)
games = ut.select_games(conn)
players = ut.select_players(conn)

@st.cache_data
def get_games(game_summary, games):
    game_summary = pd.merge(left=game_summary,
                            right=games,
                            on='GAME_ID'
    )
    game_summary = pd.merge(game_summary,
                            players,
                            left_on='PLAYER_ID',
                            right_on='NUMBER'
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
                            + (game_summary['FGM'])
    )
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
        inner = .76 * row['ASSITS'] + row['POINTS']
        return inner * row['OFFENSIVE_EFFICENCY']

    def effective_fgp(row):
        num = row['FGM'] + (.5 * row['THREE_FGM'])
        denom = row['FGA']
        if denom > 0:
            return num / denom
        else:
            return 0
        
    game_summary['OFFENSIVE_EFFICENCY'] = game_summary.apply(offensive_efficiency, 
                                                            axis='columns'
    )
    game_summary['EFF_POINTS'] = game_summary.apply(efficient_offense, 
                                                    axis='columns'
    )
    game_summary['EFG%'] = game_summary.apply(effective_fgp, 
                                            axis='columns'
    )
    game_summary['2PPA'] = game_summary.apply(get_ppa_two, 
                                            axis='columns'
    )
    game_summary['3PPA'] = game_summary.apply(get_ppa_three, 
                                            axis='columns'
    )
    game_summary['PPA'] = game_summary.apply(get_total_ppa, 
                                            axis='columns'
    )
    game_summary['LABEL'] = (game_summary['OPPONENT']
                            + ' - '
                            + game_summary['DATE']
    )
    return game_summary

game_summary = get_games(game_summary=game_summary,
                         games=games
)
list_of_stats = ['OFFENSIVE_EFFICENCY',
                 'EFF_POINTS',
                 'EFG%',
                 '2PPA',
                 '3PPA',
                 'PPA'
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
    if games_list:
        final_data = game_summary_season[game_summary_season['LABEL'].isin(game)]
        table = (pd.DataFrame(final_data[list_of_stats].mean())
                   .T
        )
        st.dataframe(table, 
                     use_container_width=True, 
                     hide_index=True
                     )
        data_list = st.radio(label='Select Stat',
                             options=list_of_stats,
                             horizontal=True
        )
        if data_list:
            final_data[data_list] = final_data[data_list].round(2)
            fig = px.bar(final_data, 
                         x=data_list, 
                         y='NAME', 
                         orientation='h',
                         text=data_list
            )
            st.plotly_chart(fig, use_container_width=True)
