import streamlit as st
import yfinance as yf
import pandas as pd

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_indicators(df):
    df['EMA8'] = df['Close'].ewm(span=8, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    return df

def scalping_logic(df):
    last = df.iloc[-1]
    return last['EMA8'] > last['EMA21'] and last['MACD'] > last['Signal'] and 40 < last['RSI'] < 60

def swing_logic(df):
    last = df.iloc[-1]
    return last['EMA50'] > last['EMA200'] and last['MACD'] > last['Signal'] and 30 < last['RSI'] < 70

def run_screener(assets, screener_type):
    result = []
    timeframe = '1m' if screener_type == 'Scalping' else '1h'
    for symbol in assets:
        try:
            data = yf.download(symbol, interval=timeframe, period='5d', progress=False)
            if data.empty:
                result.append({'Asset': symbol, 'Signal': '❌ No Data'})
                continue
            df = compute_indicators(data)
            is_opportunity = scalping_logic(df) if screener_type == 'Scalping' else swing_logic(df)
            result.append({'Asset': symbol, 'Signal': '✅ Opportunity' if is_opportunity else '❌ No Setup'})
        except Exception as e:
            result.append({'Asset': symbol, 'Signal': f"Error: {str(e)}"})
    return pd.DataFrame(result)

# --- Streamlit UI ---
st.title("📈 Multi-Market Screener (Scalping & Swing)")

asset_input = st.text_input("Enter Assets (comma separated)", "RELIANCE.NS,AAPL,BTC-USD,EURUSD=X")
assets = [a.strip() for a in asset_input.split(',') if a.strip()]

screener_type = st.radio("Select Screener Type", ['Scalping', 'Swing'])

if st.button("Run Screener"):
    output = run_screener(assets, screener_type)
    st.write(output)
