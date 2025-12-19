import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import polars as pl
from py import sql, data_source
import joblib

pd.options.mode.chained_assignment = None

st.cache_resource.clear()

sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

effective_field_goal_description = '''
Effective FG% is a useful metric to understand shot selection.
The formula is (2FGM + 1.5 * 3FGM) / FGA. This weights 3 point
makes as more since they count for more points. In the NBA,
87% of teams who win have a higher EFG%.
'''

expected_points_description = '''
Expected points takes the point value for a shot multiplied by
the percent chance of making that shot. The percent chance of making that
shot is determined by a model that uses historical data to predict the
liklihood of the shot being made.

Example: 33% chance of making a 3 pointer is 0.33 * 3 = 1 expected point.
'''
# ----------------------------------------------------------------------------
@st.cache_resource
def load_data():
    game_summary = data_source.run_query(
        sql=sql.get_game_summary_sql(), connection=sql_lite_connect
    )
    player_data = data_source.run_query(
        sql=sql.get_play_by_play_sql(), connection=sql_lite_connect
    )
    game_summary = pl.from_pandas(data=game_summary)
    player_data = pl.from_pandas(data=player_data)
    return game_summary, player_data


#-----------------------------------------------------------------------------
def format_data(
        player_data: pl.DataFrame,
        game_summary_data: pl.DataFrame,
        selected_season: int
    ):
    '''
    Format data to count makes and misses.

    Args:
        spot (pd.DataFrame): DataFrame containing spot data.
        games (pd.DataFrame): DataFrame containing game data.
        players (pd.DataFrame): DataFrame containing player data.
        game_summary_data (pd.DataFrame): DataFrame containing
            game summary data.
        selected_season (int): The selected season to filter the data.

    Returns:
        tuple: A tuple containing the following elements:
            - player_data (pd.DataFrame): DataFrame containing
                merged player data.
            - player_data2 (pd.DataFrame): DataFrame containing
                selected columns from player_data.
            - game_summary (pd.DataFrame): DataFrame containin
                 merged game summary data.
    '''
    #game_summary = game_summary_data[game_summary_data['YEAR'] == selected_season]
    #player_data = player_data[player_data['SEASON'] == selected_season]
    
    #player_data2 = player_data[
    #    ['NAME', 'SHOT_SPOT', 'MAKE', 'ATTEMPT', 'SHOT_DEFENSE']
    #]
    game_summary = game_summary_data.filter(
        pl.col(name='YEAR') == str(selected_season)
    )
    player_data = player_data.filter(
        pl.col(name='SEASON') == str(selected_season)
    )
    player_data2 = player_data.select(
        pl.col(name='NAME'),
        pl.col(name='SHOT_SPOT'),
        pl.col(name='MAKE'),
        pl.col(name='ATTEMPT'),
        pl.col(name='SHOT_DEFENSE')
    )
    return player_data, player_data2, game_summary


#-------------------------------------------------------------------------------
def get_games_data(
        player_data: pl.DataFrame, game_summary: pl.DataFrame, game: str
    ):
    '''
    Get game data for the selected game.

    Args:
    player_data (pd.DataFrame): DataFrame containing player data.
    game_summary (pd.DataFrame): DataFrame containing game summary data.
    game (str): The label of the game to retrieve data for.

    Returns:
    tuple: A tuple containing two DataFrames:
        - t_game (pd.DataFrame): DataFrame containing player
            data for the selected game.
        - game_data (pd.DataFrame): DataFrame containing sorted
            game summary data with a new 'DATE_DTTM' column.
    '''
    #t_game = player_data[player_data['LABEL'] == game]
    #game_data = game_summary[game_summary['LABEL'] == game]
    t_game = player_data.filter(
        pl.col(name='LABEL') == game
    )
    game_data = game_summary.filter(
        pl.col(name='LABEL') == game
    )
    game_data = (
        game_data.with_columns(
            DATE_DTTM=pl.col(name='DATE').str.strptime(
                dtype=pl.Datetime, fmt='%Y-%m-%d'
            )
        )
        .sort(by='DATE_DTTM')
    )
    #game_data.loc[:, 'DATE_DTTM'] = pd.to_datetime(game_data['DATE'])
    #game_data = game_data.sort_values(by='DATE_DTTM')
    return t_game, game_data


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
        'HEAVILY_GUARDED': 2
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
    pipeline = joblib.load(filename='pipeline.pkl')
    model_columns = [
        'XSPOT', 'YSPOT',
        'SPOT_TOTAL_MAKES', 'GAME_PERCENTAGE',
        'GAME_ATTEMPTS', 'INTIAL_PERCENTAGE',
        'GAME_TOTAL_MAKES','SHOT_DEFENSE_CODED', 'ROLLING_PERCENT',
        'SEASON_LAST_5_PERCENT', 'INIT_EXPECTED',
        'HOME_FLAG', 'GAME_TEAM_PERCENTAGE', 'OPP_EXPECTED',
        'LAST_ROLLING_POINTS_TEAM_OPPONENT', 'TEAM_SPREAD',
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
    '''
    for sim_count in range(sims):
    Parameters:
    tritons (DataFrame): DataFrame containing Tritons' game data.
    opp (DataFrame): DataFrame containing opponent's game data.
    sims (int): Number of simulations to run.
    standard_dev (float): Standard deviation for the normal distribution.

    Returns:
    DataFrame: DataFrame containing the results of all simulations.
    '''
    my_frame_list = []
    sim_count = 0
    my_bar = st.progress(0)
    while sim_count < sims:
        this_sim_nda = tritons
        this_sim_opp = opp
        probs_opp = this_sim_opp['PROB'].to_numpy()
        simulated_opp = np.random.normal(loc=probs_opp, scale=standard_dev)
        probs_nda = this_sim_nda['PROB'].to_numpy()
        simulated_nda = np.random.normal(loc=probs_nda, scale=standard_dev)
        this_sim_opp = this_sim_opp.with_columns(
            pl.Series('SIMULATED_PERCENT', simulated_opp)
        )
        this_sim_opp = this_sim_opp.with_columns(
            SIMULATED_PERCENT=(
                pl.when(pl.col(name='SIMULATED_PERCENT') < 0)
                  .then(0)
                  .otherwise(pl.col(name='SIMULATED_PERCENT'))
            )
        )
        this_sim_opp = this_sim_opp.with_columns(
            SIMULATED_PERCENT=(
                pl.when(pl.col(name='SIMULATED_PERCENT') > 1)
                  .then(1)
                  .otherwise(pl.col(name='SIMULATED_PERCENT'))
            )
        )
        this_sim_opp = this_sim_opp.with_columns(
            SIMULATED_EXPECTED=(
                pl.col(name='POINTS') * pl.col(name='SIMULATED_PERCENT')
            )
        )
        this_sim_opp = this_sim_opp.with_columns(
            SIMULATED_POINTS=(
                pl.col(name='ATTEMPT') * pl.col(name='SIMULATED_EXPECTED')
            )
        )
        this_sim_nda = this_sim_nda.with_columns(
            pl.Series('SIMULATED_PERCENT', simulated_nda)
        )
        this_sim_nda = this_sim_nda.with_columns(
            SIMULATED_PERCENT=(
                pl.when(pl.col(name='SIMULATED_PERCENT') < 0)
                  .then(0)
                  .otherwise(pl.col(name='SIMULATED_PERCENT'))
            )
        )
        this_sim_nda = this_sim_nda.with_columns(
            SIMULATED_PERCENT=(
                pl.when(pl.col(name='SIMULATED_PERCENT') > 1)
                  .then(1)
                  .otherwise(pl.col(name='SIMULATED_PERCENT'))
            )
        )
        this_sim_nda = this_sim_nda.with_columns(
            SIMULATED_EXPECTED=(
                pl.col(name='POINTS') * pl.col(name='SIMULATED_PERCENT')
            )
        )
        this_sim_nda = this_sim_nda.with_columns(
            SIMULATED_POINTS=(
                pl.col(name='ATTEMPT') * pl.col(name='SIMULATED_EXPECTED')
            )
        )
        this_sim_opp = this_sim_opp.with_columns(
            SIMULATED_POINTS=(
                pl.when(pl.col(name='SIMULATED_POINTS') < 0)
                  .then(0)
                  .otherwise(pl.col(name='SIMULATED_POINTS'))
            ),
            RUN=pl.lit(sim_count)
        )
        this_sim_nda = this_sim_nda.with_columns(
            SIMULATED_POINTS=(
                pl.when(pl.col(name='SIMULATED_POINTS') < 0)
                  .then(0)
                  .otherwise(pl.col(name='SIMULATED_POINTS'))
            ),
            RUN=pl.lit(sim_count)
        )
        this_sim_simple_nda = (
            this_sim_nda.groupby('RUN')
                .agg(
                    NDA_SIMULATED_POINTS=pl.col('SIMULATED_POINTS').sum()
                )
        )
        this_sim_simple_opp = (
            this_sim_opp.groupby('RUN')
                .agg(
                    OPP_SIMULATED_POINTS=pl.col('SIMULATED_POINTS').sum()
                )
        )
        #this_sim_simple = pd.merge(
        #    left=this_sim_simple_nda, right=this_sim_simple_opp, on='RUN'
        #)
        this_sim_simple = this_sim_simple_nda.join(
            other=this_sim_simple_opp, on='RUN', how='inner'
        )
        this_sim_simple = this_sim_simple.with_columns(
            WIN=pl.when(
                pl.col(name='NDA_SIMULATED_POINTS') 
                > pl.col(name='OPP_SIMULATED_POINTS')
            ).then(1).otherwise(0)
        )
        sim_count += 1
        percent_complete = sim_count / sims
        my_bar.progress(value=percent_complete)
        my_frame_list.append(this_sim_simple)
    all_sims = pl.concat(my_frame_list)
    return all_sims


game_summary, player_data = load_data()
play_event_spot = build_features(
    player_data=player_data
)
play_event_spot = apply_model(play_event_spot=play_event_spot)
game_summary = (
    game_summary.with_columns(
        SEASON2=pl.col(name='SEASON').cast(dtype=pl.Int64)
    )
                .sort(by='SEASON2', descending=False)
)

season_list = player_data.select('SEASON').unique().to_series().to_list()
season_list = sorted(season_list, key=lambda x: int(x), reverse=True)
col1, col2 = st.columns(spec=2)
with col1:
    season = st.radio(label='Select Season', options=season_list, horizontal=True)
if season:
    player_data, player_data2, game_summary = format_data(
        player_data=player_data, game_summary_data=game_summary, selected_season=season
    )


    games_list = player_data.select('LABEL').unique().to_series().to_list()
    games_list = sorted(games_list, key=lambda x: pd.to_datetime(x.split(' - ')[1]) ,reverse=True)
    with col2:
        game = st.selectbox(label='Select Game', options=games_list)

    if game != []:
        t_game, game_data = get_games_data(
            player_data=player_data,
            game_summary=game_summary,
            game=game
        )

        this_game = get_expected_points(
            play_event_spot=play_event_spot, this_game=game
        )
        opp_team_name = game.split(' - ')[0]
        last_20 = this_game.sort(by='PLAY_NUM')
        last_20 = this_game.tail(50)
        last_20 = last_20[[
            'NUMBER', 'SHOT_SPOT', 'PROB', 'EXPECTED_POINTS', 'ACTUAL_POINTS',
            'LAST_ROLLING_POINTS_TEAM_NDA',
            'LAST_ROLLING_POINTS_TEAM_OPPONENT'
        ]]
        last_20 = last_20.rename(
            {
                'LAST_ROLLING_POINTS_TEAM_NDA': 'NDA_POINTS',
                'LAST_ROLLING_POINTS_TEAM_OPPONENT': 'OPP_POINTS'
            }
        )
        # ========== EXPECTED TRITONS ==========
        tritons = this_game.filter(
            pl.col(name='TEAM') != 'OPPONENT'
        )
        #tritons = this_game[this_game['TEAM'] != 'OPPONENT']
        tritons_grouped = (
            tritons.groupby(by=['POINTS'])
                .agg(
                    ATTEMPTS=pl.col('ATTEMPT').sum(),
                    MAKES=pl.col('MAKE').sum()
                )
                .filter(
                    pl.col(name='POINTS') != 1
                )
                .with_columns(
                    pl.when(pl.col(name='POINTS') == 3)
                    .then(1.5 * pl.col(name='MAKES'))
                    .otherwise(0)
                    .alias('3MAKE'),
                    pl.when(pl.col(name='POINTS') == 2)
                    .then(pl.col(name='MAKES'))
                    .otherwise(0)
                    .alias('2MAKE')
                )
        )
        tritons_efg_percent = np.where(
            tritons_grouped['ATTEMPTS'].sum() > 0,
            (tritons_grouped['2MAKE'].sum() + tritons_grouped['3MAKE'].sum())
            / tritons_grouped['ATTEMPTS'].sum(),
            0
        )
        expected_fg = tritons['EXPECTED_POINTS'].sum()
        
        # ========== ACTUAL TRITONS ==========
        actual_fg = tritons['ACTUAL_POINTS'].sum()#.astype(int)

        # ========== EXPECTED OPP ==========
        opp = this_game.filter(
            pl.col(name='TEAM') == 'OPPONENT'
        )
        opp_grouped =(
            opp.groupby(by=['POINTS'])
                .agg(
                    ATTEMPTS=pl.col('ATTEMPT').sum(),
                    MAKES=pl.col('MAKE').sum()
                )
                .filter(
                    pl.col(name='POINTS') != 1
                )
                .with_columns(
                    pl.when(pl.col(name='POINTS') == 3)
                    .then(1.5 * pl.col(name='MAKES'))
                    .otherwise(0)
                    .alias('3MAKE'),
                    pl.when(pl.col(name='POINTS') == 2)
                    .then(pl.col(name='MAKES'))
                    .otherwise(0)
                    .alias('2MAKE')
                )
        )
        #opp = this_game[this_game['TEAM'] == 'OPPONENT']
        opp_efg_percent = np.where(
            opp_grouped['ATTEMPTS'].sum() > 0,
            (opp_grouped['2MAKE'].sum() + opp_grouped['3MAKE'].sum())
            / opp_grouped['ATTEMPTS'].sum(),
            0
        )
        expected_fg_opp = opp['EXPECTED_POINTS'].sum()

        # ========== ACTUAL OPP ==========
        actual_fg_opp = opp['ACTUAL_POINTS'].sum()

        tritons_delta = round(number=actual_fg-expected_fg, ndigits=2)
        opp_delta = float(
            round(number=actual_fg_opp-expected_fg_opp, ndigits=2)
        )


        triton_expected, opp_expected = st.columns(spec=2)

        triton_actual, opp_actual = st.columns(spec=2)

        tri_efg, op_efg = st.columns(spec=2)

        with triton_expected:
            st.metric(
                value=np.round(a=expected_fg, decimals=2),
                label='Expected NDA Points',
                help=expected_points_description
            )

        with triton_actual:
            st.metric(
                value=int(actual_fg),
                label='Actual NDA Points',
                delta=tritons_delta
            )

        with opp_expected:
            st.metric(
                value=np.round(a=expected_fg_opp, decimals=2),
                label=f'Expected {opp_team_name} Points',
                help=expected_points_description
            )

        with opp_actual:
            st.metric(
                value=int(actual_fg_opp),
                label=f'Actual {opp_team_name} Points',
                delta=opp_delta,
                delta_color='inverse'
            )

        with tri_efg:
            st.metric(
                value=f'{tritons_efg_percent:.1%}',
                label='NDA EFG%',
                help=effective_field_goal_description
            )

        with op_efg:
            st.metric(
                value=f'{opp_efg_percent:.1%}',
                label=f'{opp_team_name} EFG%',
                help=effective_field_goal_description
            )
        st.dataframe(data=last_20, width='stretch', hide_index=True)
        sims, std = st.columns(spec=2)

        with sims:
            sim_count = st.number_input(
                label='Number of Simulations',
                min_value=1,
                max_value=10000,
                value=500
            )
        
        with std:
            standard_dev = st.number_input(
                label='Standard Deviation',
                min_value=0.01,
                max_value=1.0,
                value=0.3
            )

        run_sim = st.button(label='Run Simulation')
        if run_sim:
            st.write('Running Simulation...')
            all_sims = run_simulations(
                tritons=tritons,
                opp=opp,
                sims=sim_count,
                standard_dev=standard_dev
            )
            nda_win_percent = (
                all_sims['WIN'].mean()
            )

            win_percent, twenty_five, seventy_five = st.columns(spec=3)
            with win_percent:
                st.metric(
                    label=f'NDA Win % of simulations',
                    value=f'{nda_win_percent:.1%}'
                )
                
            with twenty_five:
                st.metric(
                    label='10th Percentile Points',
                    value=(
                        np.round(all_sims['NDA_SIMULATED_POINTS'].quantile(0.1), 2)
                    )
                )
                st.metric(
                    label='10th Percentile Points',
                    value=(
                        np.round(all_sims['OPP_SIMULATED_POINTS'].quantile(0.1), 2)
                    )
                )
                
            with seventy_five:
                st.metric(
                    label='90th Percentile Points',
                    value=(
                        np.round(all_sims['NDA_SIMULATED_POINTS'].quantile(0.9), 2)
                    )
                )
                st.metric(
                    label='90 Percentile Points',
                    value=(
                        np.round(all_sims['OPP_SIMULATED_POINTS'].quantile(0.9), 2)
                    )
                )
                
            nda = (
                all_sims.select(
                    pl.col(name='NDA_SIMULATED_POINTS')
                      .alias('POINTS')
                        )
                        .with_columns(
                            pl.lit('NDA').alias('NAME')
                        )
            )
            opp = (
                all_sims.select(
                    pl.col(name='OPP_SIMULATED_POINTS').alias('POINTS')
                      )
                      .with_columns(
                            pl.lit(f'{opp_team_name}').alias('NAME')
                        )
            )
            all_sims = pl.concat([nda, opp])
            all_sims = all_sims.to_pandas()
            fig = px.histogram(
                data_frame=all_sims,
                x='POINTS',
                histnorm='percent', 
                color='NAME',
                color_discrete_sequence=['blue', 'indianred'],

            )
            fig.update_layout(barmode='overlay')
            # Reduce opacity to see both histograms
            fig.update_traces(opacity=0.75)
            st.plotly_chart(figure_or_data=fig)
