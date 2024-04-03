import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from streamlit_gsheets import GSheetsConnection
from functions import utils as ut
pd.options.mode.chained_assignment = None


conn = st.connection("gsheets", type=GSheetsConnection)
play_event = conn.read(worksheet='play_event')
spot = conn.read(worksheet='spots')
games = conn.read(worksheet='games')
players = conn.read(worksheet='players')
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
player_data['LABEL'] = (player_data['OPPONENT']
                             + ' - '
                             + player_data['DATE']
)
games_list = (player_data['LABEL'].unique()
                                              .tolist()
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
player_data2 = player_data[[#'FIRST_NAME',
                           #'LAST_NAME',
                           'NAME',
                           'SHOT_SPOT',
                           'MAKE',
                           'ATTEMPT',
                         #  'XSPOT',
                         #  'YSPOT',
                        #   'WAS_ASSIST',
                           'SHOT_DEFENSE'
]]
game = st.selectbox(label='Select Games',
                      options=games_list
)
if game != []:
    t_game = player_data[player_data['LABEL']==game]
    grouped = (player_data2.groupby(by=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'],
                        as_index=False)
                .agg(ATTEMPTS=('ATTEMPT', np.sum),
                    MAKES=('MAKE', np.sum))
    )
    grouped['MAKE_PERCENT'] = np.where(grouped['ATTEMPTS']>0,
                                    grouped['MAKES']/grouped['ATTEMPTS'],
                                    0
    )
    all_spots = spot.copy()
    all_spots['POINT_VALUE'] = (all_spots['SPOT'].str
                                                    .strip()
                                                    .str[-1]
                                                    .astype('int64')
    )
    grouped_all_spots = (pd.merge(all_spots,
                                grouped,
                                left_on=['SPOT'],
                                right_on=['SHOT_SPOT'],
                                how='left')
    )
    grouped_all_spots['EXPECTED_VALUE'] = (grouped_all_spots['POINT_VALUE']
                                *grouped_all_spots['MAKE_PERCENT']
    )
    grouped_all_spots = grouped_all_spots.drop(columns=['SPOT',
                                        'XSPOT',
                                        'YSPOT',
                                        'MAKES',
                                        'ATTEMPTS'])
    tgame_2 = (t_game.groupby(by=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'],
                        as_index=False)
                .agg(ATTEMPTS=('ATTEMPT', np.sum),
                    MAKES=('MAKE', np.sum))
                .merge(grouped_all_spots,
                        on=['NAME',
                            'SHOT_SPOT',
                            'SHOT_DEFENSE'])
    )
    tgame_2['EXPECTED_POINTS'] = tgame_2['ATTEMPTS']*tgame_2['EXPECTED_VALUE']
    tgame_2['ACTUAL_POINTS'] = tgame_2['MAKES']*tgame_2['POINT_VALUE']
    st.metric(value=tgame_2['EXPECTED_POINTS'].sum(),
            label='TOTAL EXPECTED')
    st.metric(value=tgame_2['ACTUAL_POINTS'].sum(),
            label='ACTUAL')
    st.dataframe(tgame_2)