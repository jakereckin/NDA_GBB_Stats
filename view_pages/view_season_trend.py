import streamlit as st
import plotly.express as px
import pandas as pd
import polars as pl
import numpy as np
from py import sql, data_source
import plotly.graph_objects as go
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
        game_summary_pl.groupby(by=['LABEL', 'SEASON']).sum()
    )
    return team_data


# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
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
@st.cache_data(show_spinner=True)
def game_seasons(game_summary, season):
    game_summary_season = (
        game_summary[game_summary['SEASON'] == season]
                    .sort_values(by='GAME_ID')
    )
    return game_summary_season

# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def get_game_player_details(team_data, game_summary_season, season):
    final_data = game_summary_season
    team_data = team_data[team_data['SEASON'] == season]
    team_data = apply_derived(data=team_data)
    team_data = (
            team_data[list_of_stats]
                     .rename(columns={'LABEL': 'Opponent'})
                     .round(decimals=4)
    )
    game_len = game_summary_season['GAME_ID'].nunique()
    player_level = final_data.groupby(by=['NAME', 'LABEL'], as_index=False).sum()
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
    player_level['Date'] = player_level['LABEL'].apply(lambda x: x.split(' - ')[1])
    player_level['Date'] = pd.to_datetime(player_level['Date']).dt.date
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
    team_data['Date'] = team_data['Opponent'].apply(lambda x: x.split(' - ')[1])
    team_data['Date'] = pd.to_datetime(team_data['Date']).dt.date
    player_level = player_level.sort_values(by='Date', ascending=True).reset_index(drop=True)
    return team_data, player_level, player_season_avg

# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
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
    team_data = team_data.sort_values(by='Date', ascending=True).reset_index(drop=True)
    return team_data, player_level, column_config


# ============================================================================
game_summary = load_data()
team_data = get_team_games(game_summary=game_summary)
col1, col2, col3 = st.columns([2, 2, 4])
team_data = team_data.to_pandas()
season_list = game_summary['SEASON'].unique().tolist()
season_list = sorted(season_list, reverse=True)

with col1:
    season = st.radio(label='Select Season', options=season_list, horizontal=True)

game_summary_season = game_seasons(game_summary=game_summary, season=season)
team_data, player_level, player_season_avg = get_game_player_details(
    team_data=team_data,
    game_summary_season=game_summary_season,
    season=season
)

with col2:
    select_level = st.radio(
        label='Select Data Level',
        options=['Team', 'Player'],
        horizontal=True
    )

if select_level == 'Team':
    team_data_clean, player_level, column_config = clean_frames(
        team_data=team_data,
        player_level=player_level,
        player_season_avg=player_season_avg,
        other_stats=other_stats
    )

    choose_stats = team_data_clean.columns.tolist()[1:-1]
    with col3:
        choose_stats = st.selectbox(label='Choose Stats to Show', options=choose_stats)

    y = pd.to_numeric(team_data_clean[choose_stats], errors='coerce').fillna(0).values
    x_labels = team_data_clean['Opponent'].astype(str).tolist()
    x_idx = np.arange(len(x_labels))

    fig = go.FigureWidget()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=y,
            mode="lines+markers",
            name=choose_stats,
            marker=dict(size=8),
            line=dict(width=2)
        )
    )

    if len(x_idx) > 1:
        coeffs = np.polyfit(x_idx, y, 1)
        trend_y = np.polyval(coeffs, x_idx)
        # R-squared
        ss_res = np.sum((y - trend_y) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2) if np.sum((y - np.mean(y)) ** 2) != 0 else 1
        r2 = 1 - ss_res / ss_tot

        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=trend_y,
                mode="lines",
                name=f"Trendline (slope={coeffs[0]:.3f}, R²={r2:.3f})",
                line=dict(dash="dash", color="red", width=2),
                hoverinfo="text",
                hovertext=[f"{label}: {val:.2f}" for label, val in zip(x_labels, trend_y)]
            )
        )

    fig.update_layout(
        xaxis_title="Opponent",
        yaxis_title=choose_stats,
        xaxis_tickangle=-45,
        margin=dict(l=40, r=20, t=40, b=120),
        height=420
    )

    st.plotly_chart(fig, use_container_width=True)

elif select_level == 'Player':
    team_data, player_level, column_config = clean_frames(
        team_data=team_data,
        player_level=player_level,
        player_season_avg=player_season_avg,
        other_stats=other_stats
    )

    player_list = player_level['NAME'].unique().tolist()
    with col3:
        choose_stats = st.selectbox(label='Choose Stats to Show', options=other_stats)

    player_select = st.radio(label='Select Player', options=player_list, horizontal=True)
    this_player = player_level[player_level['NAME'] == player_select].reset_index(drop=True)

    # ensure chosen stat is numeric and handle missing values
    y_series = pd.to_numeric(this_player[choose_stats], errors='coerce').fillna(0)
    x_labels = this_player['LABEL'].astype(str).tolist()
    x_idx = np.arange(len(x_labels))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=y_series,
            mode="lines+markers",
            name=choose_stats,
            marker=dict(size=8),
            line=dict(width=2),
            connectgaps=False
        )
    )

    if len(x_idx) > 1:
        coeffs = np.polyfit(x_idx, y_series.values, 1)
        trend_y = np.polyval(coeffs, x_idx)
        ss_res = np.sum((y_series.values - trend_y) ** 2)
        ss_tot = np.sum((y_series.values - np.mean(y_series.values)) ** 2) or 1
        r2 = 1 - ss_res / ss_tot

        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=trend_y,
                mode="lines",
                name=f"Trendline (slope={coeffs[0]:.3f}, R²={r2:.3f})",
                line=dict(dash="dash", color="red", width=2),
                hoverinfo="text",
                hovertext=[f"{lbl}: {val:.2f}" for lbl, val in zip(x_labels, trend_y)]
            )
        )

    fig.update_layout(
        xaxis_title="Game (Opponent - Date)",
        yaxis_title=choose_stats,
        xaxis_tickangle=-45,
        margin=dict(l=40, r=20, t=40, b=120),
        height=420,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)
