import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# ----------------------------
# Indicator Calculation
# ----------------------------
def compute_indicators(df):
    df['EMA8'] = df['Close'].ewm(span=8).mean()
    df['EMA21'] = df['Close'].ewm(span=21).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['EMA200'] = df['Close'].ewm(span=200).mean()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    return df

# ----------------------------
# Telegram Bot Alert
# ----------------------------
def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.get(url, params=params)
        return response.ok
    except Exception as e:
        print("Telegram Error:", e)
        return False

# ----------------------------
# Screener
# ----------------------------
def screener(assets, strategy, interval, period, macd_buy, macd_sell, bot_token, chat_id):
    results = []
    for symbol in assets:
        try:
            df = yf.download(symbol, interval=interval, period=period, progress=False)
            if df.empty or len(df) < 20:
                results.append({'Asset': symbol, 'Signal': 'No Data'})
                continue
            df = compute_indicators(df)
            last, prev = df.iloc[-1], df.iloc[-2]

            ema8, ema21 = last['EMA8'], last['EMA21']
            ema50, ema200 = last['EMA50'], last['EMA200']
            rsi, rsi_prev = last['RSI'], prev['RSI']
            macd, signal = last['MACD'], last['Signal']
            atr = last['ATR']
            rsi_trend = '🔼 Rising' if rsi > rsi_prev else '🔽 Falling'
            prev_high = df['High'].shift(1).iloc[-1]
            prev_low = df['Low'].shift(1).iloc[-1]
            week_high = df['High'].rolling(window=5).max().iloc[-1]
            week_low = df['Low'].rolling(window=5).min().iloc[-1]

            signal_result = '❌ No Setup'
            if strategy == 'Scalping':
                if ema8 > ema21 and macd > signal and macd > macd_buy and 40 < rsi < 60:
                    signal_result = '🔼 Buy'
                elif ema8 < ema21 and macd < signal and macd < macd_sell and 40 < rsi < 60:
                    signal_result = '🔽 Sell'
            elif strategy == 'Swing':
                if ema50 > ema200 and macd > signal and macd > macd_buy and 30 < rsi < 70:
                    signal_result = '🔼 Buy'
                elif ema50 < ema200 and macd < signal and macd < macd_sell and 30 < rsi < 70:
                    signal_result = '🔽 Sell'

            row = {
                'Asset': symbol,
                'Signal': signal_result,
                'EMA8 > EMA21': '✅' if ema8 > ema21 else '❌',
                'EMA50 > EMA200': '✅' if ema50 > ema200 else '❌',
                'RSI': round(rsi, 2),
                'RSI Trend': rsi_trend,
                'MACD': round(macd, 2),
                'Signal Line': round(signal, 2),
                'ATR': round(atr, 4),
                'Prev High': round(prev_high, 2),
                'Prev Low': round(prev_low, 2),
                'Week High': round(week_high, 2),
                'Week Low': round(week_low, 2)
            }

            if signal_result in ['🔼 Buy', '🔽 Sell'] and bot_token and chat_id:
                msg = (
                    f"*{signal_result}* `{symbol}`\n"
                    f"Strategy: {strategy}\nMACD: {macd:.2f} | Signal: {signal:.2f}\n"
                    f"RSI: {rsi:.2f} ({rsi_trend})\nEMA8: {ema8:.2f} | EMA21: {ema21:.2f}\n"
                    f"ATR: {atr:.4f}\nHigh: {prev_high:.2f} | Low: {prev_low:.2f}"
                )
                send_telegram(bot_token, chat_id, msg)

            results.append(row)
        except Exception as e:
            results.append({'Asset': symbol, 'Signal': f"⚠️ Error: {e}"})
    return pd.DataFrame(results)

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config("Screener", layout="wide")
st.title("📈 Real-Time Screener")

symbols = st.text_input("Enter symbols (comma-separated)", "AAPL, BTC-USD, INFY.NS").split(',')
symbols = [s.strip() for s in symbols if s.strip()]

col1, col2, col3 = st.columns(3)
strategy = col1.selectbox("Strategy", ["Scalping", "Swing"])
interval = col2.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=2)
period = col3.selectbox("Period", ["1d", "5d", "1mo", "3mo"], index=1)

macd_buy = st.slider("MACD Buy Threshold", -5.0, 5.0, 0.0)
macd_sell = st.slider("MACD Sell Threshold", -5.0, 5.0, 0.0)

with st.sidebar:
    st.header("📲 Telegram Alert (Optional)")
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")

if st.button("Run Screener"):
    with st.spinner("Analyzing..."):
        result = screener(symbols, strategy, interval, period, macd_buy, macd_sell,
                          bot_token if bot_token else None, chat_id if chat_id else None)
        st.success("Scan Complete ✅")
        st.dataframe(result, use_container_width=True)
