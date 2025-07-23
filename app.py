from market_data import fetch_spot_price
from risk_engine import calculate_delta, calculate_var

# Simulated portfolio position
position_size = 1.2  # 1.2 ETH
beta = 1  # assume 100% correlation

# Simulated price history (can use live data later)
eth_prices = [3000, 3020, 3010, 3035, 3040, 3032]

# 1. Get live ETH price
current_price = fetch_spot_price("ETH/USDT", "bybit")

# 2. Calculate delta
delta = calculate_delta(position_size, beta)

# 3. Calculate VaR (using past prices)
var = calculate_var(eth_prices)

# Show results
print(f"✅ ETH Price: ${current_price}")
print(f"📉 Delta Exposure: {delta:.2f} ETH")
print(f"⚠️ Value at Risk (95%): {round(var * 100, 2)}%")
