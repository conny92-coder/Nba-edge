# NBA Edge V2 — development contract

## Goal
Deliver a trustworthy NBA research dashboard. Never claim a projection is a verified bet unless inputs, odds timestamps, and calibration are available.

## Release gates
1. Every change starts on `develop/nba-edge-v2` or a feature branch and enters `main` through a pull request.
2. CI must pass Python compilation, deterministic data-contract tests, and Streamlit startup checks.
3. Data freshness, partial source failures, missing teams, and absent odds must be visible in the app.
4. Never overwrite last known-good verified data with empty responses.
5. Save pregame projections and market odds immutably before tipoff. Grade them only after finals.
6. Backtests must avoid future information and report sample size, ATS, totals, ROI, calibration and CLV.
7. No fake live odds, fabricated injury adjustments, or uncalibrated EV presented as actionable picks.

## Sprint 1 acceptance criteria
- [ ] Thirty unique team codes with finite baseline ratings.
- [ ] A failed ESPN date preserves collected games and reports an incomplete refresh.
- [ ] Today's NBA schedule is resolved in America/New_York, not only UTC date.
- [ ] Independent results, schedule, and injury stages run even when another fails.
- [ ] CI tests both successful and partial-failure ingest with fixtures.
- [ ] Streamlit app starts in a clean environment and visibly flags stale data.
- [ ] Green pull request checks before production merge.

## Next sprints
Possession-based model; injury and schedule adjustments; sportsbook odds integration; calibrated Monte Carlo and EV; immutable prediction history; automatic grading and monitoring.
