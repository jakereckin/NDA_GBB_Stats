import streamlit as st
import pandas as pd
from py import sql, data_source
from PIL import Image
import streamlit_authenticator as stauth
pd.options.mode.chained_assignment = None

st.set_page_config(page_title='Notre Dame Academy Girls Basketball Analytics')
version = '2026.0.3'
st.sidebar.caption('Version ' + version)



sql_lite_connect = st.secrets['nda_gbb_connection']['DB_CONNECTION']

data_source.run_query(sql.get_users(), sql_lite_connect)

    #st.header(body='', divider='blue')
image = Image.open(fp='NDA_LOGO.jpg')

st.logo(image=image, size='large')
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
cookie_expiry_days = 0

authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name=cookie_name,
    key=cookie_key,
    cookie_expiry_days=cookie_expiry_days,
)

authenticator.login(
    location="main",
    key="auth_login_widget",
    fields={'Login': 'Admin Login', 'Form name': 'Admin Login'}
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
    body='''
    <style>
    .login-kicker {
        color: #2f6f72;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .login-title {
        color: #173042;
        font-size: clamp(2.2rem, 5vw, 4rem);
        font-weight: 700;
        line-height: 1.02;
        margin: 0.25rem 0 0.75rem;
    }
    .login-copy {
        color: #52636b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .login-band {
        background: #e8f1ef;
        border-left: 5px solid #d49a3a;
        color: #173042;
        padding: 1rem 1.25rem;
        margin: 1.5rem 0 1rem;
    }
    </style>
    <div class="login-kicker">Notre Dame Academy Girls Basketball Analytics</div>
    <h1 class="login-title">Notre Dame Academy Girls Basketball Analytics</h1>
    <div class="login-copy">Review performance, explore the season, and keep game data in one place.</div>
    ''',
    unsafe_allow_html=True,
    )
    st.caption("Version " + version)
    login_col, guest_col = st.columns(2, vertical_alignment="top")
    with login_col:
        st.markdown('<div class="login-band"><strong>Admin access</strong><br>Enter your credentials to manage game data and view all reports.</div>', unsafe_allow_html=True)
    with guest_col:
        st.image(image=image, width=220)
        st.markdown('<div class="login-band"><strong>Explore analytics</strong><br>Browse reports without entering data.</div>', unsafe_allow_html=True)
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
    st.sidebar.title('NDA Analytics')
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
        'Home': [st.Page('home_pages/guest_home.py', title='Guest Home', default=True)],
        'View Data': [
            st.Page('view_pages/team_shot_chart.py', title='Team Shot Chart'),
            st.Page('view_pages/player_shot_chart.py', title='Player Shot Chart'),
            st.Page('view_pages/view_expected_points.py', title='Expected Points'),
            st.Page('view_pages/view_game_summary.py', title='Game Summary'),
            st.Page('view_pages/view_minutes.py', title='Lineups'),
            st.Page('view_pages/view_lineup_network.py', title='Lineup Network')
        ]
        }
        st.session_state.pg = st.navigation(st.session_state.PAGES)
        st.session_state.pg.run()
    elif st.session_state.auth_role == 'nda_admin':
        st.session_state.PAGES = {
        'Home': [st.Page('home_pages/admin_home.py', title='Admin Home', default=True)],
        'Add Data': [
            st.Page('add_pages/add_plays.py', title='Add Plays'),
            st.Page('add_pages/add_players.py', title='Add Players'),
            st.Page('add_pages/add_minutes.py', title='Add Minutes'),
            st.Page('add_pages/add_games.py', title='Add Games'),
            st.Page('add_pages/add_game_summary.py', title='Add Game Summary'),
        ],
        'View Data': [
            st.Page('view_pages/team_shot_chart.py', title='Team Shot Chart'),
            st.Page('view_pages/player_shot_chart.py', title='Player Shot Chart'),
            st.Page('view_pages/view_expected_points.py', title='Expected Points'),
            st.Page('view_pages/view_game_summary.py', title='Game Summary'),
            st.Page('view_pages/view_minutes.py', title='Lineups'),
            st.Page('view_pages/view_lineup_network.py', title='Lineup Network'),
            st.Page('view_pages/view_season_trend.py', title='Season Trends') 
        ]
        }
        st.session_state.pg = st.navigation(st.session_state.PAGES)
        st.session_state.pg.run()


