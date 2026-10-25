import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="NBA Edge", page_icon="🏀", layout="wide")
st.title("🏀 NBA Edge | Walters-Inspired Model")
st.caption("Automated results and provisional rating-adjusted projections • No verified live odds")
@st.cache_data(ttl=300)
def load_data():
    from pathlib import Path
    base=pd.read_csv("data/power_ratings.csv")
    schedule_path=Path("data/live_projections.csv")
    games=pd.read_csv(schedule_path) if schedule_path.exists() else pd.DataFrame(columns=["UTC tipoff","Away","Home","Away projected","Home projected"])
    if "UTC tipoff" not in games.columns:
        games["UTC tipoff"]=pd.NaT
    updated_path=Path("data/updated_ratings.csv")
    if updated_path.exists():
        updates=pd.read_csv(updated_path)
        base=base.merge(updates[["Code","Updated Net","Recorded Games"]],on="Code",how="left")
        base["Live Net"]=base["Updated Net"].fillna(base["Live Net"])
    return base,games
ratings, games = load_data()

from datetime import datetime, timezone
from math import erf, sqrt

# NBA team logo assets served from ESPN's public CDN.
TEAM_IDS = {"ATL":1,"BOS":2,"BKN":17,"CHA":30,"CHI":4,"CLE":5,"DAL":6,"DEN":7,"DET":8,"GSW":9,"HOU":10,"IND":11,"LAC":12,"LAL":13,"MEM":29,"MIA":14,"MIL":15,"MIN":16,"NOP":3,"NYK":18,"OKC":25,"ORL":19,"PHI":20,"PHX":21,"POR":22,"SAC":23,"SAS":24,"TOR":28,"UTA":26,"WAS":27}
def logo(team):
    code = str(team).upper().strip()
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{code.lower()}.png" if code in TEAM_IDS else None

def today_games():
    dates = pd.to_datetime(games["UTC tipoff"], errors="coerce", utc=True).dt.date if "UTC tipoff" in games else pd.Series([],dtype="object")
    return games.loc[dates == datetime.now(timezone.utc).date()].copy() if len(dates) else games.iloc[0:0].copy()



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
tabs = st.tabs(["🏀 Today’s Matchups", "⭐ Best Bets", "Power Rankings", "Matchups", "Best Bets & EV", "Injuries & Mismatches", "Monte Carlo", "Bet Tracker", "Model Accuracy", "Data Health"])
with tabs[0]:
    st.subheader("Today’s NBA Matchups")
    today = today_games()
    st.caption(f"Date (UTC): {datetime.now(timezone.utc).date()} • Automated schedule/projections; verify freshness in Data Health")
    if today.empty:
        st.info("No current-day games in the last refreshed schedule. Check the workflow status.")
    for _, g in today.iterrows():
        with st.container(border=True):
            a,mid,h=st.columns([2,1,2])
            with a:
                if logo(g["Away"]): st.image(logo(g["Away"]),width=70)
                st.markdown(f"**{g[\u0027Away\u0027]}**")
                st.metric("Projected points",f"{float(g[\u0027Away projected\u0027]):.1f}")
            with mid:
                st.markdown("### @")
                st.caption(f"Total {float(g[\u0027Away projected\u0027])+float(g[\u0027Home projected\u0027]):.1f}")
            with h:
                if logo(g["Home"]): st.image(logo(g["Home"]),width=70)
                st.markdown(f"**{g[\u0027Home\u0027]}**")
                st.metric("Projected points",f"{float(g[\u0027Home projected\u0027]):.1f}")
            st.caption("Ratings updated from completed scores; injury reports shown separately, not yet priced into projections")
            from pathlib import Path
            injury_path=Path("data/injuries.csv")
            if injury_path.exists():
                injuries=pd.read_csv(injury_path)
                teams=ratings.set_index("Code")["Team"].to_dict()
                for code in [g["Away"],g["Home"]]:
                    name=teams.get(code,"")
                    active=injuries[injuries["team"].astype(str).str.casefold()==name.casefold()] if "team" in injuries.columns else pd.DataFrame()
                    if not active.empty:
                        st.caption(f"{code} reported injuries ({len(active)}): " + ", ".join(active["player"].astype(str).head(4)))

with tabs[1]:
    st.subheader("Best Bets — verification required")
    st.caption("Matches the sheet’s ranked bet-board concept, but does not mistake point differences for true EV.")
    st.warning("No verified current odds feed. Upload dated odds to evaluate candidates. Uncalibrated win probabilities are illustrative.")
    odds_upload=st.file_uploader("Upload odds CSV: Away,Home,Home spread,Spread odds,Total,Over odds,Book,Captured UTC",type=["csv"],key="board_odds")
    if odds_upload:
        try:
            odds_df=pd.read_csv(odds_upload)
            required={"Away","Home","Home spread","Spread odds","Total","Over odds","Book","Captured UTC"}
            if not required.issubset(odds_df.columns):
                st.error("Missing columns: "+", ".join(sorted(required-set(odds_df.columns))))
            else:
                slate=today_games()
                joined=slate.merge(odds_df,on=["Away","Home"],how="inner")
                picks=[]
                for _,g in joined.iterrows():
                    margin=float(g["Home projected"])-float(g["Away projected"])
                    total=float(g["Home projected"])+float(g["Away projected"])
                    spread=float(g["Home spread"]); line=float(g["Total"])
                    for label,p,price,edge in [(f"{g[\u0027Home\u0027]} {spread:+g}",cdf((margin+spread)/margin_sd),int(g["Spread odds"]),margin+spread),(f"Over {line:g}",cdf((total-line)/total_sd),int(g["Over odds"]),total-line)]:
                        if price <= -100 or price >= 100:
                            picks.append({"Away":g["Away"],"Home":g["Home"],"Pick":label,"Book":g["Book"],"Odds":price,"Edge (pts)":round(edge,1),"EV %":round(100*ev(p,price),2),"Captured UTC":g["Captured UTC"]})
                if picks:
                    board=pd.DataFrame(picks).sort_values("EV %",ascending=False)
                    board=board[board["EV %"]>=min_ev]
                    st.dataframe(board,hide_index=True,use_container_width=True)
                    st.download_button("Export candidates",board.to_csv(index=False),"nba_best_bets.csv","text/csv")
                else: st.info("No valid matching market rows found for today.")
        except Exception as exc: st.error(f"Unable to parse odds file: {exc}")

with tabs[2]:
    st.subheader("30-Team Power Rankings")
    st.dataframe(ratings.sort_values("Live Net",ascending=False),use_container_width=True,hide_index=True)
    st.download_button("Export ratings",ratings.to_csv(index=False),"nba_ratings.csv","text/csv")
with tabs[3]:
    st.subheader("Game projections")
    st.warning("Imported spreadsheet snapshot, not a verified live NBA schedule.")
    st.dataframe(games,use_container_width=True,hide_index=True)
    st.download_button("Export projections",games.to_csv(index=False),"nba_projections.csv","text/csv")
with tabs[4]:
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
with tabs[5]:
    st.subheader("Injuries and positional mismatches")
    st.info("ESPN injury snapshot is collected automatically, but player-specific point penalties and positional rotations are not yet calibrated. Review the report below.")
    from pathlib import Path
    if Path("data/injuries.csv").exists():
        injury_df=pd.read_csv("data/injuries.csv")
        st.dataframe(injury_df,hide_index=True,use_container_width=True)
    st.dataframe(games[[c for c in ["Away","Home","Away projected","Home projected"] if c in games.columns]],hide_index=True,use_container_width=True)
    penalty_away=st.number_input("Away injury / matchup point adjustment",value=0.0,step=0.5)
    penalty_home=st.number_input("Home injury / matchup point adjustment",value=0.0,step=0.5)
    st.write(f"Net home margin adjustment: {penalty_home-penalty_away:+.1f} points. Enter adjustments in your model after confirming news.")
with tabs[6]:
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
        hist_counts, hist_edges = np.histogram(margins, bins=30)
        hist_df = pd.DataFrame({"Home margin bin": [f"{hist_edges[i]:.1f} to {hist_edges[i+1]:.1f}" for i in range(len(hist_counts))], "Simulations": hist_counts}).set_index("Home margin bin")
        st.bar_chart(hist_df)
        st.caption("Normal-model simulation using assumed uncertainty; not independently validated.")
with tabs[7]:
    st.subheader("Bet tracker")
    st.caption("Edit this table and download CSV for permanent storage. Cloud session edits are not a persistent database.")
    template=pd.DataFrame([{"Date (UTC)":"","Game":"","Market":"","Selection":"","American odds":-110,"Stake":1.0,"Result (W/L/P)":"","Closing odds":"","Notes":""}])
    tracked=st.data_editor(template,num_rows="dynamic",use_container_width=True,hide_index=True)
    st.download_button("Save tracker CSV",tracked.to_csv(index=False),"nba_bet_tracker.csv","text/csv")
    existing=st.file_uploader("Import previous tracker CSV",type=["csv"],key="tracker")
    if existing:
        st.dataframe(pd.read_csv(existing),use_container_width=True)
with tabs[8]:
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
with tabs[9]:
    st.subheader("Data health and provenance")
    st.write("Source: ESPN scoreboard schedule/results; ratings use provisional score-margin adjustments to imported baseline.")
    from pathlib import Path
    from datetime import datetime as dt
    import json
    p=Path("data/refresh_status.json")
    if p.exists():
        try:
            status=json.loads(p.read_text())
            st.json(status)
            if status.get("errors"): st.error("Latest results refresh reported errors.")
        except Exception as exc: st.warning(f"Refresh status unreadable: {exc}")
    else:
        st.warning("Automated results refresh has not produced a status file yet.")
    for label,path in [("Completed game history","data/game_results.csv"),("Updated team ratings","data/updated_ratings.csv"),("Injury reports","data/injuries.csv")]:
        p=Path(path)
        if p.exists():
            try:
                df=pd.read_csv(p)
                st.markdown(f"**{label}** — {len(df)} records")
                st.dataframe(df,hide_index=True,use_container_width=True)
            except Exception as exc: st.warning(f"{label}: {exc}")
        else:
            st.caption(f"{label}: waiting for first successful refresh")
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
