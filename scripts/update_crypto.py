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

def exponential_moving_average(values, period):
    """Calculate EMA (Exponential Moving Average)"""
    if len(values) < period:
        return None
    
    # Calculate initial SMA for the first EMA value
    sma = statistics.fmean(values[:period])
    multiplier = 2 / (period + 1)
    ema = sma
    
    # Calculate EMA for remaining values
    for i in range(period, len(values)):
        ema = (values[i] * multiplier) + (ema * (1 - multiplier))
    
    return ema

def calculate_cdc_actionzone_signal(prices, fast_period=12, slow_period=26, smoothing_period=1):
    """
    Calculate CDC ActionZone V3 2020 signal based on the provided formula
    Returns signal type and relevant EMA values
    """
    if len(prices) < max(fast_period, slow_period) + smoothing_period:
        return "INSUFFICIENT_DATA", None, None, None
    
    # Apply smoothing to source data (EMA with smoothing period)
    if smoothing_period > 1:
        smoothed_prices = []
        for i in range(len(prices)):
            if i + 1 < smoothing_period:
                smoothed_prices.append(prices[i])
            else:
                smoothed_prices.append(exponential_moving_average(prices[max(0, i-smoothing_period+1):i+1], smoothing_period))
        xPrice = smoothed_prices[-1]
    else:
        xPrice = prices[-1]
    
    # Calculate Fast and Slow EMAs
    FastMA = exponential_moving_average(prices, fast_period)
    SlowMA = exponential_moving_average(prices, slow_period)
    
    if FastMA is None or SlowMA is None:
        return "INSUFFICIENT_DATA", None, None, None
    
    # Determine Bull/Bear trend
    Bull = FastMA > SlowMA
    Bear = FastMA < SlowMA
    
    # Define Color Zones based on CDC ActionZone V3 2020 formula
    if Bull and xPrice > FastMA:
        signal = "BUY"  # Green zone
    elif Bear and xPrice > FastMA and xPrice > SlowMA:
        signal = "PRE_BUY_2"  # Blue zone
    elif Bear and xPrice > FastMA and xPrice < SlowMA:
        signal = "PRE_BUY_1"  # Light Blue zone
    elif Bear and xPrice < FastMA:
        signal = "SELL"  # Red zone
    elif Bull and xPrice < FastMA and xPrice < SlowMA:
        signal = "PRE_SELL_2"  # Orange zone
    elif Bull and xPrice < FastMA and xPrice > SlowMA:
        signal = "PRE_SELL_1"  # Yellow zone
    else:
        signal = "NEUTRAL"
    
    return signal, FastMA, SlowMA, xPrice

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

def format_rsi_status(rsi):
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.2f} (Overbought)"
    if rsi <= 30:
        return f"{rsi:.2f} (Oversold)"
    return f"{rsi:.2f}"

def format_cdc_signal(signal):
    """Format CDC ActionZone signal for display"""
    signal_mapping = {
        "BUY": "🟢 BUY",
        "SELL": "🔴 SELL", 
        "PRE_BUY_1": "🔵 Pre Buy 1",
        "PRE_BUY_2": "🔵 Pre Buy 2",
        "PRE_SELL_1": "🟡 Pre Sell 1",
        "PRE_SELL_2": "🟠 Pre Sell 2",
        "NEUTRAL": "⚪ Neutral",
        "INSUFFICIENT_DATA": "❓ Insufficient Data"
    }
    return signal_mapping.get(signal, signal)

def generate_report(summary):
    lines = []
    lines.append("# Crypto Daily Summary (CDC ActionZone V3 2020)")
    lines.append("")
    lines.append(f"Last Update (UTC): {summary['last_run_utc']}")
    lines.append("")
    lines.append("| Coin | Symbol | Price (vs base) | RSI | Fast EMA | Slow EMA | CDC Signal |")
    lines.append("|------|--------|------------------|-----|----------|----------|------------|")
    for c in summary["coins"]:
        if "error" in c:
            lines.append(f"| {c['name']} | {c.get('symbol','')} | ERROR | - | - | - | {c['error']} |")
            continue
        price = f"{c['current_price']:.2f}"
        rsi_display = format_rsi_status(c['rsi']) if c['rsi'] is not None else "N/A"
        fast_ma_display = f"{c['fast_ma']:.2f}" if c.get("fast_ma") is not None else "N/A"
        slow_ma_display = f"{c['slow_ma']:.2f}" if c.get("slow_ma") is not None else "N/A"
        cdc_signal_display = format_cdc_signal(c['signal'])
        lines.append(f"| {c['name']} | {c['symbol']} | {price} {c['vs_currency'].upper()} | {rsi_display} | {fast_ma_display} | {slow_ma_display} | {cdc_signal_display} |")
    lines.append("")
    lines.append("**CDC ActionZone V3 2020 Signals:**")
    lines.append("- 🟢 BUY: Bull trend + Price > Fast EMA")
    lines.append("- 🔵 Pre Buy 1: Bear trend + Price > Fast EMA + Price < Slow EMA") 
    lines.append("- 🔵 Pre Buy 2: Bear trend + Price > Fast EMA + Price > Slow EMA")
    lines.append("- 🔴 SELL: Bear trend + Price < Fast EMA")
    lines.append("- 🟡 Pre Sell 1: Bull trend + Price < Fast EMA + Price > Slow EMA")
    lines.append("- 🟠 Pre Sell 2: Bull trend + Price < Fast EMA + Price < Slow EMA")
    lines.append("")
    lines.append("หมายเหตุ: สัญญาณเป็นเพียงการประเมินเชิงเทคนิคจาก CDC ActionZone + RSI (ไม่ใช่คำแนะนำการลงทุน)")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

def main():
    cfg = load_config()
    vs_currency = cfg.get("vs_currency", "usd")
    rsi_period = cfg.get("rsi_period", 14)
    ma_window = cfg.get("ma_window", 200)
    fast_ema_period = cfg.get("fast_ema_period", 12)
    slow_ema_period = cfg.get("slow_ema_period", 26)
    smoothing_period = cfg.get("smoothing_period", 1)
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
            
            # Calculate traditional MA200 for reference
            ma200 = moving_average(prices, ma_window)
            prev_ma200 = moving_average(prices[:-1], ma_window) if len(prices) >= ma_window + 1 else None
            traditional_signal = classify_signal(current_price, prev_price, ma200, prev_ma200)
            
            # Calculate CDC ActionZone signal
            cdc_signal, fast_ma, slow_ma, smoothed_price = calculate_cdc_actionzone_signal(
                prices, fast_ema_period, slow_ema_period, smoothing_period
            )
            
            rsi_value = compute_rsi(prices, period=rsi_period)
            
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
                "traditional_signal": traditional_signal,
                "fast_ema_period": fast_ema_period,
                "slow_ema_period": slow_ema_period,
                "smoothing_period": smoothing_period,
                "fast_ma": None if fast_ma is None else round(fast_ma, 2),
                "slow_ma": None if slow_ma is None else round(slow_ma, 2),
                "smoothed_price": None if smoothed_price is None else round(smoothed_price, 2),
                "signal": cdc_signal
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