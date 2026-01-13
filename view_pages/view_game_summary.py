import streamlit as st
import plotly.express as px
import pandas as pd
import polars as pl
from py import sql, data_source
pd.options.mode.chained_assignment = None

st.cache_resource.clear()
st.set_page_config(layout='wide')
sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']
list_of_stats = [
    'LABEL', 'EFG%', 'TURNOVER_RATE', 'PPA', 
    'POINTS_PER_POSSESSION', 'FREE_THROW_RATE', 'TRUE_SHOOTING_PERCENTAGE',
    'POSSESSIONS', 'OFFENSIVE_EFFICENCY', 
    '2PPA', '3PPA', 'POINTS',
    'GAME_SCORE'
]
other_stats = [
    'OE', 'EFG %', 'TS %', '2 PPA', '3 PPA', 'PPA', 'Points',
    'Game Score', 'Minutes', 'FTR'
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
            + pl.col(name='FTM')
        ),
        FIELD_POINTS_SCORED=(
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
            (pl.col(name='FGA')-pl.col(name='OFFENSIVE_REBOUNDS'))
               + pl.col(name='TURNOVER') 
               + (.44 * pl.col(name='FTA'))
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
          .then(statement=pl.col(name='FIELD_POINTS_SCORED') 
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
        ),
        POINTS_PER_POSSESSION=(
            pl.col(name='POINTS') / pl.col(name='POSSESSIONS')
        ),
        TRUE_SHOOTING_PERCENTAGE=(
            pl.when(condition=pl.col(name='FGA') + (.44 * pl.col(name='FTA')) > 0)
              .then(statement=pl.col(name='POINTS') / (2 * (pl.col(name='FGA') + (.44 * pl.col(name='FTA')))))
              .otherwise(statement=0)
              .alias(name='TS %')
        ),
        FREE_THROW_RATE=(
            pl.when(condition=pl.col(name='FGA') > 0)
                .then(statement=pl.col(name='FTA') / pl.col(name='FGA'))
                .otherwise(statement=0)
                .alias(name='FTR')
        ),
        POSSESSIONS_PER_MINUTE=(
            pl.col('POSSESSIONS') / 36
        )
    )
    data = data.to_pandas()
    return data

# ----------------------------------------------------------------------------
def game_seasons(game_summary, season):
    game_summary_season = (
        game_summary[game_summary['SEASON'] == season]
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
    game_len = game_summary_season['GAME_ID'].nunique()
    player_level = final_data.groupby(by='NAME', as_index=False).sum()
    player_season_avg = game_summary_season.groupby(by='NAME', as_index=False).sum()
    player_level = apply_derived(data=player_level).round(decimals=4)
    player_season_avg = apply_derived(data=player_season_avg).round(decimals=4)
    player_season_avg['GAME_LEN'] = game_len
    player_season_avg['GAME_SCORE'] = player_season_avg['GAME_SCORE'] / player_season_avg['GAME_LEN']
    team_data = team_data.rename(
            columns={
                'OFFENSIVE_EFFICENCY': 'OE',
                'EFG%': 'EFG %',
                '2PPA': '2 PPA',
                '3PPA': '3 PPA',
                'PPA': 'PPA',
                'POINTS': 'Points',
                'GAME_SCORE': 'Game Score',
                'POSSESSIONS': 'Possessions',
                'TURNOVER_RATE': 'TO %',
                'TRUE_SHOOTING_PERCENTAGE': 'TS %',
                'POINTS_PER_POSSESSION': 'PPP',
                'FREE_THROW_RATE': 'FTR'
            }
        )
        
    player_level = player_level.rename(
            columns={
                'OFFENSIVE_EFFICENCY': 'OE',
                'EFG%': 'EFG %',
                'TRUE_SHOOTING_PERCENTAGE': 'TS %',
                '2PPA': '2 PPA',
                '3PPA': '3 PPA',
                'PPA': 'PPA',
                'POINTS': 'Points',
                'GAME_SCORE': 'Game Score',
                'MINUTES_PLAYED': 'Minutes',
                'FREE_THROW_RATE': 'FTR'
            }
    )
    player_season_avg = player_season_avg.rename(
            columns={
                'OFFENSIVE_EFFICENCY': 'OE',
                'EFG%': 'EFG %',
                'TRUE_SHOOTING_PERCENTAGE': 'TS %',
                '2PPA': '2 PPA',
                '3PPA': '3 PPA',
                'PPA': 'PPA',
                'POINTS': 'Points',
                'GAME_SCORE': 'Game Score',
                'MINUTES_PLAYED': 'Minutes',
                'FREE_THROW_RATE': 'FTR'
            }
    )
    return team_data, player_level, player_season_avg

def clean_frames(team_data, player_level, player_season_avg, other_stats):
    team_data['EFG %'] = team_data['EFG %'] * 100
    team_data['TO %'] = team_data['TO %'] * 100
    team_data['TS %'] = team_data['TS %'] * 100
    team_data['FTR'] = team_data['FTR'] * 100
    column_config = {
            "Opponent": st.column_config.Column(width=125),
            'OE': st.column_config.NumberColumn(format="%.2f", width=None),
            '2 PPA': st.column_config.NumberColumn(format="%.2f", width=None),
            '3 PPA': st.column_config.NumberColumn(format="%.2f", width=None),
            'Possessions': st.column_config.NumberColumn(format="%.0f", width=None),
            'PPA': st.column_config.NumberColumn(format="%.2f", width=None),
            'EFG %': st.column_config.NumberColumn(format="%.1f%%", width=None),
            'TO %': st.column_config.NumberColumn(format="%.1f%%", width=None),
            'TS %': st.column_config.NumberColumn(format="%.1f%%", width=None),
            'PPP': st.column_config.NumberColumn(format="%.2f", width=None),
            'FTR': st.column_config.NumberColumn(format="%.1f%%", width=None),
            'NAME': st.column_config.Column(width=125),
            'Minutes': st.column_config.NumberColumn(format="%.0f", width=None),
    }
    team_data['DATE'] = team_data['Opponent'].apply(lambda x: x.split(' - ')[1])
    team_data = team_data.sort_values(by='DATE', ascending=False).reset_index(drop=True)
    team_data = team_data.drop(columns=['DATE'])

    player_level['EFG %'] = player_level['EFG %'] * 100
    player_level['TS %'] = player_level['TS %'] * 100
    player_level['FTR'] = player_level['FTR'] * 100
    player_level['TYPE'] = 'Selected Games'
    player_season_avg_show = player_season_avg[other_stats].round(3)
    player_season_avg_show['NAME'] = player_season_avg['NAME']
    player_season_avg_show['EFG %'] = player_season_avg_show['EFG %'] * 100
    player_season_avg_show['TS %'] = player_season_avg_show['TS %'] * 100
    player_season_avg_show['FTR'] = player_season_avg_show['FTR'] * 100
    player_season_avg_show['TYPE'] = 'Season Average'
    player_level = pd.concat([player_level, player_season_avg_show], ignore_index=True)
    return team_data, player_level, column_config
        

# ============================================================================
game_summary = load_data()
team_data = get_team_games(game_summary=game_summary)
col1, col2, col3 = st.columns([2, 4, 2])
team_data = team_data.to_pandas()
season_list = game_summary['SEASON'].unique().tolist()
season_list = sorted(season_list, reverse=True)

with col1:
    season = st.radio(label='Select Season', options=season_list, horizontal=True)

if season_list:

    game_summary_season = game_seasons(
        game_summary=game_summary, season=season
    )
    games_list = game_summary_season['LABEL'].unique().tolist()
    games_list = reversed(games_list)

    with col2:
        st.session_state.game = st.multiselect(label='Select Games', options=games_list)
    
    if st.session_state.game != []:
        with col3:
            level_view = st.radio(
                label='Select View',
                options=['Team Level', 'Player Level', 'Both'],
                horizontal=True
            )
        team_data, player_level, player_season_avg = get_game_player_details(
            team_data=team_data,
            game_summary_season=game_summary_season,
            game=st.session_state.game
        )
        team_data_clean, player_level, column_config = clean_frames(
            team_data=team_data,
            player_level=player_level,
            player_season_avg=player_season_avg,
            other_stats=other_stats
        )
        player_level_show = player_level[['NAME', 'TYPE'] + other_stats]
        player_level_show = player_level_show[player_level_show['TYPE'] == 'Selected Games']
        player_level_show = player_level_show.drop(columns=['TYPE']).sort_values(by=['Game Score'], ascending=False)
        if level_view == 'Team Level':
            st.text(body='Team Level Data')
            st.dataframe(
                data=team_data_clean,
                width='stretch', 
                hide_index=True,
                column_config=column_config
            )
        elif level_view == 'Player Level':
            st.text(body='Player Level Data')
            st.dataframe(
                data=player_level_show,
                width='stretch', 
                hide_index=True,
                column_config=column_config
            )
        elif level_view == 'Both':
            st.text(body='Team Level Data')
            st.dataframe(
                data=team_data_clean,
                width='stretch', 
                hide_index=True,
                column_config=column_config
            )
            st.text(body='Player Level Data')
            st.dataframe(
                data=player_level_show,
                width='stretch', 
                hide_index=True,
                column_config=column_config
            )
        if level_view in ['Team Level']:
            data = st.radio(
                label='Select Stat', options=other_stats, horizontal=True
            )
            if data:
                
                fig = px.bar(
                    data_frame=player_level.round(1),
                    x=data,
                    y='NAME',
                    orientation='h',
                    text=data,
                    color_discrete_sequence=['green', 'blue'],
                    color='TYPE'
                )
                fig.update_layout(
                    xaxis_title=data,
                    yaxis_title='Player Name',
                    width=800,
                    height=600
                )
                st.plotly_chart(figure_or_data=fig, width='stretch')