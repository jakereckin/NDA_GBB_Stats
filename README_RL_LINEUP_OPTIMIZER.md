# Offline RL Lineup Optimizer

This feature adds an admin-only historical reinforcement-learning workflow. The objective is **cumulative point differential**, not win probability.

## Data contract and validation

The pipeline reads the existing MINUTES, GAMES, and PLAYERS tables, using the app's season-specific jersey-number join. It assumes a descending 36-minute clock: 2160 seconds remaining at tip and 0 at game end. The clock length is configurable in build_dataset and must be verified for every competition format.

Each interval between recorded substitution boundaries becomes one stint. A game is excluded in full if it has an invalid clock interval, overlapping shifts for one player, anything other than five distinct active players, missing/conflicting score snapshots, negative/decreasing scores, clock gaps, score discontinuities, or rewards that fail to reconcile to the final point differential.

Reward is:

    (team points at stint end - team points at stint start)
    - (opponent points at stint end - opponent points at stint start)

State: score differential, seconds remaining, previous lineup.
Action: the five-player lineup used for the next observed stint.
Transition: end score differential, end clock, and current lineup as previous lineup.
Terminal rows do not bootstrap a future value. Gamma defaults to 1 for total remaining-game point differential.

## Model

Fitted Q-Iteration uses an ExtraTrees regressor. Candidate actions are restricted to lineups observed in the selected season with at least the configured minimum stint support (default 5). This reduces but does not eliminate extrapolation risk. Recommendation output includes historical stint support.

## Run locally

Install requirements and launch the app:

    pip install -r requirements.txt
    streamlit run Home.py

Open View Data → RL Lineup Optimizer as an authorized administrator. The page loads historical minutes, displays validation issues, allows selection of season and support threshold, trains FQI, and ranks supported lineups for the entered state. Models remain in Streamlit session state; no credentials or model files are committed.

Run unit tests:

    pytest -q tests/test_rl_data_pipeline.py tests/test_rl_fqi.py

The supplied tests use synthetic fixtures. Before operational use, perform game-level holdout and season-forward evaluation. Do not randomly split stint rows: adjacent stints in a game are dependent and can leak context. Compare against simple baselines such as the most-used lineup, historical plus/minus per minute, and current coaching rotation.

## Important limitation

This is observational offline RL. Historical lineup selection is confounded by opponent strength, player availability, foul trouble, score state, and coaching decisions. FQI estimates associations in historical data; it does not identify causal lineup effects or guarantee that changing a lineup will improve point differential. Treat recommendations as exploratory decision support, not automated coaching decisions.
