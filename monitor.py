
import json
import urllib.request
from datetime import datetime, timezone

def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BTC-Market-Monitor/1.0"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)

def main():
    prices = {}

    try:
        data = get_json(
            "https://api.bytick.com/v5/market/tickers"
            "?category=spot&symbol=BTCUSDT"
        )
        if data.get("retCode") != 0:
            raise ValueError(data.get("retMsg"))

        ticker = data["result"]["list"][0]
        prices["Bybit"] = float(ticker["lastPrice"])

        print("Bybit BTC/USDT:", prices["Bybit"])
        print("Bid:", ticker["bid1Price"])
        print("Ask:", ticker["ask1Price"])
    except Exception as error:
        print("Bybit error:", error)

    try:
        data = get_json(
            "https://api.pionex.com/api/v1/market/tickers"
            "?symbol=BTC_USDT"
        )
        if not data.get("result"):
            raise ValueError("Pionex API error")

        ticker = data["data"]["tickers"][0]
        prices["Pionex"] = float(ticker["close"])

        print("Pionex BTC/USDT:", prices["Pionex"])
    except Exception as error:
        print("Pionex error:", error)

    if len(prices) == 2:
        difference = prices["Bybit"] - prices["Pionex"]
        print("Price difference:", round(difference, 2), "USDT")

    print(
        "Check time UTC:",
        datetime.now(timezone.utc).isoformat()
    )

if __name__ == "__main__":
    main()
