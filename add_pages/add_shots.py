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

@st.cache_data(show_spinner=False)
def load_shot_spots(connection: str):
    return data_source.run_query(sql=sql.get_shot_spots_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_player_game(connection: str):
    return data_source.run_query(sql=sql.get_player_game_sql(), connection=connection)

@st.cache_data(show_spinner=False)
def load_game_summary(connection: str):
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
game_summary_data = load_game_summary(SQL_CONN)

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

st.write("Previous 30 shots")
editor_key = f"prev_shots_editor_{game_id}"
# Use use_container_width to make it render nicely; keep a stable key
edited_df = st.data_editor(simple_data, hide_index=True, key=editor_key, use_container_width=True)

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
# 