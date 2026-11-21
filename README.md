# btc-market-monitor-
BTC/USDT market monitoring

## History

GitHub Actions starts with the latest `main` and appends observations to
`btc-history.csv`. The first run imports the existing `btc-monitor-state`
artifact. If the artifact has expired, restore a backed-up CSV with the original
header into `main` before running the workflow. The workflow requires permission
for its GitHub token to push data commits to `main`. A rejected push fails the
run and leaves the published CSV intact.

After the first successful publication, the public CSV is available at
https://raw.githubusercontent.com/DeamonS58/btc-market-monitor-/main/btc-history.csv.
For a daily ChatGPT task, use that URL as the source and test one scheduled run
in the intended workspace. Have it report the latest UTC timestamp and number
of observations read in the past 24 hours. If the file is unavailable or there
are no fresh observations, it should report that instead of inferring a trend.
Each timestamp is the collection time. Multiple observations can refer to the
same completed candle, especially for 4H and 1D.

## Drop alerts

Each run compares the latest completed hourly close with the closes exactly
one and four hours earlier. A decline of at least 3% or 5%, respectively,
produces a GitHub Actions warning. Both thresholds are included in one alert
when they are reached on the same candle.

Alerts rely on completed hourly candles and actual Actions run times. GitHub
may delay scheduled runs. The monitor performs analysis only.
