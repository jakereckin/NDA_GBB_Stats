import streamlit as st
import pandas as pd
import numpy as np
from py import sql, data_source, utils as ut
pd.options.mode.chained_assignment = None

st.cache_data.clear()
st.set_page_config(layout='wide')

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']


# ----------------------------------------------------------------------------
@st.cache_data
def get_game_data():
     team_data = data_source.run_query(
        sql=sql.team_shot_chart_sql(), connection=sql_lite_connect
    )
     opp_data = data_source.run_query(
          sql=sql.opp_shot_chart_sql(), connection=sql_lite_connect
     )
     play_by_play = data_source.run_query(
          sql=sql.get_play_by_play_sql(), connection=sql_lite_connect
     )
     return team_data, opp_data, play_by_play


# ----------------------------------------------------------------------------
@st.cache_data
def filter_team_data(team_data):
     team_data_filtered = team_data.copy()
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
     totals = this_game.copy().reset_index(drop=True)
     totals_sorted = totals.sort_values(
          by=['POINTS_PER_ATTEMPT', 'ATTEMPTS'], ascending=False
     )
     totals_sorted = totals_sorted[totals_sorted['ATTEMPTS'] >= 1]
     totals_sorted = (
          totals_sorted[[
               'SHOT_SPOT',
               'MAKES',
               'ATTEMPTS',
               'MAKE_PERCENT', 
               'POINTS_PER_ATTEMPT',
               'HG_PERCENT',
               'PAINT_TOUCH'
               ]]
               .round(3)
     )

     return totals, totals_sorted

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
     pbp['POINTS'] = pbp['SHOT_SPOT'].str[-1].astype(int)
     pbp['SCORE'] = pbp['SHOT_LIST'].map(shot_map)
     pbp = pbp.dropna()
     pbp['GPA'] = pbp['SCORE'].map(map_gpa)
     pbp['TEAM'] = np.where(
          pbp['PLAYER_ID'] == '0', 'OPP', 'NDA'
     )
     pbp_gpa = (
          pbp.groupby(by=['TEAM', 'LABEL'], as_index=False)
             .agg(GPA_SUM=('GPA', 'sum'),
                  ATTEMPTS=('ATTEMPT', 'sum'))
     )
     player_data = pbp.groupby(by=['PLAYER_ID', 'POINTS'], as_index=False).agg(
          ATTEMPTS=('ATTEMPT', 'sum'),
          MAKES=('MAKE', 'sum')
     )
     player_twos = player_data[player_data['POINTS'] == 2].rename(columns={'ATTEMPTS': 'TWOS_ATTEMPTS', 'MAKES': 'TWOS_MAKES'})
     player_threes = player_data[player_data['POINTS'] == 3].rename(columns={'ATTEMPTS': 'THREES_ATTEMPTS', 'MAKES': 'THREES_MAKES'})
     player_fts = player_data[player_data['POINTS'] == 1].rename(columns={'ATTEMPTS': 'FTS_ATTEMPTS', 'MAKES': 'FTS_MAKES'})
     player_data = player_twos.merge(player_threes, on='PLAYER_ID', how='outer').merge(player_fts, on='PLAYER_ID', how='outer').fillna(0)
     
     pbp_gpa['AVG_GPA'] = pbp_gpa['GPA_SUM'] / pbp_gpa[f'ATTEMPTS']
     return pbp_gpa, player_data

# ----------------------------------------------------------------------------
@st.cache_data
def split_grades(this_game_gpa):
     pbp_nda = this_game_gpa[this_game_gpa['TEAM'] == 'NDA']
     pbp_opp = this_game_gpa[this_game_gpa['TEAM'] != 'NDA']
     pbp_nda_gpa = pbp_nda['GPA_SUM'].sum() / pbp_nda['ATTEMPTS'].sum()
     pbp_opp_gpa = pbp_opp['GPA_SUM'].sum() / pbp_opp['ATTEMPTS'].sum()
     return pbp_nda_gpa, pbp_opp_gpa

# ----------------------------------------------------------------------------
@st.cache_data
def get_shot_data(totals_sorted):
     totals_sorted['VALUES'] = totals_sorted['SHOT_SPOT'].str[-1]
     team_totals = (
               totals_sorted.groupby(
                              by=['VALUES', 'PAINT_TOUCH'],
                              as_index=False
                            )
                            .agg(TOTAL_MAKES=('MAKES', 'sum'),
                                 TOTAL_ATTEMPTS=('ATTEMPTS', 'sum'))
     )
     twos = team_totals[team_totals['VALUES'] == '2']
     threes = team_totals[team_totals['VALUES'] == '3']
     three_pt = threes[threes['PAINT_TOUCH'] == 'Y']
     three_no_pt = threes[threes['PAINT_TOUCH'] == 'N']
     total_threes = (
               three_pt['TOTAL_ATTEMPTS'].sum() 
               + three_no_pt['TOTAL_ATTEMPTS'].sum()
     )
     twos_makes = twos['TOTAL_MAKES'].sum()
     twos_attempts = twos['TOTAL_ATTEMPTS'].sum()
     three_pt_makes = three_pt['TOTAL_MAKES'].sum()
     three_pt_attempts = three_pt['TOTAL_ATTEMPTS'].sum()
     three_no_pt_makes = three_no_pt['TOTAL_MAKES'].sum()
     three_no_pt_attempts = three_no_pt['TOTAL_ATTEMPTS'].sum()
     three_total_makes = threes['TOTAL_MAKES'].sum()
     three_total_attempts = threes['TOTAL_ATTEMPTS'].sum()
     if total_threes > 0:
          three_pt_percent = (
               three_pt['TOTAL_ATTEMPTS'].sum() / total_threes
          )
     else:
          three_pt_percent = 0
     fts = team_totals[team_totals['VALUES'] == '1']
     fts_attempts = fts['TOTAL_ATTEMPTS'].sum()
     fts_makes = fts['TOTAL_MAKES'].sum()
     return (twos_makes, twos_attempts, three_pt_makes, three_pt_attempts,
             three_no_pt_makes, three_no_pt_attempts,
             three_total_makes, three_total_attempts,
             three_pt_percent, fts_makes, fts_attempts)

# ----------------------------------------------------------------------------
@st.cache_data
def clean_team_totals(totals):
     totals = (
          totals[totals['SHOT_SPOT'].str[-1] != '1']
                .reset_index(drop=True)
     )
     totals['HG_COUNT'] = totals['HG_PERCENT'] * totals['ATTEMPTS']
     totals_new = (
          totals.groupby(by=['SHOT_SPOT', 'XSPOT', 'YSPOT'],
                         as_index=False)
                .agg(
                     MAKES=('MAKES', 'sum'),
                     ATTEMPTS=('ATTEMPTS', 'sum'),
                     MAKE_PERCENT=('MAKE_PERCENT', 'mean'),
                     HG_COUNT=('HG_COUNT', 'mean'))
     )
     totals_new['POINTS'] = totals['SHOT_SPOT'].str[-1].astype(int)
     totals_new['POINTS_PER_ATTEMPT'] = (
          (totals_new['MAKES']*totals_new['POINTS']) 
          / totals_new['ATTEMPTS']
     ).round(3)
     return totals_new

team_data, opp_data, pbp_data = get_game_data()

team_data_filtered = filter_team_data(team_data=team_data)
opp_data_filtered = filter_team_data(team_data=opp_data)
pbp_data_filtered = filter_team_data(team_data=pbp_data)

season_list = (
     team_data['SEASON'].sort_values(ascending=False).unique().tolist()
)

col1, col2 = st.columns([1, 2])
with col1:
     season = st.radio(
          label='Select Season', options=season_list, horizontal=True
     )

this_year = (
          team_data_filtered[team_data_filtered['SEASON'] == season]
                         .sort_values(by='GAME_ID')
)
games = this_year['U_ID'].unique()
with col2:
     games_selected = st.multiselect(
          label='Choose Games',
          options=reversed(games),
          placeholder='Select one or more games to view shot chart'
     )
if games_selected:

     this_game = get_selected_games(
          games_selected=games_selected, team_data_filtered=team_data_filtered
     )
     this_game_opp = get_selected_games(
          games_selected=games_selected, team_data_filtered=opp_data_filtered
     )
     this_game_pbp = get_selected_games(
          games_selected=games_selected, team_data_filtered=pbp_data_filtered
     )
     this_game_gpa, player_data = get_grades(this_game_pbp)
     pbp_nda_gpa, pbp_opp_gpa = split_grades(this_game_gpa)
     shot_chart, buttons= st.columns([2, 1])
     with buttons:
          select_team = st.radio(
               label='Select to View NDA or Opponent',
               options=['NDA', 'Opponent'],
               horizontal=True
          )
          st.metric(
               label='NDA Shot Selection GPA',
               value=pbp_nda_gpa.round(2)
          )  
          st.metric(
               label='Opponents Shot Selection GPA',
               value=pbp_opp_gpa.round(2)
          )

     if select_team == 'Opponent':
          this_game = this_game_opp

     # ----------------------------------------------------------------------------
     if games_selected:
          totals, totals_sorted = format_selected_games(this_game=this_game)
          (twos_makes, twos_attempts, three_pt_makes, three_pt_attempts,
           three_no_pt_makes, three_no_pt_attempts,
           three_total_makes, three_total_attempts,
           three_pt_percent, fts_makes, fts_attempts) = get_shot_data(
               totals_sorted=totals_sorted
          )
          totals_new = clean_team_totals(totals=totals)
          with buttons:
               st.write('### Shot Selection Totals')
               st.write(f'Two Point Shots: {twos_makes}/{twos_attempts}')
               st.write(f'Three Point Shots with PT: {three_pt_makes}/{three_pt_attempts}')
               st.write(f'Three Point Shots without PT: {three_no_pt_makes}/{three_no_pt_attempts}')
               st.write(f'Total Three Point Shots: {three_total_makes}/{three_total_attempts}')
               st.write(f'Three PT Percentage of Total Threes: {three_pt_percent.round(3)*100}%')
               st.write(f'Free Throws: {fts_makes}/{fts_attempts}')
               st.dataframe(data=player_data, width='stretch')
          fig = ut.load_shot_chart_team(totals=totals_new, team_selected=games_selected)
          fig.update_layout(
               width=700,
               height=500
          )
          with shot_chart:
               st.markdown(
                    body=f"<h1 style='text-align: center; color: black;'>Shot Chart for {select_team}</h1>", 
                    unsafe_allow_html=True
               )
               st.plotly_chart(figure_or_data=fig, width='stretch', selection_mode='points')