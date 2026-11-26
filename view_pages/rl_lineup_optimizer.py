import streamlit as st
import pandas as pd

from rl_lineup_optimizer.data_pipeline import build_dataset, fetch_minutes
from rl_lineup_optimizer.fqi import FQIConfig, FittedQIteration

st.set_page_config(page_title="RL Lineup Optimizer", layout="wide")
st.title("Offline RL Lineup Optimizer")
st.caption("Historical lineup decision support · Objective: cumulative point differential")

# Defense in depth: Home.py registers this page only for verified admins.
if st.session_state.get("auth_role") != "nda_admin":
    st.error("This page is available only to authorized NDA administrators.")
    st.stop()

connection = st.secrets.get("nda_gbb_connection", {}).get("DB_CONNECTION")
if not connection:
    st.error("Missing [nda_gbb_connection].DB_CONNECTION in Streamlit secrets.")
    st.stop()


@st.cache_data(show_spinner="Loading historical minutes and validating games…")
def load_data(db_connection):
    raw = fetch_minutes(db_connection)
    return build_dataset(raw, game_end_sec=2160)


try:
    stints, transitions, issues = load_data(connection)
except Exception as exc:
    st.exception(exc)
    st.stop()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Valid games", int(stints.GAME_ID.nunique()) if not stints.empty else 0)
c2.metric("Valid stints", len(stints))
c3.metric("RL transitions", len(transitions))
c4.metric("Excluded games", int(issues.GAME_ID.nunique()) if not issues.empty else 0)

with st.expander("Data validation details", expanded=not issues.empty):
    if issues.empty:
        st.success("No validation issues found in the loaded data.")
    else:
        st.warning("A game with any validation issue is excluded in full.")
        st.dataframe(issues,use_container_width=True,hide_index=True)

if transitions.empty:
    st.info("No valid transitions are available. Correct the source minutes/score records before training.")
    st.stop()

st.subheader("Train a season-specific model")
seasons = sorted(transitions.SEASON.astype(str).unique().tolist(),reverse=True)
season = st.selectbox("Season",seasons)
a,b,c = st.columns(3)
with a:
    min_support = st.number_input("Minimum historical stint support",min_value=2,max_value=100,value=5,step=1)
with b:
    iterations = st.number_input("FQI iterations",min_value=1,max_value=20,value=8,step=1)
with c:
    top_k = st.number_input("Recommendations to show",min_value=1,max_value=20,value=5,step=1)

season_data = transitions[transitions.SEASON.astype(str)==season].copy()
st.write(f"Training sample: **{len(season_data):,}** stint transitions across **{season_data.GAME_ID.nunique()}** games.")

if st.button("Train / refresh model",type="primary"):
    with st.spinner("Fitting fitted Q-iteration model…"):
        model = FittedQIteration(FQIConfig(iterations=int(iterations),min_lineup_stints=int(min_support)))
        try:
            model.fit(season_data)
            st.session_state["nda_rl_model"] = model
            st.session_state["nda_rl_model_season"] = season
            st.success(f"Model trained on {model.training_rows:,} transitions. It is stored for this session only.")
        except Exception as exc:
            st.session_state.pop("nda_rl_model",None)
            st.session_state.pop("nda_rl_model_season",None)
            st.exception(exc)

model = st.session_state.get("nda_rl_model")
model_season = st.session_state.get("nda_rl_model_season")
if model is not None and model_season == season:
    st.subheader("Evaluate a game state")
    x,y,z = st.columns(3)
    with x:
        score_diff = st.number_input("Current score differential (NDA minus opponent)",value=0,step=1)
    with y:
        seconds_remaining = st.number_input("Seconds remaining",min_value=0,max_value=2160,value=1080,step=30)
    with z:
        roster = model.players_by_season[season]
        previous_lineup = st.multiselect("Previous lineup (optional)",roster,format_func=lambda p:f"#{p}")
    if previous_lineup and len(previous_lineup)!=5:
        st.warning("Select exactly five players for the previous lineup, or clear the selection.")
    elif st.button("Recommend lineups"):
        try:
            result = model.recommend(season,score_diff,seconds_remaining,previous_lineup,int(top_k))
            result = result.rename(columns={
                "LINEUP":"Lineup",
                "ESTIMATED_FUTURE_POINT_DIFFERENTIAL":"Estimated future point differential",
                "HISTORICAL_STINT_SUPPORT":"Historical stint support"})
            st.dataframe(result.round(3),use_container_width=True,hide_index=True)
            st.caption("Model estimates are not calibrated causal effects or guaranteed point margins.")
        except Exception as exc:
            st.exception(exc)
else:
    st.info("Train a model for the selected season to generate recommendations.")

st.divider()
st.caption("Observational offline model. Validate on held-out games and future seasons before coaching use.")
