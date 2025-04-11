from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # <- add this line
import matplotlib.pyplot as plt
import requests
import json
import urllib3
import os
import mplfinance as mpf
import traceback

app = Flask(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_data(symbol):
    df = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True)
    print(f"Downloaded {len(df)} rows for {symbol}")
    print(df.head())
    
    if df.empty:
        return None, None, None

    # Flatten multi-level column names (e.g., from df['Close']['IBM'] to df['Close'])
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df["SMA_10"] = df["Close"].rolling(window=10).mean()
    df["SMA_50"] = df["Close"].rolling(window=50).mean()
    df = df.dropna()

    for col in ["Open", "High", "Low", "Close"]:
        if col not in df.columns:
            return None, f"Missing data column: {col}", symbol
        value = df[col]
        if not isinstance(value, pd.Series):
            return None, f"{col} column is not a Series (type={type(value)}):\n{value}", symbol
        df[col] = pd.to_numeric(value, errors="coerce")

    df.dropna(subset=["Open", "High", "Low", "Close", "SMA_10", "SMA_50"], inplace=True)

    # Final check to confirm all are numeric before plotting
    if not all(df[col].apply(lambda x: isinstance(x, (int, float))).all() for col in ["Open", "High", "Low", "Close"]):
        return None, "Some price values could not be converted to numeric format.", symbol

    df_mpf = df.copy()
    df_mpf = df_mpf.astype({"Open": "float", "High": "float", "Low": "float", "Close": "float"})
    df_mpf.index.name = 'Date'
    df_mpf = df_mpf[['Open', 'High', 'Low', 'Close', 'SMA_10', 'SMA_50']]

    print(f"Plotting data for: {symbol}")
    print("df_mpf dtypes:\n", df_mpf.dtypes)
    print("df_mpf head:\n", df_mpf.head())
    
    chart_path = f"static/{symbol}_chart.png"
    
    try:
        mpf.plot(
            df_mpf,
            type='candle',
            mav=(10, 50),
            style='yahoo',
            volume=False,
            savefig=chart_path
        )
    except Exception as e:
        traceback.print_exc()
        return None, f"Error generating chart: {e}", symbol

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    prev_sma10 = float(previous["SMA_10"])
    prev_sma50 = float(previous["SMA_50"])
    latest_sma10 = float(latest["SMA_10"])
    latest_sma50 = float(latest["SMA_50"])

    cross = None
    if prev_sma10 < prev_sma50 and latest_sma10 > latest_sma50:
        cross = "bullish"
    elif prev_sma10 > prev_sma50 and latest_sma10 < latest_sma50:
        cross = "bearish"

    summary = f"""
As of {latest.name.strftime("%Y-%m-%d")}, the closing price of {symbol} is {float(latest['Close']):.2f}.
The 10-day moving average is {latest_sma10:.2f} and the 50-day moving average is {latest_sma50:.2f}.
"""
    if cross:
        summary += f"A {cross} crossover just occurred."

    return chart_path, summary.strip(), symbol

def get_llama_insight(prompt):
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={"model": "llama2", "prompt": prompt, "stream": False},
            verify=False
        )
        return response.json().get("response", "No response.")
    except Exception as e:
        return f"Error communicating with LLaMA: {e}"

@app.route("/", methods=["GET", "POST"])
def index():
    chart_path = None
    llama_response = ""
    summary = ""
    symbol = ""

    if request.method == "POST":
        symbol = request.form["symbol"].strip().upper()
        chart_path, summary, symbol = fetch_data(symbol)
        if chart_path:
            llama_response = get_llama_insight(f"Based on the following stock data, what is your interpretation of the trend?\n{summary}")
        else:
            summary = "No data found for this symbol."

    return render_template("index.html", chart_path=chart_path, summary=summary, llama_response=llama_response, symbol=symbol)

if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True)