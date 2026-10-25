import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="NBA Edge", page_icon="🏀", layout="wide")
st.title("🏀 NBA Edge | Walters-Inspired Model")
st.caption("V1 deployment • Imported spreadsheet snapshots • No live odds or injury verification")
@st.cache_data
def load_data():
    return pd.read_csv("data/power_ratings.csv"), pd.read_csv("data/projections.csv")
ratings, games = load_data()
tab1,tab2,tab3,tab4 = st.tabs(["Power Ratings","Game Projections","Monte Carlo","Model Status"])
with tab1:
    st.subheader("30-Team Power Ratings")
    st.dataframe(ratings.sort_values("Live Net",ascending=False),use_container_width=True,hide_index=True)
with tab2:
    st.subheader("Spreadsheet Game Projections")
    st.warning("These are imported projections, not newly verified game schedules or betting lines.")
    st.dataframe(games,use_container_width=True,hide_index=True)
with tab3:
    st.subheader("Score Simulation")
    if games.empty:
        st.info("No projections loaded.")
    else:
        labels=[f"{r.Away} @ {r.Home}" for r in games.itertuples()]
        idx=st.selectbox("Matchup",range(len(labels)),format_func=lambda i:labels[i])
        sd=st.slider("Team score standard deviation (assumption)",8.0,20.0,12.0,0.5)
        n=st.select_slider("Simulations",options=[1000,5000,10000,25000],value=10000)
        seed=st.number_input("Random seed",value=42,step=1)
        r=games.iloc[idx]
        rng=np.random.default_rng(int(seed))
        away=rng.normal(float(r["Away projected"]),sd,n)
        home=rng.normal(float(r["Home projected"]),sd,n)
        margin=home-away
        c1,c2,c3=st.columns(3)
        c1.metric("Home win probability",f"{np.mean(margin>0):.1%}")
        c2.metric("Average home margin",f"{np.mean(margin):+.1f}")
        c3.metric("Average total",f"{np.mean(home+away):.1f}")
        st.bar_chart(pd.Series(margin).value_counts(bins=30).sort_index())
        st.caption("Illustrative independent normal-score simulation; variance is not yet calibrated to historical NBA games.")
with tab4:
    st.subheader("Operational status")
    st.error("Live odds: not connected. EV picks: disabled until verified market prices and calibrated distributions are available.")
    st.info("Next: migrate remaining sheet formulas, connect trusted results and odds sources, archive predictions, backtest and calibrate.")
    st.write("Source: NBA sheet, Google Drive snapshot captured during migration.")
