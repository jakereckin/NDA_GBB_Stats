import time
import sqlitecloud
import numpy as np
import pandas as pd
import streamlit as st
from plotly import graph_objs as go
from streamlit_plotly_events import plotly_events
from py import utils, data_source, sql

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

SQL_CONN = st.secrets["nda_gbb_connection"]["DB_CONNECTION"]
SHOT_DEFENSES = ["Open", "Guarded", "Heavily Guarded"]
GRID_SPACING = 20
CHART_WIDTH, CHART_HEIGHT = 350, 400

if "refresh_pbp" not in st.session_state:
    st.session_state.refresh_pbp = False
if "pbp_version" not in st.session_state:
    st.session_state.pbp_version = 0
if 'game_version' not in st.session_state:
    st.session_state.game_version = 0

@st.cache_data(show_spinner=False)
def load_shot_spots(connection: str):
    return data_source.run_query(sql=sql.get_shot_spots_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_player_game(connection: str):
    return data_source.run_query(sql=sql.get_player_game_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_game_summary(connection: str, version: int):
    return data_source.run_query(sql=sql.get_game_summary_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_pbp_data_cached(game_id: int, version: int):
    my_sql = sql.get_play_sql().replace("?", str(game_id))
    return data_source.run_query(sql=my_sql, connection=SQL_CONN)

@st.cache_data(show_spinner=False)
def make_grid(xmin, xmax, ymin, ymax, spacing):
    xs = np.arange(xmin, xmax + 1, spacing)
    ys = np.arange(ymin, ymax + 1, spacing)
    xx, yy = np.meshgrid(xs, ys)
    return xx.ravel().tolist(), yy.ravel().tolist()

@st.cache_resource
def build_blank_chart():
    fig = utils.build_blank_shot_chart()
    X_MIN, X_MAX = -250, 250
    Y_MIN, Y_MAX = -50, 450
    capture_x, capture_y = make_grid(X_MIN, X_MAX, Y_MIN, Y_MAX, GRID_SPACING)
    fig.update_layout(
        xaxis=dict(range=[X_MIN, X_MAX], showgrid=False, zeroline=False),
        yaxis=dict(range=[Y_MIN, Y_MAX], showgrid=False, zeroline=False, scaleanchor="x"),
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="white",
        clickmode="event+select",
    )
    fig.add_trace(
        go.Scatter(
            x=capture_x,
            y=capture_y,
            mode="markers",
            marker=dict(opacity=1, size=1, color="white"),
        )
    )
    return fig

def create_df(
    game_val_final,
    player_number,
    spot_val,
    shot_defense,
    make_miss,
    spot_x,
    spot_y,
    paint_touch,
) -> pd.DataFrame:
    cols = [
        "GAME_ID",
        "NUMBER",
        "SPOT",
        "SHOT_DEFENSE",
        "MAKE_MISS",
        "XSPOT",
        "YSPOT",
        "PAINT_TOUCH",
    ]
    row = [
        game_val_final,
        player_number,
        spot_val,
        shot_defense,
        make_miss,
        spot_x,
        spot_y,
        paint_touch,
    ]
    return pd.DataFrame([row], columns=cols)

def create_stat_df(
        player_number,
        game_val_final,
        stat_type
):
    cols = [
        "GAME_ID",
        "NUMBER",
        "STAT_TYPE"
    ]
    row = [
        game_val_final,
        player_number,
        stat_type
    ]
    return pd.DataFrame([row], columns=cols)

def get_values_needed(game_val: str, game_df: pd.DataFrame, player_val: str):
    opponent_name, game_date = game_val.split(" - ")
    game_row = game_df[
        (game_df["OPPONENT"] == opponent_name) & (game_df["DATE"] == game_date)
    ]
    player_number = int(player_val.split(" - ")[0])
    game_id = int(game_row["GAME_ID"].values[0])
    return player_number, game_id

shot_spots = load_shot_spots(SQL_CONN)
player_game = load_player_game(SQL_CONN)

games = player_game.sort_values(by="SEASON", ascending=False).reset_index(drop=True)
season_list = games["SEASON"].unique().tolist()

left, right = st.columns(2)
with left:
    season = st.radio(label="Select Season", options=season_list, horizontal=True)

games_season = games[games["SEASON"] == season].copy()
games_season["DATE_DTTM"] = pd.to_datetime(games_season["DATE"])
games_season = games_season.sort_values(by="DATE_DTTM")
games_season["GAME_LABEL"] = games_season["GAME_LABEL"].astype(str)
game_list = games_season["GAME_LABEL"].unique().tolist()[::-1]

with right:
    game_select = st.selectbox(label="Select Game", options=game_list, index=0)

game = games_season[games_season["GAME_LABEL"] == game_select].iloc[0]
game_id = int(game["GAME_ID"])
game_val = game["GAME_LABEL"]

games_season["NUMBER_INT"] = games_season["NUMBER"].astype(int)
unique_players = games_season.sort_values("NUMBER_INT")["PLAYER_LABEL"].unique()

fig = build_blank_chart()
col_chart, col_form = st.columns(2)
with col_chart:
    clicked = plotly_events(plot_fig=fig, click_event=True, key=f"shot-capture-{game_id}")

# Load pbp data (cached, versioned)
pbp_data = load_pbp_data_cached(game_select, st.session_state.pbp_version)

# Add shot flow
if clicked:
    ev = clicked[0]
    x_click = ev.get("x")
    y_click = ev.get("y")
    shot_spot = utils.get_nearest_spot(x=x_click, y=y_click, spots_df=shot_spots)
    spot_val = shot_spot.get("spot") if shot_spot else None

    if spot_val:
        with col_form:
            st.write(f"Adding shot at {spot_val} for {game_val}")
            with st.form(key=f"shot_form_{game_id}", clear_on_submit=False):
                player_val = st.radio(label="Player", options=unique_players, horizontal=True)
                c2, c3, c4, c5 = st.columns(4)
                with c4:
                    free_throw = st.radio(label="Free Throw", options=["N", "Y"], horizontal=True)
                with c2:
                    make_miss = st.radio(label="Make/Miss", options=["N", "Y"], horizontal=True)
                with c3:
                    shot_defense = st.radio(label="Shot Defense", options=SHOT_DEFENSES, horizontal=True)
                    if shot_defense == "Open":
                        shot_defense = "OPEN"
                    elif shot_defense == "Guarded":
                        shot_defense = "GUARDED"
                    else:
                        shot_defense = "HEAVILY_GUARDED"
                with c5:
                    paint_touch = st.radio(label="Paint Touch", options=["N", "Y"], horizontal=True)
                other_stats = [
                    'Shot','Offensive Rebound', 'Defensive Rebound', 'Turnover',
                    'Steal', 'Block', 'Foul', 'Assist'
                ]
                choose_stat = st.radio(label="Other Stats", options=other_stats, horizontal=True)
                add = st.form_submit_button(label="Add Play")
                if add:
                    player_number, game_val_final = get_values_needed(
                        game_val=game_val, game_df=games_season, player_val=player_val
                    )
                    if free_throw == "Y":
                        spot_val = "FREE_THROW1"
                        x_click = 0
                        y_click = 150

                    my_df = create_df(
                        game_val_final=game_val_final,
                        player_number=player_number,
                        spot_val=spot_val,
                        shot_defense=shot_defense,
                        make_miss=make_miss,
                        spot_x=x_click,
                        spot_y=y_click,
                        paint_touch=paint_touch,
                    )
                    if choose_stat == 'Offensive Rebound':
                        final_stat = 'OFFENSIVE_REBOUNDS'
                    elif choose_stat == 'Defensive Rebound':
                        final_stat = 'DEFENSIVE_REBOUNDS'
                    elif choose_stat == 'Turnover':
                        final_stat = 'TURNOVER'
                    elif choose_stat == 'Steal':
                        final_stat = 'STEALS'
                    elif choose_stat == 'Block':
                        final_stat = 'BLOCKS'
                    elif choose_stat == 'Foul':
                        final_stat = 'FOULS'
                    elif choose_stat == 'Assist':
                        final_stat = 'ASSISTS'
                    elif choose_stat == 'Shot':
                        if spot_val == "FREE_THROW1":
                            final_stat = 'FTA'
                        elif spot_val[-1] == '2':
                            final_stat = 'TWO_FGA'
                        else:
                            final_stat = 'THREE_FGA'
                    if player_number == 0:
                        st.error('Please select a valid player number')
                        st.stop()
                    stat_df = create_stat_df(
                        player_number=player_number,
                        game_val_final=game_val_final,
                        stat_type=final_stat
                    )

                    with sqlitecloud.connect(SQL_CONN) as conn:
                        cursor = conn.cursor()
                        for _, row in stat_df.iterrows():
                            cursor.execute(
                                sql=sql.insert_game_play(),
                                parameters=(
                                    str(row["GAME_ID"]),
                                    str(row["NUMBER"]),
                                    str(row["STAT_TYPE"]),
                                ),
                            )
                        conn.commit()
                        st.success(f'Added {final_stat} for player {player_number}')
                    if (choose_stat == 'Shot') & (make_miss == 'Y'):
                        if spot_val == "FREE_THROW1":
                            final_stat = 'FTM'
                        elif spot_val[-1] == '2':
                            final_stat = 'TWO_FGM'
                        else:
                            final_stat = 'THREE_FGM'
                        stat_df_make = create_stat_df(
                            player_number=player_number,
                            game_val_final=game_val_final,
                            stat_type=final_stat
                        )
                        with sqlitecloud.connect(SQL_CONN) as conn:
                            cursor = conn.cursor()
                            for _, row in stat_df_make.iterrows():
                                cursor.execute(
                                    sql=sql.insert_game_play(),
                                    parameters=(
                                        str(row["GAME_ID"]),
                                        str(row["NUMBER"]),
                                        str(row["STAT_TYPE"]),
                                    ),
                                )
                            conn.commit()
                            st.success(f'Added {final_stat} for player {player_number}')
                    new_query = (
                        sql.get_formatted_game_sql()
                           .replace('this_game_id', str(game_val_final))
                           .replace('this_player_id', str(player_number))
                    )
                    new_game_summary = data_source.run_query(
                        sql=new_query, connection=SQL_CONN
                    )
                    game_summary_data = load_game_summary(SQL_CONN, st.session_state.game_version)
                    # Update or Insert game summary
                    my_id = (
                        str(object=player_number)
                        + '_'
                        + str(game_val_final)
                    )
                    game_summary_ids = game_summary_data.copy()
                    game_summary_ids['_id'] = (
                        game_summary_ids['PLAYER_ID'].astype(dtype=str)
                        + '_'
                        + (
                            game_summary_ids['GAME_ID'].astype(dtype=int)
                                                    .astype(dtype=str)
                                                    .values
                        )
                    )

                    game_summary_ids_list = game_summary_ids['_id'].unique().tolist()
                    if my_id not in game_summary_ids_list:
                        with sqlitecloud.connect(SQL_CONN) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                sql=sql.insert_game_summary_sql(),
                                parameters=(
                                    player_number,
                                    str(game_val_final),
                                    str(new_game_summary['TWO_FGM'].values[0]),
                                    str(new_game_summary['TWO_FGA'].values[0]),
                                    str(new_game_summary['THREE_FGM'].values[0]),
                                    str(new_game_summary['THREE_FGA'].values[0]),
                                    str(new_game_summary['FTM'].values[0]),
                                    str(new_game_summary['FTA'].values[0]),
                                    str(new_game_summary['OFFENSIVE_REBOUNDS'].values[0]),
                                    str(new_game_summary['DEFENSIVE_REBOUNDS'].values[0]),
                                    str(new_game_summary['ASSISTS'].values[0]),
                                    str(new_game_summary['STEALS'].values[0]),
                                    str(new_game_summary['BLOCKS'].values[0]),
                                    str(new_game_summary['TURNOVER'].values[0]),
                                    str(new_game_summary['FOULS'].values[0])
                                )
                            )
                            conn.commit()
                    else:
                        with sqlitecloud.connect(SQL_CONN) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                sql=sql.update_game_summary_sql(),
                                parameters=(
                                    str(new_game_summary['TWO_FGM'].values[0]),
                                    str(new_game_summary['TWO_FGA'].values[0]),
                                    str(new_game_summary['THREE_FGM'].values[0]),
                                    str(new_game_summary['THREE_FGA'].values[0]),
                                    str(new_game_summary['FTM'].values[0]),
                                    str(new_game_summary['FTA'].values[0]),
                                    str(new_game_summary['OFFENSIVE_REBOUNDS'].values[0]),
                                    str(new_game_summary['DEFENSIVE_REBOUNDS'].values[0]),
                                    str(new_game_summary['ASSISTS'].values[0]),
                                    str(new_game_summary['STEALS'].values[0]),
                                    str(new_game_summary['BLOCKS'].values[0]),
                                    str(new_game_summary['TURNOVER'].values[0]),
                                    str(new_game_summary['FOULS'].values[0]),
                                    str(player_number),
                                    str(game_val_final)
                                )
                            )
                            conn.commit()
                    stat_val = new_game_summary[final_stat].values[0]
                    st.success(
                        f'Player {player_number} now has {stat_val} {final_stat} '
                        f'for game {game_val}'
                    )
                    st.session_state.game_version += 1
                    
                    if choose_stat == 'Shot':
                        spot_lookup = shot_spots.drop(columns=["XSPOT", "YSPOT"]).set_index("SPOT")
                        my_df = my_df.join(spot_lookup, on="SPOT")

                        all_data_game = pbp_data
                        if len(all_data_game) == 0:
                            my_df["PLAY_NUM"] = 0
                        else:
                            my_df["PLAY_NUM"] = len(all_data_game)

                        with sqlitecloud.connect(SQL_CONN) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                sql=sql.insert_plays_sql(),
                                parameters=(
                                    str(game_val_final),
                                    str(player_number),
                                    str(spot_val),
                                    str(shot_defense),
                                    str(make_miss),
                                    str(int(my_df["PLAY_NUM"].values[0])),
                                    str(x_click),
                                    str(y_click),
                                    str(paint_touch),
                                ),
                            )
                            conn.commit()
                        current_game = pd.concat(
                            objs=[
                                all_data_game.reset_index(drop=True), 
                                my_df.reset_index(drop=True)
                            ],
                            ignore_index=True,
                        )
                        current_game['ACTUAL_POINTS'] = np.where(
                            current_game['MAKE_MISS'] == 'Y',
                            current_game['POINTS'],
                            0
                        )
                        
                        current_game['NUMBER'] = (
                            current_game['NUMBER'].astype(int)
                        )
                        my_len = len(current_game)
                        st.success(
                            f'Submitted shot by player {player_number} '
                            f' from spot {spot_val} '
                            f' with defense {shot_defense} '
                            f' for game {game_val_final} '
                            f'Added to DB, {my_len} '
                            f' shots in DB for game {game_val_final}'
                        )

                        nda_points = current_game[current_game['NUMBER'] != 0]
                        opp_points = current_game[current_game['NUMBER'] == 0]
                        nda_points_val = int(nda_points.ACTUAL_POINTS.sum())
                        opp_points_val = int(opp_points.ACTUAL_POINTS.sum())
                        st.write(f'NDA Points: {nda_points_val}') 
                        st.write(f'Opp Points: {opp_points_val}')

                        st.session_state.pbp_version += 1
                        st.session_state.refresh_pbp = True

# Ensure pbp_data is fresh if requested
if st.session_state.refresh_pbp:
    pbp_data = load_pbp_data_cached(game_select, st.session_state.pbp_version)
    st.session_state.refresh_pbp = False

# Build simple_data robustly so it always displays
desired_cols = ["NUMBER", "SPOT", "SHOT_DEFENSE", "MAKE_MISS", "PLAY_NUM", "GAME_ID"]
# If pbp_data is empty or missing columns, create an empty DataFrame with desired columns
if pbp_data is None or len(pbp_data) == 0:
    simple_data = pd.DataFrame(columns=desired_cols)
else:
    # Select only existing columns, fill missing ones with defaults
    existing = [c for c in desired_cols if c in pbp_data.columns]
    simple_data = pbp_data.reset_index(drop=True)[existing].copy()
    for c in desired_cols:
        if c not in simple_data.columns:
            # sensible defaults
            if c in ("NUMBER", "PLAY_NUM", "GAME_ID"):
                simple_data[c] = 0
            else:
                simple_data[c] = ""
    # ensure types
    simple_data["NUMBER"] = simple_data["NUMBER"].astype(int)
    simple_data["PLAY_NUM"] = simple_data["PLAY_NUM"].astype(int)
    simple_data["GAME_ID"] = simple_data["GAME_ID"].astype(int)

# Sort and limit rows
simple_data = simple_data.sort_values(by="PLAY_NUM", ascending=False).head(30).reset_index(drop=True)

# Add DELETE column as boolean and ensure deterministic column order
simple_data["DELETE"] = False
simple_data = simple_data[["NUMBER", "SPOT", "SHOT_DEFENSE", "MAKE_MISS", "PLAY_NUM", "GAME_ID", "DELETE"]]

left_col, right_col = st.columns([2, 1])
with left_col:
    st.write(f"Showing last 30 shots for Game ID: {game_id}")
    editor_key = f"prev_shots_editor_{game_id}"
    # Use use_container_width to make it render nicely; keep a stable key
    edited_df = st.data_editor(
        simple_data, 
        hide_index=True,
        key=editor_key,
        use_container_width=True,
        column_config={
            "NUMBER": st.column_config.NumberColumn(
                "Player",
                help="Jersey number of the player who took the shot",
                width=75
            ),
            "SPOT": st.column_config.TextColumn(
                "Shot Spot",
                help="Location on the court where the shot was taken",
            ),
            "SHOT_DEFENSE": st.column_config.TextColumn(
                "Shot Defense",
                help="Type of defense on the shot (Open, Guarded, Heavily Guarded)",
            ),
            "MAKE_MISS": st.column_config.TextColumn(
                "Make",
                help="Whether the shot was made (Y) or missed (N)",
                width=75
            ),
            "PLAY_NUM": st.column_config.NumberColumn(
                "Play Number",
                help="Sequential number of the play in the game",

            ),
            "GAME_ID": st.column_config.NumberColumn(
                "Game ID",
                help="Identifier for the game",
            ),
            "DELETE": st.column_config.CheckboxColumn(
                "Delete",
                help="Check to mark this shot for deletion from the database",
            ),
        },
    )
    

    delete = st.button("Delete Selected Shots", key=f"delete_btn_{game_id}")
    if delete:
        # Guard: edited_df may be None if widget wasn't read; handle gracefully
        if edited_df is None:
            st.info("No data available to delete.")
        else:
            selected_deletes = edited_df[edited_df["DELETE"] == True]
            if len(selected_deletes) == 0:
                st.info("No rows selected for deletion.")
            else:
                deleted_count = 0
                with sqlitecloud.connect(SQL_CONN) as conn:
                    cursor = conn.cursor()
                    for _, row in selected_deletes.iterrows():
                        cursor.execute(
                            sql=sql.delete_shot(),
                            parameters=(str(int(row["GAME_ID"])), str(int(row["PLAY_NUM"])), str(int(row["NUMBER"]))),
                        )
                        deleted_count += 1
                    conn.commit()

                st.success(f"Deleted {deleted_count} shots")
                st.session_state.pbp_version += 1
                st.session_state.refresh_pbp = True
                st.rerun()

with right_col:
    opponent_name, game_date = game_val.split(" - ")
    game_row = games_season[
        (games_season["OPPONENT"] == opponent_name) & (games_season["DATE"] == game_date)
    ]
    current_totals = data_source.run_query(
        sql=sql.select_quick_game_info(game_row['GAME_ID'].values[0]),
        connection=SQL_CONN
    )
    current_totals = current_totals.drop(columns=['GAME_ID'])
    current_totals = (
        current_totals.rename(
            columns={
            'TEAM_OFFENSIVE_REBOUNDS': 'OREB',
             'TEAM_DEFENSIVE_REBOUNDS': 'DREB',
             'TEAM_TWO_FGM': '2FGM',
             'TEAM_TWO_FGA': '2FGA',
             'TEAM_THREE_FGM': '3FGM',
             'TEAM_THREE_FGA': '3FGA',
             'TEAM_FTM': 'FTM',
             'TEAM_FTA': 'FTA',
             'EFG_PERCENT': 'eFG%',
             'TEAM_FGA': 'FGA',
             'TEAM_TURNOVERS': 'Turnovers',
             'TEAM_FGM': 'FGM',
             'TEAM_ASSISTS': 'Assists',
             'TEAM_STEALS': 'Steals',
             'TEAM_BLOCKS': 'Blocks'},
        )
    )
    current_totals['PPP'] = current_totals['POINTS'] / np.where(
        current_totals['POSSESSIONS'] == 0,
        1,
        current_totals['POSSESSIONS']
    )
    current_totals['PPA'] = current_totals['FG_POINTS'] / np.where(
        current_totals['FGA'] == 0,
        1,
        current_totals['FGA']
    )
    current_totals = current_totals.drop(columns=['FG_POINTS'])
    current_totals = current_totals[[
        '2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA',
        'OREB', 'DREB', 'Assists', 'Steals', 'Blocks',
        'Turnovers', 'eFG%', 'POSSESSIONS', 'PPP', 'PPA'
    ]]
    st.dataframe(
        current_totals.T.rename(columns={0: "Total"}).reset_index().rename(columns={"index": "Stat"}),
        use_container_width=True,
        height=750,
        hide_index=True
    )

game_summary_data = load_game_summary(SQL_CONN, st.session_state.game_version)
game_row = games_season[
    (games_season["OPPONENT"] == opponent_name)
    & (games_season["DATE"] == game_date)
]
this_game_summary = game_summary_data[
    game_summary_data['GAME_ID'] == game_row['GAME_ID'].values[0]
]
this_game_summary = this_game_summary[[
    'PLAYER_ID', 'TWO_FGM', 'TWO_FGA', 'THREE_FGM', 'THREE_FGA',
    'FTM', 'FTA', 'OFFENSIVE_REBOUNDS', 'DEFENSIVE_REBOUNDS',
    'ASSISTS', 'STEALS', 'BLOCKS', 'TURNOVER', 'FOULS',
    'GAME_SCORE', 'POINTS'
]]
st.dataframe(
    this_game_summary,
    width='content',
    hide_index=True,
    column_config={
        'PLAYER_ID': st.column_config.NumberColumn(
            'Player Number',
            help='Jersey number of the player',
        ),
        'TWO_FGM': st.column_config.NumberColumn('2FGM'),
        'TWO_FGA': st.column_config.NumberColumn('2FGA'),
        'THREE_FGM': st.column_config.NumberColumn('3FGM'), 
        'THREE_FGA': st.column_config.NumberColumn('3FGA'),
        'FTM': st.column_config.NumberColumn('FTM'),
        'FTA': st.column_config.NumberColumn('FTA'),
        'OFFENSIVE_REBOUNDS': st.column_config.NumberColumn('OREB'),
        'DEFENSIVE_REBOUNDS': st.column_config.NumberColumn('DREB'),
        'ASSISTS': st.column_config.NumberColumn('Assists'),
        'STEALS': st.column_config.NumberColumn('Steals'),
        'BLOCKS': st.column_config.NumberColumn('Blocks'),
        'TURNOVER': st.column_config.NumberColumn('Turnovers'),
        'FOULS': st.column_config.NumberColumn('Fouls'),
        'GAME_SCORE': st.column_config.NumberColumn('Game Score'),
        'POINTS': st.column_config.NumberColumn('Points')
    }
)