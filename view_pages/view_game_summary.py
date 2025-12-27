import streamlit as st
import plotly.express as px
import pandas as pd
import polars as pl
from py import sql, data_source
pd.options.mode.chained_assignment = None

st.cache_resource.clear()

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']
list_of_stats = [
    'LABEL', 'OFFENSIVE_EFFICENCY', 'EFG%', '2PPA', '3PPA',
    'PPA', 'POINTS', 'POSSESSIONS', 'GAME_SCORE', 'TURNOVER_RATE'
]
other_stats = [
    'OE', 'EFG%', '2 PPA', '3 PPA', 'PPA', 'Points',
    'Game Score'
]

# ----------------------------------------------------------------------------
@st.cache_resource
def load_data():
    game_summary = data_source.run_query(
        sql=sql.get_game_summary_sql(), connection=sql_lite_connect
    )
    return game_summary

# ----------------------------------------------------------------------------
def get_team_games(game_summary):
    game_summary_pl = pl.from_pandas(data=game_summary)
    team_data = (
        game_summary_pl.groupby(by='LABEL').sum()
    )
    return team_data


# ----------------------------------------------------------------------------
def apply_derived(data):
    data = pl.from_pandas(data)
    data = data.with_columns(
        TWO_POINTS_SCORED=(2 * pl.col(name='TWO_FGM')),
        THREE_POINTS_SCORED=(3 * pl.col(name='THREE_FGM'))
    )
    data = data.with_columns(
        TOTAL_POINTS_SCORED=(
            pl.col(name='TWO_POINTS_SCORED') 
            + pl.col(name='THREE_POINTS_SCORED')
        ),
        OE_NUM=(
            pl.col(name='FGM') + pl.col(name='ASSISTS')
        ),
        OE_DENOM=(
            pl.col(name='FGA')
            - pl.col(name='OFFENSIVE_REBOUNDS') 
            + pl.col(name='ASSISTS') 
            + pl.col(name='TURNOVER')
        ),
        EFG_NUM=(
            pl.col(name='TWO_FGM') + (1.5*pl.col(name='THREE_FGM'))
        ),
        POSSESSIONS=(
            .96 
            * (pl.col(name='FGA') 
               + pl.col(name='TURNOVER') 
               + (.44 * pl.col(name='FTA')) 
               - pl.col(name='OFFENSIVE_REBOUNDS'))
        )
    )
    data = data.with_columns(
        TURNOVER_RATE=(
            pl.col(name='TURNOVER') / pl.col(name='POSSESSIONS')
        )
    )
    data = data.with_columns(
        pl.when(condition=pl.col(name='TWO_FGA') > 0)
          .then(statement=pl.col(name='TWO_POINTS_SCORED') 
                / pl.col(name='TWO_FGA'))
          .otherwise(statement=0)
          .alias(name='2PPA'),
        pl.when(condition=pl.col(name='THREE_FGA') > 0)
          .then(statement=pl.col(name='THREE_POINTS_SCORED') 
              / pl.col(name='THREE_FGA'))
          .otherwise(statement=0)
          .alias(name='3PPA'),
        pl.when(condition=pl.col(name='FGA') > 0)
          .then(statement=pl.col(name='TOTAL_POINTS_SCORED') 
                / pl.col(name='FGA'))
          .otherwise(statement=0)
          .alias(name='PPA'),
        pl.when(condition=pl.col(name='OE_DENOM') != 0)
          .then(statement=pl.col(name='OE_NUM') 
                / pl.col(name='OE_DENOM'))
          .otherwise(statement=0)
          .alias(name='OFFENSIVE_EFFICENCY'),
        pl.when(condition=pl.col(name='FGA') > 0)
          .then(statement=pl.col(name='EFG_NUM') 
                / pl.col(name='FGA'))
          .otherwise(statement=0)
          .alias(name='EFG%'),

    )
    data = data.with_columns(
        EFF_POINTS=(
            pl.col(name='POINTS') * pl.col(name='OFFENSIVE_EFFICENCY')
        )
    )
    data = data.to_pandas()
    return data

# ----------------------------------------------------------------------------
def game_seasons(game_summary, season):
    game_summary_season = (
        game_summary[game_summary['SEASON'].isin(values=season)]
                    .sort_values(by='GAME_ID')
    )
    return game_summary_season

# ----------------------------------------------------------------------------
def get_game_player_details(team_data, game_summary_season, game):
    final_data = game_summary_season[
            game_summary_season['LABEL'].isin(values=game)
    ]
    team_data = team_data[team_data['LABEL'].isin(values=game)]
    team_data = apply_derived(data=team_data)
    team_data = (
            team_data[list_of_stats]
                     .rename(columns={'LABEL': 'Opponent'})
                     .round(decimals=4)
    )
    player_level = final_data.groupby(by='NAME', as_index=False).sum()
    player_level = apply_derived(data=player_level).round(decimals=4)
    team_data = team_data.rename(
            columns={
                'OFFENSIVE_EFFICENCY': 'OE',
                'EFG%': 'EFG%',
                '2PPA': '2 PPA',
                '3PPA': '3 PPA',
                'PPA': 'PPA',
                'POINTS': 'Points',
                'GAME_SCORE': 'Game Score',
                'POSSESSIONS': 'Possessions',
                'TURNOVER_RATE': 'TO %'
            }
        )
    player_level = player_level.rename(
            columns={
                'OFFENSIVE_EFFICENCY': 'OE',
                'EFG%': 'EFG%',
                '2PPA': '2 PPA',
                '3PPA': '3 PPA',
                'PPA': 'PPA',
                'POINTS': 'Points',
                'GAME_SCORE': 'Game Score'
            }
    )
    return team_data, player_level


# ============================================================================
game_summary = load_data()
team_data = get_team_games(game_summary=game_summary)
col1, col2 = st.columns([2, 4])
team_data = team_data.to_pandas()

season_list = game_summary['SEASON'].unique().tolist()
season_list = sorted(season_list, reverse=True)

with col1:
    season = st.multiselect(label='Select Season', options=season_list)

if season_list:

    game_summary_season = game_seasons(
        game_summary=game_summary, season=season
    )
    games_list = game_summary_season['LABEL'].unique().tolist()
    games_list = reversed(games_list)

    with col2:
        st.session_state.game = st.multiselect(label='Select Games', options=games_list)
    
    if st.session_state.game != []:
        team_data, player_level = get_game_player_details(
            team_data=team_data,
            game_summary_season=game_summary_season,
            game=st.session_state.game
        )
        st.text(body='Team Level Data')
        team_data['EFG%'] = team_data['EFG%'] * 100
        team_data['TO %'] = team_data['TO %'] * 100
        column_config = {
            "Opponent": st.column_config.Column(width=125),
            'OE': st.column_config.NumberColumn(format="%.2f"),
            '2 PPA': st.column_config.NumberColumn(format="%.2f"),
            '3 PPA': st.column_config.NumberColumn(format="%.2f"),
            'Possessions': st.column_config.NumberColumn(format="%.0f"),
            'PPA': st.column_config.NumberColumn(format="%.2f"),
            'EFG%': st.column_config.NumberColumn(format="%.1f%%"),
            'TO %': st.column_config.NumberColumn(format="%.1f%%"),
        }
        st.dataframe(
            data=team_data,
            width='stretch', 
            hide_index=True,
            column_config=column_config
        )

        data = st.radio(
            label='Select Stat', options=other_stats, horizontal=True
        )

        if data:
            fig = px.bar(
                data_frame=player_level,
                x=data,
                y='NAME',
                orientation='h',
                text=data,
                color_discrete_sequence=['green']
            )
            st.plotly_chart(figure_or_data=fig, width='stretch')
