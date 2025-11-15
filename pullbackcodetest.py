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

show_all_pairs = st.checkbox("Show all pairs summary", value=True)

# -----------------------------
# Build summary for all pairs
# -----------------------------
summary_data = []

for pair in pairs:
    # H2 Data
    df_h2 = get_data(pair, period="60d", interval="2h")
    df_h2 = calculate_ema_trend(df_h2, ema_fast, ema_slow)
    df_h2 = find_pullback_signals(df_h2)
    
    # Daily Data
    df_daily = get_data(pair, period="180d", interval="1d")
    df_daily = calculate_ema_trend(df_daily, ema_fast, ema_slow)
    last_daily_cross = df_daily['EMA_Cross'].dropna().iloc[-1] if not df_daily['EMA_Cross'].dropna().empty else "No Cross"
    
    # Latest H2 Setup
    latest_setup = df_h2[df_h2['H2_Signal'].notnull()].tail(1)
    if not latest_setup.empty:
        summary_data.append({
            "Pair": pair,
            "Time": latest_setup.index[-1],
            "Close": latest_setup['Close'].values[0],
            "H2 Trend": latest_setup['Trend'].values[0],
            "H2 Signal": latest_setup['H2_Signal'].values[0],
            "Daily EMA Cross": last_daily_cross
        })
    else:
        summary_data.append({
            "Pair": pair,
            "Time": "-",
            "Close": "-",
            "H2 Trend": "-",
            "H2 Signal": "-",
            "Daily EMA Cross": last_daily_cross
        })

summary_df = pd.DataFrame(summary_data)

# -----------------------------
# Display in Streamlit
# -----------------------------
if show_all_pairs:
    st.subheader("📊 All Pairs Summary")
    st.dataframe(summary_df)

# Optional: select a single pair
selected_pair = st.selectbox("Select a Forex Pair for detailed view", pairs)
detailed_setup = summary_df[summary_df['Pair'] == selected_pair]
st.subheader(f"🔍 Detailed View - {selected_pair}")
st.write(detailed_setup.T)
