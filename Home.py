import streamlit as st
import pandas as pd
from py import sql, data_source
from PIL import Image
import streamlit_authenticator as stauth
pd.options.mode.chained_assignment = None

st.set_page_config(page_title='NDA GBB Analytics')


sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

data_source.run_query(sql.get_users(), sql_lite_connect)

    #st.header(body='', divider='blue')
image = Image.open(fp='NDA_LOGO.jpg')

credentials = {
    'usernames': {
        'nda_admin': {
            'name': 'NDA Admin',
            'password': st.secrets['page_password']['PAGE_PASSWORD']
        }
    }
}

allowed_for_guest = ['View Data']

cookie_name = "nda_app_cookie"
cookie_key = st.secrets['page_password']['COOKIE_KEY'] # use an environment var in production
cookie_expiry_days = 30

authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name=cookie_name,
    key=cookie_key,
    cookie_expiry_days=cookie_expiry_days,
)

if "is_guest" not in st.session_state:
    st.session_state["is_guest"] = False
if "auth_role" not in st.session_state:
    st.session_state["auth_role"] = None
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
    st.session_state.PAGES = None
    st.session_state.pg = None



if st.session_state['authentication_status'] is None:
    st.markdown(
    body='<h1 style="text-align: center; color: blue;">Welcome to NDA GBB Analytics</h1>', 
    unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns(3)
    with col2:
        st.image(image=image)


    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        authenticator.login(
        location="main",
        key="auth_login_widget",
        fields={'Login': 'Admin Login', 'Form name':'Admin Login'}
    )
    with col_right:
        st.write("Or view analytics only")
        if st.button("View Analytics", key="guest_button"):
            st.session_state["is_guest"] = True
            st.session_state["auth_role"] = "guest"
            st.session_state["auth_name"] = "Guest"
            st.session_state["authentication_status"] = True
            st.session_state['username'] = 'Guest'
            st.session_state.auth_username = 'Guest'

# Read authenticator results from session_state
auth_status = st.session_state.get("authentication_status")
auth_name = st.session_state.get("name")        # set by streamlit-authenticator
auth_username = st.session_state.get("username")  # set by streamlit-authenticator

if auth_status is False and st.session_state.get("is_guest") == True:
    st.session_state['is_guest'] = False
    
if auth_status is True and not st.session_state.get("is_guest"):
    # map username -> roles using your config; example assumes roles in YAML as list
    st.session_state["auth_role"] = 'nda_admin'
    st.session_state["auth_name"] = auth_name
    st.session_state["auth_username"] = auth_username
    st.session_state["is_guest"] = False
    # show logout (unique key)

if (auth_status is True) & (auth_username == 'nda_admin'):
    authenticator.logout("Logout", "sidebar", key="auth_logout_widget")

if st.session_state.is_guest == True:
    guest_logout_button = st.sidebar.button('Logout', key='guest_logout')
    if guest_logout_button:
        for key in ['name', 'username', 'authentication_status', 'email', 'roles', 'is_guest']:
            st.session_state.setdefault(key, None)
            st.session_state[key] = None
        st.rerun()

elif auth_status is False and not st.session_state.get("is_guest"):
    st.error("Username/password is incorrect")





# Determine visible pages based on role / guest
if st.session_state.authentication_status == True:
    if st.session_state.is_guest == True:
        st.session_state.PAGES = {
        'Home': [st.Page('home_page.py', title='Home', default=True)],
        'View Data': [
            st.Page('team_shot_chart.py', title='Team Shot Chart'),
            st.Page('player_shot_chart.py', title='Player Shot Chart'),
            st.Page('view_expected_points.py', title='Expected Points'),
            st.Page('view_game_summary.py', title='Game Summary')
        ]
        }
        st.session_state.pg = st.navigation(st.session_state.PAGES)
        st.session_state.pg.run()
    elif st.session_state.auth_role == 'nda_admin':
        st.session_state.PAGES = {
        'Home': [st.Page('home_page.py', title='Home', default=True)],
        'Add Data': [
            st.Page('add_shots.py', title='Add Shots'),
            st.Page('add_players.py', title='Add Players'),
            st.Page('add_minutes.py', title='Add Minutes'),
            st.Page('add_games.py', title='Add Games'),
            st.Page('add_game_summary.py', title='Add Game Summary'),
        ],
        'View Data': [
            st.Page('team_shot_chart.py', title='Team Shot Chart'),
            st.Page('player_shot_chart.py', title='Player Shot Chart'),
            st.Page('view_expected_points.py', title='Expected Points'),
            st.Page('view_game_summary.py', title='Game Summary')
        ]
        }
        st.session_state.pg = st.navigation(st.session_state.PAGES)
        st.session_state.pg.run()


