# NBA Edge automated data refresh
GitHub Actions runs twice per day (UTC) and can also be run manually under Actions > NBA daily results and injury refresh > Run workflow.

- ESPN public scoreboard results are ingested for the last four UTC dates and deduplicated by game ID.
- Team net ratings are replayed from the static baseline and completed game score margins with a 0.10 residual learning rate. This is provisional, NOT a full possession-adjusted model.
- Injury snapshots are attempted from ESPN's public injury endpoint. The workflow tolerates endpoint failure and does not overwrite a prior snapshot on an error. Injury status is NOT converted to betting point penalties automatically.
- GitHub Actions requires repository Actions enabled and workflow permissions allowing writes. Scheduled jobs may be delayed.
- The dashboard reads committed CSV snapshots on rebuild. Live odds, reliable player-vs-player rotation matchups, possession-based team efficiencies, historical closing lines and pregame prediction archival are NOT implemented.
- ESPN endpoints are third-party and may change without notice; check the Actions logs and Data Health tab.
- Never commit sportsbook API keys.

## Development and recovery

Use Python 3.11 or newer, install `requirements.txt`, then run `streamlit run app.py` from the repository root. Run `python -m compileall -q app.py scripts tests` and `python -m unittest discover -s tests -v` for compilation, pipeline regression tests, and dashboard execution.

All 30 NBA franchises have baseline ratings restored from the model sheet on main and replayed ratings rebuilt from the committed game history. Completed game margins update these provisional ratings; betting outputs still require independent calibration.

The refresh runs results/ratings, projections, then injuries. Projections fall back to baseline ratings when the updated snapshot is absent or incomplete. ESPN abbreviations are normalized to the dashboard codes. A valid empty scoreboard clears the day's projections; malformed payloads and failed requests preserve the previous projection snapshot. Network timeouts, rate limits and transient server errors get bounded retries, with TLS verification enabled. Permanent HTTP errors are not retried.

Feed errors are recorded in `data/refresh_status.json`, `data/projections_status.json`, and `data/injuries_status.json` and displayed under Data Health. A failed upstream request does not stop independent refresh stages or erase a prior snapshot. Inspect error fields even when the Actions job succeeds. CSV publication uses atomic replacement. Serialized refresh jobs avoid concurrent snapshot writers. Rotations and live sportsbook odds remain unsupported.
