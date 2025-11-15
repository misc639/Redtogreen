import streamlit as st
import pandas as pd
import yfinance as yf
import ta

# -----------------------------
# Configuration
# -----------------------------
pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCHF=X",
         "USDCAD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X", "NZDUSD=X"]
ema_fast = 50
ema_slow = 200

st.set_page_config(page_title="Forex Screener", layout="wide")
st.title("📈 Forex Screener - H2 Pullback + Daily EMA Cross")

# -----------------------------
# Functions
# -----------------------------
def get_data(pair, period="60d", interval="2h"):
    """Fetch data and return empty DataFrame on failure."""
    try:
        df = yf.download(pair, period=period, interval=interval, progress=False)
        if df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def calculate_ema_trend(df, fast=50, slow=200):
    if df.empty:
        return df
    df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=fast)
    df['EMA200'] = ta.trend.ema_indicator(df['Close'], window=slow)
    df['Trend'] = df['EMA50'] > df['EMA200']
    df['T]()
