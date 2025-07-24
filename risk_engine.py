

# 2. Value at Risk (VaR) at a 95% confidence level
def calculate_var(price_history, confidence=0.95):
    if len(price_history) < 2:
        return 0  # Not enough data
    
    # Log returns
    log_returns = np.diff(np.log(price_history))
    var = np.percentile(log_returns, (1 - confidence) * 100)
    return abs(var)
