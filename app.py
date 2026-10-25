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

from datetime import datetime, timezone
from math import erf, sqrt

def cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))

def ev(p, odds):
    payout = odds / 100 if odds > 0 else 100 / abs(odds)
    return p * payout - (1-p)

st.sidebar.header("Betting model")
margin_sd = st.sidebar.number_input("Margin SD (unvalidated)", 5.0, 25.0, 12.0, 0.5)
total_sd = st.sidebar.number_input("Total SD (unvalidated)", 8.0, 35.0, 18.0, 0.5)
min_ev = st.sidebar.number_input("Minimum EV %", 0.0, 25.0, 2.0, 0.5)
st.sidebar.warning("SD inputs are assumptions, not historically calibrated. Do not treat apparent EV as verified.")
tabs = st.tabs(["Power Rankings", "Matchups", "Best Bets & EV", "Injuries & Mismatches", "Monte Carlo", "Bet Tracker", "Model Accuracy", "Data Health"])
with tabs[0]:
    st.subheader("30-Team Power Rankings")
    st.dataframe(ratings.sort_values("Live Net",ascending=False),use_container_width=True,hide_index=True)
    st.download_button("Export ratings",ratings.to_csv(index=False),"nba_ratings.csv","text/csv")
with tabs[1]:
    st.subheader("Game projections")
    st.warning("Imported spreadsheet snapshot, not a verified live NBA schedule.")
    st.dataframe(games,use_container_width=True,hide_index=True)
    st.download_button("Export projections",games.to_csv(index=False),"nba_projections.csv","text/csv")
with tabs[2]:
    st.subheader("Manual sportsbook comparison")
    st.caption("Use current sportsbook lines and prices. Results are hypothetical unless inputs are independently verified.")
    if games.empty:
        st.info("No projections available.")
    else:
        ix=st.selectbox("Matchup for EV",range(len(games)),format_func=lambda i:f"{games.iloc[i]['Away']} @ {games.iloc[i]['Home']}")
        g=games.iloc[ix]
        away_pts=float(g["Away projected"])
        home_pts=float(g["Home projected"])
        model_margin=home_pts-away_pts
        model_total=home_pts+away_pts
        st.write(f"Model: {g['Away']} {away_pts:.1f} – {g['Home']} {home_pts:.1f} | Home margin {model_margin:+.1f} | Total {model_total:.1f}")
        col1,col2=st.columns(2)
        with col1:
            line=st.number_input("Home spread (negative if favored)",value=-2.5,step=0.5)
            spread_price=st.number_input("Home spread American price",value=-110,step=5)
        with col2:
            total_line=st.number_input("Market total",value=230.5,step=0.5)
            over_price=st.number_input("Over American price",value=-110,step=5)
        book=st.text_input("Sportsbook",value="Manual")
        captured=st.text_input("Price timestamp and timezone",placeholder="e.g. 2026-10-25 13:00 EDT")
        if all(x <= -100 or x >= 100 for x in [spread_price,over_price]):
            spread_prob=cdf((model_margin+line)/margin_sd)
            over_prob=cdf((model_total-total_line)/total_sd)
            rows=[{"Selection":f"{g['Home']} {line:+g}","American odds":spread_price,"Model win %":100*spread_prob,"EV %":100*ev(spread_prob,spread_price)},
                  {"Selection":f"Over {total_line:g}","American odds":over_price,"Model win %":100*over_prob,"EV %":100*ev(over_prob,over_price)}]
            df=pd.DataFrame(rows)
            df["Meets EV threshold"]=df["EV %"]>=min_ev
            st.dataframe(df.style.format({"Model win %":"{:.1f}","EV %":"{:+.1f}"}),use_container_width=True,hide_index=True)
            st.download_button("Export EV analysis",df.to_csv(index=False),"nba_ev.csv","text/csv")
            st.caption(f"Source: {book} | Captured: {captured or 'not provided'} | Push probabilities not explicitly modeled on integer lines.")
        else:
            st.error("American prices must be <= -100 or >= +100.")
with tabs[3]:
    st.subheader("Injuries and positional mismatches")
    st.info("No verified injury/rotation feed is connected. Apply manually researched point adjustments to projections; do not assume player availability.")
    st.dataframe(games[[c for c in ["Away","Home","Away projected","Home projected"] if c in games.columns]],hide_index=True,use_container_width=True)
    penalty_away=st.number_input("Away injury / matchup point adjustment",value=0.0,step=0.5)
    penalty_home=st.number_input("Home injury / matchup point adjustment",value=0.0,step=0.5)
    st.write(f"Net home margin adjustment: {penalty_home-penalty_away:+.1f} points. Enter adjustments in your model after confirming news.")
with tabs[4]:
    st.subheader("Monte Carlo")
    if games.empty:
        st.info("No games loaded.")
    else:
        ix2=st.selectbox("Matchup for simulation",range(len(games)),format_func=lambda i:f"{games.iloc[i]['Away']} @ {games.iloc[i]['Home']}",key="mc_game")
        n=st.select_slider("Simulations",options=[1000,5000,10000,25000,50000],value=10000)
        r=games.iloc[ix2]
        rng=np.random.default_rng(42)
        model_margin=float(r["Home projected"])-float(r["Away projected"])
        model_total=float(r["Home projected"])+float(r["Away projected"])
        margins=rng.normal(model_margin,margin_sd,n)
        totals=rng.normal(model_total,total_sd,n)
        a,b,c=st.columns(3)
        a.metric("Home win %",f"{np.mean(margins>0):.1%}")
        b.metric("Mean home margin",f"{np.mean(margins):+.1f}")
        c.metric("Mean total",f"{np.mean(totals):.1f}")
        st.bar_chart(pd.DataFrame({"Home margin":margins}).value_counts(bins=30).sort_index())
        st.caption("Normal-model simulation using assumed uncertainty; not independently validated.")
with tabs[5]:
    st.subheader("Bet tracker")
    st.caption("Edit this table and download CSV for permanent storage. Cloud session edits are not a persistent database.")
    template=pd.DataFrame([{"Date (UTC)":"","Game":"","Market":"","Selection":"","American odds":-110,"Stake":1.0,"Result (W/L/P)":"","Closing odds":"","Notes":""}])
    tracked=st.data_editor(template,num_rows="dynamic",use_container_width=True,hide_index=True)
    st.download_button("Save tracker CSV",tracked.to_csv(index=False),"nba_bet_tracker.csv","text/csv")
    existing=st.file_uploader("Import previous tracker CSV",type=["csv"],key="tracker")
    if existing:
        st.dataframe(pd.read_csv(existing),use_container_width=True)
with tabs[6]:
    st.subheader("Model accuracy")
    st.info("Accuracy, ATS, ROI, calibration and CLV require dated pregame predictions plus final scores and closing lines. These records are not yet connected.")
    archive=st.file_uploader("Upload graded bet history CSV (American odds, Stake, Result (W/L/P))",type=["csv"],key="graded")
    if archive:
        try:
            hist=pd.read_csv(archive)
            required={"American odds","Stake","Result (W/L/P)"}
            if not required.issubset(hist.columns):
                st.error("Required columns: American odds, Stake, Result (W/L/P)")
            else:
                odds=pd.to_numeric(hist["American odds"],errors="coerce")
                stakes=pd.to_numeric(hist["Stake"],errors="coerce")
                outcome=hist["Result (W/L/P)"].astype(str).str.upper().str.strip()
                valid=(odds.le(-100)|odds.ge(100)) & stakes.gt(0) & outcome.isin(["W","L","P"])
                h=hist.loc[valid].copy()
                o=odds.loc[valid]
                s=stakes.loc[valid]
                res=outcome.loc[valid]
                profit=np.where(res=="W",s*np.where(o>0,o/100,100/abs(o)),np.where(res=="L",-s,0))
                st.metric("Graded bets",len(h))
                st.metric("Win rate (excluding pushes)",f"{(res.eq('W').sum()/max(1,res.isin(['W','L']).sum())):.1%}")
                st.metric("ROI",f"{(profit.sum()/s.sum()):+.1%}" if s.sum()>0 else "N/A")
                st.caption("ROI uses uploaded prices/stakes and does not verify bet placement or closing line.")
        except Exception as exc:
            st.error(str(exc))
with tabs[7]:
    st.subheader("Data health and provenance")
    st.write("Source: Google Sheets imported snapshots.")
    st.write("Ratings rows:",len(ratings)," | Projection rows:",len(games))
    st.dataframe(pd.DataFrame([
        {"Feed":"Power ratings","Status":"Static CSV snapshot"},
        {"Feed":"Schedule / results","Status":"Static projections only"},
        {"Feed":"Injuries / rotations","Status":"Not connected"},
        {"Feed":"Sportsbook / Pinnacle odds","Status":"Manual entry only"},
        {"Feed":"Prediction archive / CLV","Status":"Not connected"},
        {"Feed":"Monte Carlo","Status":"Available, uncalibrated"},
        {"Feed":"Bet tracking","Status":"CSV download / upload only"}]),hide_index=True,use_container_width=True)
    st.warning("No automatic daily update or persistent database yet. Do not mistake stale projections for today's slate.")
