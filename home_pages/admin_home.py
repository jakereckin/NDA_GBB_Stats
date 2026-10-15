import streamlit as st
from PIL import Image

st.markdown(
	"""
	<style>
	.home-kicker {
		color: #2f6f72;
		font-size: 0.78rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		margin-bottom: 0.25rem;
	}
	.home-title {
		color: #173042;
		font-size: clamp(2rem, 4vw, 3.4rem);
		font-weight: 700;
		line-height: 1.05;
		margin: 0;
	}
	.home-copy {
		color: #52636b;
		font-size: 1.05rem;
		margin-top: 0.75rem;
	}
	.home-band {
		background: #e8f1ef;
		border-left: 5px solid #d49a3a;
		padding: 1rem 1.25rem;
		margin: 1.75rem 0 1rem;
	}
	.home-band strong { color: #173042; }
	</style>
	""",
	unsafe_allow_html=True,
)

logo = Image.open("NDA_LOGO.png")
hero_col, logo_col = st.columns([3, 1], vertical_alignment="center")
with hero_col:
	st.markdown('<div class="home-kicker">NDA GBB Analytics</div>', unsafe_allow_html=True)
	st.markdown(
		f'<h1 class="home-title">Welcome back, {st.session_state.auth_username}.</h1>',
		unsafe_allow_html=True,
	)
	st.markdown(
		'<div class="home-copy">Capture game data, review team performance, and keep the season record current.</div>',
		unsafe_allow_html=True,
	)
with logo_col:
	st.image(logo, width=150)

st.markdown(
	'<div class="home-band"><strong>Admin workspace</strong><br>Use Add Data for game-day entry or View Data for analysis and reporting.</div>',
	unsafe_allow_html=True,
)

