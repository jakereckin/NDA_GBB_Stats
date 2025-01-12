import streamlit as st
import time
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
pd.options.mode.chained_assignment = None


# ----------------------------------------------------------------------------
@st.cache_resource
def get_client():
    pwd = st.secrets['mongo_gbb']['MONGBO_GBB_PASSWORD']
    uri =  f"mongodb+srv://nda-gbb-admin:{pwd}@nda-gbb.1lq4irv.mongodb.net/"
    # Create a new client and connect to the server
    client = MongoClient(host=uri, server_api=ServerApi(version='1'))
    return client


# ----------------------------------------------------------------------------
def get_my_db(client):
    my_db = client['NDA_GBB']
    games_db = my_db['GAMES']
    players_db = my_db['PLAYERS']
    game_summary_db = my_db['GAME_SUMMARY']
    games = pd.DataFrame(data=list(games_db.find())).drop(columns=['_id'])
    players = pd.DataFrame(data=list(players_db.find())).drop(columns=['_id'])
    game_summary = (
        pd.DataFrame(data=list(game_summary_db.find())).drop(columns=['_id'])
    )
    return games, players, game_summary, game_summary_db


# ----------------------------------------------------------------------------
def load_data():
    client = get_client()
    games, players, game_summary, game_summary_db = get_my_db(client=client)
    games = games[games['OPPONENT'] != 'PRACTICE']
    games['SEASON'] = (
        games['SEASON'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False)
    )
    players['YEAR'] = (
        players['YEAR'].astype(dtype='str').str.replace(pat='.0',
                                                        repl='',
                                                        regex=False)
    )
    games = games.dropna(subset=['SEASON'])
    return players, games, game_summary, game_summary_db


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
    games_season = games_season[games_season['OPPONENT'] != 'PRACTICE']
    this_game = games_season[
        (games_season['OPPONENT']==game_val_opp)
        & (games_season['DATE']==game_val_date)
    ]
    return this_game


# ----------------------------------------------------------------------------
password = st.text_input(label='Password', type='password')

if password == st.secrets['page_password']['PAGE_PASSWORD']:

    players, games, game_summary_data, game_summary_db = load_data()

    my_season_options = (
        games['SEASON'].sort_values(ascending=False).unique().tolist()
    )
    season = st.radio(
        label='Select Season', options=my_season_options, horizontal=True
    )

    games_season, players_season = get_season_data(
        games=games, players=players, season=season
    )
    players_season = players_season[players_season['NUMBER'] != 0]
    my_game_options = games_season['LABEL'].unique().tolist()
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
        (game_summary_data['PLAYER_ID'].astype(int) 
         == player_val) 
        & (game_summary_data['GAME_ID'] 
           == this_game['GAME_ID'].astype(int).values[0])
    ]
    if len(this_player_val) == 0:
        data = [
            player_val, this_game['GAME_ID'].astype(int).values[0], 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        ]
        columns = [
            'PLAYER_ID', 'GAME_ID', 'TWO_FGM', 'TWO_FGA', 'THREE_FGM',
            'THREE_FGA', 'FTM', 'FTA', 'OFFENSIVE_REBOUNDS',
            'DEFENSIVE_REBOUNDS', 'ASSISTS', 'STEALS', 'BLOCKS', 'TURNOVER'
        ]
        this_player_val = pd.DataFrame(data=[data], columns=columns)
        this_player_val['PLAYER_ID'] = player_val
        this_player_val['GAME_ID'] = this_game['GAME_ID'].astype(int).values[0]
        this_player_val['TWO_FGM'] = 0
        this_player_val['TWO_FGA'] = 0
        this_player_val['THREE_FGM'] = 0
        this_player_val['THREE_FGA'] = 0
        this_player_val['FTM'] = 0
        this_player_val['FTA'] = 0
        this_player_val['OFFENSIVE_REBOUNDS'] = 0
        this_player_val['DEFENSIVE_REBOUNDS'] = 0
        this_player_val['ASSISTS'] = 0
        this_player_val['STEALS'] = 0
        this_player_val['BLOCKS'] = 0
        this_player_val['TURNOVER'] = 0
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
                value=this_player_val['TWO_FGA'].values[0].astype(int))
        with three_one:
            three_fgm = st.number_input(
                label='3pt FGM', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['THREE_FGM'].values[0].astype(int))
        with three_two:
            three_fga = st.number_input(
                label='3pt FGA', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['THREE_FGA'].values[0].astype(int))
        with ft_one:
            ftm = st.number_input(
                label='FTM', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['FTM'].values[0].astype(int))
        with ft_two:
            fta = st.number_input(
                label='FTA', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['FTA'].values[0].astype(int))
        with reb_one:
            off_rebounds = st.number_input(
                label='Off Reb', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['OFFENSIVE_REBOUNDS'].values[0].astype(int))
        with reb_two:
            def_rebounds = st.number_input(
                label='Def Reb', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['DEFENSIVE_REBOUNDS'].values[0].astype(int))
        with ast_one:
            assists = st.number_input(
                label='Ast', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['ASSISTS'].values[0].astype(int))
        with stl_one:
            steals = st.number_input(
                label='Steal', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['STEALS'].values[0].astype(int))
        with blk_two:
            blocks = st.number_input(
                label='Block', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['BLOCKS'].values[0].astype(int))
        with turn:
            turnover = st.number_input(
                label='Turnover', 
                min_value=0, 
                max_value=100, 
                value=this_player_val['TURNOVER'].values[0].astype(int))
        save = st.form_submit_button(label='Save')
        if save:
            my_id = (
                str(object=player_val) 
                + '_' 
                + this_game['GAME_ID'].astype(int).astype(str).values[0]
            )
            game_summary_ids = pd.DataFrame(data=list(game_summary_db.find()))
            game_summary_ids_list = game_summary_ids['_id'].unique().tolist()
            my_vals = [
                my_id, player_val, this_game['GAME_ID'].astype(int).values[0], 
                two_fgm, two_fga, three_fgm, three_fga, ftm, fta, off_rebounds,
                def_rebounds, assists, steals, blocks, turnover
            ]
            data = pd.DataFrame(
                data=[my_vals], 
                columns=['_id', 'PLAYER_ID', 'GAME_ID', 'TWO_FGM', 'TWO_FGA',
                        'THREE_FGM', 'THREE_FGA', 'FTM', 'FTA',
                        'OFFENSIVE_REBOUNDS', 'DEFENSIVE_REBOUNDS', 'ASSISTS',
                        'STEALS', 'BLOCKS', 'TURNOVER']
            )
            #data = data.fillna(0)
            game_summary_ids = pd.DataFrame(data=list(game_summary_db.find()))
            game_summary_ids_list = game_summary_ids['_id'].unique().tolist()
            data[['TWO_FGM',
                'TWO_FGA',
                'THREE_FGM',
                'THREE_FGA',
                'FTM',
                'FTA',
                'OFFENSIVE_REBOUNDS',
                'DEFENSIVE_REBOUNDS',
                'ASSISTS',
                'STEALS',
                'BLOCKS',
                'TURNOVER']] = data[['TWO_FGM',
                                        'TWO_FGA',
                                        'THREE_FGM',
                                        'THREE_FGA',
                                        'FTM',
                                        'FTA',
                                        'OFFENSIVE_REBOUNDS',
                                        'DEFENSIVE_REBOUNDS',
                                        'ASSISTS',
                                        'STEALS',
                                        'BLOCKS',
                                        'TURNOVER']].astype(int)
            new_data = data[~data['_id'].isin(game_summary_ids_list)]
            if len(new_data) > 0:
                data_list = new_data.to_dict('records')
                game_summary_db.insert_many(
                    documents=data_list, bypass_document_validation=True
                )
            update_data = data[data['_id'].isin(game_summary_ids_list)]
            data_list = update_data.to_dict('records')
            for doc in data_list:
                game_summary_db.update_one(
                    filter={'_id': doc['_id']}, update={"$set": doc}, upsert=True
                )    
            st.write('Added to DB!')
