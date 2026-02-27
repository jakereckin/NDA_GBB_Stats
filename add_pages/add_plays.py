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
if 'refresh_game_stat_version' not in st.session_state:
    st.session_state.refresh_game_stat_version = False
if 'game_stat_version' not in st.session_state:
    st.session_state.game_stat_version = 0

@st.cache_resource
def load_shot_spots(connection: str):
    return data_source.run_query(sql=sql.get_shot_spots_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_player_game(connection: str):
    return data_source.run_query(sql=sql.get_player_game_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_game_summary(connection: str, version: int):
    return data_source.run_query(sql=sql.get_game_summary_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_pbp_data_cached(game_selelct, version: int):
    my_sql = sql.get_play_sql().replace("?", str(game_selelct))
    return data_source.run_query(sql=my_sql, connection=SQL_CONN)

@st.cache_data(show_spinner=False)
def load_game_stats(connection, version: int):
    return data_source.run_query(sql=sql.get_current_game_stats_plays_sql(), connection=connection)

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

def create_stat_df(player_number, game_val_final, stat_type):
    cols = ["GAME_ID", "NUMBER", "STAT_TYPE"]
    row = [game_val_final, player_number, stat_type]
    return pd.DataFrame([row], columns=cols)

def get_values_needed(game_val: str, game_df: pd.DataFrame, player_val: str):
    opponent_name, game_date = game_val.split(" - ")
    game_row = game_df[
        (game_df["OPPONENT"] == opponent_name) & (game_df["DATE"] == game_date)
    ]
    player_number = int(player_val.split(" - ")[0])
    game_id = int(game_row["GAME_ID"].values[0])
    return player_number, game_id

def upsert_game_summary(player_number, game_id, SQL_CONN):
    # Build formatted SQL for this player/game
    new_query = (
        sql.get_formatted_game_sql()
        .replace("this_game_id", str(game_id))
        .replace("this_player_id", str(player_number))
    )

    # Pull fresh computed summary for this player/game
    new_game_summary = data_source.run_query(sql=new_query, connection=SQL_CONN)

    # Load existing summaries
    game_summary_data = load_game_summary(SQL_CONN, st.session_state.game_version)

    # Build composite ID
    my_id = f"{player_number}_{game_id}"

    # Build list of existing IDs
    game_summary_ids = game_summary_data.copy()
    game_summary_ids["_id"] = (
        game_summary_ids["PLAYER_ID"].astype(str)
        + "_"
        + game_summary_ids["GAME_ID"].astype(int).astype(str)
    )
    existing_ids = set(game_summary_ids["_id"].unique().tolist())

    # Extract values in correct order
    if len(new_game_summary) == 0:
        vals = [
            str(0),  # TWO_FGM,
            str(0),  # TWO_FGA,
            str(0),  # THREE_FGM,
            str(0),  # THREE_FGA,
            str(0),  # FTM,
            str(0),  # FTA,
            str(0),  # OFFENSIVE_REBOUNDS,
            str(0),  # DEFENSIVE_REBOUNDS,
            str(0),  # ASSISTS,
            str(0),  # STEALS,
            str(0),  # BLOCKS,
            str(0),  # TURNOVER,
            str(0),  # FOULS,
        ]
    else:
        vals = [
            str(new_game_summary["TWO_FGM"].values[0]),
            str(new_game_summary["TWO_FGA"].values[0]),
            str(new_game_summary["THREE_FGM"].values[0]),
            str(new_game_summary["THREE_FGA"].values[0]),
            str(new_game_summary["FTM"].values[0]),
            str(new_game_summary["FTA"].values[0]),
            str(new_game_summary["OFFENSIVE_REBOUNDS"].values[0]),
            str(new_game_summary["DEFENSIVE_REBOUNDS"].values[0]),
            str(new_game_summary["ASSISTS"].values[0]),
            str(new_game_summary["STEALS"].values[0]),
            str(new_game_summary["BLOCKS"].values[0]),
            str(new_game_summary["TURNOVER"].values[0]),
            str(new_game_summary["FOULS"].values[0]),
        ]

    # Insert or update
    with sqlitecloud.connect(SQL_CONN) as conn:
        cursor = conn.cursor()

        if my_id not in existing_ids:
            cursor.execute(
                sql=sql.insert_game_summary_sql(),
                parameters=(player_number, str(game_id), *vals),
            )
        else:
            cursor.execute(
                sql=sql.update_game_summary_sql(),
                parameters=(*vals, str(player_number), str(game_id)),
            )

        conn.commit()
    return new_game_summary

shot_spots = load_shot_spots(SQL_CONN)
player_game = load_player_game(SQL_CONN)

games = player_game.sort_values(by="SEASON", ascending=False).reset_index(drop=True)
season_list = games["SEASON"].unique().tolist()


top_left, top_mid, top_right = st.columns([1.2, 1.2, 0.2])

with top_left:
    season = st.radio("Season", season_list, horizontal=True)

games_season = games[games["SEASON"] == season].copy()
games_season["DATE_DTTM"] = pd.to_datetime(games_season["DATE"])
games_season = games_season.sort_values(by="DATE_DTTM")
games_season["GAME_LABEL"] = games_season["GAME_LABEL"].astype(str)
game_list = games_season["GAME_LABEL"].unique().tolist()[::-1]

with top_mid:
    game_select = st.selectbox("Game", game_list, index=0)
    
with top_right:
    if st.button("Clear Cache", key="clear_cache_btn", type='primary'):
        load_pbp_data_cached.clear()
        load_player_game.clear()
        load_game_summary.clear()
        st.success("Cache cleared")
        time.sleep(1)
        st.rerun()

game = games_season[games_season["GAME_LABEL"] == game_select].iloc[0]
game_id = int(game["GAME_ID"])
game_val = game["GAME_LABEL"]

games_season["NUMBER_INT"] = games_season["NUMBER"].astype(int)
unique_players = games_season.sort_values("NUMBER_INT")["PLAYER_LABEL"].unique()

fig = build_blank_chart()
col_chart, col_form = st.columns([0.45, 0.55])
with col_chart:
    clicked = plotly_events(plot_fig=fig, click_event=True, key=f"shot-capture-{game_id}")

# Load pbp data (cached, versioned)
pbp_data = load_pbp_data_cached(game_select, st.session_state.pbp_version)
game_stat_plays = load_game_stats(SQL_CONN, st.session_state.game_stat_version)
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
                c2, c3, c4, c5 = st.columns([1, 1, 1, 1])
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
                    'Shot','Offensive Rebound', 'Defensive Rebound', 'Assist',
                     'Steal', 'Block', 'Turnover', 'Foul'
                ]
                choose_stat = st.radio(label="Stat Type", options=other_stats, horizontal=True)
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
                    if choose_stat != 'Shot' and player_number == 0:
                        st.error('Please select a valid player number')
                        st.stop()
                    if player_number != 0:
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
                            st.session_state.refresh_game_stat_version = True
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
                        st.session_state.game_stat_version += 1
                        load_game_stats.clear()
                        new_game_summary = upsert_game_summary(
                            player_number=player_number,
                            game_id=game_val_final,
                            SQL_CONN=SQL_CONN
                        )
                        stat_val = new_game_summary[final_stat].values[0]
                        st.success(
                            f'Player {player_number} now has {stat_val} {final_stat} '
                            f'for game {game_val}'
                        )
                        st.session_state.game_stat_version += 1
                        st.session_state.refresh_game_stat_version = True
                    
                    if choose_stat == 'Shot':
                        spot_lookup = shot_spots.drop(columns=["XSPOT", "YSPOT"]).set_index("SPOT")
                        my_df = my_df.join(spot_lookup, on="SPOT")
                        all_data_game = pbp_data
                        max_play_num = all_data_game["PLAY_NUM"].max() if len(all_data_game) > 0 else 0
                        my_df["PLAY_NUM"] = max_play_num + 1

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
                        load_pbp_data_cached.clear()
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
    st.success("Play-by-play data refreshed!")
    st.session_state.refresh_pbp = False

if st.session_state.refresh_game_stat_version:
    st.write("Refreshing game stats data...")
    load_game_stats.clear()
    game_stat_plays = load_game_stats(SQL_CONN, st.session_state.refresh_game_stat_version)
    st.success("Game stats data refreshed!")
    st.session_state.refresh_game_stat_version = False

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
simple_data = simple_data.sort_values(by="PLAY_NUM", ascending=False).head(100).reset_index(drop=True)

# Add DELETE column as boolean and ensure deterministic column order
simple_data["DELETE"] = False
simple_data = simple_data[["NUMBER", "SPOT", "SHOT_DEFENSE", "MAKE_MISS", "PLAY_NUM", "GAME_ID", "DELETE"]]

left_col, right_col = st.columns([2, 1])
with left_col:
    left_side, right_side = st.columns([1, .5])
    st.markdown(f"**Showing last 100 shots for Game ID: {game_id}**")
    with right_side:
        delete = st.button("Delete Selected Shots", key=f"delete_btn_{game_id}")
    editor_key = f"prev_shots_editor_{game_id}"
    edited_df = st.data_editor(
        simple_data, 
        hide_index=True,
        key=editor_key,
        width='stretch',
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
    current_totals['Turnover %'] = (
        current_totals['TEAM_TURNOVERS'] / np.where(
            current_totals['POSSESSIONS'] == 0,
            1,
            current_totals['POSSESSIONS']
        )
    )
    current_totals['Assist %'] = (
        current_totals['TEAM_ASSISTS'] / np.where(
            current_totals['TEAM_FGM'] == 0,
            1,
            current_totals['TEAM_FGM']
        )
    )
    current_totals['Free Throw Rate'] = (
        current_totals['TEAM_FTA'] / np.where(
            current_totals['TEAM_FGA'] == 0,
            1,
            current_totals['TEAM_FGA']
        )
    )
    current_totals['True Shooting %'] = (
        current_totals['POINTS'] / np.where(
            (current_totals['TEAM_FGA'] + 0.44 * current_totals['TEAM_FTA']) == 0,
            1,
           2 * (current_totals['TEAM_FGA'] + 0.44 * current_totals['TEAM_FTA'])
        )
    )
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
             'TEAM_BLOCKS': 'Blocks',
             'POSSESSIONS': 'Possessions',
             'POINTS': 'Points'},
        )
    )
    current_totals['PPP'] = current_totals['Points'] / np.where(
        current_totals['Possessions'] == 0,
        1,
        current_totals['Possessions']
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
        'Turnovers', 'eFG%', 'Possessions', 'PPP', 'PPA',
        'Turnover %', 'Assist %', 'Free Throw Rate', 'True Shooting %', 'Points'
    ]]
    st.markdown("#### Current Game Totals")
    def efg_val(val):
        if val >= .6:
            return "background-color: green"
        elif val >= .5:
            return "background-color: lightyellow"
        else:
            return "background-color: red"
        
    def ppp_val(val):
        if val >= 1.1:
            return "background-color: green"
        elif val >= 1.0:
            return "background-color: lightyellow"
        else: 
            return "background-color: red"
    
    def to_val(val):
        if val >= .2:
            return "background-color: red"
        elif val >= .155:
            return "background-color: lightyellow"
        else:
            return "background-color: green"
    
    def tr_val(val):
        if val >= .6:
            return "background-color: green"
        elif val >= .55:
            return "background-color: lightyellow"
        else:
            return "background-color: red"
        
    def ft_val(val):
        if val >= .25:
            return "background-color: green"
        elif val >= .175:
            return "background-color: lightyellow"
        else:
            return "background-color: red"

    top_row = current_totals[['2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA']]
    second_row = current_totals[[
        'OREB', 'DREB', 'Assists', 'Steals', 'Blocks',
    ]]
    third_row = current_totals[[
        'Turnovers', 'eFG%', 'Possessions', 'PPP', 'PPA',
    ]]
    fourth_row = current_totals[[
        'Turnover %', 'Assist %', 'Free Throw Rate', 'True Shooting %', 'Points'
    ]]
    fourth_row = fourth_row.rename(
        columns={
            'True Shooting %': 'TS%',
             'Free Throw Rate': 'FTR',
        }
    )
    third_row_styled = (
        third_row.style.map(efg_val, subset=['eFG%'])
        .map(ppp_val, subset=['PPP'])
        .format({
            'Turnovers': '{:.0f}',
            'Possessions': '{:.0f}',
            'eFG%': '{:.1%}',
            'PPP': '{:.2f}',
            'PPA': '{:.2f}',
        })
    )
    fourth_row_styled = (
        fourth_row.style.map(lambda x: to_val(x), subset=['Turnover %'])
        .map(tr_val, subset=['TS%'])
        .map(ft_val, subset=['FTR'])
        .format({
            'Turnover %': '{:.1%}',
            'Assist %': '{:.1%}',
            'FTR': '{:.1%}',
            'TS%': '{:.1%}',
            'Points': '{:.0f}',
        })
    )
    # build df_display as you already do
    # render with data_editor
    st.dataframe(
       top_row,
        width="stretch",
        hide_index=True
    )
    st.dataframe(
        second_row,
        width="stretch",
        hide_index=True
    )
    st.dataframe(
        third_row_styled,
        width="stretch",
        hide_index=True
    )
    st.dataframe(
        fourth_row_styled,
        width="stretch",
        hide_index=True
    )

    game_stat_plays['DELETE'] = False
    game_stat_plays['GAME_ID'] = game_stat_plays['GAME_ID'].astype(int)
    game_stat_plays = game_stat_plays[game_stat_plays['GAME_ID'] == game_id]
    delete_data = st.data_editor(
        game_stat_plays,
        hide_index=True,
        key=f"delete_stats_editor_{game_id}",
        column_config={
            "PLAYER_ID": st.column_config.NumberColumn(
                "Player",
                help="Jersey number of the player who took the shot",
                width=75
            ),
            'STAT': st.column_config.TextColumn(
                'Stat Type',
                help='Type of stat (e.g. 2FGM, ASSISTS, TURNOVER)',
            ),
            "id": st.column_config.NumberColumn(
                "Play Number",
                help="Sequential number of the play in the game",
                width=75

            ),
            "GAME_ID": st.column_config.NumberColumn(
                "Game ID",
                help="Identifier for the game",
            ),
            "DELETE": st.column_config.CheckboxColumn(
                "Delete",
                help="Check to mark this shot for deletion from the database",
            ),
        }
    )
    delete = st.button("Delete Selected Stat", key=f"delete_stat_btn_{game_id}")
    if delete:
        # Guard: edited_df may be None if widget wasn't read; handle gracefully
        if delete_data is None:
            st.info("No data available to delete.")
        else:
            selected_deletes = delete_data[delete_data["DELETE"] == True]
            game_val_delete_id = None
            if len(selected_deletes) == 0:
                st.info("No rows selected for deletion.")
            else:
                deleted_count = 0
                with sqlitecloud.connect(SQL_CONN) as conn:
                    cursor = conn.cursor()
                    for _, row in selected_deletes.iterrows():
                        st.write(row['GAME_ID'], row['PLAYER_ID'], row['STAT'], row['id'])
                        cursor.execute(
                            sql=sql.delete_game_play(),
                            parameters=(
                                str(int(row["GAME_ID"])),
                                str((row["PLAYER_ID"])),
                                str((row["STAT"])),
                                str(int(row["id"])))
                        )
                        deleted_count += 1
                        game_val_delete_id = int(row["GAME_ID"])
                        player_number = int(row["PLAYER_ID"])
                    conn.commit()

                st.success(f"Deleted {deleted_count} shots")
                load_game_stats.clear()
                new_game_summary = upsert_game_summary(
                    player_number=player_number,
                    game_id=game_val_delete_id,
                    SQL_CONN=SQL_CONN
                )
                st.session_state.game_stat_version += 1
                st.session_state.refresh_game_stat_version = True
                st.rerun()


load_game_summary.clear()
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
with left_col:
    st.dataframe(
        this_game_summary,
        width='stretch',
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