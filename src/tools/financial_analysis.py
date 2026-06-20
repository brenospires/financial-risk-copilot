import yfinance as yf

data = yf.download("AAPL", start="2015-01-01", end="2025-12-31")
print(data.columns)