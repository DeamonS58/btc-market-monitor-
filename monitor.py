
import json
import csv
import urllib.request
from pathlib import Path
from datetime import datetime, timezone


BASE = "https://api.pionex.com/api/v1/market"
SYMBOL = "BTC_USDT"


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BTC-Market-Monitor/2.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    if data.get("result") is not True:
        raise ValueError(f"API error: {data}")
    return data["data"]


def get_price():
    data = get_json(f"{BASE}/tickers?symbol={SYMBOL}")
    tickers = data.get("tickers", [])
    if not tickers:
        raise ValueError("No ticker data")
    return float(tickers[0]["close"])


def get_candles(interval):
    url = (
        f"{BASE}/klines?symbol={SYMBOL}"
        f"&interval={interval}&limit=100"
    )
    data = get_json(url)
    raw = data.get("klines", [])

    candles = []
    for c in raw:
        candles.append({
            "time": int(c["time"]),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": float(c["volume"]),
        })

    candles.sort(key=lambda c: c["time"])

    # Exclude the currently forming candle.
    seconds = {"60M": 3600, "4H": 14400, "1D": 86400}
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    duration_ms = seconds[interval] * 1000
    candles = [
        c for c in candles
        if c["time"] + duration_ms <= now_ms
    ]

    if len(candles) < 35:
        raise ValueError("Not enough completed candles")

    return candles


def calculate_rsi(closes, period=14):
    changes = [
        closes[i] - closes[i - 1]
        for i in range(1, len(closes))
    ]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def analyze(interval):
    candles = get_candles(interval)
    closes = [c["close"] for c in candles]

    last = candles[-1]
    previous = candles[-2]

    rsi = calculate_rsi(closes)

    # Use preceding candles for support/resistance.
    history = candles[-21:-1]
    support = min(c["low"] for c in history)
    resistance = max(c["high"] for c in history)

    recent_vol = sum(c["volume"] for c in candles[-5:]) / 5
    older_vol = sum(c["volume"] for c in candles[-25:-5]) / 20
    vol_ratio = recent_vol / older_vol if older_vol else 0

    change = (last["close"] / previous["close"] - 1) * 100

    if closes[-1] > closes[-5] > closes[-10]:
        trend = "UP"
    elif closes[-1] < closes[-5] < closes[-10]:
        trend = "DOWN"
    else:
        trend = "SIDEWAYS / MIXED"

    possible_bottom = (
        rsi < 35
        and last["close"] > previous["close"]
        and vol_ratio > 1.2
    )

    print(f"\n--- {interval} ---")
    print(f"Last completed close: {last['close']:.2f}")
    print(f"Change vs previous candle: {change:+.2f}%")
    print(f"RSI(14): {rsi:.2f}")
    print(f"Trend: {trend}")
    print(f"Support (20 candles): {support:.2f}")
    print(f"Resistance (20 candles): {resistance:.2f}")
    print(f"Volume ratio (5 vs 20): {vol_ratio:.2f}")
    print(f"Possible bottom: {'YES' if possible_bottom else 'NO'}")

    
    return {
        "trend": trend,
        "rsi": rsi,
        "bottom": possible_bottom,
        "close": last["close"],
        "volume": last["volume"],
        "volume_ratio": vol_ratio,
        "support": support,
        "resistance": resistance
    }



def main():
    print("BTC MARKET MONITOR v2")
    print("Source: Pionex spot BTC/USDT")
    print("UTC:", datetime.now(timezone.utc).isoformat())

    try:
        price = get_price()
        print(f"Current BTC/USDT: {price:.2f}")
    except Exception as error:
        print("Ticker error:", error)

    
    previous_state = load_previous_state()
    results = {}

    for interval in ("60M", "4H", "1D"):

        try:
            results[interval] = analyze(interval)
        except Exception as error:
            print(f"{interval} analysis error: {error}")

    if not results:
        print("\nSTATUS: NO DATA - DO NOT ENTER")
        return

    if len(results) != 3:
        print("\nSTATUS: INCOMPLETE DATA - OBSERVE")
        return

    h1 = results["60M"]
    h4 = results["4H"]
    d1 = results["1D"]

    if h4["trend"] == "DOWN" or d1["trend"] == "DOWN":
        decision = "WAIT - higher timeframe downtrend"
    elif h1["bottom"] or h4["bottom"]:
        decision = "OBSERVE - possible bottom, unconfirmed"
    elif h1["trend"] == "UP" and h4["trend"] == "UP":
        decision = "OBSERVE - bullish structure"
    else:
        decision = "WAIT - no confirmed setup"

    print("\nFINAL DECISION:", decision)
    print("No automatic trades. Analysis only.")
    
    compare_states(previous_state, {"results": results})
    save_state(results)
    save_history(results)

STATE_FILE = Path("monitor-state.json")

HISTORY_FILE = Path("btc-history.csv")

PREVIOUS_FILE = Path("previous-state/monitor-state.json")


def load_previous_state():
    if not PREVIOUS_FILE.exists():
        print("\nMEMORY: No previous analysis available")
        return None

    try:
        with PREVIOUS_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        print("\nMEMORY: Previous analysis loaded")
        return state
    except (OSError, ValueError) as error:
        print("MEMORY: Could not read previous state:", error)
        return None


def compare_states(previous, current):
    print("\n--- CHANGES SINCE PREVIOUS RUN ---")

    if not previous:
        print("First observation. Nothing to compare yet.")
        return

    for interval in ("60M", "4H", "1D"):
        old = previous.get("results", {}).get(interval)
        new = current.get("results", {}).get(interval)

        if not old or not new:
            print(f"{interval}: Comparison unavailable")
            continue

        if old["trend"] != new["trend"]:
            print(
                f"{interval}: TREND CHANGED "
                f"{old['trend']} -> {new['trend']}"
            )

        if old["bottom"] != new["bottom"]:
            print(
                f"{interval}: BOTTOM SIGNAL CHANGED "
                f"{old['bottom']} -> {new['bottom']}"
            )

        rsi_change = new["rsi"] - old["rsi"]
        if abs(rsi_change) >= 3:
            print(f"{interval}: RSI changed by {rsi_change:+.2f}")

    print("Comparison completed.")


def save_state(results):
    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "Pionex",
        "symbol": SYMBOL,
        "results": results,
    }

    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print("MEMORY: Current analysis saved")
    
def save_history(results):
    previous = Path("previous-state/btc-history.csv")

    if previous.exists():
        HISTORY_FILE.write_bytes(previous.read_bytes())

    new_file = not HISTORY_FILE.exists()
    
    if not new_file:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            header = f.readline().strip()

        if '"close"' not in header and "close" not in header.split(","):
            import shutil
            shutil.copyfile(HISTORY_FILE, "btc-history-old.csv")
            HISTORY_FILE.unlink()
            new_file = True
            print("HISTORY: Old format backed up")

    with HISTORY_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        
        if new_file:
                writer.writerow([
                    "timestamp_utc", "interval",
                    "trend", "rsi", "possible_bottom",
                    "close", "volume", "volume_ratio",
                    "support", "resistance"
                ])


        timestamp = datetime.now(timezone.utc).isoformat()

        for interval, data in results.items():
            writer.writerow([
                timestamp,
                interval,
                data["trend"],
                round(data["rsi"], 2),
                data["bottom"],
                round(data["close"], 2),
                round(data["volume"], 2),
                round(data["volume_ratio"], 2),
                round(data["support"], 2),
                round(data["resistance"], 2),
            ])

    print("HISTORY: BTC observations saved")

if __name__ == "__main__":
    main()
