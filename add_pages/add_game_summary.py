import streamlit as st
import time
import pandas as pd
from py import sql, data_source
import sqlitecloud
pd.options.mode.chained_assignment = None


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']



# ----------------------------------------------------------------------------
def load_data():
    game_summary = data_source.run_query(
            sql=sql.get_game_summary_sql(), connection=sql_lite_connect
    )
    players = data_source.run_query(
        sql=sql.get_players_sql(), connection=sql_lite_connect
    )
    games = data_source.run_query(
        sql=sql.get_games_sql(), connection=sql_lite_connect
    )
    return players, games, game_summary


# ----------------------------------------------------------------------------
@st.cache_data
def get_season_data(games, players, season):

    games_season = games[games['SEASON'] == season]
    players_season = players[players['YEAR'] == season]

    games_season['LABEL'] = (
        games_season['OPPONENT'] + ' - ' + games_season['DATE']
    )

    return games_season, players_season


# ----------------------------------------------------------------------------
@st.cache_data
def get_selected_game(games_season, game_select):
    game_val_opp = game_select.split(' - ')[0]
    game_val_date = game_select.split(' - ')[1]
    this_game = games_season[
        (games_season['OPPONENT']==game_val_opp)
        & (games_season['DATE']==game_val_date)
    ]
    return this_game


# ----------------------------------------------------------------------------

players, games, game_summary_data = load_data()

my_season_options = (
    games['SEASON'].sort_values(ascending=False).unique().tolist()
)
left, right = st.columns(2)
with left:
    season = st.radio(
        label='Select Season', options=my_season_options, horizontal=True
    )
games_season, players_season = get_season_data(
    games=games, players=players, season=season
)
players_season = players_season[players_season['NUMBER'] != 0]
my_game_options = games_season['LABEL'].unique().tolist()

with right:
    game_select = st.selectbox(label='Select Game', options=my_game_options)

this_game = get_selected_game(
    games_season=games_season, game_select=game_select
)
data_columns = game_summary_data.columns.tolist()
player_values = players_season['NUMBER'].astype(int).sort_values().tolist()
game_list = game_summary_data['GAME_ID'].unique().tolist()
player_val = st.radio(
    label='Select Player', options=player_values, horizontal=True
)

this_player_val = game_summary_data[
    (game_summary_data['PLAYER_ID'].astype(int) == player_val)
    & (
        game_summary_data['GAME_ID'].astype(int)
        == this_game['GAME_ID'].astype(int).values[0]
    )
]
if len(this_player_val) == 0:
    data = [
        player_val,
        this_game['GAME_ID'].astype(int).values[0],
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0
    ]
    columns = [
        'PLAYER_ID', 'GAME_ID', 'TWO_FGM', 'TWO_FGA', 'THREE_FGM',
        'THREE_FGA', 'FTM', 'FTA', 'OFFENSIVE_REBOUNDS',
        'DEFENSIVE_REBOUNDS', 'ASSISTS', 'STEALS', 'BLOCKS', 'TURNOVER'
    ]
    this_player_val = pd.DataFrame(data=[data], columns=columns)
    this_player_val = this_player_val.assign(
        PLAYER_ID=player_val,
        GAME_ID=this_game['GAME_ID'].astype(int).values[0],
        TWO_FGM=0,
        TWO_FGA=0,
        THREE_FGM=0,
        THREE_FGA=0,
        FTM=0,
        FTA=0,
        OFFENSIVE_REBOUNDS=0,
        DEFENSIVE_REBOUNDS=0,
        ASSISTS=0,
        STEALS=0,
        BLOCKS=0,
        TURNOVER=0
    )

with st.form(key='Game Data', clear_on_submit=False):
    two_one, two_two = st.columns(spec=2)
    three_one, three_two = st.columns(spec=2)
    ft_one, ft_two = st.columns(spec=2)
    reb_one, reb_two = st.columns(spec=2)
    ast_one, stl_one = st.columns(spec=2)
    blk_two, turn = st.columns(spec=2)

    with two_one:
        two_fgm = st.number_input(
            label='2pt FGM',
            min_value=0,
            max_value=100,
            value=this_player_val['TWO_FGM'].values[0].astype(int)
        )
    with two_two:
        two_fga = st.number_input(
            label='2pt FGA',
            min_value=0,
            max_value=100,
            value=this_player_val['TWO_FGA'].values[0].astype(int)
        )
    with three_one:
        three_fgm = st.number_input(
            label='3pt FGM',
            min_value=0,
            max_value=100,
            value=this_player_val['THREE_FGM'].values[0].astype(int)
        )
    with three_two:
        three_fga = st.number_input(
            label='3pt FGA',
            min_value=0,
            max_value=100,
            value=this_player_val['THREE_FGA'].values[0].astype(int)
        )
    with ft_one:
        ftm = st.number_input(
            label='FTM',
            min_value=0,
            max_value=100,
            value=this_player_val['FTM'].values[0].astype(int)
        )
    with ft_two:
        fta = st.number_input(
            label='FTA',
            min_value=0,
            max_value=100,
            value=this_player_val['FTA'].values[0].astype(int)
        )
    with reb_one:
        off_rebounds = st.number_input(
            label='Off Reb',
            min_value=0,
            max_value=100,
            value=this_player_val['OFFENSIVE_REBOUNDS'].values[0].astype(int)
        )
    with reb_two:
        def_rebounds = st.number_input(
            label='Def Reb',
            min_value=0,
            max_value=100,
            value=this_player_val['DEFENSIVE_REBOUNDS'].values[0].astype(int)
        )
    with ast_one:
        assists = st.number_input(
            label='Ast',
            min_value=0,
            max_value=100,
            value=this_player_val['ASSISTS'].values[0].astype(int)
        )
    with stl_one:
        steals = st.number_input(
            label='Steal',
            min_value=0,
            max_value=100,
            value=this_player_val['STEALS'].values[0].astype(int)
        )
    with blk_two:
        blocks = st.number_input(
            label='Block',
            min_value=0,
            max_value=100,
            value=this_player_val['BLOCKS'].values[0].astype(int)
        )
    with turn:
        turnover = st.number_input(
            label='Turnover',
            min_value=0,
            max_value=100,
            value=this_player_val['TURNOVER'].values[0].astype(int)
        )
    save = st.form_submit_button(label='Save')
    if save:
        my_id = (
            str(object=player_val)
            + '_'
            + this_game['GAME_ID'].astype(int).astype(str).values[0]
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
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.insert_game_summary_sql(),
                    parameters=(
                        str(player_val),
                        str(this_game['GAME_ID'].astype(int).values[0]),
                        str(two_fgm),
                        str(two_fga),
                        str(three_fgm),
                        str(three_fga),
                        str(ftm),
                        str(fta),
                        str(off_rebounds),
                        str(def_rebounds),
                        str(assists),
                        str(steals),
                        str(blocks),
                        str(turnover)
                    )
                )
                conn.commit()
        else:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                st.write('HERE')
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.update_game_summary_sql(),
                    parameters=(
                        str(two_fgm),
                        str(two_fga),
                        str(three_fgm),
                        str(three_fga),
                        str(ftm),
                        str(fta),
                        str(off_rebounds),
                        str(def_rebounds),
                        str(assists),
                        str(steals),
                        str(blocks),
                        str(turnover),
                        str(player_val),
                        str(this_game['GAME_ID'].astype(int).values[0])
                    )
                )
                conn.commit()
        st.write('Added to DB!')
        time.sleep(.1)
        st.rerun()
