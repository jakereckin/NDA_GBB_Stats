import streamlit as st
from PIL import Image

st.markdown(
	"""
	<style>
	.guest-kicker {
		color: #2f6f72;
		font-size: 0.78rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.guest-title {
		color: #173042;
		font-size: clamp(2rem, 4vw, 3.4rem);
		font-weight: 700;
		line-height: 1.05;
		margin: 0.25rem 0 0;
	}
	.guest-copy {
		color: #52636b;
		font-size: 1.05rem;
		margin: 0.75rem 0 1.75rem;
	}
	.guest-band {
		background: #f4ead8;
		border-left: 5px solid #2f6f72;
		padding: 1rem 1.25rem;
		margin-bottom: 1.5rem;
	}
	.guest-band strong { color: #173042; }
	</style>
	""",
	unsafe_allow_html=True,
)

logo = Image.open("NDA_LOGO.png")
hero_col, logo_col = st.columns([3, 1], vertical_alignment="center")
with hero_col:
	st.markdown('<div class="guest-kicker">NDA GBB Analytics</div>', unsafe_allow_html=True)
	st.markdown('<h1 class="guest-title">Explore the season.</h1>', unsafe_allow_html=True)
	st.markdown(
		'<div class="guest-copy">Browse shot profiles, game summaries, expected points, and lineup trends from the analytics menu.</div>',
		unsafe_allow_html=True,
	)
with logo_col:
	st.image(logo, width=150)

st.markdown(
	'<div class="guest-band"><strong>Analytics view</strong><br>Select a report below or use the View Data section in the sidebar.</div>',
	unsafe_allow_html=True,
)

st.subheader("Featured reports")
left_col, right_col = st.columns(2)
with left_col:
	st.page_link("view_pages/team_shot_chart.py", label="Team shot chart", icon="📊")
	st.page_link("view_pages/player_shot_chart.py", label="Player shot chart", icon="👤")
	st.page_link("view_pages/view_game_summary.py", label="Game summary", icon="📋")
with right_col:
	st.page_link("view_pages/view_expected_points.py", label="Expected points", icon="🎯")
	st.page_link("view_pages/view_minutes.py", label="Lineups", icon="⏱️")
	st.page_link("view_pages/view_lineup_network.py", label="Lineup network", icon="🔗")
