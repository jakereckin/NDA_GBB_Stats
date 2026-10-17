import streamlit as st
from PIL import Image

st.set_page_config(page_title="Notre Dame Academy Girls Basketball Analytics")
version = "2026.0.3"
st.sidebar.caption("Version " + version)

image = Image.open("NDA_LOGO.jpg")
st.logo(image=image, size="large")

st.session_state.setdefault("is_guest", False)
st.session_state.setdefault("auth_role", None)
st.session_state.setdefault("auth_username", None)

auth_settings = st.secrets.get("auth", {})
required_auth_settings = (
    "redirect_uri",
    "cookie_secret",
    "client_id",
    "client_secret",
    "server_metadata_url",
)
missing_auth_settings = [
    setting for setting in required_auth_settings if setting not in auth_settings
]

admin_settings = st.secrets.get("admin", {})
admin_emails_config = admin_settings.get("emails", [])
if not isinstance(admin_emails_config, list):
    st.error("Admin email configuration must be a list in the [admin] secrets section.")
    st.stop()
admin_emails = {
    email.strip().lower()
    for email in admin_emails_config
    if isinstance(email, str) and email.strip()
}

if st.user.get("is_logged_in", False):
    email = str(getattr(st.user, "email", "")).strip().lower()
    email_verified = getattr(st.user, "email_verified", False)

    if email not in admin_emails or not email_verified:
        st.session_state["auth_role"] = None
        st.session_state["auth_username"] = None
        st.error("This verified Google account is not authorized for admin access.")
        if st.button("Sign out"):
            st.logout()
        st.stop()

    st.session_state["is_guest"] = False
    st.session_state["auth_role"] = "nda_admin"
    st.session_state["auth_username"] = email
    st.sidebar.caption(f"Signed in as {email}")
    if st.sidebar.button("Sign out"):
        st.logout()

elif st.session_state["is_guest"]:
    st.session_state["auth_role"] = "guest"
    st.session_state["auth_username"] = "Guest"
    st.sidebar.title("NDA Analytics")
    if st.sidebar.button("Logout", key="guest_logout"):
        st.session_state["is_guest"] = False
        st.session_state["auth_role"] = None
        st.session_state["auth_username"] = None
        st.rerun()

else:
    st.session_state["auth_role"] = None
    st.session_state["auth_username"] = None
    st.title("NDA Girls Basketball Analytics")
    st.caption("Sign in with an authorized Google account or continue as a guest.")
    login_col, guest_col = st.columns(2, vertical_alignment="top")
    with login_col:
        if missing_auth_settings:
            st.error(
                "Google sign-in is not configured. Add the missing [auth] secrets: "
                + ", ".join(missing_auth_settings)
            )
        elif st.button("Sign in with Google"):
            st.login()
    with guest_col:
        st.subheader("Guest access")
        st.write("Browse reports without access to data entry.")
        if st.button("Browse as guest", key="guest_button"):
            st.session_state["is_guest"] = True
            st.session_state["auth_role"] = "guest"
            st.session_state["auth_username"] = "Guest"
            st.rerun()
    st.stop()

if not admin_emails:
    st.sidebar.warning("No admin emails are configured; Google users cannot access admin pages.")

if st.session_state["auth_role"] == "guest":
    pages = {
        "Home": [
            st.Page("home_pages/guest_home.py", title="Guest Home", default=True)
        ],
        "View Data": [
            st.Page("view_pages/team_shot_chart.py", title="Team Shot Chart"),
            st.Page("view_pages/player_shot_chart.py", title="Player Shot Chart"),
            st.Page("view_pages/view_expected_points.py", title="Expected Points"),
            st.Page("view_pages/view_game_summary.py", title="Game Summary"),
            st.Page("view_pages/view_minutes.py", title="Lineups"),
            st.Page("view_pages/view_lineup_network.py", title="Lineup Network"),
        ],
    }
else:
    pages = {
        "Home": [
            st.Page("home_pages/admin_home.py", title="Admin Home", default=True)
        ],
        "Add Data": [
            st.Page("add_pages/add_plays.py", title="Add Plays"),
            st.Page("add_pages/add_players.py", title="Add Players"),
            st.Page("add_pages/add_minutes.py", title="Add Minutes"),
            st.Page("add_pages/add_games.py", title="Add Games"),
            st.Page("add_pages/add_game_summary.py", title="Add Game Summary"),
        ],
        "View Data": [
            st.Page("view_pages/team_shot_chart.py", title="Team Shot Chart"),
            st.Page("view_pages/player_shot_chart.py", title="Player Shot Chart"),
            st.Page("view_pages/view_expected_points.py", title="Expected Points"),
            st.Page("view_pages/view_game_summary.py", title="Game Summary"),
            st.Page("view_pages/view_minutes.py", title="Lineups"),
            st.Page("view_pages/view_lineup_network.py", title="Lineup Network"),
            st.Page("view_pages/view_season_trend.py", title="Season Trends"),
        ],
    }

st.navigation(pages).run()
