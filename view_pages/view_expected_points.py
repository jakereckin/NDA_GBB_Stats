import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import polars as pl
from py import sql, data_source, view_ui
import joblib
from pathlib import Path

pd.options.mode.chained_assignment = None

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']
st.set_page_config(page_title='Expected Points', layout='wide')
st.title('Expected Points')
st.caption(
    'Compare expected and actual scoring, review shot quality, and explore '
    'a range of possible game outcomes.'
)

effective_field_goal_description = '''
Effective FG% is a useful metric to understand shot selection.
The formula is (2FGM + 1.5 * 3FGM) / FGA. The extra weight for made
threes reflects their additional point value.
'''

expected_points_description = '''
Expected points is the shot's point value multiplied by the model-estimated
chance of making it.

Example: a 3-pointer with a 33% make probability is worth 0.33 * 3 = 0.99
expected points.
'''

with st.expander('About these metrics'):
    st.markdown(effective_field_goal_description)
    st.markdown(expected_points_description)
@st.cache_resource
def load_pipeline():
    pipeline_path = Path(__file__).resolve().parents[1] / 'pipeline.pkl'
    return joblib.load(filename=pipeline_path)


@st.cache_data(
    show_spinner='Loading game data and preparing shot predictions...',
    ttl='15m',
    max_entries=1
)
def load_expected_points_data():
    player_data = data_source.run_query(
        sql=sql.get_play_by_play_sql(),
        connection=sql_lite_connect
    )
    player_data = pl.from_pandas(data=player_data)
    play_event_spot = build_features(player_data=player_data)
    play_event_spot = apply_model(play_event_spot=play_event_spot)
    return play_event_spot


# ----------------------------------------------------------------------------
def build_features(player_data):
    '''
    Build features for basketball play events.

    Parameters:
    play_event (pd.DataFrame): DataFrame containing play event data.
    spot (pd.DataFrame): DataFrame containing spot data.
    players (pd.DataFrame): DataFrame containing player data.
    games (pd.DataFrame): DataFrame containing game data.

    Returns:
    pd.DataFrame: DataFrame with additional features built from the input data.
    
    Features created:
    - INTIAL_PERCENTAGE: Initial percentage based on player ID.
    - MAKE: Binary indicator if the shot was made.
    - ATTEMPT: Binary indicator of a shot attempt.
    - INIT_EXPECTED: Initial expected points.
    - SPOT_TOTAL_MAKES: Total makes by spot.
    - SPOT_TOTAL_ATTEMPTS: Total attempts by spot.
    - SPOT_TOTAL_PERCENTAGE: Shooting percentage by spot.
    - GAME_MAKES: Total makes in the game.
    - GAME_ATTEMPTS: Total attempts in the game.
    - GAME_PERCENTAGE: Shooting percentage in the game.
    - GAME_TOTAL_MAKES: Total makes in the game by year.
    - GAME_TOTAL_ATTEMPTS: Total attempts in the game by year.
    - SHOT_DEFENSE_CODED: Coded shot defense.
    - GAME_ROLLING_MAKES: Rolling sum of makes in the game.
    - GAME_ROLLING_ATTEMPTS: Rolling sum of attempts in the game.
    - ROLLING_PERCENT: Rolling shooting percentage.
    - SEASON_LAST_5: Rolling sum of makes in the last 5 games.
    - SEASON_LAST_5_ATTEMPTS: Rolling sum of attempts in the last 5 games.
    - SEASON_LAST_5_PERCENT: Rolling shooting percentage in the last 5 games.
    - HOME_FLAG: Binary indicator if the game is at home.
    - ACTUAL_POINTS: Actual points scored.
    - TEAM: Team identifier.
    - ROLLING_POINTS_TEAM: Rolling sum of points by team.
    - GAME_TEAM_MAKES: Total makes by team in the game.
    - GAME_TEAM_ATTEMPTS: Total attempts by team in the game.
    - GAME_TEAM_PERCENTAGE: Shooting percentage by team in the game.
    - LAST_ROLLING_POINTS_TEAM_NDA: Last rolling points for NDA team.
    - LAST_ROLLING_POINTS_TEAM_OPPONENT: Last rolling points for opponent team.
    - TEAM_SPREAD: Difference in rolling points between teams.
    '''
    CODED_SHOT_DEFENSE = {
        'OPEN': 0,
        'GUARDED': 1,
        'HEAVILY_GUARDED': 2,
        'Heavily Guarded': 2,
        'Guarded': 1
    }
    _player_merge_list = ['PLAYER_ID', 'SPOT', 'SHOT_DEFENSE', 'YEAR']
    _player_game_merge_list = ['GAME_ID', 'PLAYER_ID', 'YEAR', 'SPOT', 'SHOT_DEFENSE']
    _player_year_list = ['GAME_ID', 'PLAYER_ID', 'YEAR']
    _player_game_list = ['GAME_ID', 'PLAYER_ID', 'YEAR', 'SHOT_DEFENSE']
    _team_game_list = ['GAME_ID', 'TEAM', 'YEAR', 'SPOT', 'SHOT_DEFENSE']
    play_event_spot = (
        player_data.sort(by=['GAME_ID', 'PLAY_NUM'])
                   .with_columns(
                       INTIAL_PERCENTAGE=pl.when(
                            condition=pl.col(name='PLAYER_ID') == '0'
                          ).then(
                            statement=pl.col(name='OPP_EXPECTED') / pl.col(name='POINTS')
                          ).otherwise(statement=0.33),
                       MAKE=pl.when(condition=pl.col(name='MAKE_MISS') == 'Y')
                              .then(statement=1)
                              .otherwise(statement=0),
                       ATTEMPT=1
                   )
    )
    #play_event_spot = player_event_spot.to_pandas()
    play_event_spot = play_event_spot.with_columns(
        INIT_EXPECTED=(
            pl.col(name='INTIAL_PERCENTAGE') * pl.col(name='POINTS')
        ),
        SPOT_TOTAL_MAKES=(
            pl.col(name='MAKE')
              .sum()
              .over(_player_merge_list)
        ),
        SPOT_TOTAL_ATTEMPTS=(
            pl.col(name='ATTEMPT')
              .sum()
              .over(_player_merge_list)
        ),
    )
    play_event_spot = (
        play_event_spot.with_columns(
            SPOT_TOTAL_PERCENTAGE=(
                pl.col(name='SPOT_TOTAL_MAKES')
                / pl.col(name='SPOT_TOTAL_ATTEMPTS')
            ),
            GAME_MAKES=(
                pl.col(name='MAKE')
                  .sum()
                  .over(_player_game_merge_list)
            ),
            GAME_ATTEMPTS=(
                pl.col('ATTEMPT')
                  .sum()
                  .over(_player_game_merge_list)
            ),
            GAME_TOTAL_MAKES=(
                pl.col('MAKE')
                  .sum()
                  .over(_player_year_list)
            ),
            GAME_TOTAL_ATTEMPTS=(
                pl.col('ATTEMPT')
                  .sum()
                  .over(_player_year_list)
            )
        )
    )
    #play_event_spot = play_event_spot.to_pandas()
    play_event_spot = play_event_spot.with_columns(
        GAME_PERCENTAGE=(
            pl.col(name='GAME_MAKES') / pl.col(name='GAME_ATTEMPTS')
        ),
        SHOT_DEFENSE_CODED=(
            pl.col(name='SHOT_DEFENSE').map_dict(CODED_SHOT_DEFENSE)
        )
    )
    play_event_spot = play_event_spot.with_columns(
        GAME_ROLLING_MAKES=(
            pl.col('MAKE')
              .rolling_sum(window_size=1000, min_periods=0)
              .over(_player_game_list)
        ),
        GAME_ROLLING_ATTEMPTS=(
            pl.col('ATTEMPT')
              .rolling_sum(window_size=1000, min_periods=0)
                .over(_player_game_list)
        ),
        SEASON_LAST_5=(
            pl.col('MAKE')
              .rolling_sum(window_size=5, min_periods=0)
              .over(['PLAYER_ID', 'YEAR'])
        ),
        SEASON_LAST_5_ATTEMPTS=(
            pl.col('ATTEMPT')
              .rolling_sum(window_size=5, min_periods=0)
              .over(['PLAYER_ID', 'YEAR'])
        ),
        HOME_FLAG=(
            pl.when(condition=pl.col(name='LOCATION') == 'Home')
              .then(statement=1)
              .otherwise(statement=0)
        ),
        ACTUAL_POINTS=(
            pl.col(name='MAKE') * pl.col(name='POINTS')
        ),
        TEAM=(
            pl.when(condition=pl.col(name='PLAYER_ID') == '0')
              .then(statement='OPPONENT')
              .otherwise(statement='NDA')
        )

    )
    play_event_spot = play_event_spot.with_columns(
        ROLLING_PERCENT=(
            pl.col(name='GAME_ROLLING_MAKES')
            / pl.col(name='GAME_ROLLING_ATTEMPTS')
        ),
        SEASON_LAST_5_PERCENT=(
            pl.col(name='SEASON_LAST_5')
            / pl.col(name='SEASON_LAST_5_ATTEMPTS')
        ),
        ROLLING_POINTS_TEAM=(
            pl.col('ACTUAL_POINTS')
            .rolling_sum(window_size=1000, min_periods=0)
            .over(['GAME_ID', 'YEAR', 'TEAM'])
        ),
        GAME_TEAM_MAKES=(
            pl.col('MAKE')
            .sum()
            .over(_team_game_list)
        ),
        GAME_TEAM_ATTEMPTS=(
            pl.col('ATTEMPT')
            .sum()
            .over(_team_game_list)
        ),
    )
    play_event_spot = play_event_spot.with_columns(
        GAME_TEAM_PERCENTAGE=(
            pl.col(name='GAME_TEAM_MAKES')
            / pl.col(name='GAME_TEAM_ATTEMPTS')
        ),
        LAST_ROLLING_POINTS_TEAM_NDA=(
            pl.when(pl.col('TEAM') == 'NDA')
            .then(pl.col('ROLLING_POINTS_TEAM').shift(1).over('GAME_ID'))
            .otherwise(None)
        )
    )
    play_event_spot = play_event_spot.with_columns(
        LAST_ROLLING_POINTS_TEAM_NDA=(
            pl.col('LAST_ROLLING_POINTS_TEAM_NDA')
            .fill_null(strategy='forward')
            .fill_null(value=0)
        ),
        LAST_ROLLING_POINTS_TEAM_OPPONENT=(
            pl.when(pl.col('TEAM') == 'OPPONENT')
            .then(pl.col('ROLLING_POINTS_TEAM').shift(1).over('GAME_ID'))
            .otherwise(None)
        )
    )
    play_event_spot = play_event_spot.with_columns(
        LAST_ROLLING_POINTS_TEAM_OPPONENT=(
            pl.col('LAST_ROLLING_POINTS_TEAM_OPPONENT')
            .fill_null(strategy='forward')
            .fill_null(value=0)
        )
    )
    play_event_spot = play_event_spot.with_columns(
        TEAM_SPREAD=(
            pl.col('ROLLING_POINTS_TEAM') 
            - pl.col('LAST_ROLLING_POINTS_TEAM_OPPONENT')
        )
    )
    #play_event_spot = play_event_spot.to_pandas()
    # Compute LAST_ROLLING_POINTS_TEAM_NDA in polars before converting to pandas
    return play_event_spot

def apply_model(play_event_spot):
    '''
    Apply a pre-trained model to predict the expected 
    points for a given play event spot.

    Parameters:
    play_event_spot (DataFrame): A pandas DataFrame containing
    the play event spot data with the following columns:
        - 'XSPOT'
        - 'YSPOT'
        - 'SPOT_TOTAL_MAKES'
        - 'GAME_PERCENTAGE'
        - 'GAME_ATTEMPTS'
        - 'INTIAL_PERCENTAGE'
        - 'GAME_TOTAL_MAKES'
        - 'SHOT_DEFENSE_CODED'
        - 'ROLLING_PERCENT'
        - 'SEASON_LAST_5_PERCENT'
        - 'INIT_EXPECTED'
        - 'HOME_FLAG'
        - 'GAME_TEAM_PERCENTAGE'
        - 'OPP_EXPECTED'
        - 'LAST_ROLLING_POINTS_TEAM_OPPONENT'
        - 'TEAM_SPREAD'
        - 'LAST_ROLLING_POINTS_TEAM_NDA'
        - 'POINTS'
        - 'OPPONENT'
        - 'DATE'

    Returns:
    DataFrame: The input DataFrame with additional columns:
        - 'PROB': The predicted probability of the event.
        - 'EXPECTED_POINTS': The expected points calculated
            as the product of 'PROB' and 'POINTS'.
        - 'LABEL': A label combining the 'OPPONENT' and 'DATE' columns.
    '''
    pipeline = load_pipeline()
    model_columns = [
    'XSPOT', 'YSPOT',
     'INTIAL_PERCENTAGE',
    'SHOT_DEFENSE_CODED', 'INIT_EXPECTED',
    'HOME_FLAG',  'OPP_EXPECTED',
    'LAST_ROLLING_POINTS_TEAM_OPPONENT', 
    'LAST_ROLLING_POINTS_TEAM_NDA'
    ]
    X = play_event_spot.select(model_columns)
    #X = play_event_spot[model_columns]
    play_event_spot = (
        play_event_spot.with_columns(
            PROB=pl.lit(pipeline.predict_proba(X)[:, 1])
        )
    )
    play_event_spot = play_event_spot.with_columns(
        EXPECTED_POINTS=(
            pl.col(name='PROB') * pl.col(name='POINTS')
        ),
        LABEL=(
            pl.col(name='OPPONENT') + ' - ' + pl.col(name='DATE')
        )
    )
    #play_event_spot['PROB'] = pipeline.predict_proba(X)[:,1]
    #play_event_spot['EXPECTED_POINTS'] = (
    #    play_event_spot['PROB'] * play_event_spot['POINTS']
    #)
    #play_event_spot['LABEL'] = (
    #    play_event_spot['OPPONENT'] + ' - ' + play_event_spot['DATE']
    #)
    return play_event_spot

def get_expected_points(play_event_spot, this_game):
    #return play_event_spot[play_event_spot['LABEL'] == this_game]
    game = play_event_spot.filter(
        pl.col(name='LABEL') == this_game
    )
    #game = game.to_pandas()
    return game



#-----------------------------------------------------------------------------
def run_simulations(tritons, opp, sims, standard_dev):
    def simulate_team(team_data, simulation_count):
        probabilities = team_data['PROB'].to_numpy()
        points = team_data['POINTS'].to_numpy()
        attempts = team_data['ATTEMPT'].to_numpy()
        simulated_percent = np.random.normal(
            loc=probabilities,
            scale=standard_dev,
            size=(simulation_count, len(probabilities))
        )
        np.clip(simulated_percent, 0, 1, out=simulated_percent)
        return (simulated_percent * points * attempts).sum(axis=1)

    team_shot_count = max(
        len(tritons),
        len(opp),
        1
    )
    batch_size = max(1, min(512, 2_000_000 // team_shot_count))
    nda_scores = np.empty(sims, dtype=float)
    opp_scores = np.empty(sims, dtype=float)
    progress = st.progress(0)

    for start in range(0, sims, batch_size):
        stop = min(start + batch_size, sims)
        nda_scores[start:stop] = simulate_team(tritons, stop - start)
        opp_scores[start:stop] = simulate_team(opp, stop - start)
        progress.progress(
            stop / sims,
            text=f'Simulating outcomes: {stop:,} of {sims:,}'
        )

    return pd.DataFrame({
        'NDA_SIMULATED_POINTS': nda_scores,
        'OPP_SIMULATED_POINTS': opp_scores,
        'WIN': (nda_scores > opp_scores).astype(int)
    })


play_event_spot = load_expected_points_data()

season_list = play_event_spot.select('SEASON').unique().to_series().to_list()
season_list = sorted(season_list, key=lambda value: int(value), reverse=True)
st.subheader('Choose a game')

if not season_list:
    st.info('No seasons with shot data are available yet.')
else:
    season_col, game_col = st.columns(spec=2, vertical_alignment='bottom')
    with season_col:
        season = view_ui.select_season(
            options=season_list,
            key='expected_points_season'
        )

    season_data = play_event_spot.filter(
        pl.col(name='SEASON') == str(season)
    )
    games_list = season_data.select('LABEL').unique().to_series().to_list()
    games_list = sorted(
        games_list,
        key=lambda label: pd.to_datetime(label.split(' - ')[1]),
        reverse=True
    )

    if not games_list:
        st.info('No games with shot data are available for this season.')
    else:
        with game_col:
            game = view_ui.select_game(
                options=games_list,
                key='expected_points_game',
                label='Game'
            )

        view_ui.render_page_context(
            page_key='view_expected_points',
            scope=f'{season} season · {game}'
        )
        this_game = get_expected_points(
            play_event_spot=play_event_spot,
            this_game=game
        )
        opp_team_name = game.split(' - ')[0]
        tritons = this_game.filter(pl.col(name='TEAM') != 'OPPONENT')
        opp = this_game.filter(pl.col(name='TEAM') == 'OPPONENT')

        def get_efg_percent(team_data):
            attempts = team_data.filter(pl.col(name='POINTS') != 1)
            total_attempts = attempts['ATTEMPT'].sum()
            if not total_attempts:
                return 0.0
            twos = attempts.filter(pl.col(name='POINTS') == 2)['MAKE'].sum()
            threes = attempts.filter(pl.col(name='POINTS') == 3)['MAKE'].sum()
            return (twos + 1.5 * threes) / total_attempts

        expected_fg = tritons['EXPECTED_POINTS'].sum()
        actual_fg = tritons['ACTUAL_POINTS'].sum()
        expected_fg_opp = opp['EXPECTED_POINTS'].sum()
        actual_fg_opp = opp['ACTUAL_POINTS'].sum()
        tritons_delta = actual_fg - expected_fg
        opp_delta = actual_fg_opp - expected_fg_opp

        st.caption(
            f"Sample size: {int(tritons['ATTEMPT'].sum())} NDA shot attempts "
            f"and {int(opp['ATTEMPT'].sum())} opponent shot attempts."
        )
        st.subheader('Game snapshot')
        team_cols = st.columns(spec=2)
        for team_col, team_name, actual, expected, delta, efg in (
            (
                team_cols[0],
                'NDA',
                actual_fg,
                expected_fg,
                tritons_delta,
                get_efg_percent(tritons)
            ),
            (
                team_cols[1],
                opp_team_name,
                actual_fg_opp,
                expected_fg_opp,
                opp_delta,
                get_efg_percent(opp)
            )
        ):
            with team_col:
                with st.container(border=True):
                    st.markdown(f'### {team_name}')
                    metric_cols = st.columns(spec=3)
                    with metric_cols[0]:
                        st.metric(
                            label='Actual points',
                            value=int(actual),
                            delta=f'{delta:+.2f} vs expected'
                        )
                    with metric_cols[1]:
                        st.metric(
                            label='Expected points',
                            value=f'{expected:.2f}',
                            help=expected_points_description
                        )
                    with metric_cols[2]:
                        st.metric(
                            label='Effective FG%',
                            value=f'{efg:.1%}',
                            help=effective_field_goal_description
                        )

        st.subheader('Outcome simulation')
        st.caption(
            'Run a scenario using the selected scoring assumptions. '
            'Results stay available while you switch between the chart and table.'
        )
        with st.form('expected_points_simulation_form', border=True):
            sim_cols = st.columns(spec=2)
            with sim_cols[0]:
                sim_count = st.number_input(
                    label='Number of simulations',
                    min_value=1,
                    max_value=10000,
                    value=500,
                    step=100,
                    help='More simulations provide a steadier estimate but take longer.'
                )
            with sim_cols[1]:
                standard_dev = st.number_input(
                    label='Probability variation',
                    min_value=0.01,
                    max_value=1.0,
                    value=0.3,
                    help='Standard deviation applied to each shot make probability.'
                )
            run_sim = st.form_submit_button(
                'Run simulation',
                type='primary',
                width='stretch'
            )

        simulation_key = (game, int(sim_count), float(standard_dev))
        if run_sim:
            all_sims = run_simulations(
                tritons=tritons,
                opp=opp,
                sims=int(sim_count),
                standard_dev=float(standard_dev)
            )
            st.session_state['expected_points_simulation'] = {
                'key': simulation_key,
                'results': all_sims
            }

        saved_simulation = st.session_state.get('expected_points_simulation')
        if saved_simulation and saved_simulation['key'] == simulation_key:
            all_sims = saved_simulation['results']
            lower_nda = all_sims['NDA_SIMULATED_POINTS'].quantile(0.1)
            upper_nda = all_sims['NDA_SIMULATED_POINTS'].quantile(0.9)
            lower_opp = all_sims['OPP_SIMULATED_POINTS'].quantile(0.1)
            upper_opp = all_sims['OPP_SIMULATED_POINTS'].quantile(0.9)
            win_percent, nda_range, opp_range = st.columns(spec=3)
            with win_percent:
                st.metric(
                    label='NDA simulated win rate',
                    value=f"{all_sims['WIN'].mean():.1%}"
                )
            with nda_range:
                st.metric(
                    label='NDA scoring range (10th-90th percentile)',
                    value=f'{lower_nda:.1f}-{upper_nda:.1f}'
                )
            with opp_range:
                st.metric(
                    label=f'{opp_team_name} scoring range (10th-90th percentile)',
                    value=f'{lower_opp:.1f}-{upper_opp:.1f}'
                )

            simulation_view = st.segmented_control(
                'Simulation display',
                options=['Distribution chart', 'Percentile table'],
                default='Distribution chart',
                key='expected_points_simulation_display'
            )
            if simulation_view == 'Percentile table':
                percentile_table = pd.DataFrame({
                    'Team': ['NDA', opp_team_name],
                    '10th percentile points': [lower_nda, lower_opp],
                    'Median points': [
                        all_sims['NDA_SIMULATED_POINTS'].median(),
                        all_sims['OPP_SIMULATED_POINTS'].median()
                    ],
                    '90th percentile points': [upper_nda, upper_opp]
                }).round(1)
                st.dataframe(
                    percentile_table,
                    width='stretch',
                    hide_index=True
                )
            else:
                chart_data = pd.DataFrame({
                    'Team': (
                        ['NDA'] * len(all_sims)
                        + [opp_team_name] * len(all_sims)
                    ),
                    'Points': np.concatenate([
                        all_sims['NDA_SIMULATED_POINTS'].to_numpy(),
                        all_sims['OPP_SIMULATED_POINTS'].to_numpy()
                    ])
                })
                fig = px.histogram(
                    data_frame=chart_data,
                    x='Points',
                    histnorm='percent',
                    color='Team',
                    barmode='overlay',
                    nbins=30,
                    opacity=0.7,
                    color_discrete_map={
                        'NDA': '#1f4e79',
                        opp_team_name: '#d95f59'
                    },
                    title='Simulated scoring distribution'
                )
                fig.update_layout(
                    xaxis_title='Points scored',
                    yaxis_title='Share of simulations (%)',
                    legend_title='Team',
                    bargap=0.08
                )
                st.plotly_chart(figure_or_data=fig, width='stretch')
        else:
            st.info('Run a simulation to see the scoring range and win rate.')
