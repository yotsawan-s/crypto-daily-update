#!/usr/bin/env python3
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
import requests

CONFIG_PATH = Path("coins.json")
DATA_DIR = Path("data")
REPORT_MD = Path("REPORT.md")
SUMMARY_JSON = DATA_DIR / "summary.json"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_market_chart(coin_id: str, vs_currency: str, days: int = 250):
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(-min(delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0)
        loss = -min(delta, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def moving_average(values, window):
    if len(values) < window:
        return None
    return statistics.fmean(values[-window:])

def classify_signal(current_price, prev_price, ma200, prev_ma200):
    if ma200 is None or prev_ma200 is None:
        return "INSUFFICIENT_DATA"
    crossed_up = prev_price <= prev_ma200 and current_price > ma200
    crossed_down = prev_price >= prev_ma200 and current_price < ma200
    if crossed_up:
        return "BUY (Cross Above MA200)"
    if crossed_down:
        return "SELL (Cross Below MA200)"
    if current_price > ma200:
        return "UPTREND (Above MA200)"
    return "DOWNTREND (Below MA200)"

def classify_signal2(current_price, prev_price, ma20, prev_ma20, rsi):
    """
    1-day based signal calculation using MA20 and RSI for more responsive trading signals
    """
    if ma20 is None or prev_ma20 is None:
        return "INSUFFICIENT_DATA"
    
    # Calculate price change percentage
    price_change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
    
    # MA20 crossover detection
    crossed_up_ma20 = prev_price <= prev_ma20 and current_price > ma20
    crossed_down_ma20 = prev_price >= prev_ma20 and current_price < ma20
    
    # Strong signals based on MA20 crossover + RSI confirmation
    if crossed_up_ma20:
        if rsi is not None and rsi < 70:  # Not overbought
            return "STRONG_BUY (MA20 Cross + RSI)"
        else:
            return "BUY (MA20 Cross)"
    
    if crossed_down_ma20:
        if rsi is not None and rsi > 30:  # Not oversold
            return "STRONG_SELL (MA20 Cross + RSI)"
        else:
            return "SELL (MA20 Cross)"
    
    # Trend signals with RSI confirmation
    if current_price > ma20:
        if rsi is not None and rsi >= 70:
            return "OVERBOUGHT (Above MA20)"
        elif price_change_pct > 2:  # Strong daily gain
            return "STRONG_UP (Above MA20)"
        else:
            return "UPTREND (Above MA20)"
    else:
        if rsi is not None and rsi <= 30:
            return "OVERSOLD (Below MA20)"
        elif price_change_pct < -2:  # Strong daily loss
            return "STRONG_DOWN (Below MA20)"
        else:
            return "DOWNTREND (Below MA20)"

def format_rsi_status(rsi):
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.2f} (Overbought)"
    if rsi <= 30:
        return f"{rsi:.2f} (Oversold)"
    return f"{rsi:.2f}"

def generate_report(summary):
    lines = []
    lines.append("# Crypto Daily Summary")
    lines.append("")
    lines.append(f"Last Update (UTC): {summary['last_run_utc']}")
    lines.append("")
    lines.append("| Coin | Symbol | Price (vs base) | RSI | MA200 | MA20 | Signal (MA200) | Signal2 (1-Day) |")
    lines.append("|------|--------|------------------|-----|-------|------|----------------|-----------------|")
    for c in summary["coins"]:
        if "error" in c:
            lines.append(f"| {c['name']} | {c.get('symbol','')} | ERROR | - | - | - | {c['error']} | - |")
            continue
        price = f"{c['current_price']:.2f}"
        rsi_display = format_rsi_status(c['rsi']) if c['rsi'] is not None else "N/A"
        ma200_display = f"{c['ma200']:.2f}" if c.get("ma200") is not None else "N/A"
        ma20_display = f"{c['ma20']:.2f}" if c.get("ma20") is not None else "N/A"
        signal_display = c.get('signal', 'N/A')
        signal2_display = c.get('signal2', 'N/A')
        lines.append(f"| {c['name']} | {c['symbol']} | {price} {c['vs_currency'].upper()} | {rsi_display} | {ma200_display} | {ma20_display} | {signal_display} | {signal2_display} |")
    lines.append("")
    lines.append("หมายเหตุ: Signal = สัญญาณจาก MA200 (ระยะยาว), Signal2 = สัญญาณแบบ 1-day (ระยะสั้น) จาก MA20 + RSI (ไม่ใช่คำแนะนำการลงทุน)")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

def main():
    cfg = load_config()
    vs_currency = cfg.get("vs_currency", "usd")
    rsi_period = cfg.get("rsi_period", 14)
    ma_window = cfg.get("ma_window", 200)
    ma20_window = 20  # For 1-day signal calculation
    coins = cfg.get("coins", [])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    now_utc = datetime.now(timezone.utc).isoformat()

    for coin in coins:
        coin_id = coin["id"]
        symbol = coin.get("symbol", "").upper()
        name = coin.get("name", coin_id)
        try:
            chart = fetch_market_chart(coin_id, vs_currency, days=max(250, ma_window + 10))
            prices = [p[1] for p in chart["prices"]]
            current_price = prices[-1]
            prev_price = prices[-2] if len(prices) >= 2 else prices[-1]
            
            # Calculate MA200 for original signal
            ma200 = moving_average(prices, ma_window)
            prev_ma200 = moving_average(prices[:-1], ma_window) if len(prices) >= ma_window + 1 else None
            
            # Calculate MA20 for 1-day signal
            ma20 = moving_average(prices, ma20_window)
            prev_ma20 = moving_average(prices[:-1], ma20_window) if len(prices) >= ma20_window + 1 else None
            
            rsi_value = compute_rsi(prices, period=rsi_period)
            signal = classify_signal(current_price, prev_price, ma200, prev_ma200)
            signal2 = classify_signal2(current_price, prev_price, ma20, prev_ma20, rsi_value)
            
            entry = {
                "id": coin_id,
                "name": name,
                "symbol": symbol,
                "vs_currency": vs_currency,
                "timestamp_utc": now_utc,
                "current_price": current_price,
                "rsi_period": rsi_period,
                "rsi": None if rsi_value is None else round(rsi_value, 2),
                "ma_window": ma_window,
                "ma200": None if ma200 is None else round(ma200, 2),
                "ma20": None if ma20 is None else round(ma20, 2),
                "signal": signal,
                "signal2": signal2
            }
            results.append(entry)
        except Exception as e:
            results.append({
                "id": coin_id,
                "name": name,
                "symbol": symbol,
                "error": str(e),
                "timestamp_utc": now_utc
            })

    history = []
    if SUMMARY_JSON.exists():
        try:
            old = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
            if isinstance(old, dict) and "history" in old:
                history = old["history"]
        except Exception:
            pass

    history.append({"run_at": now_utc, "data": results})
    if len(history) > 60:
        history = history[-60:]

    summary_data = {
        "last_run_utc": now_utc,
        "coins": results,
        "history": history
    }
    SUMMARY_JSON.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_report(summary_data)

if __name__ == "__main__":
    main()