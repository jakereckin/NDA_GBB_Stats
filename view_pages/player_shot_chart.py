import streamlit as st
import pandas as pd
from py import sql, data_source, utils as ut
pd.options.mode.chained_assignment = None

st.cache_data.clear()
st.set_page_config(layout='wide')

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
@st.cache_data
def get_player_data():
     player_data = data_source.run_query(
          sql=sql.player_shot_chart_sql(), connection=sql_lite_connect
     )
     player_grouped_data = data_source.run_query(
          sql=sql.player_grouped_shot_chart_sql(), connection=sql_lite_connect
     )
     play_by_play = data_source.run_query(
          sql=sql.get_play_by_play_sql(), connection=sql_lite_connect
     )
     #player_data = player_data[player_data['SEASON'] == season]
     return player_data, player_grouped_data, play_by_play

# ----------------------------------------------------------------------------
def format_visual_data(this_game, player_grouped_data):
     totals = this_game.copy().reset_index(drop=True)
     totals_sorted = player_grouped_data.sort_values(
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
def filter_player_data(players_selected, player_data, player_grouped_data, pbp):
     this_game = (
          player_data[player_data['NAME'] == players_selected]
                     .reset_index(drop=True)
     )
     this_game_grouped = (
          player_grouped_data[player_grouped_data['NAME'] == players_selected]
                             .reset_index(drop=True)
     )
     pbp_grouped = (
          pbp[pbp['NAME'] == players_selected].reset_index(drop=True)
     )
     return this_game, this_game_grouped, pbp_grouped

# ----------------------------------------------------------------------------
@st.cache_data
def get_grades(pbp):
     shot_map = {
     ('RB2', 'OPEN'): 'A',
     ('RB2', 'GUARDED'): 'B',
     ('RB2', 'HEAVILY_GUARDED'): 'C',
     ('LB2', 'OPEN'): 'A',
     ('LB2', 'GUARDED'): 'B',
     ('LB2', 'HEAVILY_GUARDED'): 'C',
     ('ML2', 'OPEN'): 'A',
     ('ML2', 'GUARDED'): 'B',
     ('ML2', 'HEAVILY_GUARDED'): 'C',
     ('FT2', 'OPEN'): 'C',
     ('FT2', 'GUARDED'): 'D',
     ('FT2', 'HEAVILY_GUARDED'): 'F',
     ('LE2', 'OPEN'): 'C',
     ('LE2', 'GUARDED'): 'D',
     ('LE2', 'HEAVILY_GUARDED'): 'F',
     ('RE2', 'OPEN'): 'C',
     ('RE2', 'GUARDED'): 'D',
     ('RE2', 'HEAVILY_GUARDED'): 'F',
     ('LMR2', 'OPEN'): 'C',
     ('LMR2', 'GUARDED'): 'D',
     ('LMR2', 'HEAVILY_GUARDED'): 'F',
     ('RMR2', 'OPEN'): 'C',
     ('RMR2', 'GUARDED'): 'D',
     ('RMR2', 'HEAVILY_GUARDED'): 'F',
     ('LC3', 'OPEN'): 'A',
     ('LC3', 'GUARDED'): 'C',
     ('LC3', 'HEAVILY_GUARDED'): 'F',
     ('LW3', 'OPEN'): 'A',
     ('LW3', 'GUARDED'): 'C',
     ('LW3', 'HEAVILY_GUARDED'): 'F',
     ('TK3', 'OPEN'): 'A',
     ('TK3', 'GUARDED'): 'C',
     ('TK3', 'HEAVILY_GUARDED'): 'F',
     ('RW3', 'OPEN'): 'A',
     ('RW3', 'GUARDED'): 'C',
     ('RW3', 'HEAVILY_GUARDED'): 'F',
     ('RC3', 'OPEN'): 'A',
     ('RC3', 'GUARDED'): 'C',
     ('RC3', 'HEAVILY_GUARDED'): 'F',
     }
     map_gpa = {
          'A': 4,
          'B': 3,
          'C': 2,
          'D': 1,
          'F': 0
     }

     pbp['SHOT_LIST'] = list(zip(pbp['SHOT_SPOT'], pbp['SHOT_DEFENSE']))
     pbp['SCORE'] = pbp['SHOT_LIST'].map(shot_map)
     pbp = pbp.dropna()
     pbp['GPA'] = pbp['SCORE'].map(map_gpa)
     pbp_gpa = (
          pbp.groupby(by=['NAME', 'LABEL'], as_index=False)
             .agg(GPA_SUM=('GPA', 'sum'),
                  ATTEMPTS=('ATTEMPT', 'sum'))
     )
     pbp_gpa['AVG_GPA'] = pbp_gpa['GPA_SUM'] / pbp_gpa[f'ATTEMPTS']
     return pbp_gpa


players, player_grouped_data, pbp = get_player_data()
players = players.sort_values(by='SEASON', ascending=False)
season_list = players.SEASON.unique().tolist()
season = st.radio(label='Select Season', options=season_list, horizontal=True)

if season:
     player_data = players[players['SEASON'] == season]
     player_grouped_data = player_grouped_data[player_grouped_data['SEASON'] == season]
     pbp_data = pbp[pbp['SEASON'] == season]
     player_names = player_data['NAME'].unique()
     players_selected = st.radio(
          label='Choose Player', options=player_names, horizontal=True
     )

     this_game, this_game_grouped, pbp_grouped = filter_player_data(
          players_selected=players_selected,
          player_data=player_data,
          player_grouped_data=player_grouped_data,
          pbp=pbp_data
     )
     pbp_score = get_grades(pbp_grouped)
     pbp_gpa = pbp_score['GPA_SUM'].sum() / pbp_score['ATTEMPTS'].sum()
     st.metric(label='Shot Selection GPA', value=pbp_gpa.round(2))
     if players_selected:
          totals, totals_sorted = format_visual_data(
               this_game=this_game, player_grouped_data=this_game_grouped
          )
          fig = ut.load_shot_chart_player(
               totals=totals, players_selected=players_selected
          )
          fig.update_layout(
               width=500,
               height=500
          )
          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Shot Chart for {players_selected}</h1>",
               unsafe_allow_html=True
          )

          st.plotly_chart(figure_or_data=fig, width='stretch')

          st.markdown(
               body=f"<h1 style='text-align: center; color: black;'>Top 5 Spots for {players_selected}</h1>", 
               unsafe_allow_html=True
          )
          st.dataframe(
               data=totals_sorted.head(5), width='stretch', hide_index=True
          )