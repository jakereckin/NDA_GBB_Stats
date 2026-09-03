import streamlit as st
import pandas as pd
import sqlitecloud
from py import sql, data_source
pd.options.mode.chained_assignment = None


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data():
    players = data_source.run_query(
        sql=sql.get_players_sql(), connection=sql_lite_connect
    )
    return players

st.set_page_config(page_title='Add Players', layout='wide')
st.title('Add Players')
st.caption('Add a player to a season roster or remove an existing roster entry.')

players = load_data()
seasons = players['YEAR'].unique().tolist()
selected_season = st.selectbox(
    label='Season',
    placeholder='Enter Season',
    options=seasons
)
add_new_season = st.text_input('Or Add New Season')

if add_new_season != '':
    selected_season = add_new_season
    
players = players[players['YEAR'] == selected_season]
st.subheader(f'Roster for {selected_season}')
st.dataframe(data=players, width='stretch')
if selected_season:

    with st.form(key='player_form'):
        left, middle, right = st.columns(3)

        with left:
            number = st.text_input(
                label='Player number',
                placeholder='Enter Player Number'
            )
        
        with middle:
            first_name = st.text_input(
                label='First name',
                placeholder='Enter First Name'
            )
        
        with right:
            last_name = st.text_input(
                label='Last name',
                placeholder='Enter Last Name'
            )
        save_col, delete_col = st.columns(spec=2)
        with save_col:
            save = st.form_submit_button(label='Add player', key='add_player', type='primary')
        with delete_col:
            delete = st.form_submit_button(
                label='Delete Player', key='delete_player'
            )
        if save:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.insert_player_sql(),
                    parameters=(
                        str(number),
                        str(first_name),
                        str(last_name),
                        str(selected_season)
                    )
                )
                conn.commit()
                load_data.clear()
                st.success(f'Added {first_name} {last_name} to the {selected_season} roster.')
            st.rerun()

        if delete:
            with sqlitecloud.connect(sql_lite_connect) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql=sql.delete_player_sql(),
                    parameters=(
                        str(number),
                        str(selected_season)
                    )
                )
                conn.commit()
                load_data.clear()
                st.success(f'Deleted player {number} from the {selected_season} roster.')
            st.rerun()
