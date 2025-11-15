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

# -----------------------------
# Functions
# -----------------------------
def get_data(pair, period="60d", interval="2h"):
    df = yf.download(pair, period=period, interval=interval)
    df.dropna(inplace=True)
    return df

def calculate_ema_trend(df, fast=50, slow=200):
    df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=fast)
    df['EMA200'] = ta.trend.ema_indicator(df['Close'], window=slow)
    df['Trend'] = df['EMA50'] > df['EMA200']
    df['Trend'] = df['Trend'].replace({True: 'Uptrend', False: 'Downtrend'})
    
    df['EMA_Cross'] = None
    for i in range(1, len(df)):
        if df['EMA50'][i-1] < df['EMA200'][i-1] and df['EMA50'][i] > df['EMA200'][i]:
            df['EMA_Cross'][i] = 'Bullish Cross'
        elif df['EMA50'][i-1] > df['EMA200'][i-1] and df['EMA50'][i] < df['EMA200'][i]:
            df['EMA_Cross'][i] = 'Bearish Cross'
    return df

def find_pullback_signals(df):
    signals = []
    for i in range(1, len(df)):
        if df['Trend'][i] == 'Uptrend' and df['Low'][i] <= df['EMA50'][i]:
            signals.append("Buy Setup")
        elif df['Trend'][i] == 'Downtrend' and df['High'][i] >= df['EMA50'][i]:
            signals.append("Sell Setup")
        else:
            signals.append(None)
    signals.insert(0, None)
    df['H2_Signal'] = signals
    return df

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📈 Forex Screener - H2 Pullback + Daily EMA Cross")

selected_pair = st.selectbox("Select Forex Pair", pairs)
show_history = st.checkbox("Show Last 10 Setups", value=True)

# Get H2 data
df_h2 = get_data(selected_pair, period="60d", interval="2h")
df_h2 = calculate_ema_trend(df_h2, ema_fast, ema_slow)
df_h2 = find_pullback_signals(df_h2)

# Get Daily EMA Cross
df_daily = get_data(selected_pair, period="180d", interval="1d")
df_daily = calculate_ema_trend(df_daily, ema_fast, ema_slow)
last_daily_cross = df_daily['EMA_Cross'].dropna().iloc[-1] if not df_daily['EMA_Cross'].dropna().empty else "No Cross"

st.subheader(f"{selected_pair} Latest Setup")
latest_setup = df_h2[df_h2['H2_Signal'].notnull()].tail(1)
if not latest_setup.empty:
    st.write(f"Time: {latest_setup.index[-1]}")
    st.write(f"Close: {latest_setup['Close'].values[0]:.5f}")
    st.write(f"H2 Trend: {latest_setup['Trend'].values[0]}")
    st.write(f"H2 Signal: {latest_setup['H2_Signal'].values[0]}")
    st.write(f"Daily EMA Cross: {last_daily_cross}")
else:
    st.write("No current setup found.")

# Show last setups if selected
if show_history:
    st.subheader(f"Last 10 Setups for {selected_pair}")
    history = df_h2[df_h2['H2_Signal'].notnull()].tail(10)
    if not history.empty:
        st.dataframe(history[['Close', 'Trend', 'H2_Signal']])
    else:
        st.write("No setups found in history.")
