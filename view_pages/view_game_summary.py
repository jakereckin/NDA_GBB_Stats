import streamlit as st
import pandas as pd
import polars as pl
from py import sql, data_source, view_ui

st.set_page_config(page_title='Game Summary', layout='wide')
st.title('Game Summary')
st.caption(
    'A coach-friendly recap of scoring, shooting, ball movement, and player impact.'
)
sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

# ----------------------------------------------------------------------------
@st.cache_data(ttl='15m', max_entries=1, show_spinner='Loading game stats...')
def load_data():
    game_summary = data_source.run_query(
        sql=sql.get_game_summary_sql(), connection=sql_lite_connect
    )
    return game_summary

# ----------------------------------------------------------------------------
def get_team_games(game_summary):
    game_summary_pl = pl.from_pandas(data=game_summary)
    team_data = (
        game_summary_pl.groupby(by=['SEASON', 'LABEL']).sum()
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
        pl.when(condition=pl.col(name='FGA') > 0)
          .then(pl.col(name='FGM') / pl.col(name='FGA'))
          .otherwise(0)
          .alias(name='FG %'),
        pl.when(condition=pl.col(name='THREE_FGA') > 0)
          .then(pl.col(name='THREE_FGM') / pl.col(name='THREE_FGA'))
          .otherwise(0)
          .alias(name='3P %'),
        pl.when(condition=pl.col(name='FTA') > 0)
          .then(pl.col(name='FTM') / pl.col(name='FTA'))
          .otherwise(0)
          .alias(name='FT %'),
        REBOUNDS=(
            pl.col(name='OFFENSIVE_REBOUNDS')
            + pl.col(name='DEFENSIVE_REBOUNDS')
        ),
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
    game_summary_season = game_summary[
        game_summary['SEASON'] == season
    ].copy()
    game_summary_season['_GAME_DATE'] = pd.to_datetime(
        game_summary_season['DATE'],
        errors='coerce'
    )
    return (
        game_summary_season
        .sort_values(
            by=['_GAME_DATE', 'GAME_ID'],
            ascending=[False, False],
            na_position='last'
        )
        .drop(columns='_GAME_DATE')
    )

# ----------------------------------------------------------------------------
def get_player_leaderboard(game_summary_season, selected_games):
    selected_data = game_summary_season[
        game_summary_season['LABEL'].isin(selected_games)
    ]
    if selected_data.empty:
        return pd.DataFrame()

    player_totals = (
        selected_data.groupby('NAME', as_index=False)
        .sum(numeric_only=True)
    )
    games_played = (
        selected_data.groupby('NAME')['GAME_ID']
        .nunique()
        .rename('Games')
        .reset_index()
    )
    player_totals = player_totals.merge(games_played, on='NAME')
    player_totals = apply_derived(player_totals)

    per_game_stats = {
        'POINTS': 'Points / game',
        'REBOUNDS': 'Rebounds / game',
        'ASSISTS': 'Assists / game',
        'STEALS': 'Steals / game',
        'BLOCKS': 'Blocks / game',
        'TURNOVER': 'Turnovers / game',
        'MINUTES_PLAYED': 'Minutes / game',
        'GAME_SCORE': 'Game Score / game',
    }
    for source, display in per_game_stats.items():
        player_totals[display] = (
            player_totals[source] / player_totals['Games']
        )

    player_totals['FG %'] *= 100
    player_totals['3P %'] *= 100
    player_totals['FT %'] *= 100
    player_totals['eFG %'] = player_totals['EFG%'] * 100
    player_totals['2 PPA'] = player_totals['2PPA']
    player_totals['3 PPA'] = player_totals['3PPA']
    columns = [
        'NAME', 'Games', 'Points / game', 'Rebounds / game',
        'Assists / game', 'Steals / game', 'Blocks / game',
        'Turnovers / game', 'Minutes / game', 'FG %', '2 PPA', '3 PPA',
        'PPA', '3P %', 'FT %', 'eFG %', 'Game Score / game'
    ]
    return (
        player_totals[columns]
        .rename(columns={'NAME': 'Player'})
        .sort_values(
            by=['Points / game', 'Game Score / game'],
            ascending=False
        )
        .round(1)
        .reset_index(drop=True)
    )


def get_game_log(team_data, selected_games):
    game_log = apply_derived(team_data[
        team_data['LABEL'].isin(selected_games)
    ].copy())
    if game_log.empty:
        return game_log

    opponent_and_date = game_log['LABEL'].str.split('-', n=1, expand=True)
    game_log['Opponent'] = opponent_and_date[0].str.strip()
    game_log['_GAME_DATE'] = pd.to_datetime(
        opponent_and_date[1].str.strip(),
        errors='coerce'
    )
    game_log['Date'] = game_log['_GAME_DATE'].dt.strftime('%b %d, %Y')
    game_log['3PT'] = (
        game_log['THREE_FGM'].astype(int).astype(str)
        + '/'
        + game_log['THREE_FGA'].astype(int).astype(str)
    )
    game_log['FG'] = (
        game_log['FGM'].astype(int).astype(str)
        + '/'
        + game_log['FGA'].astype(int).astype(str)
    )
    game_log['eFG %'] = game_log['EFG%'] * 100
    return (
        game_log[[
            'Date', 'Opponent', 'POINTS', 'FG', '3PT', 'eFG %',
            'ASSISTS', 'TURNOVER', 'REBOUNDS', 'STEALS', '_GAME_DATE'
        ]]
        .rename(columns={
            'POINTS': 'NDA points',
            'ASSISTS': 'Assists',
            'TURNOVER': 'Turnovers',
            'REBOUNDS': 'Rebounds',
            'STEALS': 'Steals'
        })
        .sort_values('_GAME_DATE', ascending=False, na_position='last')
        .drop(columns='_GAME_DATE')
        .reset_index(drop=True)
    )


def get_summary_values(team_data, selected_games):
    selected_team_data = team_data[
        team_data['LABEL'].isin(selected_games)
    ]
    totals = selected_team_data.select_dtypes(include='number').sum()
    summary = apply_derived(totals.to_frame().T)
    game_count = selected_team_data['LABEL'].nunique()
    return {
        'games': game_count,
        'points_per_game': summary['POINTS'].iloc[0] / game_count,
        'oe': summary['OFFENSIVE_EFFICENCY'].iloc[0],
        'efg_percent': summary['EFG%'].iloc[0] * 100,
        'game_score_per_game': summary['GAME_SCORE'].iloc[0] / game_count,
        'ppa': summary['PPA'].iloc[0],
        'two_ppa': summary['2PPA'].iloc[0],
        'three_ppa': summary['3PPA'].iloc[0],
        'ppp': summary['POINTS_PER_POSSESSION'].iloc[0],
        'assists_per_game': summary['ASSISTS'].iloc[0] / game_count,
        'turnovers_per_game': summary['TURNOVER'].iloc[0] / game_count,
        'rebounds_per_game': summary['REBOUNDS'].iloc[0] / game_count,
        'steals_per_game': summary['STEALS'].iloc[0] / game_count,
        'blocks_per_game': summary['BLOCKS'].iloc[0] / game_count,
    }


def get_shooting_breakdown(team_data, selected_games):
    selected_team_data = team_data[
        team_data['LABEL'].isin(selected_games)
    ]
    totals = selected_team_data.select_dtypes(include='number').sum()
    shot_types = [
        ('2-point', 'TWO_FGM', 'TWO_FGA'),
        ('3-point', 'THREE_FGM', 'THREE_FGA'),
        ('Free throw', 'FTM', 'FTA')
    ]
    breakdown = []
    for label, makes_column, attempts_column in shot_types:
        makes = totals[makes_column]
        attempts = totals[attempts_column]
        percentage = makes / attempts * 100 if attempts else 0
        breakdown.append({
            'Shot type': label,
            'Made / attempted': f'{makes:.0f} / {attempts:.0f}',
            'Make %': percentage
        })
    return breakdown


def get_activity_breakdown(team_data, selected_games, game_count):
    selected_team_data = team_data[
        team_data['LABEL'].isin(selected_games)
    ]
    totals = selected_team_data.select_dtypes(include='number').sum()
    return pd.DataFrame({
        'Team stat': [
            'Assists / game', 'Turnovers / game', 'Rebounds / game',
            'Steals / game', 'Blocks / game'
        ],
        'Average': [
            totals['ASSISTS'] / game_count,
            totals['TURNOVER'] / game_count,
            (
                totals['OFFENSIVE_REBOUNDS']
                + totals['DEFENSIVE_REBOUNDS']
            ) / game_count,
            totals['STEALS'] / game_count,
            totals['BLOCKS'] / game_count
        ]
    }).round(1)


def get_detailed_team_stats(team_data, selected_games):
    selected_data = team_data[
        team_data['LABEL'].isin(selected_games)
    ].copy()
    if selected_data.empty:
        return pd.DataFrame()

    detailed = apply_derived(selected_data)
    opponent_and_date = detailed['LABEL'].str.split('-', n=1, expand=True)
    detailed['Opponent'] = opponent_and_date[0].str.strip()
    detailed['_GAME_DATE'] = pd.to_datetime(
        opponent_and_date[1].str.strip(),
        errors='coerce'
    )
    detailed['Date'] = detailed['_GAME_DATE'].dt.strftime('%b %d, %Y')
    detailed = detailed.rename(columns={
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
    })
    for column in ['EFG %', 'TO %', 'TS %', 'FTR']:
        detailed[column] *= 100

    return (
        detailed[[
            'Date', 'Opponent', 'Points', 'OE', 'EFG %', 'TS %',
            '2 PPA', '3 PPA', 'PPA', 'PPP', 'FTR', 'Possessions',
            'TO %', 'Game Score', '_GAME_DATE'
        ]]
        .sort_values('_GAME_DATE', ascending=False, na_position='last')
        .drop(columns='_GAME_DATE')
        .round(2)
        .reset_index(drop=True)
    )


def get_detailed_player_stats(game_summary_season, selected_games):
    selected_data = game_summary_season[
        game_summary_season['LABEL'].isin(selected_games)
    ]
    if selected_data.empty:
        return pd.DataFrame()

    player_totals = (
        selected_data.groupby('NAME', as_index=False)
        .sum(numeric_only=True)
    )
    detailed = apply_derived(player_totals)
    detailed['EFG %'] = detailed['EFG%'] * 100
    detailed['TS %'] = detailed['TRUE_SHOOTING_PERCENTAGE'] * 100
    detailed['FTR'] = detailed['FREE_THROW_RATE'] * 100
    detailed = detailed.rename(columns={
        'NAME': 'Player',
        'MINUTES_PLAYED': 'Minutes',
        'OFFENSIVE_EFFICENCY': 'OE',
        '2PPA': '2 PPA',
        '3PPA': '3 PPA',
        'POINTS': 'Points',
        'GAME_SCORE': 'Game Score'
    })
    return (
        detailed[[
            'Player', 'OE', 'EFG %', 'TS %', '2 PPA', '3 PPA',
            'PPA', 'Points', 'Game Score', 'Minutes', 'FTR'
        ]]
        .sort_values('Game Score', ascending=False)
        .round(2)
        .reset_index(drop=True)
    )


# ============================================================================
game_summary = load_data()
team_data = get_team_games(game_summary=game_summary).to_pandas()
season_list = sorted(game_summary['SEASON'].dropna().unique().tolist(), reverse=True)

st.subheader('Select a season and game')
if not season_list:
    st.info('No game summaries are available yet.')
else:
    season_col, games_col = st.columns([1, 3], vertical_alignment='bottom')
    with season_col:
        season = view_ui.select_season(
            options=season_list,
            key='game_summary_season'
        )

    game_summary_season = game_seasons(
        game_summary=game_summary,
        season=season
    )
    team_data_season = team_data[team_data['SEASON'] == season]
    games_list = game_summary_season['LABEL'].drop_duplicates().tolist()
    with games_col:
        selected_games = view_ui.select_games(
            label='Games',
            options=games_list,
            key='game_summary_games',
            help='Choose one game for a recap or several games to compare averages.'
        )

    if not selected_games:
        st.info('Choose a game to see the team recap and player leaders.')
    else:
        view_ui.render_page_context(
            page_key='view_game_summary',
            scope=f'{season} season · {len(selected_games)} game(s)'
        )
        summary = get_summary_values(team_data_season, selected_games)
        st.subheader('Team at a glance')
        if len(selected_games) == 1:
            st.caption(
                'Key team stats for the selected game. OE and Game Score use '
                'the same definitions shown in All stats.'
            )
        else:
            st.caption(
                f'Per-game averages across {summary["games"]} selected games. '
                'Shooting percentages are calculated from combined makes and attempts.'
            )

        priority_stat_rows = (
            (
                ('Offensive efficiency (OE)', f'{summary["oe"]:.2f}',
                 'Field goals made plus assists, divided by estimated possessions used.'),
                ('Game Score / game', f'{summary["game_score_per_game"]:.1f}',
                 'Combined player Game Score, averaged over selected games.'),
                ('Effective FG%', f'{summary["efg_percent"]:.1f}%',
                 'Shooting efficiency adjusted for the extra value of made threes.'),
                ('PPP', f'{summary["ppp"]:.2f}',
                 'Points scored per estimated possession.')
            ),
            (
                ('PPA', f'{summary["ppa"]:.2f}',
                 'Points scored per field-goal attempt.'),
                ('2 PPA', f'{summary["two_ppa"]:.2f}',
                 'Two-point scoring value per two-point attempt.'),
                ('3 PPA', f'{summary["three_ppa"]:.2f}',
                 'Three-point scoring value per three-point attempt.')
            )
        )
        for stat_row in priority_stat_rows:
            priority_stats = st.columns(len(stat_row))
            for stat_col, (label, value, help_text) in zip(
                priority_stats,
                stat_row
            ):
                with stat_col:
                    with st.container(border=True):
                        st.metric(label=label, value=value, help=help_text)

        team_totals = st.columns(4)
        for stat_col, label, value in (
            (
                team_totals[0], 'Points / game',
                f'{summary["points_per_game"]:.1f}'
            ),
            (
                team_totals[1], 'Rebounds / game',
                f'{summary["rebounds_per_game"]:.1f}'
            ),
            (
                team_totals[2], 'Assists / game',
                f'{summary["assists_per_game"]:.1f}'
            ),
            (
                team_totals[3], 'Turnovers / game',
                f'{summary["turnovers_per_game"]:.1f}'
            )
        ):
            with stat_col:
                st.metric(label=label, value=value)

        overview_tab, player_tab, game_log_tab, detailed_tab = st.tabs([
            'Team recap', 'Player leaders', 'Game log', 'All stats'
        ])
        with overview_tab:
            st.markdown('#### Shooting breakdown')
            st.caption(
                'Bars show make percentage; totals combine all selected games.'
            )
            shooting_cols = st.columns(3)
            for shot_col, shot in zip(
                shooting_cols,
                get_shooting_breakdown(team_data_season, selected_games)
            ):
                with shot_col:
                    with st.container(border=True):
                        st.markdown(f'**{shot["Shot type"]}**')
                        st.progress(
                            max(0, min(100, int(round(shot['Make %'])))),
                            text=(
                                f'{shot["Made / attempted"]} · '
                                f'{shot["Make %"]:.1f}%'
                            )
                        )
            st.markdown('#### Ball movement and defense')
            activity = get_activity_breakdown(
                team_data_season,
                selected_games,
                summary['games']
            )
            for start, row_size in ((0, 3), (3, 2)):
                activity_cols = st.columns(row_size)
                for offset, stat_col in enumerate(activity_cols):
                    stat = activity.iloc[start + offset]
                    with stat_col:
                        st.metric(
                            label=stat['Team stat'],
                            value=f'{stat["Average"]:.1f}'
                        )
        with player_tab:
            player_leaderboard = get_player_leaderboard(
                game_summary_season,
                selected_games
            )
            if player_leaderboard.empty:
                st.info('No player box-score data was found for these games.')
            else:
                filter_cols = st.columns(2)
                with filter_cols[0]:
                    min_games_played = st.number_input(
                        'Minimum games played',
                        min_value=1,
                        max_value=max(1, len(selected_games)),
                        value=1,
                        step=1,
                        key='game_summary_min_games',
                        help='Only include players with a box-score record in at least this many selected games.'
                    )
                with filter_cols[1]:
                    min_minutes_per_game = st.number_input(
                        'Minimum minutes per game',
                        min_value=0.0,
                        max_value=40.0,
                        value=0.0,
                        step=1.0,
                        key='game_summary_min_minutes',
                        help='Only include players who average at least this many minutes per game.'
                    )
                eligible_players = player_leaderboard[
                    (player_leaderboard['Games'] >= min_games_played)
                    & (
                        player_leaderboard['Minutes / game']
                        >= min_minutes_per_game
                    )
                ]
                leader_stats = [
                    'Points / game',
                    'Game Score / game',
                    'eFG %',
                    'PPA',
                    '2 PPA',
                    '3 PPA',
                    'Rebounds / game',
                    'Assists / game',
                    'Steals / game',
                    'Blocks / game',
                    'Turnovers / game',
                    'Minutes / game',
                    'FG %',
                    '3P %',
                    'FT %',
                ]
                selected_leader_stats = st.multiselect(
                    'Stats to view leaders on',
                    options=leader_stats,
                    default=['Points / game', 'Game Score / game', 'eFG %'],
                    max_selections=5,
                    key='game_summary_leader_stats',
                    help='Choose up to five stats. Turnovers rank lowest first; other stats rank highest first.'
                )
                percentage_stats = {'FG %', '3P %', 'FT %', 'eFG %'}
                per_game_stats = {
                    'Points / game', 'Rebounds / game', 'Assists / game',
                    'Steals / game', 'Blocks / game', 'Turnovers / game',
                    'Minutes / game', 'Game Score / game'
                }
                if selected_leader_stats:
                    if eligible_players.empty:
                        st.info(
                            'No players meet both playing-time minimums. '
                            'Lower one or both filters to view leaders.'
                        )
                    else:
                        leader_cols = st.columns(2)
                        for index, stat_name in enumerate(selected_leader_stats):
                            stat_ranking = eligible_players.sort_values(
                                stat_name,
                                ascending=(stat_name == 'Turnovers / game'),
                                kind='stable'
                            ).head(3)
                            leader = stat_ranking.iloc[0]

                            def format_leader_value(value):
                                if stat_name in percentage_stats:
                                    return f'{value:.1f}%'
                                if stat_name in per_game_stats:
                                    return f'{value:.1f}'
                                return f'{value:.2f}'

                            with leader_cols[index % 2]:
                                with st.container(border=True):
                                    st.markdown(f'#### {stat_name}')
                                    st.metric(
                                        label='Leader is',
                                        value=(
                                            f'{leader["Player"]} '
                                            f'({format_leader_value(leader[stat_name])})'
                                        )
                                    )
                                    runner_ups = [
                                        (
                                            f'{rank}. {row["Player"]} '
                                            f'({format_leader_value(row[stat_name])})'
                                        )
                                        for rank, (_, row) in enumerate(
                                            stat_ranking.iloc[1:].iterrows(),
                                            start=2
                                        )
                                    ]
                                    if runner_ups:
                                        st.caption(' · '.join(runner_ups))
                st.caption(
                    'Per-game counting stats are divided by each player’s games '
                    'played; shooting percentages are calculated from combined makes and attempts.'
                )
                st.dataframe(
                    eligible_players,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        'Games': st.column_config.NumberColumn(
                            help='Selected games in which the player has a box-score record.'
                        ),
                        'FG %': st.column_config.NumberColumn(format='%.1f%%'),
                        '3P %': st.column_config.NumberColumn(format='%.1f%%'),
                        'FT %': st.column_config.NumberColumn(format='%.1f%%'),
                        'eFG %': st.column_config.NumberColumn(format='%.1f%%'),
                    }
                )
        with game_log_tab:
            st.caption(
                'Use the game log to spot scoring and ball-security trends '
                'across the selected games.'
            )
            st.dataframe(
                get_game_log(team_data_season, selected_games),
                width='stretch',
                hide_index=True,
                column_config={
                    'NDA points': st.column_config.NumberColumn(),
                    'eFG %': st.column_config.NumberColumn(format='%.1f%%'),
                }
            )
        with detailed_tab:
            st.caption(
                'All advanced stats previously available are retained here. '
                'Team stats are shown for each selected game; player totals '
                'combine the selected games.'
            )
            st.markdown('#### Team stats by game')
            st.dataframe(
                get_detailed_team_stats(team_data_season, selected_games),
                width='stretch',
                hide_index=True,
                column_config={
                    'OE': st.column_config.NumberColumn(
                        help='Offensive efficiency: (field goals made + assists) divided by estimated possessions used.'
                    ),
                    'EFG %': st.column_config.NumberColumn(format='%.1f%%'),
                    'TS %': st.column_config.NumberColumn(format='%.1f%%'),
                    'TO %': st.column_config.NumberColumn(format='%.1f%%'),
                    'FTR': st.column_config.NumberColumn(format='%.1f%%'),
                }
            )
            st.markdown('#### Player stats across selected games')
            st.dataframe(
                get_detailed_player_stats(game_summary_season, selected_games),
                width='stretch',
                hide_index=True,
                column_config={
                    'OE': st.column_config.NumberColumn(
                        help='Offensive efficiency: (field goals made + assists) divided by estimated possessions used.'
                    ),
                    'EFG %': st.column_config.NumberColumn(format='%.1f%%'),
                    'TS %': st.column_config.NumberColumn(format='%.1f%%'),
                    'FTR': st.column_config.NumberColumn(format='%.1f%%'),
                }
            )