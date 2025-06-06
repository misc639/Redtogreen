import streamlit as st
import yfinance as yf
import pandas as pd

# --- Indicator calculations ---

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def compute_macd(df):
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def compute_ema(df, period):
    return df['Close'].ewm(span=period, adjust=False).mean()

def compute_indicators(df, indicators):
    if 'EMA8' in indicators:
        df['EMA8'] = compute_ema(df, 8)
    if 'EMA21' in indicators:
        df['EMA21'] = compute_ema(df, 21)
    if 'EMA50' in indicators:
        df['EMA50'] = compute_ema(df, 50)
    if 'EMA200' in indicators:
        df['EMA200'] = compute_ema(df, 200)
    if 'MACD' in indicators or 'Signal' in indicators:
        macd, signal = compute_macd(df)
        if 'MACD' in indicators:
            df['MACD'] = macd
        if 'Signal' in indicators:
            df['Signal'] = signal
    if 'RSI' in indicators:
        df['RSI'] = compute_rsi(df['Close'])
    if 'ATR' in indicators:
        df['ATR'] = compute_atr(df)
    return df

# --- Strategy logic ---

def scalping_signal(df):
    try:
        last = df.iloc[-1]
        ema8 = float(last.get('EMA8', 0))
        ema21 = float(last.get('EMA21', 0))
        macd = float(last.get('MACD', 0))
        signal = float(last.get('Signal', 0))
        rsi = float(last.get('RSI', 50))
        return ema8 > ema21 and macd > signal and 40 < rsi < 60
    except:
        return False

def swing_signal(df):
    try:
        last = df.iloc[-1]
        ema50 = float(last.get('EMA50', 0))
        ema200 = float(last.get('EMA200', 0))
        macd = float(last.get('MACD', 0))
        signal = float(last.get('Signal', 0))
        rsi = float(last.get('RSI', 50))
        return ema50 > ema200 and macd > signal and 30 < rsi < 70
    except:
        return False


# --- Run Screener ---

def run_screener(assets, indicators, method, interval, period):
    results = []
    for symbol in assets:
        try:
            data = yf.download(symbol, interval=interval, period=period, progress=False)
            if data.empty:
                results.append({'Asset': symbol, 'Signal': 'No data'})
                continue
            data = compute_indicators(data, indicators)
            signal = False
            if method == 'Scalping':
                signal = scalping_signal(data)
            elif method == 'Swing':
                signal = swing_signal(data)
            last = data.iloc[-1]
            res = {
                'Asset': symbol,
                'Signal': '✅ Opportunity' if signal else '❌ No Setup'
            }
            # Add indicator values for display
            for ind in indicators:
                if ind in last:
                    res[ind] = round(last[ind], 4)
            results.append(res)
        except Exception as e:
            results.append({'Asset': symbol, 'Signal': f"Error: {str(e)}"})
    return pd.DataFrame(results)

# --- Streamlit UI ---

st.title("📊 Multi-Market Screener with Custom Indicators")

# Input assets
asset_text = st.text_area("Enter asset symbols (comma separated)", 
                         value="RELIANCE.NS,AAPL,BTC-USD,EURUSD=X")
assets = [a.strip().upper() for a in asset_text.split(',') if a.strip()]

# Select indicators
all_indicators = ['EMA8', 'EMA21', 'EMA50', 'EMA200', 'MACD', 'Signal', 'RSI', 'ATR']
selected_indicators = st.multiselect("Select Indicators to include", all_indicators, 
                                     default=['EMA8', 'EMA21', 'MACD', 'Signal', 'RSI', 'ATR'])

# Choose strategy method
method = st.selectbox("Select Strategy Method", ['Scalping', 'Swing'])

# Interval and period
interval_map = {
    'Scalping': '5m',
    'Swing': '1h'
}
interval = interval_map[method]
period = '7d' if method == 'Scalping' else '30d'

st.write(f"Using interval: **{interval}**, period: **{period}**")

if st.button("Run Screener"):
    with st.spinner("Fetching data and computing signals..."):
        df_result = run_screener(assets, selected_indicators, method, interval, period)
    st.dataframe(df_result)
