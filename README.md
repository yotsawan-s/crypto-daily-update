# Crypto Daily Update (RSI & MA200)

Daily scheduled fetch of crypto prices (Bitcoin, Ethereum, Solana) with RSI (14) & MA200 signals via GitHub Actions. Runs every day at 07:00 GMT+7 (00:00 UTC) and commits the updated summary.

## Features
- Daily schedule (cron) using GitHub Actions
- Fetch prices from CoinGecko (free public API)
- Calculate RSI (Wilder 14) and 200-day Simple Moving Average (MA200)
- Calculate CDC ActionZone V3 2020 signals using 12/26-period EMAs
- Generate trading-style signals (Signal: MA200 cross, Signal2: ActionZone)
- Persist historical snapshots (rolling history)
- Easy coin list expansion via `coins.json`

## File Overview
| Path | Description |
|------|-------------|
| `coins.json` | Configuration: base currency, RSI period, MA window, coin list |
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

## Signals

### Signal (MA200 + RSI)
- BUY (Cross Above MA200): Price crosses from below to above MA200
- SELL (Cross Below MA200): Price crosses from above to below MA200
- UPTREND (Above MA200): Price > MA200 without new cross
- DOWNTREND (Below MA200): Price < MA200 without new cross
- RSI Tags: >70 Overbought, <30 Oversold

### Signal2 (CDC ActionZone V3 2020)
CDC ActionZone uses two EMAs (12-period and 26-period) to determine market zones:
- GREEN (Buy Signal): Strong bullish trend (Price > EMA12 > EMA26)
- RED (Sell Signal): Strong bearish trend (Price < EMA12 < EMA26)
- YELLOW (Mixed Bull): Mixed bullish signal (Price > EMA12 but EMA12 < EMA26)
- ORANGE (Bull Transition): Bullish transition (Price > EMA26 > EMA12)
- BLUE (Mixed Bear): Mixed bearish signal (Price < EMA12 but EMA12 > EMA26)
- AQUA (Bear Transition): Bearish transition (Price < EMA26 < EMA12)

Basic trading: Buy on GREEN, Sell on RED. Advanced usage involves using different zones for various trading strategies.

## Extend Ideas
- Slack / Telegram notifications
- Additional indicators: MACD, EMA (50/100/200), Bollinger Bands
- More ActionZone variants or custom EMA periods
- Trigger-only commits when signal changes
- GitHub Pages dashboard

## Disclaimer
Educational use only. Not financial advice.

## License
MIT License (see LICENSE).