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
    df['Trend'] = df['Trend'].replace({True: 'Uptrend', False: 'Downtrend'})
    
    df['EMA_Cross'] = None
    for i in range(1, len(df)):
        try:
            if df['EMA50'][i-1] < df['EMA200'][i-1] and df['EMA50'][i] > df['EMA200'][i]:
                df.at[i, 'EMA_Cross'] = 'Bullish Cross'
            elif df['EMA50'][i-1] > df['EMA200'][i-1] and df['EMA50'][i] < df['EMA200'][i]:
                df.at[i, 'EMA_Cross'] = 'Bearish Cross'
        except Exception:
            continue
    return df

def find_pullback_signals(df):
    if df.empty:
        return df
    signals = []
    for i in range(len(df)):
        if i == 0:
            signals.append(None)
            continue
        try:
            if df['Trend'][i] == 'Uptrend' and df['Low'][i] <= df['EMA50'][i]:
                signals.append("Buy Setup")
            elif df['Trend'][i] == 'Downtrend' and df['High'][i] >= df['EMA50'][i]:
                signals.append("Sell Setup")
            else:
                signals.append(None)
        except Exception:
            signals.append(None)
    df['H2_Signal'] = signals
    return df

# -----------------------------
# Build summary table
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
    last_daily_cross = "No Data"
    if not df_daily.empty:
        crosses = df_daily['EMA_Cross'].dropna()
        if not crosses.empty:
            last_daily_cross = crosses.iloc[-1]
    
    # Latest H2 setup
    latest_setup = {"Pair": pair, "Time": "-", "Close": "-", "H2 Trend": "-", "H2 Signal": "-", "Daily EMA Cross": last_daily_cross}
    if not df_h2.empty:
        setups = df_h2[df_h2['H2_Signal'].notnull()]
        if not setups.empty:
            last = setups.tail(1)
            latest_setup.update({
                "Time": last.index[-1],
                "Close": round(last['Close'].values[0], 5),
                "H2 Trend": last['Trend'].values[0],
                "H2 Signal": last['H2_Signal'].values[0],
            })
    summary_data.append(latest_setup)

summary_df = pd.DataFrame(summary_data)

# -----------------------------
# Display in Streamlit with colors
# -----------------------------
def highlight_signal(row):
    if row["H2 Signal"] == "Buy Setup":
        return ['background-color: #b6fcb6']*len(row)
    elif row["H2 Signal"] == "Sell Setup":
        return ['background-color: #ffb6b6']*len(row)
    else:
        return ['']*len(row)

st.subheader("All Pairs Summary")
st.dataframe(summary_df.style.apply(highlight_signal, axis=1))

# -----------------------------
# Detailed View for selected pair
# -----------------------------
selected_pair = st.selectbox("Select a Forex Pair for detailed view", pairs)
detailed = summary_df[summary_df['Pair'] == selected_pair]
st.subheader(f"Detailed View - {selected_pair}")
st.write(detailed.T)
