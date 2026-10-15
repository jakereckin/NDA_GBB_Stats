import streamlit as st
import numpy as np
import pandas as pd
import ast
import plotly.express as px
import polars as pl
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from py import sql, data_source, view_ui
pd.options.mode.chained_assignment = None

st.set_page_config(page_title='Lineup Network', layout='wide')
st.title('Lineup Network')
st.caption('Explore lineup transitions and identify combinations that create the strongest scoring margin.')

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

_PLAYER_LINEUPS_MAP_NAMES = {
    'TOTAL_MIN': 'Total Minutes Played',
    'POITNS_SCORED_PER_GAME': 'Points Scored per Game',
    'POINTS_PER_MINUTE': 'Points per Minute Played',
    'OPP_POINTS_PER_MINUTE': 'Points Allowed per Minute Played',
    'PLUS_MINUS_PER_MINUTE': 'Plus/Minus per Minute Played',
    'GAME_COUNT': 'Games Played'
}

_PLAYER_MAP_NAMES = {
    'GAME_COUNT': 'Games Played',
    'POINTS_PER_MINUTE': 'Team Points while Playing per Minute',
    'OPP_POINTS_PER_MINUTE': 'Points Allowed while Playing per Minute',
    'PLUS_MINUS_PER_MINUTE': 'Plus/Minus per Minute Played',
    'MINUTES_PER_GAME': 'Minutes per Game Played'
}

# ----------------------------------------------------------------------------
@st.cache_data
def get_data():
    minute_data = data_source.run_query(
        sql=sql.view_minutes_sql(), connection=sql_lite_connect
    )
    return minute_data

# ----------------------------------------------------------------------------
@st.cache_data
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

st.subheader('Choose a game scope and lineup filter')
season, scope, game, players = st.columns(4, vertical_alignment='bottom')

minute_data = get_data()
years = minute_data['SEASON'].sort_values(ascending=False).drop_duplicates().tolist()

with season:
    select_season = view_ui.select_season(
        options=years, key='lineup_network_season'
    )
with scope:
    analysis_scope = st.segmented_control(
        'Scope',
        options=['Single game', 'Season'],
        default='Single game',
        key='lineup_network_scope',
    )
minute_data = minute_data[minute_data['SEASON'] == select_season]
clean_lineups = build_lineup_intervals(minutes_data=minute_data)
games_info, player_info = get_game_player_info(minutes_data=minute_data)
games_info_dict = dict(zip(games_info['GAME_ID'], games_info['GAME_DATE']))
grouped_lineups = group_data(clean_lineups=clean_lineups, game_dict=games_info_dict)
unique_player_lineups, my_players = get_unique_lineups(grouped_lineups=grouped_lineups, player_info=player_info)
player_map = dict(zip(player_info['PLAYER_NAME'], player_info['PLAYER_ID'].astype(int)))

lineup_analysis = clean_lineups.groupby('GAME_ID').apply(
    lambda x: x.sort_values('TIME_IN', ascending=False).reset_index(drop=True)
).reset_index(drop=True)

lineup_analysis['RANK'] = lineup_analysis.groupby('GAME_ID').cumcount() + 1
player_ids = player_info['PLAYER_ID'].astype(int).drop_duplicates().tolist()
player_names = dict(zip(
    player_info['PLAYER_ID'].astype(int), player_info['PLAYER_NAME']
))

with players:
    select_players = st.multiselect(
        'Players to include',
        options=player_ids,
        format_func=lambda player_id: (
            f"{player_names.get(player_id, 'Player')} (#{player_id})"
        ),
        placeholder='Filter to lineups containing these players',
        help='Choose one or more players to focus the transition graph.'
    )

available_games = (
    games_info.sort_values('GAME_ID', ascending=False)['GAME_DATE']
    .drop_duplicates()
    .tolist()
)
selected_game_id = None
selected_game = None
if analysis_scope == 'Single game':
    with game:
        selected_game = view_ui.select_game(
            options=available_games,
            key='lineup_network_game',
            label='Game',
        )
    selected_game_id = games_info.loc[
        games_info['GAME_DATE'] == selected_game, 'GAME_ID'
    ].iloc[0]
    scope_lineup_analysis = lineup_analysis[
        lineup_analysis['GAME_ID'] == selected_game_id
    ].copy()
else:
    scope_lineup_analysis = lineup_analysis.copy()

scope_lineup_analysis["LINEUP_SET"] = scope_lineup_analysis["LINEUP_KEY"].apply(
    lambda lineup: set(ast.literal_eval(lineup))
)
player_filtered = scope_lineup_analysis
if select_players:
    player_filtered = player_filtered[
        player_filtered['LINEUP_SET'].apply(
            lambda lineup: set(select_players).issubset(lineup)
        )
    ]

lineup_stats = (
    player_filtered.groupby('LINEUP_KEY', as_index=False)
    .agg(
        TOTAL_MINUTES=('MIN_PLAYED', 'sum'),
        TEAM_POINTS=('POINTS_SCORED', 'sum'),
        OPPONENT_POINTS=('OPP_POINTS_SCORED', 'sum'),
        GAMES_PLAYED=('GAME_ID', 'nunique'),
    )
)
lineup_stats['SCORING_MARGIN_PER_MINUTE'] = (
    (lineup_stats['TEAM_POINTS'] - lineup_stats['OPPONENT_POINTS'])
    / lineup_stats['TOTAL_MINUTES']
)

filter_col, rank_col, limit_col = st.columns([1, 1.4, 1])
with filter_col:
    minimum_minutes = st.number_input(
        'Minimum lineup minutes',
        min_value=0,
        value=0,
        step=1,
        help='Exclude lineups with fewer total minutes this season.',
    )
lineup_stats = lineup_stats[
    lineup_stats['TOTAL_MINUTES'] >= minimum_minutes
]
with rank_col:
    rank_by = st.selectbox(
        'Rank lineups by',
        options=['Scoring margin per minute', 'Minutes played'],
    )
rank_column = (
    'SCORING_MARGIN_PER_MINUTE'
    if rank_by == 'Scoring margin per minute'
    else 'TOTAL_MINUTES'
)
lineup_stats = lineup_stats.sort_values(rank_column, ascending=False)
with limit_col:
    top_count = st.slider(
        'Maximum lineups to show',
        min_value=1,
       # max_value=max(1, len(lineup_stats)),
        value=min(25, max(1, len(lineup_stats))),
    )
filtered_stats = lineup_stats.head(top_count).copy()
filtered_stats.insert(0, 'RANK', np.arange(len(filtered_stats)) + 1)
visible_lineups = set(filtered_stats['LINEUP_KEY'])

def lineup_label(lineup):
    lineup_players = ast.literal_eval(lineup)
    return ', '.join(f'#{int(player_id)}' for player_id in lineup_players)

G = nx.DiGraph()
G.add_nodes_from(visible_lineups)
for _, group in scope_lineup_analysis.sort_values(['GAME_ID', 'RANK']).groupby('GAME_ID'):
    game_lineups = group['LINEUP_KEY'].tolist()
    for source, target in zip(game_lineups, game_lineups[1:]):
        if source == target or source not in visible_lineups or target not in visible_lineups:
            continue
        if G.has_edge(source, target):
            G[source][target]['weight'] += 1
        else:
            G.add_edge(source, target, weight=1)

transition_data = pd.DataFrame(
    [
        {
            'From lineup': lineup_label(source),
            'To lineup': lineup_label(target),
            'Transitions': details['weight'],
        }
        for source, target, details in G.edges(data=True)
    ],
    columns=['From lineup', 'To lineup', 'Transitions'],
).sort_values('Transitions', ascending=False)

jersey_key = pd.DataFrame(
    [
        {'Jersey number': player_id, 'Player': player_name}
        for player_id, player_name in sorted(player_names.items())
    ]
)
with st.expander('Jersey number key'):
    st.dataframe(jersey_key, width='content', hide_index=True)

scope_filter = ', '.join(
    player_names.get(player_id, str(player_id)) for player_id in select_players
) or 'all players'
scope_label = selected_game if selected_game is not None else 'all games'
view_ui.render_page_context(
    page_key='view_lineup_network',
    scope=f"{select_season} season · {scope_label} · {scope_filter} · {rank_by}",
)
st.caption(
    f"Sample size: {len(filtered_stats)} lineups · "
    f"{filtered_stats['TOTAL_MINUTES'].sum():.1f} lineup-minutes · "
    f"{scope_lineup_analysis['GAME_ID'].nunique()} game(s)."
)
if not filtered_stats.empty:
    best_lineup = filtered_stats.sort_values(
        'SCORING_MARGIN_PER_MINUTE', ascending=False
    ).iloc[0]
    st.caption(
        f"Best filtered lineup: {lineup_label(best_lineup['LINEUP_KEY'])} · "
        f"{best_lineup['SCORING_MARGIN_PER_MINUTE']:+.2f} points/min over "
        f"{best_lineup['TOTAL_MINUTES']:.1f} minutes."
    )
results_view = st.segmented_control(
    'Results',
    options=['Graph and table', 'Graph', 'Table'],
    default='Graph and table',
    key='lineup_network_display',
)

if results_view != 'Table':
    fig, ax = plt.subplots(figsize=(14, 9), constrained_layout=True)
    pos = nx.spring_layout(G, k=2, seed=13) if G.number_of_nodes() else {}
    stats_by_lineup = filtered_stats.set_index('LINEUP_KEY')
    node_colors = [
        'red' if stats_by_lineup.loc[node, 'SCORING_MARGIN_PER_MINUTE'] < 0 else 'green'
        for node in G.nodes()
    ]
    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_size=1800, node_color=node_colors
    )
    edge_widths = [
        min(6, 1 + G[source][target]['weight'] * 0.4)
        for source, target in G.edges()
    ]
    nx.draw_networkx_edges(
        G, pos, ax=ax, width=edge_widths, arrowsize=16, arrowstyle='-|>'
    )
    for node, (x, y) in pos.items():
        ax.text(
            x, y,
            lineup_label(node),
            fontsize=7,
            fontweight='bold',
            ha='center',
            va='center',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')],
        )
    ax.set_title('Lineup transition graph', fontsize=16)
    ax.axis('off')
    st.pyplot(fig, width='stretch')
    plt.close(fig)

if results_view != 'Graph':
    display_stats = filtered_stats.copy()
    display_stats['LINEUP'] = display_stats['LINEUP_KEY'].apply(lineup_label)
    display_stats = display_stats[[
        'RANK', 'LINEUP', 'TOTAL_MINUTES', 'GAMES_PLAYED', 'TEAM_POINTS',
        'OPPONENT_POINTS', 'SCORING_MARGIN_PER_MINUTE',
    ]].rename(columns={
        'RANK': 'Rank',
        'LINEUP': 'Lineup',
        'TOTAL_MINUTES': 'Minutes played',
        'GAMES_PLAYED': 'Games played',
        'TEAM_POINTS': 'Team points',
        'OPPONENT_POINTS': 'Opponent points',
        'SCORING_MARGIN_PER_MINUTE': 'Scoring margin per minute',
    })
    st.dataframe(display_stats, width='stretch', hide_index=True)
    if not transition_data.empty:
        st.markdown('#### Lineup transitions')
        st.dataframe(transition_data, width='stretch', hide_index=True)
