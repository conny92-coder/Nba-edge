# NBA Edge automated data refresh
GitHub Actions runs twice per day (UTC) and can also be run manually under Actions > NBA daily results and injury refresh > Run workflow.

- ESPN public scoreboard results are ingested for the last four UTC dates and deduplicated by game ID.
- Team net ratings are replayed from the static baseline and completed game score margins with a 0.10 residual learning rate. This is provisional, NOT a full possession-adjusted model.
- Injury snapshots are attempted from ESPN's public injury endpoint. The workflow tolerates endpoint failure and does not overwrite a prior snapshot on an error. Injury status is NOT converted to betting point penalties automatically.
- GitHub Actions requires repository Actions enabled and workflow permissions allowing writes. Scheduled jobs may be delayed.
- The dashboard reads committed CSV snapshots on rebuild. Live odds, reliable player-vs-player rotation matchups, possession-based team efficiencies, historical closing lines and pregame prediction archival are NOT implemented.
- ESPN endpoints are third-party and may change without notice; check the Actions logs and Data Health tab.
- Never commit sportsbook API keys.
