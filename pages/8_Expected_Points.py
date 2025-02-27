import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import joblib

pd.options.mode.chained_assignment = None

st.cache_resource.clear()

effective_field_goal_description = """
Effective FG% is a useful metric to understand shot selection.
The formula is (2FGM + 1.5 * 3FGM) / FGA. This weights 3 point
makes as more since they count for more points. In the NBA,
87% of teams who win have a higher EFG%.
"""

expected_points_description = """
Expected points takes the point value for a shot multiplied by
the percent chance of making that shot. For NDA, this uses their
historical data to determine the percentage. For opponents, it
uses D3 womens average for different spots that are hard coded.

Example: 33% chance of making a 3 pointer is 0.33 * 3 = 1 expected point.
"""

# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    return client


# ----------------------------------------------------------------------------
def get_my_db(client):
    my_db = client['NDA_GBB']
    plays_db = my_db['PLAYS']
    spots_db = my_db['SPOTS']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    plays = pd.DataFrame(data=list(plays_db.find())).drop(columns=['_id'])
    spots = pd.DataFrame(data=list(spots_db.find())).drop(columns=['_id'])
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    game_summary = (
        pd.DataFrame(data=list(game_summary_db.find())).drop(columns=['_id'])
    )
    return plays, spots, games, players, game_summary


#-----------------------------------------------------------------------------
def load_data():
    client = get_client()
    play_event, spot, games, players, game_summary = get_my_db(client=client)
    games['SEASON'] = games['SEASON'].astype(int)
    players['YEAR'] = players['YEAR'].astype(int)
    return play_event, spot, games, players, game_summary


#-----------------------------------------------------------------------------
def format_data(spot, games, players, game_summary_data, selected_season):
    '''
    Format data to count makes and misses.
    '''
    games = games[games['SEASON'] == selected_season]
    players = players[players['YEAR'] == selected_season]
    player_data = (
        play_event.merge(right=spot, left_on='SHOT_SPOT', right_on='SPOT')
                  .merge(right=games, on='GAME_ID')
                  .merge(right=players, 
                         left_on='PLAYER_ID', 
                         right_on='NUMBER')
    )
    game_summary = pd.merge(left=game_summary_data, right=games, on='GAME_ID')

    game_summary['LABEL'] = (
        game_summary['OPPONENT'] + ' - ' + game_summary['DATE']
    )
    player_data['LABEL'] = (
        player_data['OPPONENT'] + ' - ' + player_data['DATE']
    )
    player_data['NAME'] = (
        player_data['FIRST_NAME'] + ' ' + player_data['LAST_NAME']
    )
    player_data['MAKE'] = np.where(player_data['MAKE_MISS'] == 'Y', 1, 0)

    player_data['ATTEMPT'] = 1
    player_data['DATE_DTTM'] = pd.to_datetime(arg=player_data['DATE'])
    player_data = (
        player_data.sort_values(by='DATE_DTTM').reset_index(drop=True)
    )
    player_data2 = player_data[
        ['NAME', 'SHOT_SPOT', 'MAKE', 'ATTEMPT', 'SHOT_DEFENSE']
    ]
    return player_data, player_data2, game_summary


#-------------------------------------------------------------------------------
def get_games_data(player_data, game_summary, game):
    '''
    Get game data for selected game
    '''
    t_game = player_data[player_data['LABEL'] == game]
    game_data = game_summary[game_summary['LABEL'] == game]
    game_data['DATE_DTTM'] = pd.to_datetime(game_data['DATE'])
    game_data = game_data.sort_values(by='DATE_DTTM')
    return t_game, game_data


# ----------------------------------------------------------------------------
def build_features(play_event, spot, players, games):
    CODED_SHOT_DEFENSE = {
        'OPEN': 0,
        'GUARDED': 1,
        'HEAVILY_GUARDED': 2
    }
    _player_merge_list = ['PLAYER_ID', 'SPOT', 'SHOT_DEFENSE', 'YEAR']
    _player_game_merge_list = ['GAME_ID', 'PLAYER_ID', 'YEAR', 'SPOT', 'SHOT_DEFENSE']
    _player_year_list = ['GAME_ID', 'PLAYER_ID', 'YEAR']
    _player_game_list = ['GAME_ID', 'PLAYER_ID', 'YEAR', 'SHOT_DEFENSE']
    play_event = play_event.merge(players, left_on='PLAYER_ID', right_on='NUMBER').merge(games, on='GAME_ID')
    play_event = play_event[play_event['YEAR'] == play_event['SEASON']]
    play_event_spot = (
        pd.merge(left=play_event, right=spot, left_on='SHOT_SPOT',
                 right_on='SPOT', how='left')
          .sort_values(by=['GAME_ID', 'PLAY_NUM'])
          .reset_index(drop=True)
    )
    play_event_spot['INTIAL_PERCENTAGE'] = np.where(
        play_event_spot['PLAYER_ID'] == 0,
        play_event_spot['OPP_EXPECTED'] / play_event_spot['POINTS'],
        .33
    )
    play_event_spot['MAKE'] = np.where(
        play_event_spot['MAKE_MISS'] == 'Y', 1, 0
    )
    play_event_spot['ATTEMPT'] = 1
    play_event_spot['INIT_EXPECTED'] = (
        play_event_spot['INTIAL_PERCENTAGE'] * play_event_spot['POINTS']
    )
    play_event_spot['SPOT_TOTAL_MAKES'] = (
        play_event_spot.groupby(by=_player_merge_list)
                       ['MAKE'].transform(func='sum')
    )
    play_event_spot['SPOT_TOTAL_ATTEMPTS'] = (
        play_event_spot.groupby(by=_player_merge_list)['ATTEMPT'].transform('sum')
    )
    play_event_spot['SPOT_TOTAL_PERCENTAGE'] = (
        play_event_spot['SPOT_TOTAL_MAKES'] / play_event_spot['SPOT_TOTAL_ATTEMPTS']
    )
    play_event_spot['GAME_MAKES'] = (
        play_event_spot.groupby(by=_player_game_merge_list)['MAKE'].transform('sum')
    )
    play_event_spot['GAME_ATTEMPTS'] = (
        play_event_spot.groupby(by=_player_game_merge_list)['ATTEMPT'].transform('sum')
    )
    play_event_spot['GAME_PERCENTAGE'] = (
        play_event_spot['GAME_MAKES'] / play_event_spot['GAME_ATTEMPTS']
    )
    play_event_spot['GAME_TOTAL_MAKES'] = (
        play_event_spot.groupby(by=_player_year_list)['MAKE'].transform('sum')
    )
    play_event_spot['GAME_TOTAL_ATTEMPTS'] = (
        play_event_spot.groupby(by=_player_year_list)['ATTEMPT'].transform('sum')
    )
    play_event_spot['SHOT_DEFENSE_CODED'] = (
        play_event_spot['SHOT_DEFENSE'].map(CODED_SHOT_DEFENSE)
    )
    play_event_spot['GAME_ROLLING_MAKES'] = (
        play_event_spot.groupby(by=_player_game_list)['MAKE'].transform(lambda x: x.rolling(window=1000, min_periods=0).sum())
    )
    play_event_spot['GAME_ROLLING_ATTEMPTS'] = (
        play_event_spot.groupby(by=_player_game_list)['ATTEMPT'].transform(lambda x: x.rolling(window=1000, min_periods=0).sum())
    )
    play_event_spot['ROLLING_PERCENT'] = (
        play_event_spot['GAME_ROLLING_MAKES'] / play_event_spot['GAME_ROLLING_ATTEMPTS']
    )
    play_event_spot['SEASON_LAST_5'] = (
        play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['MAKE'].transform(lambda x: x.rolling(window=5, min_periods=0).sum())
    )
    play_event_spot['SEASON_LAST_5_ATTEMPTS'] = (
        play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['ATTEMPT'].transform(lambda x: x.rolling(window=5, min_periods=0).sum())
    )
    play_event_spot['SEASON_LAST_5_PERCENT'] = (
        play_event_spot['SEASON_LAST_5'] / play_event_spot['SEASON_LAST_5_ATTEMPTS']
    )
    play_event_spot['SEASON_LAST_50'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['MAKE'].transform(lambda x: x.rolling(window=50, min_periods=0).sum())
    play_event_spot['SEASON_LAST_50_ATTEMPTS'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['ATTEMPT'].transform(lambda x: x.rolling(window=50, min_periods=0).sum())
    play_event_spot['SEASON_LAST_50_PERCENT'] = play_event_spot['SEASON_LAST_50'] / play_event_spot['SEASON_LAST_50_ATTEMPTS']
    play_event_spot['SEASON_LAST_100_HOME'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR', 'LOCATION'])['MAKE'].transform(lambda x: x.rolling(window=100, min_periods=0).sum())
    play_event_spot['SEASON_LAST_100_HOME_ATTEMPTS'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR', 'LOCATION'])['ATTEMPT'].transform(lambda x: x.rolling(window=100, min_periods=0).sum())
    play_event_spot['SEASON_LAST_200'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['MAKE'].transform(lambda x: x.rolling(window=200, min_periods=0).sum())
    play_event_spot['SEASON_LAST_200_ATTEMPTS'] = play_event_spot.groupby(by=['PLAYER_ID', 'YEAR'])['ATTEMPT'].transform(lambda x: x.rolling(window=200, min_periods=0).sum())
    play_event_spot['SEASON_LAST_200_PERCENT'] = play_event_spot['SEASON_LAST_200'] / play_event_spot['SEASON_LAST_200_ATTEMPTS']
    play_event_spot['SEASON_LAST_100_HOME_PERCENT'] = play_event_spot['SEASON_LAST_100_HOME'] / play_event_spot['SEASON_LAST_100_HOME_ATTEMPTS']
    play_event_spot['HOME_FLAG'] = np.where(play_event_spot['LOCATION'] == 'Home', 1, 0)
    play_event_spot['ACTUAL_POINTS'] = play_event_spot['MAKE'] * play_event_spot['POINTS']
    play_event_spot['TEAM'] = np.where(play_event_spot['PLAYER_ID'] == 0, 'OPPONENT', 'NDA')
    play_event_spot['ROLLING_POINTS_TEAM'] = play_event_spot.groupby(by=['GAME_ID', 'YEAR', 'TEAM'])['ACTUAL_POINTS'].transform(lambda x: x.rolling(window=1000, min_periods=0).sum())
    play_event_spot['GAME_TEAM_MAKES'] = play_event_spot.groupby(by=['GAME_ID', 'TEAM', 'YEAR', 'SPOT', 'SHOT_DEFENSE'])['MAKE'].transform('sum')
    play_event_spot['GAME_TEAM_ATTEMPTS'] = play_event_spot.groupby(by=['GAME_ID', 'TEAM', 'YEAR', 'SPOT', 'SHOT_DEFENSE'])['ATTEMPT'].transform('sum')
    play_event_spot['GAME_TEAM_PERCENTAGE'] = play_event_spot['GAME_TEAM_MAKES'] / play_event_spot['GAME_TEAM_ATTEMPTS']
    return play_event_spot

def apply_model(play_event_spot):
    pipeline = joblib.load('pipeline.pkl')
    model_columns = [
        'XSPOT', 'YSPOT',
        'SPOT_TOTAL_MAKES', 'GAME_PERCENTAGE',
        'GAME_ATTEMPTS',
        'GAME_TOTAL_MAKES','SHOT_DEFENSE_CODED', 'ROLLING_PERCENT',
        'SEASON_LAST_5_PERCENT', 'INIT_EXPECTED',
         'HOME_FLAG', 'ROLLING_POINTS_TEAM', 'GAME_TEAM_PERCENTAGE'
    ]
    X = play_event_spot[model_columns]
    play_event_spot['PROB'] = pipeline.predict(X)
    play_event_spot['EXPECTED_POINTS'] = play_event_spot['PROB'] * play_event_spot['POINTS']
    play_event_spot['LABEL'] = (
        play_event_spot['OPPONENT'] + ' - ' + play_event_spot['DATE']
    )
    return play_event_spot

def get_expected_points(play_event_spot, this_game):
    return play_event_spot[play_event_spot['LABEL'] == this_game]



#-----------------------------------------------------------------------------
def run_simulations(tritons, opp, sims, standard_dev):
    """
    for sim_count in range(sims):
    Parameters:
    tritons (DataFrame): DataFrame containing Tritons' game data.
    opp (DataFrame): DataFrame containing opponent's game data.
    sims (int): Number of simulations to run.
    standard_dev (float): Standard deviation for the normal distribution.

    Returns:
    DataFrame: DataFrame containing the results of all simulations.
    """
    my_frame_list = []
    sim_count = 0
    my_bar = st.progress(0)
    while sim_count < sims:
        this_sim_nda = tritons.copy()
        this_sim_opp = opp.copy()
        this_sim_opp['SIMULATED_PERCENT'] = np.random.normal(
            this_sim_opp['PROB'], standard_dev
        )
        this_sim_opp['SIMULATED_PERCENT'] = np.where(
            this_sim_opp['SIMULATED_PERCENT'] < 0,
            0,
            this_sim_opp['SIMULATED_PERCENT']
        )
        this_sim_opp['SIMULATED_PERCENT'] = np.where(
            this_sim_opp['SIMULATED_PERCENT'] > 1,
            1,
            this_sim_opp['SIMULATED_PERCENT']
        )        
        this_sim_nda['SIMULATED_PERCENT'] = np.random.normal(
                    this_sim_nda['PROB'], standard_dev
        )
        this_sim_nda['SIMULATED_PERCENT'] = np.where(
            this_sim_nda['SIMULATED_PERCENT'] < 0,
            0,
            this_sim_nda['SIMULATED_PERCENT']
        )
        this_sim_nda['SIMULATED_PERCENT'] = np.where(
            this_sim_nda['SIMULATED_PERCENT'] > 1,
            1,
            this_sim_nda['SIMULATED_PERCENT']
        )  
        this_sim_nda['SIMULATED_EXPECTED'] = (
                    this_sim_nda['POINTS'] * this_sim_nda['SIMULATED_PERCENT']
        )
        this_sim_nda['SIMULATED_POINTS'] = (
                    this_sim_nda['ATTEMPT'] * this_sim_nda['SIMULATED_EXPECTED']
        )
        this_sim_opp['SIMULATED_EXPECTED'] = (
                    this_sim_opp['POINTS'] * this_sim_opp['SIMULATED_PERCENT']
        )
        this_sim_opp['SIMULATED_POINTS'] = (
                    this_sim_opp['ATTEMPT'] * this_sim_opp['SIMULATED_EXPECTED']
        )
        this_sim_opp['SIMULATED_POINTS'] = np.where(
            this_sim_opp['SIMULATED_POINTS'] < 0,
            0,
            this_sim_opp['SIMULATED_POINTS']
        )
        this_sim_nda['SIMULATED_POINTS'] = np.where(
            this_sim_nda['SIMULATED_POINTS'] < 0,
            0,
            this_sim_nda['SIMULATED_POINTS']
        )
        this_sim_opp['RUN'] = sim_count
        this_sim_nda['RUN'] = sim_count
        this_sim_simple_nda = this_sim_nda.groupby(by='RUN', as_index=False).agg(
                    NDA_SIMULATED_POINTS=('SIMULATED_POINTS', 'sum')
        )
        this_sim_simple_opp = this_sim_opp.groupby(by='RUN', as_index=False).agg(
                    OPP_SIMULATED_POINTS=('SIMULATED_POINTS', 'sum')
        )
        this_sim_simple = pd.merge(left=this_sim_simple_nda, right=this_sim_simple_opp, on='RUN')
        this_sim_simple['WIN'] = np.where(
            (this_sim_simple['NDA_SIMULATED_POINTS'] 
             > this_sim_simple['OPP_SIMULATED_POINTS']),
            1,
            0
        )
        sim_count += 1
        percent_complete = sim_count / sims
        my_bar.progress(percent_complete)
        my_frame_list.append(this_sim_simple)
    all_sims = pd.concat(my_frame_list, ignore_index=True)
    return all_sims


play_event, spot, games, players, gs_data = load_data()
play_event_spot = build_features(play_event=play_event, spot=spot, players=players, games=games)
play_event_spot = apply_model(play_event_spot=play_event_spot)
games['SEASON2'] = games['SEASON'].astype(dtype=int)
games = (
    games.sort_values(by='SEASON2', ascending=False).reset_index(drop=True)
)
season_list = games['SEASON'].unique().tolist()
season = st.radio(label='Select Season', options=season_list, horizontal=True)
if season:
    player_data, player_data2, game_summary_cleaned = format_data(
        spot=spot, games=games, players=players, game_summary_data=gs_data,
        selected_season=season
    )


    games_list = player_data['LABEL'].unique().tolist()

    game = st.selectbox(label='Select Game', options=games_list)

    if game != []:
        t_game, game_data = get_games_data(
            player_data=player_data, game_summary=game_summary_cleaned,
            game=game
        )

        this_game = get_expected_points(
            play_event_spot=play_event_spot, this_game=game
        )

        # ========== EXPECTED TRITONS ==========
        tritons = this_game[this_game['TEAM'] != 'OPPONENT']
        tritons_grouped = (
            tritons.groupby(by=['POINTS'], as_index=False)
                   .agg(ATTEMPTS=('ATTEMPT', 'sum'),
                        MAKES=('MAKE', 'sum'))
        )
        tritons_grouped = tritons_grouped[tritons_grouped['POINTS'] != 1]
        tritons_grouped['3MAKE'] = np.where(
            tritons_grouped['POINTS'] == 3,
            1.5 * tritons_grouped['MAKES'],
            0
        )
        tritons_grouped['2MAKE'] = np.where(
            tritons_grouped['POINTS'] == 2,
            tritons_grouped['MAKES'],
            0
        )
        tritons_efg_percent = np.where(
            tritons_grouped['ATTEMPTS'].sum() > 0,
            (tritons_grouped['2MAKE'].sum()+tritons_grouped['3MAKE'].sum())
            / tritons_grouped['ATTEMPTS'].sum(),
            0
        )
        expected_fg = tritons['EXPECTED_POINTS'].sum()
        
        # ========== ACTUAL TRITONS ==========
        actual_fg = tritons['ACTUAL_POINTS'].sum()

        # ========== EXPECTED OPP ==========
        opp = this_game[this_game['TEAM'] == 'OPPONENT']
        opp_grouped = (
            opp.groupby(by=['POINTS'], as_index=False)
               .agg(ATTEMPTS=('ATTEMPT', 'sum'),
                    MAKES=('MAKE', 'sum'))
        )
        opp_grouped = opp_grouped[opp_grouped['POINTS'] != 1]
        opp_grouped['3MAKE'] = np.where(
            opp_grouped['POINTS'] == 3,
            1.5 * opp_grouped['MAKES'],
            0
        )
        opp_grouped['2MAKE'] = np.where(
            opp_grouped['POINTS'] == 2,
            opp_grouped['MAKES'],
            0
        )
        opp_efg_percent = np.where(
            opp_grouped['ATTEMPTS'].sum() > 0,
            (opp_grouped['2MAKE'].sum()+opp_grouped['3MAKE'].sum())
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
                label='EXPECTED TRITON POINTS',
                help=expected_points_description
            )

        with triton_actual:
            st.metric(
                value=actual_fg, label='ACTUAL TRITON POINTS',
                delta=tritons_delta
            )

        with opp_expected:
            st.metric(
                value=np.round(a=expected_fg_opp, decimals=2),
                label='EXPECTED OPPONENT POINTS',
                help=expected_points_description
            )

        with opp_actual:
            st.metric(
                value=actual_fg_opp, label='ACTUAL OPPONENT POINTS',
                delta=opp_delta, delta_color='inverse'
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
                label='OPPONENT EFG%',
                help=effective_field_goal_description
            )

        sims, std = st.columns(spec=2)

        with sims:
            sim_count = st.number_input(
                label='Number of Simulations', min_value=1, max_value=10000,
                value=500
            )
        
        with std:
            standard_dev = st.number_input(
                label='Standard Deviation', min_value=0.01, max_value=1.0,
                value=0.15
            )

        run_sim = st.button(label='Run Simulation')
        if run_sim:
            st.write('Running Simulation...')
            all_sims = run_simulations(
                tritons=tritons, opp=opp, sims=sim_count,
                standard_dev=standard_dev
            )
            nda_win_percent = (
                all_sims['WIN'].mean()
            )

            win_percent, twenty_five, seventy_five = st.columns(spec=3)
            with win_percent:
                st.metric(label=f'NDA Win % of simulations',
                        value=f'{nda_win_percent:.1%}')
                
            with twenty_five:
                st.metric(
                    label='10th Percentile Points',
                    value=all_sims['NDA_SIMULATED_POINTS'].quantile(0.1).round(2)
                )
                st.metric(
                    label='10th Percentile Points',
                    value=all_sims['OPP_SIMULATED_POINTS'].quantile(0.1).round(2)
                )
                
            with seventy_five:
                st.metric(
                    label='90th Percentile Points',
                    value=all_sims['NDA_SIMULATED_POINTS'].quantile(0.9).round(2)
                )
                st.metric(
                    label='90 Percentile Points',
                    value=all_sims['OPP_SIMULATED_POINTS'].quantile(0.9).round(2)
                )
                
            nda = all_sims[['NDA_SIMULATED_POINTS']].rename(columns={'NDA_SIMULATED_POINTS': 'POINTS'})
            opp = all_sims[['OPP_SIMULATED_POINTS']].rename(columns={'OPP_SIMULATED_POINTS': 'POINTS'})
            nda['NAME'] = 'NDA'
            opp['NAME'] = 'OPPONENT'
            all_sims = pd.concat([nda, opp], ignore_index=True)
            fig = px.histogram(
                data_frame=all_sims, x='POINTS', histnorm='percent', 
                color='NAME', color_discrete_sequence=['blue', 'indianred']
            )
            fig.update_layout(barmode='overlay')
            # Reduce opacity to see both histograms
            fig.update_traces(opacity=0.75)
            st.plotly_chart(figure_or_data=fig)
