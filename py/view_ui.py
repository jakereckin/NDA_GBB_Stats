import streamlit as st


METRIC_GUIDES = {
    "team_shot_chart": {
        "Shot selection GPA": "Average shot-quality grade, with A=4, B=3, C=2, D=1, and F=0.",
        "Points per attempt": "Points scored divided by shot attempts.",
        "Paint-touch threes": "Share of three-point attempts recorded with a paint touch.",
    },
    "player_shot_chart": {
        "Shot selection GPA": "Average shot-quality grade, with A=4, B=3, C=2, D=1, and F=0.",
        "Points per attempt": "Points scored divided by shot attempts.",
        "Make percentage": "Made shots divided by shot attempts.",
    },
    "view_expected_points": {
        "Expected points": "Shot value multiplied by its model-estimated make probability.",
        "Effective field-goal percentage": "FGM plus half-credit for each made three, divided by field-goal attempts.",
        "Simulation range": "The 10th-to-90th percentile range describes lower-to-higher scoring outcomes in the simulations.",
    },
    "view_game_summary": {
        "Points per game": "NDA points divided by the number of selected games.",
        "Effective FG%": "Field-goal percentage adjusted to account for the extra value of made threes.",
        "Rebounds per game": "Offensive plus defensive rebounds, averaged across selected games.",
        "Assists per game": "Recorded team assists, averaged across selected games.",
        "Turnovers per game": "Recorded team turnovers, averaged across selected games.",
        "Player per-game stats": "Counting stats are averaged over each player's games played in the selection.",
        "Shooting percentages": "Calculated from combined makes and attempts, not by averaging game percentages.",
        "Game Score": "A box-score summary score combining scoring, rebounds, assists, defensive plays, turnovers, and fouls.",
    },
    "view_season_trend": {
        "OE": "Offensive efficiency: (field goals made + assists) divided by estimated possessions used.",
        "eFG%": "Field-goal percentage adjusted to account for the extra value of made threes.",
        "TS%": "Points scored per shooting opportunity, including free throws.",
        "PPP": "Points scored divided by estimated possessions.",
        "PPA": "Points scored divided by field-goal attempts.",
        "FTR": "Free-throw attempts divided by field-goal attempts.",
        "Game Score": "A box-score summary score combining scoring, rebounds, assists, defensive plays, turnovers, and fouls.",
    },
    "view_minutes": {
        "Scoring margin per minute": "Team points minus opponent points while the player or lineup is on court, divided by minutes played.",
        "Points per minute": "Team points scored while on court, divided by minutes played.",
        "Games played": "Number of games with recorded minutes for the player or lineup.",
    },
    "view_lineup_network": {
        "Scoring margin per minute": "Team points minus opponent points while the lineup is on court, divided by minutes played.",
        "Transition count": "Number of times the graph records a change from one lineup to another.",
        "Minimum minutes": "Filters out lineups with less recorded playing time before drawing the graph.",
    },
}


def _sync_shared_selection(widget_key, shared_key):
    selected = st.session_state.get(widget_key)
    if isinstance(selected, list):
        selected = selected[0] if selected else None
    if selected is not None:
        st.session_state[shared_key] = str(selected)


def _match_shared_option(options, shared_value):
    return next(
        (option for option in options if str(option) == str(shared_value)),
        None,
    )


def select_season(options, key, label="Season"):
    options = list(options)
    shared_season = st.session_state.get("view_shared_season")
    current = st.session_state.get(key)
    shared_option = _match_shared_option(options, shared_season)
    if shared_option is not None and str(current) != str(shared_option):
        selected = shared_option
        st.session_state[key] = selected
    elif current in options:
        selected = current
    else:
        selected = options[0]
        st.session_state[key] = selected
    selected = st.segmented_control(
        label=label,
        options=options,
        default=options[0],
        key=key,
        on_change=_sync_shared_selection,
        args=(key, "view_shared_season"),
    )
    _sync_shared_selection(key, "view_shared_season")
    return selected


def select_game(options, key, label="Game", help=None):
    options = list(options)
    shared_game = st.session_state.get("view_shared_game")
    current = st.session_state.get(key)
    shared_option = _match_shared_option(options, shared_game)
    if shared_option is not None and str(current) != str(shared_option):
        selected = shared_option
        st.session_state[key] = selected
    elif current in options:
        selected = current
    else:
        selected = options[0]
        st.session_state[key] = selected
    selected = st.selectbox(
        label=label,
        options=options,
        key=key,
        help=help,
        on_change=_sync_shared_selection,
        args=(key, "view_shared_game"),
    )
    _sync_shared_selection(key, "view_shared_game")
    return selected


def select_games(options, key, label="Games", help=None):
    options = list(options)
    current = st.session_state.get(key)
    shared_game = st.session_state.get("view_shared_game")
    shared_option = _match_shared_option(options, shared_game)
    if shared_option is not None and (
        not current or str(current[0]) != str(shared_option)
    ):
        current = [shared_option]
    elif current is None:
        current = options[:1]
    else:
        current = [option for option in current if option in options]
        if not current:
            current = options[:1]
    st.session_state[key] = current
    selected = st.multiselect(
        label=label,
        options=options,
        key=key,
        placeholder="Select one or more games",
        help=help,
        on_change=_sync_shared_selection,
        args=(key, "view_shared_game"),
        wrap=True
    )
    _sync_shared_selection(key, "view_shared_game")
    return selected


def render_page_context(page_key, scope):
    st.caption(f"Current view: {scope}")
    with st.expander("Metric guide"):
        for metric, description in METRIC_GUIDES[page_key].items():
            st.markdown(f"**{metric}:** {description}")
