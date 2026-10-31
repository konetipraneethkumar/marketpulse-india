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
2. **Historical backtesting** — timestamp-safe signals, costs/slippage, out-of-sample metrics.
3. **Persistence and API** — database and FastAPI.
4. **Authorized data integration** — provider adapters for data the account is licensed to access.
5. **Scheduling and dashboard** — automated reports and visual monitoring.

## Data integrity principles

- Use Asia/Kolkata for market timestamps and a real trading calendar.
- Do not use data that was unavailable at the time a historical signal would have been produced.
- Keep signal evaluation separate from simulated trade performance.
- Never present sample data as live data.
