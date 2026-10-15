import streamlit as st
import numpy as np
import pandas as pd
import ast
import plotly.express as px
import plotly.graph_objects as go
from py import sql, data_source, view_ui
pd.options.mode.chained_assignment = None

st.set_page_config(page_title='Minutes and Lineups', layout='wide')
st.title('Minutes and Lineups')
st.caption('Inspect player workload, lineup performance, and scoring margin by season.')

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

_PLAYER_LINEUPS_MAP_NAMES = {
    'TOTAL_MIN': 'Total Minutes Played',
    'POINTS_PER_MINUTE': 'Team Points per Minute',
    'OPP_POINTS_PER_MINUTE': 'Opponent Points per Minute',
    'PLUS_MINUS_PER_MINUTE': 'Scoring Margin per Minute',
    'GAME_COUNT': 'Games Played'
}

_PLAYER_MAP_NAMES = {
    'GAME_COUNT': 'Games Played',
    'POINTS_PER_MINUTE': 'Team Points per Minute on Court',
    'OPP_POINTS_PER_MINUTE': 'Opponent Points per Minute on Court',
    'PLUS_MINUS_PER_MINUTE': 'Scoring Margin per Minute on Court',
    'MINUTES_PER_GAME': 'Minutes per Game'
}

button = st.button(label='Clear Cache Data')
if button:
    st.cache_data.clear()
    st.cache_resource.clear()

# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def get_data():
    minute_data = data_source.run_query(
        sql=sql.view_minutes_sql(), connection=sql_lite_connect
    )
    return minute_data

# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def build_lineup_intervals(minutes_data, game_end_sec=36*60):
    out_rows = []
    for game_id, grp in minutes_data.groupby('GAME_ID'):
        grp = grp.reset_index(drop=True)
        # unique event times: all IN_SEC and OUT_SEC clipped to [0, game_end_sec]
        times = np.unique(np.clip(np.concatenate([grp['TIME_IN'].values, grp['TIME_OUT'].values]), 0, game_end_sec))
        times = np.sort(times)
        # ensure we include start 0 and final end
        if times[0] != 0:
            times = np.insert(times, 0, 0)
        if times[-1] != game_end_sec:
            times = np.append(times, game_end_sec)
        times = list(reversed(times))
        # iterate intervals
        for i in range(len(times) - 1):
            start = int(times[i])
            end = int(times[i + 1])
            duration = start - end
            if duration <= 0:
                continue
            present = grp[(grp['TIME_IN'] >= start) & (grp['TIME_OUT'] <= end)]
            score_in_frame = grp[(grp['TIME_IN'] == start)]
            score_out_frame = grp[(grp['TIME_OUT'] == end)]
            my_frame = pd.DataFrame()
            my_lineup_players = present['PLAYER_ID'].astype(int).tolist()
            score_in = score_in_frame['TEAM_POINT_IN'].drop_duplicates().min()
            score_out = score_out_frame['TEAM_POINT_OUT'].drop_duplicates().min()
            opp_score_in = score_in_frame['OPP_POINT_IN'].drop_duplicates().min()
            opp_score_out = score_out_frame['OPP_POINT_OUT'].drop_duplicates().min()
            my_times = (start, end)
            lineup_key = tuple(sorted(my_lineup_players))
            lineup_start, lineup_end = my_times
            my_dict = {
                'TIME_IN': lineup_start,
                'TIME_OUT': lineup_end,
                'LINEUP_KEY': str(lineup_key),
                'SCORE_IN': score_in,
                'SCORE_OUT': score_out,
                'OPP_SCORE_IN': opp_score_in,
                'OPP_SCORE_OUT': opp_score_out,
                'GAME_ID': game_id
            }
            out_rows.append(my_dict)
    clean_lineups = pd.DataFrame(out_rows)

    clean_lineups['SECONDS_PLAYED'] = (
        clean_lineups['TIME_IN'] - clean_lineups['TIME_OUT']
    )
    clean_lineups['MIN_PLAYED'] = (
        clean_lineups['SECONDS_PLAYED'] / 60
    )
    clean_lineups['MIN_PLAYED'] = np.where(
        clean_lineups['MIN_PLAYED'] < 1, 1, clean_lineups['MIN_PLAYED']
    )
    clean_lineups['POINTS_SCORED'] = (
        clean_lineups['SCORE_OUT'] - clean_lineups['SCORE_IN']
    )
    clean_lineups['OPP_POINTS_SCORED'] = (
        clean_lineups['OPP_SCORE_OUT'] - clean_lineups['OPP_SCORE_IN']
    )
    return clean_lineups

def build_player_only(minute_data):
    minute_data['SECONDS_PLAYED'] = (
        minute_data['TIME_IN'] - minute_data['TIME_OUT']
    )
    minute_data['MIN_PLAYED'] = (
        minute_data['SECONDS_PLAYED'] / 60
    )
    minute_data['POINTS_SCORED'] = (
        minute_data['TEAM_POINT_OUT'] - minute_data['TEAM_POINT_IN']
    )
    minute_data['OPP_POINTS_SCORED'] = (
        minute_data['OPP_POINT_OUT'] - minute_data['OPP_POINT_IN']
    )
    return minute_data

def group_data(clean_lineups, game_dict):
    grouped_line_data = (
        clean_lineups.groupby(by=['LINEUP_KEY', 'GAME_ID'], as_index=False)
                     .agg(TOTAL_MIN=('MIN_PLAYED', 'sum'),
                          POINTS_SCORED=('POINTS_SCORED', 'sum'),
                          OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum'))
    )
    grouped_line_data['OPPONENT'] = grouped_line_data['GAME_ID'].map(game_dict)
    return grouped_line_data

def get_game_player_info(minutes_data):
    games_info = minutes_data[['GAME_ID', 'GAME_DATE']].drop_duplicates()
    player_info = minutes_data[['GAME_ID', 'PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()
    return games_info, player_info

def get_unique_lineups(grouped_lineups, player_info):
    unique_player_lineups = {}
    unique_lineups = grouped_lineups['LINEUP_KEY'].unique().tolist()
    unique_lineups = [ast.literal_eval(lineup) for lineup in unique_lineups]
    my_players = player_info['PLAYER_ID'].unique().tolist()
    my_players = [int(player) for player in my_players]
    for player in my_players:
        player_lineups = []
        for lineup in unique_lineups:
            if player in lineup:
                player_lineups.append(lineup)
        unique_player_lineups[player] = player_lineups
    return unique_player_lineups, my_players

def get_lineup_level_data(data):
    lineup_level = (
        data.groupby(by=['LINEUP_KEY'], as_index=False)
            .agg(
                GAME_COUNT=('OPPONENT', 'count'),
                TOTAL_MIN=('TOTAL_MIN', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    lineup_level['POINTS_SCORED_PER_GAME'] = (
        lineup_level['POINTS_SCORED'] / lineup_level['GAME_COUNT']
    )
    lineup_level['POINTS_PER_MINUTE'] = (
        lineup_level['POINTS_SCORED'] / lineup_level['TOTAL_MIN']
    )
    lineup_level['OPP_POINTS_PER_MINUTE'] = (
        lineup_level['OPP_POINTS_SCORED'] / lineup_level['TOTAL_MIN']
    )
    lineup_level['PLUS_MINUS_PER_MINUTE'] = (
        lineup_level['POINTS_PER_MINUTE'] - lineup_level['OPP_POINTS_PER_MINUTE']
    )
    lineup_level = (
        lineup_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return lineup_level

def get_player_level(data):
    player_level = (
        data.groupby(by=['PLAYER_NAME'], as_index=False)
            .agg(
                GAME_COUNT=('GAME_DATE', 'nunique'),
                TOTAL_MIN=('MIN_PLAYED', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    player_level['POINTS_SCORED_PER_GAME'] = (
        player_level['POINTS_SCORED'] / player_level['GAME_COUNT']
    )
    player_level['POINTS_PER_MINUTE'] = (
        player_level['POINTS_SCORED'] / player_level['TOTAL_MIN']
    )
    player_level['OPP_POINTS_PER_MINUTE'] = (
        player_level['OPP_POINTS_SCORED'] / player_level['TOTAL_MIN']
    )
    player_level['PLUS_MINUS_PER_MINUTE'] = (
        player_level['POINTS_PER_MINUTE'] - player_level['OPP_POINTS_PER_MINUTE']
    )
    player_level['MINUTES_PER_GAME'] = (
        player_level['TOTAL_MIN'] / player_level['GAME_COUNT']
    )
    player_level = (
        player_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return player_level

def get_game_level(data):
    game_level = (
        data.groupby(by=['LINEUP_KEY', 'OPPONENT'], as_index=False)
            .agg(
                TOTAL_MIN=('TOTAL_MIN', 'sum'),
                POINTS_SCORED=('POINTS_SCORED', 'sum'),
                OPP_POINTS_SCORED=('OPP_POINTS_SCORED', 'sum')
            )
    )
    game_level['POINTS_PER_MINUTE'] = (
        game_level['POINTS_SCORED'] / game_level['TOTAL_MIN']
    )
    game_level['OPP_POINTS_PER_MINUTE'] = (
        game_level['OPP_POINTS_SCORED'] / game_level['TOTAL_MIN']
    )
    game_level['PLUS_MINUS_PER_MINUTE'] = (
        game_level['POINTS_PER_MINUTE'] - game_level['OPP_POINTS_PER_MINUTE']
    )
    game_level = (
        game_level.sort_values(by=['PLUS_MINUS_PER_MINUTE'], ascending=False)
                    .reset_index(drop=True)
    )
    return game_level


st.subheader('Explore team performance')
minute_data = get_data()
years = minute_data['SEASON'].sort_values(ascending=False).drop_duplicates().tolist()
select_season = view_ui.select_season(
    options=years, key='minutes_season'
)
minute_data = minute_data[minute_data['SEASON'] == select_season]
clean_lineups = build_lineup_intervals(minutes_data=minute_data)
games_info, player_info = get_game_player_info(minutes_data=minute_data)
games_info_dict = dict(zip(games_info['GAME_ID'], games_info['GAME_DATE']))
grouped_lineups = group_data(clean_lineups=clean_lineups, game_dict=games_info_dict)
unique_player_lineups, my_players = get_unique_lineups(grouped_lineups=grouped_lineups, player_info=player_info)
player_map = dict(zip(player_info['PLAYER_NAME'], player_info['PLAYER_ID'].astype(int)))
player_id_to_name = {player_id: player_name for player_name, player_id in player_map.items()}

def lineup_ids_to_numbers(lineup_key):
    try:
        # lineup_key may be a stringified tuple like "(1, 2, 3, 4, 5)"
        ids = ast.literal_eval(lineup_key) if isinstance(lineup_key, str) else lineup_key
    except Exception:
        return lineup_key
    return ', '.join(f'#{int(player_id)}' for player_id in ids)


number_key = pd.DataFrame(
    [
        {'Jersey number': player_id, 'Player': player_name}
        for player_id, player_name in sorted(player_id_to_name.items())
    ]
)
with st.expander('Jersey number key'):
    st.dataframe(number_key, width='content', hide_index=True)


col1, col2 = st.columns(2)
view_analytics = st.segmented_control(
    label='What would you like to compare?',
    options=['Player Lineup', 'Overall Lineup', 'Player', 'Game'],
    default='Player Lineup',
    format_func=lambda view: {
        'Player Lineup': 'Lineups with a player',
        'Overall Lineup': 'All lineups',
        'Player': 'Players',
        'Game': 'Game'
    }[view],
    help='Compare combinations of players, individual players, or lineups from one game.'
)
st.caption(
    'Scoring margin is your team’s points minus the opponent’s points while the '
    'player or lineup is on court. Per-minute rates make playing time easier to compare.'
)


if view_analytics == 'Player Lineup':

    player_col, min_col, stat_col = st.columns([1, 1, 2])
    with player_col:
        select_player = st.selectbox(label='Player', options=list(player_map.keys()))
        selected_player = player_map.get(select_player)
    with min_col:
        min_threshold = st.number_input(
            label='Minimum lineup minutes',
            step=1,
            value=2,
            help='Hide lineups with less total court time across the selected season.'
        )

    if selected_player:
        that_player_lineups = unique_player_lineups.get(selected_player)
        df = pd.DataFrame(
            data=that_player_lineups, 
            columns=['PLAYER_1', 'PLAYER_2', 'PLAYER_3', 'PLAYER_4', 'PLAYER_5']
        )
        df['LINEUP_KEY'] = tuple(
            zip(
                df['PLAYER_1'], 
                df['PLAYER_2'], 
                df['PLAYER_3'], 
                df['PLAYER_4'],
                df['PLAYER_5']
            )
        )
        df['LINEUP_KEY'] = df['LINEUP_KEY'].astype(str)
        merged = pd.merge(df, grouped_lineups, on=['LINEUP_KEY'])
        lineup_level = get_lineup_level_data(merged)
        lineup_level = lineup_level[lineup_level['TOTAL_MIN'] >= min_threshold]
        lineup_level['Minutes per Game'] = (
            lineup_level['TOTAL_MIN'] / lineup_level['GAME_COUNT']
        )
        lineup_level = lineup_level.rename(columns=_PLAYER_LINEUPS_MAP_NAMES)

        #lineup_level['Lineup'] = lineup_level['LINEUP_KEY']
        lineup_level['Lineup'] = lineup_level['LINEUP_KEY'].apply(lineup_ids_to_numbers)
        view_stats = [
            'Scoring Margin per Minute', 'Games Played',
            'Team Points per Minute',
            'Opponent Points per Minute'
        ]
        with stat_col:
            data = st.selectbox(label='Measure', options=view_stats)
        results_view = st.segmented_control(
            'Results',
            options=['Chart and table', 'Chart', 'Table'],
            default='Chart and table',
            key='minutes_player_lineup_display',
        )
        col1, col2 = st.columns([3, 2])
        if data:
            sorted_lineup = (
                lineup_level.sort_values(by=[data], ascending=False)
                            .reset_index(drop=True)
            )
            sorted_lineup.insert(0, 'Rank', np.arange(len(sorted_lineup)) + 1)
            view_ui.render_page_context(
                page_key='view_minutes',
                scope=f"{select_season} season · lineups with {select_player} · {data}",
            )
            st.caption(
                f"Sample size: {len(lineup_level)} qualifying lineups · "
                f"{int(lineup_level['Games Played'].sum())} lineup-games."
            )
            if results_view != 'Table':
                with col1:
                    fig = px.bar(
                        data_frame=sorted_lineup.round(2),
                        x=data,
                        y='Lineup',
                        orientation='h',
                        text=data,
                        color_discrete_sequence=['green']
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(title=f'{data} by lineup')
                    st.plotly_chart(figure_or_data=fig, width='stretch')
            if results_view != 'Chart':
                with col2:
                    st.dataframe(
                        sorted_lineup[['Rank', 'Lineup', data, 'Minutes per Game']].round(2),
                        hide_index=True,
                    )

if view_analytics == 'Player':

    player_data = build_player_only(minute_data=minute_data)
    player_clean_data = get_player_level(player_data)
    player_clean_data = player_clean_data.rename(columns=_PLAYER_MAP_NAMES)
    player_clean_data['Name'] = player_clean_data['PLAYER_NAME']
    view_stats = [
        'Team Points per Minute on Court', 'Opponent Points per Minute on Court',
        'Scoring Margin per Minute on Court', 'Minutes per Game', 'Games Played'
        ]
    data = st.selectbox(label='Measure', options=view_stats)
    results_view = st.segmented_control(
        'Results',
        options=['Chart and table', 'Chart', 'Table'],
        default='Chart and table',
        key='minutes_player_display',
    )
    col1, col2 = st.columns(spec=[3,2])
    if data:
        sorted_lineup = (
            player_clean_data.sort_values(by=[data], ascending=False)
                        .reset_index(drop=True)
        )
        sorted_lineup.insert(0, 'Rank', np.arange(len(sorted_lineup)) + 1)
        view_ui.render_page_context(
            page_key='view_minutes',
            scope=f"{select_season} season · all players · {data}",
        )
        st.caption(
            f"Sample size: {len(player_clean_data)} players · "
            f"{int(player_clean_data['Games Played'].sum())} player-games."
        )
        if results_view != 'Table':
            with col1:
                fig = px.bar(
                    data_frame=sorted_lineup.round(2),
                    x=data,
                    y='Name',
                    orientation='h',
                    text=data,
                    color_discrete_sequence=['green']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(title=f'{data} by player')
                st.plotly_chart(figure_or_data=fig, width='stretch')
        if results_view != 'Chart':
            with col2:
                st.dataframe(
                    data=sorted_lineup[['Rank', 'Name', data]].round(2),
                    hide_index=True,
                    width='stretch'
                )

if view_analytics == 'Overall Lineup':
    min_col, stat_col = st.columns([1, 2])
    with min_col:
        min_threshold = st.number_input(
            label='Minimum lineup minutes',
            step=1,
            value=2,
            help='Hide lineups with less total court time across the selected season.'
        )
    lineup_level = get_lineup_level_data(grouped_lineups)
    lineup_level['Minutes per Game'] = (
        lineup_level['TOTAL_MIN'] / lineup_level['GAME_COUNT']
    )
    lineup_level = lineup_level[lineup_level['TOTAL_MIN'] >= min_threshold]
    lineup_level = lineup_level.rename(columns=_PLAYER_LINEUPS_MAP_NAMES)
    lineup_level['Lineup'] = lineup_level['LINEUP_KEY'].apply(lineup_ids_to_numbers)
    view_stats = [
            'Scoring Margin per Minute',
            'Team Points per Minute',
            'Opponent Points per Minute'
    ]
    with stat_col:
        data = st.selectbox(label='Measure', options=view_stats)
    results_view = st.segmented_control(
        'Results',
        options=['Chart and table', 'Chart', 'Table'],
        default='Chart and table',
        key='minutes_overall_lineup_display',
    )
    col1, col2 = st.columns([3, 2])
    if data:
        sorted_lineup = (
                lineup_level.sort_values(by=[data], ascending=False)
                            .reset_index(drop=True)
        )
        sorted_lineup.insert(0, 'Rank', np.arange(len(sorted_lineup)) + 1)
        view_ui.render_page_context(
            page_key='view_minutes',
            scope=f"{select_season} season · all lineups · {data}",
        )
        st.caption(
            f"Sample size: {len(lineup_level)} lineups · "
            f"{int(lineup_level['Games Played'].sum())} lineup-games."
        )
        if results_view != 'Table':
            with col1:
                fig = px.bar(
                    data_frame=sorted_lineup.round(2),
                    x=data,
                    y='Lineup',
                    orientation='h',
                    text=data,
                    color_discrete_sequence=['green']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(title=f'{data} by overall lineup')
                st.plotly_chart(figure_or_data=fig, width='stretch')
        if results_view != 'Chart':
            with col2:
                st.dataframe(
                    data=sorted_lineup[['Rank', 'Lineup', data, 'Minutes per Game']].round(2),
                    hide_index=True,
                    width='stretch'
                )

if view_analytics == 'Game':

    #game_data = build_lineup_intervals(minute_data)
    game_clean_data = get_game_level(grouped_lineups)
    game_clean_data['GAME_COUNT'] = 1
    game_data = game_clean_data.rename(columns=_PLAYER_LINEUPS_MAP_NAMES)

    game_data['Lineup'] = game_data['LINEUP_KEY'].apply(lineup_ids_to_numbers)
    games = game_data['OPPONENT'].unique().tolist()
    col1, col2 = st.columns(2)
    with col1:
        game_select = view_ui.select_game(
            options=games,
            key='minutes_game',
            label='Game',
        )
    game_data = game_data[game_data['OPPONENT'] == game_select]
    selected_game_id = games_info.loc[
        games_info['GAME_DATE'] == game_select, 'GAME_ID'
    ].iloc[0]
    rotation = clean_lineups[
        clean_lineups['GAME_ID'] == selected_game_id
    ].copy()
    rotation['Lineup'] = rotation['LINEUP_KEY'].apply(lineup_ids_to_numbers)
    rotation['ELAPSED_START'] = (36 * 60 - rotation['TIME_IN']) / 60
    rotation['STINT_MINUTES'] = rotation['SECONDS_PLAYED'] / 60
    rotation['STINT_MARGIN'] = (
        rotation['POINTS_SCORED'] - rotation['OPP_POINTS_SCORED']
    )
    st.subheader('Rotation timeline')
    st.caption(
        'Each bar shows a lineup stint from tip-off to the end of the game. '
        'Green stints gained margin; red stints lost margin.'
    )
    timeline = go.Figure()
    for lineup, stint_group in rotation.groupby('Lineup', sort=False):
        stint_colors = np.where(
            stint_group['STINT_MARGIN'].fillna(0) >= 0,
            '#2d8a62',
            '#c64949',
        )
        hover_data = stint_group[[
            'ELAPSED_START', 'STINT_MINUTES', 'SCORE_IN', 'SCORE_OUT',
            'OPP_SCORE_IN', 'OPP_SCORE_OUT', 'STINT_MARGIN',
        ]].to_numpy()
        timeline.add_trace(go.Bar(
            x=stint_group['STINT_MINUTES'],
            base=stint_group['ELAPSED_START'],
            y=[lineup] * len(stint_group),
            orientation='h',
            marker_color=stint_colors,
            customdata=hover_data,
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Elapsed: %{customdata[0]:.1f} min<br>'
                'Stint: %{customdata[1]:.1f} min<br>'
                'Score: %{customdata[2]}-%{customdata[4]} to '
                '%{customdata[3]}-%{customdata[5]}<br>'
                'Stint margin: %{customdata[6]:+.0f}<extra></extra>'
            ),
            showlegend=False,
        ))
    timeline.update_layout(
        barmode='overlay',
        xaxis=dict(
            title='Elapsed game time (minutes)',
            range=[0, 36],
            dtick=4,
            fixedrange=True,
        ),
        yaxis=dict(title='Lineup', autorange='reversed'),
        height=max(300, 48 * rotation['Lineup'].nunique()),
        margin=dict(l=20, r=20, t=20, b=40),
    )
    st.plotly_chart(timeline, width='stretch')
    view_stats = [
            'Scoring Margin per Minute',
            'Team Points per Minute',
            'Opponent Points per Minute'
        ]
    with col2:
        data = st.selectbox(label='Measure', options=view_stats)
    results_view = st.segmented_control(
        'Results',
        options=['Chart and table', 'Chart', 'Table'],
        default='Chart and table',
        key='minutes_game_display',
    )
    col1, col2 = st.columns([3, 2])
    if data:
        sorted_lineup = (
            game_data.sort_values(by=[data], ascending=False)
                        .reset_index(drop=True)
        )
        sorted_lineup.insert(0, 'Rank', np.arange(len(sorted_lineup)) + 1)
        view_ui.render_page_context(
            page_key='view_minutes',
            scope=f"{select_season} season · {game_select} · {data}",
        )
        if not game_data.empty:
            best_lineup = game_data.sort_values(
                'Scoring Margin per Minute', ascending=False
            ).iloc[0]
            st.caption(
                f"Best scoring margin: {best_lineup['Lineup']} at "
                f"{best_lineup['Scoring Margin per Minute']:+.2f} points/min "
                f"over {best_lineup['Total Minutes Played']:.1f} minutes."
            )
        st.caption(f"Sample size: {len(game_data)} lineups in this game.")
        if results_view != 'Table':
            with col1:
                fig = px.bar(
                    data_frame=sorted_lineup.round(2),
                    x=data,
                    y='Lineup',
                    orientation='h',
                    text=data,
                    color_discrete_sequence=['green']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(title=f'{data} by game')
                st.plotly_chart(figure_or_data=fig, width='stretch')
        if results_view != 'Chart':
            with col2:
                performance_columns = [
                    'Lineup',
                    'Total Minutes Played',
                    'Team Points per Minute',
                    'Opponent Points per Minute',
                    'Scoring Margin per Minute',
                ]
                st.dataframe(
                    sorted_lineup[['Rank'] + performance_columns].round(2),
                    hide_index=True,
                    width='stretch',
                )