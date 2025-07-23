import requests

def fetch_spot_price(asset, exchange):
    base, quote = asset.split("/")

    try:
        if exchange.lower() == "okx":
            inst_id = f"{base}-{quote}"
            url = f"https://www.okx.com/api/v5/market/ticker?instId={inst_id}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return float(data["data"][0]["last"])

        elif exchange.lower() == "bybit":
            symbol = f"{base}{quote}"
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return float(data["result"]["list"][0]["lastPrice"])

        else:
            print(f"❌ Unsupported exchange: {exchange}")
            return None

    except Exception as e:
        print(f"⚠️ Error fetching price for {asset} from {exchange}: {e}")
        return None
