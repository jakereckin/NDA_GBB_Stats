import numpy as np
import streamlit as st
import sys
import os
import pandas as pd
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import polars as pl
from py import sql, data_source
from functions import utils as ut
pd.options.mode.chained_assignment = None

st.cache_data.clear()

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
@st.cache_data
def get_game_data():
     team_data = data_source.run_query(
        sql=sql.team_shot_chart_sql(), connection=sql_lite_connect
    )
     return team_data


# ----------------------------------------------------------------------------
@st.cache_data
def filter_team_data(team_data):
     team_data_filtered = team_data[[
          'GAME', 'GAME_ID', 'OPPONENT', 'DATE', 'SHOT_SPOT', 'MAKE',
          'ATTEMPT', 'XSPOT', 'YSPOT', 'HEAVILY_GUARDED', 'SEASON', 'U_ID',
          'POINTS'
     ]]
     team_data_filtered = team_data_filtered.sort_values(
          by='GAME_ID', ascending=False
     )
     return team_data_filtered


# ----------------------------------------------------------------------------
def get_selected_games(games_selected, team_data_filtered):
     data_from_game_selected = pd.DataFrame(
          data=games_selected, columns=['U_ID']
     )
     data_from_game_selected['OPP'] = (
          data_from_game_selected['U_ID'].str.split(pat=' - ').str[0]
     )
     data_from_game_selected['DATE'] = (
          data_from_game_selected['U_ID']
                                 .str.split(pat=' - ')
                                 .str[1]
                                 .str.strip()
     )
     opponents = data_from_game_selected['OPP'].unique().tolist()

     dates = data_from_game_selected['DATE'].unique().tolist()
     this_game = team_data_filtered[
          (team_data_filtered['OPPONENT'].isin(opponents))
          & (team_data_filtered['DATE'].isin(dates))
     ]
     return this_game


# ----------------------------------------------------------------------------
def format_selected_games(this_game):

     totals = (
          this_game.groupby(by=['SHOT_SPOT', 'XSPOT', 'YSPOT', 'POINTS'], 
                            as_index=False)
                   [['MAKE', 'ATTEMPT', 'HEAVILY_GUARDED']]
                   .sum()
     )
     totals['MAKE_PERCENT'] = np.where(
          totals['ATTEMPT'] == 0, 0, totals['MAKE'] / totals['ATTEMPT']
     )
     totals['HG_PERCENT'] = np.where(
          totals['ATTEMPT'] == 0, 
          0, 
          totals['HEAVILY_GUARDED'] / totals['ATTEMPT']
     )
     totals['POINTS_PER_ATTEMPT'] = np.where(
          totals['ATTEMPT'] == 0, 0, totals['MAKE'] * totals['POINTS']
     )

     totals_sorted = totals.sort_values(
          by=['POINTS_PER_ATTEMPT', 'ATTEMPT'], ascending=False
     )
     totals_sorted = totals_sorted[totals_sorted['ATTEMPT'] > 1]
     totals_sorted = (
          totals_sorted[[
               'SHOT_SPOT',
               'MAKE',
               'ATTEMPT',
               'MAKE_PERCENT', 
               'POINTS_PER_ATTEMPT',
               'HG_PERCENT'
               ]]
               .round(3)
     )

     return totals, totals_sorted

#play_event, spot, games = load_frames()

team_data = get_game_data()

team_data_filtered = filter_team_data(team_data=team_data)

season_list = team_data['SEASON'].sort_values().unique().tolist()

season = st.multiselect(label='Select Season', options=season_list)
if season:
     this_year = (
          team_data_filtered[team_data_filtered['SEASON'].isin(values=season)]
                         .sort_values(by='GAME_ID')
     )
     games = this_year['U_ID'].unique()
     games_selected = st.multiselect(label='Choose Games', options=games)

     this_game = get_selected_games(
          games_selected=games_selected, team_data_filtered=team_data_filtered
     )


     
     # ----------------------------------------------------------------------------
     if games_selected:
          totals, totals_sorted = format_selected_games(this_game=this_game)
          top_five_spots = totals_sorted.head(5)
          fig = ut.load_shot_chart_team(totals=totals, team_selected=games_selected)
          st.markdown(
               body="<h1 style='text-align: center; color: black;'>Shot Chart</h1>", 
               unsafe_allow_html=True
          )
          st.plotly_chart(figure_or_data=fig, use_container_width=True)
          st.markdown(
               body="<h1 style='text-align: center; color: black;'>Top 5 Spots</h1>",
               unsafe_allow_html=True
          )
          st.dataframe(
               data=top_five_spots, use_container_width=True, hide_index=True
          )
