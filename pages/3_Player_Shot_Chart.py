from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import sqlite3 as sql
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from functions import utils as ut
pd.options.mode.chained_assignment = None

st.set_page_config(initial_sidebar_state='expanded')

SELECT_PLAYS = """
SELECT *
  FROM PLAYS
"""

SELECT_GAMES = """
SELECT *
  FROM GAMES
"""
SELECT_SPOT = """
SELECT *
  FROM SPOTS 
"""
SELECT_PLAYERS = """
SELECT *
  FROM PLAYERS
"""
my_db = ut.create_db()


with sql.connect(my_db) as nda_db:
    games = pd.read_sql(sql=SELECT_GAMES, 
                        con=nda_db
    )
    play_event = pd.read_sql(sql=SELECT_PLAYS, 
                          con=nda_db
    )
    spot = pd.read_sql(sql=SELECT_SPOT, 
                               con=nda_db
    )
    players = pd.read_sql(sql=SELECT_PLAYERS, 
                               con=nda_db
    )
    games['GAME_ID'] = games['GAME_ID'].astype(str)
    play_event['GAME_ID'] = play_event['GAME_ID'].astype(str)
    players['NUMBER'] = players['NUMBER'].astype(str)
    play_event['PLAYER_ID'] = play_event['PLAYER_ID'].astype(str)

players = players[players['YEAR']==2024]
player_data = (play_event.merge(spot,
                                left_on=['SHOT_SPOT'],
                                right_on=['SPOT'])
                         .merge(games,
                                on=['GAME_ID'])
                         .merge(players,
                                left_on=['PLAYER_ID'],
                                right_on=['NUMBER'])
)
player_data['NAME'] = (player_data['FIRST_NAME']
                       + ' '
                       + player_data['LAST_NAME']
)
player_data['MAKE'] = np.where(player_data['MAKE_MISS']=='Y',
                               1,
                               0
)
player_data['WAS_ASSIST'] = np.where(player_data['ASSISTED']=='Y',
                               1,
                               0
)
player_data['HEAVILY_GUARDED'] = np.where(player_data['SHOT_DEFENSE']=='HEAVILY_GUARDED',
                               1,
                               0
)
player_data['ATTEMPT'] = 1
player_data = player_data[['FIRST_NAME',
                           'LAST_NAME',
                           'NAME',
                           'SHOT_SPOT',
                           'MAKE',
                           'ATTEMPT',
                           'XSPOT',
                           'YSPOT',
                           'WAS_ASSIST',
                           'HEAVILY_GUARDED'
]]
player_data['U_ID'] = (player_data['FIRST_NAME']
                       + ' '
                       + player_data['LAST_NAME']
)
player_names = player_data['U_ID'].unique()
players_selected = st.radio(label='Choose Player', 
                            options=player_names,
                            horizontal=True
)
first_name = players_selected.split(' ')[0]
last_name = players_selected.split(' ')[1]
this_game = player_data[(player_data['FIRST_NAME']==first_name)
                        & (player_data['LAST_NAME']==last_name)
]

if players_selected:
    totals = (this_game.groupby(by=['NAME', 
                                    'SHOT_SPOT', 
                                    'XSPOT', 
                                    'YSPOT'], 
                                as_index=False)
                       [['MAKE', 
                         'ATTEMPT', 
                         'WAS_ASSIST',
                         'HEAVILY_GUARDED']]
                       .sum()
    )
    totals['POINT_VALUE'] = (totals['SHOT_SPOT'].str
                                                .strip()
                                                .str[-1]
                                                .astype('int64')
    )
    totals['MAKE_PERCENT'] = (totals['MAKE']
                              / totals['ATTEMPT'].replace(0, 1)
    )
    totals['ASSIST_PERCENT'] = (totals['WAS_ASSIST']
                                / totals['MAKE'].replace(0, 1)
    )
    totals['HG_PERCENT'] = (totals['HEAVILY_GUARDED'] 
                                / totals['ATTEMPT'].replace(0, 1)
    )
    totals['POINTS_PER_ATTEMPT'] = ((totals['MAKE']*totals['POINT_VALUE']) 
                                    / totals['ATTEMPT'].replace(0, 1)
    )
    totals_sorted = totals.sort_values(by=['POINTS_PER_ATTEMPT', 
                                           'ATTEMPT'], 
                                       ascending=False)
    totals_sorted = totals_sorted[totals_sorted['ATTEMPT'] > 1]
    totals_sorted = totals_sorted[['SHOT_SPOT',
                                   'MAKE',
                                   'ATTEMPT',
                                   'MAKE_PERCENT',
                                   'POINTS_PER_ATTEMPT',
                                   'ASSIST_PERCENT',
                                   'HG_PERCENT']].round(3)
    st.header(f'Top 5 Spots for {players_selected}')
    st.dataframe(totals_sorted.head(5), 
                 use_container_width=True,
                 hide_index=True
    )
    fig = ut.load_shot_chart_player(totals,
                                    players_selected)
    st.header(f'Shot Chart for {players_selected}')
    st.plotly_chart(fig, 
                    use_container_width=True
    )
