from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None


conn = st.connection("gsheets", 
                     type=GSheetsConnection
)
play_event = conn.read(worksheet='play_event')
spot = conn.read(worksheet='spots')
games = conn.read(worksheet='games')
player_data = (play_event.merge(spot,
                                left_on=['SHOT_SPOT'],
                                right_on=['SPOT'])
                         .merge(games,
                                on=['GAME_ID'])
)
player_data['GAME'] = (player_data['OPPONENT']
                       + ' '
                       + player_data['DATE']
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
player_data = player_data[['GAME',
                           'GAME_ID',
                           'OPPONENT',
                           'DATE',
                           'SHOT_SPOT',
                           'MAKE',
                           'ATTEMPT',
                           'XSPOT',
                           'YSPOT',
                           'WAS_ASSIST',
                           'HEAVILY_GUARDED'
]]
player_data = player_data.sort_values(by='GAME_ID',
                                      ascending=False
)
player_data['U_ID'] = (player_data['OPPONENT']
                       + ' - '
                       + player_data['DATE']
)
games = player_data['U_ID'].unique()
team_selected = st.multiselect('Choose Games', 
                               games
)
return_frame = pd.DataFrame(team_selected, 
                            columns=['U_ID']
)
return_frame['OPP'] = (return_frame['U_ID'].str
                                           .split(' - ')
                                           .str[0]
)
return_frame['DATE'] = (return_frame['U_ID'].str
                                            .split(' - ')
                                            .str[1]
)
opps = (return_frame['OPP'].unique()
                           .tolist()
)
dates = (return_frame['DATE'].unique()
                             .tolist()
)
this_game = player_data[(player_data['OPPONENT'].isin(opps))
                        & (player_data['DATE'].isin(dates))]

if team_selected:
    totals = (this_game.groupby(by=['SHOT_SPOT', 
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
    totals['POINTS_PER_ATTEMPT'] = ((totals['MAKE'] * totals['POINT_VALUE']) 
                                    / totals['ATTEMPT'].replace(0, 1)
    )
    totals_sorted = totals.sort_values(by=['POINTS_PER_ATTEMPT', 
                                           'ATTEMPT'], 
                                       ascending=False
    )
    totals_sorted = totals_sorted[totals_sorted['ATTEMPT'] > 1]
    totals_sorted = totals_sorted[['SHOT_SPOT',
                                   'MAKE',
                                   'ATTEMPT',
                                   'MAKE_PERCENT',
                                   'POINTS_PER_ATTEMPT',
                                   'ASSIST_PERCENT',
                                   'HG_PERCENT']].round(3)
    fig = ut.load_shot_chart_team(totals,
                                  team_selected=team_selected)
    st.header('Shot Chart')
    st.plotly_chart(fig, use_container_width=True)
    st.header('Top 5 Spots')
    st.dataframe(totals_sorted.head(5), 
                 use_container_width=True,
                 hide_index=True
    )
