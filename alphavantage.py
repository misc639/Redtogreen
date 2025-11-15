import streamlit as st
import pandas as pd
import requests
import ta
import time

st.set_page_config(page_title="Forex Screener", layout="wide")
st.title("📈 Forex Screener - H2 Pullback + Daily EMA Cross (Alpha Vantage)")

# -----------------------------
# Configuration
# -----------------------------
API_KEY = "RJEFPVVFXTYC9ZD6"  # Replace with your API key
pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF",
         "USD/CAD", "EUR/GBP", "EUR/JPY", "GBP/JPY", "NZD/USD"]
ema_fast = 50
ema_slow = 200

# -----------------------------
# Functions
# -----------------------------
def get_alpha_vantage_data(pair, interval="60min", outputsize="compact"):
    """
    Fetch intraday Forex data from Alpha Vantage
    """
    from_symbol, to_symbol = pair.split('/')
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval={interval}&outputsize={outputsize}&apikey={API_KEY}&datatype=csv"
    try:
        df = pd.read_csv(url)
        if df.empty:
            return pd.DataFrame()
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)
        df = df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close'})
        df = df[['Open','High','Low','Close']]
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching {pair}: {e}")
        return pd.DataFrame()

def get_alpha_vantage_daily(pair):
    """
    Fetch daily Forex data from Alpha Vantage
    """
    from_symbol, to_symbol = pair.split('/')
    url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&outputsize=full&apikey={API_KEY}&datatype=csv"
    try:
        df = pd.read_csv(url)
        if df.empty:
            return pd.DataFrame()
        df['time'] = pd.to_datetime(df['timestamp'])
        df.set_index('time', inplace=True)
        df = df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close'})
        df = df[['Open','High','Low','Close']]
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching daily {pair}: {e}")
        return pd.DataFrame()

def calculate_ema_trend(df, fast=50, slow=200):
    if df.empty:
        return df
    df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=fast)
    df['EMA200'] = ta.trend.ema_indicator(df['Close'], window=slow)
    df['Trend'] = df['EMA50'] > df['EMA200']
    df['Trend'] = df['Trend'].replace({True:'Uptrend', False:'Downtrend'})
    
    # EMA Cross
    df['EMA_Cross'] = None
    for i in range(1,len(df)):
        if df['EMA50'].iloc[i-1] < df['EMA200'].iloc[i-1] and df['EMA50'].iloc[i] > df['EMA200'].iloc[i]:
            df.at[df.index[i],'EMA_Cross'] = 'Bullish Cross'
        elif df['EMA50'].iloc[i-1] > df['EMA200'].iloc[i-1] and df['EMA50'].iloc[i] < df['EMA200'].iloc[i]:
            df.at[df.index[i],'EMA_Cross'] = 'Bearish Cross'
    return df

def find_pullback_signals(df):
    if df.empty:
        return df
    signals = []
    for i in range(len(df)):
        if i==0:
            signals.append(None)
            continue
        if df['Trend'].iloc[i]=='Uptrend' and df['Low'].iloc[i]<=df['EMA50'].iloc[i]:
            signals.append("Buy Setup")
        elif df['Trend'].ilo
