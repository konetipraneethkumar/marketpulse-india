# MarketPulse India

**Indian Market Signals & Backtesting Engine**  
*Read the market. Test the signal.*

MarketPulse India is a Python project for analyzing Indian market-opening conditions using GIFT Nifty, India VIX, NSE market breadth, and NIFTY 50 opening price action. It is designed to grow from an explainable sample-data engine into a historical backtesting and live-reporting platform.

> **Research and education only.** Signals are rule-based observations, not financial advice or guarantees of market direction. No live trading or broker order execution is implemented.

## First milestone

- Load a dated market snapshot from CSV.
- Generate an explainable bullish / bearish / mixed opening assessment.
- Treat missing critical inputs as **insufficient data**, not neutral.
- Use India VIX as a volatility-context indicator, not a directional vote.
- Run a small deterministic test suite.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python -m marketpulse report --date 2026-10-30
pytest
python -m marketpulse backtest
```

The initial report uses `data/sample_market.csv`. The sample data is illustrative and is **not live or verified historical market data**.

## Input fields

| Field | Meaning |
|---|---|
| `date` | Trading date (YYYY-MM-DD) |
| `gift_nifty_change_pct` | GIFT Nifty percentage change available at the report timestamp |
| `india_vix_previous`, `india_vix_current` | Previous and current India VIX values |
| `advances`, `declines` | NSE advances and declines counts |
| `nifty_previous_close`, `nifty_open` | Previous close and opening NIFTY 50 level |

## Signal logic (initial illustrative rules)

Three directional components are scored from -1 to +1: GIFT Nifty, market breadth, and NIFTY opening gap. Their sum is classified as bullish (+2 to +3), weak bullish (+1), mixed (0), weak bearish (-1), or bearish (-2 to -3). Thresholds are configurable in a later milestone and must be validated with historical data before being relied on.

India VIX change is reported separately as volatility context. It does not independently imply a bullish or bearish market.

## Roadmap

1. **Core engine** — CSV input, explainable report, deterministic tests.
2. **Historical backtesting (first pass)** — timestamped inputs, forward entry/exit prices, estimated round-trip costs, and basic performance metrics.
3. **Persistence and API** — database and FastAPI.
4. **Authorized data integration** — provider adapters for data the account is licensed to access.
5. **Scheduling and dashboard** — automated reports and visual monitoring.

## Data integrity principles

- Use Asia/Kolkata for market timestamps and a real trading calendar.
- Do not use data that was unavailable at the time a historical signal would have been produced.
- Keep signal evaluation separate from simulated trade performance.
- Never present sample data as live data.


## Historical backtest (first pass)

Run the timestamped example:

```bash
python -m marketpulse backtest
```

Use your own CSV with `--data path/to/file.csv` and optionally set estimated combined round-trip costs with `--cost-bps 10` (10 basis points = 0.10% per trade). Required columns are:

- `date`
- `signal_time_ist`, `entry_time_ist`, `exit_time_ist` — ISO 8601 timestamps with the India UTC+05:30 offset
- `entry_price`, `exit_price` — positive prices for the measured forward interval
- All signal input columns listed above

The tool requires signal, entry, and exit timestamps to use the India UTC+05:30 offset and match the row's trading date. Entry must be strictly after signal; exit must be after entry. It skips missing-critical-data rows and score-zero rows. Non-zero scores take a simple long (+1) or short (-1) directional position; round-trip costs are subtracted from each trade's return. It reports directional accuracy, average net trade return, compounded net return, and average return versus a buy-and-hold benchmark over the same entry/exit intervals.

**Important limitations:** `data/sample_backtest.csv` is synthetic/illustrative only, not real historical market data. The backtest is a basic research harness, not evidence of a profitable strategy. Timestamp validation cannot prove that each feature was genuinely published by the signal time; only use licensed data and verify availability timestamps yourself. Costs are a flat estimate and do not model taxes, market impact, liquidity, slippage variation, position sizing, drawdown, or overlapping exposure. No broker execution is implemented. Do not use these results for live trading decisions.


## Validation protocol before interpreting results

1. **Verify inputs and provenance.** Record provider, retrieval date, instrument, timezone, sampling interval, and the time each feature was actually published. NSE provides official historical index data, India VIX history, and market advances/declines reports; see [NSE historical reports](https://www.nseindia.com/static/resources/historical-reports-capital-market-daily-monthly-archives), [historical index data](https://www.nseindia.com/reports-indices-historical-index-data), and [India VIX history](https://www.nseindia.com/reports-indices-historical-vix). These sources do not by themselves provide a verified timestamp-aligned GIFT Nifty history in this repository. Obtain GIFT Nifty data from a provider authorized to distribute it.
2. **Use one row per trading session** and ensure every feature was available by `signal_time_ist`. Daily closing breadth or a daily close must not be used as if it were known at the opening. If availability time cannot be verified, exclude that feature or the session.
3. **Use chronological splits.** Choose thresholds and any rules only on an earlier training period; freeze them; report results on a later untouched test period. Do not tune on the test period. Prefer walk-forward evaluation across multiple periods.
4. **Compare baselines.** Compare against always-long buy-and-hold over the same entry/exit interval, and eventually a no-signal/flat baseline. Include realistic brokerage, taxes, spread, slippage and other costs for the instrument actually traded.
5. **Report uncertainty, not only accuracy.** Use enough independent sessions, show per-period results, drawdown, volatility and confidence intervals. A high directional hit rate alone does not establish profitability.
6. **Keep a reproducible raw-data snapshot** and data dictionary with checksums and source terms/licensing. Do not overwrite raw source files.

**Current evidence status:** unit tests and sample-data smoke tests validate code paths, not the predictive value of the rules. The repository does not yet contain verified historical market data, so no real-history performance claim has been established.
