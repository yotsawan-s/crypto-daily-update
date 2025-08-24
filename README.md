# Crypto Daily Update (CDC ActionZone V3 2020)

Daily scheduled fetch of crypto prices (Bitcoin, Ethereum, Solana) with RSI (14) & CDC ActionZone V3 2020 signals via GitHub Actions. Runs every day at 07:00 GMT+7 (00:00 UTC) and commits the updated summary.

## Features
- Daily schedule (cron) using GitHub Actions
- Fetch prices from CoinGecko (free public API)
- Calculate RSI (Wilder 14) and CDC ActionZone V3 2020 signals
- Generate trading-style signals based on dual EMA system (Fast EMA 12, Slow EMA 26)
- Persist historical snapshots (rolling history)
- Easy coin list expansion via `coins.json`

## File Overview
| Path | Description |
|------|-------------|
| `coins.json` | Configuration: base currency, RSI period, CDC ActionZone parameters, coin list |
| `scripts/update_crypto.py` | Main script to fetch & compute indicators |
| `data/summary.json` | Auto-generated latest data + history |
| `REPORT.md` | Human-readable daily table (auto updated) |
| `.github/workflows/update-crypto.yml` | Scheduled workflow (00:00 UTC) |
| `requirements.txt` | Python dependency list |
| `LICENSE` | MIT license |

## Usage
1. Clone repo
2. (Optional) Adjust `coins.json`
3. Commit & push
4. Workflow will run automatically at 00:00 UTC (07:00 GMT+7)

Manual run: Actions tab -> Daily Crypto Update -> Run workflow

## Adding / Removing Coins
Edit `coins.json`:
```json
{
  "id": "solana",
  "symbol": "SOL",
  "name": "Solana"
}
```
Commit & push. รอบถัดไปจะรวม Solana ให้

## Change Base Currency
Change `vs_currency` (ex: `usd`, `thb`, `eur`, `usdt`) in `coins.json`.

## CDC ActionZone V3 2020 Signals
Based on the TradingView formula with dual EMA system:
- **🟢 BUY**: Bull trend (Fast EMA > Slow EMA) + Price > Fast EMA
- **🔵 Pre Buy 1**: Bear trend + Price > Fast EMA + Price < Slow EMA
- **🔵 Pre Buy 2**: Bear trend + Price > Fast EMA + Price > Slow EMA
- **🔴 SELL**: Bear trend (Fast EMA < Slow EMA) + Price < Fast EMA
- **🟡 Pre Sell 1**: Bull trend + Price < Fast EMA + Price > Slow EMA
- **🟠 Pre Sell 2**: Bull trend + Price < Fast EMA + Price < Slow EMA

**Configuration Parameters:**
- Fast EMA Period: 12 (configurable in `coins.json`)
- Slow EMA Period: 26 (configurable in `coins.json`)
- Smoothing Period: 1 (configurable in `coins.json`)
- RSI Period: 14

## Extend Ideas
- Slack / Telegram notifications
- Additional timeframes or EMA periods
- Trigger-only commits when signal changes
- GitHub Pages dashboard

## Disclaimer
Educational use only. Not financial advice.

## License
MIT License (see LICENSE).