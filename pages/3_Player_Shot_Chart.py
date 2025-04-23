import streamlit as st
import pandas as pd
import pandas as pd
from py import sql, data_source, utils as ut
pd.options.mode.chained_assignment = None

st.cache_data.clear()

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
@st.cache_data
def get_player_data():
     player_data = data_source.run_query(
          sql=sql.player_shot_chart_sql(), connection=sql_lite_connect
     )
     #player_data = player_data[player_data['SEASON'] == season]
     return player_data

# ----------------------------------------------------------------------------
def format_visual_data(this_game):
     totals = this_game.copy().reset_index(drop=True)
     totals_sorted = totals.sort_values(
          by=['POINTS_PER_ATTEMPT', 'ATTEMPTS'], ascending=False
     )
     totals_sorted = totals_sorted[totals_sorted['ATTEMPTS'] > 1]
     totals_sorted = totals_sorted[[
          'SHOT_SPOT', 'MAKES', 'ATTEMPTS', 'MAKE_PERCENT',
          'POINTS_PER_ATTEMPT', 'HG_PERCENT'
     ]].round(3)
     return totals, totals_sorted


# ----------------------------------------------------------------------------
@st.cache_data
def filter_player_data(players_selected, player_data):
     this_game = (
          player_data[(player_data['NAME'] == players_selected)]
                     .reset_index(drop=True)
     )
     return this_game



players = get_player_data()
season_list = players.SEASON.unique().tolist()
season = st.radio(label='Select Season', options=season_list, horizontal=True)

if season:
     player_data = players[players['SEASON'] == season]

     player_names = player_data['NAME'].unique()
     players_selected = st.radio(
          label='Choose Player', options=player_names, horizontal=True
     )

     this_game = filter_player_data(
          players_selected=players_selected, player_data=player_data
     )
     if players_selected:
          totals, totals_sorted = format_visual_data(this_game=this_game)
          fig = ut.load_shot_chart_player(
               totals=totals, players_selected=players_selected
          )
          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Shot Chart for {players_selected}</h1>", 
               unsafe_allow_html=True
          )

          st.plotly_chart(figure_or_data=fig, use_container_width=True)

          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Top 5 Spots for {players_selected}</h1>", 
               unsafe_allow_html=True
          )

          st.dataframe(
               data=totals_sorted.head(5), use_container_width=True, hide_index=True
          )