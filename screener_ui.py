import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# ----------------------------
# Indicator Computation
# ----------------------------
def compute_indicators(df, indicators):
    if 'EMA8' in indicators:
        df['EMA8'] = df['Close'].ewm(span=8).mean()
    if 'EMA21' in indicators:
        df['EMA21'] = df['Close'].ewm(span=21).mean()
    if 'EMA50' in indicators:
        df['EMA50'] = df['Close'].ewm(span=50).mean()
    if 'EMA200' in indicators:
        df['EMA200'] = df['Close'].ewm(span=200).mean()
    if 'RSI' in indicators:
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
    if 'ATR' in indicators:
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
    if 'MACD' in indicators:
        ema12 = df['Close'].ewm(span=12).mean()
        ema26 = df['Close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26
        df['Signal'] = df['MACD'].ewm(span=9).mean()
    return df

# ----------------------------
# Telegram Alert
# ----------------------------
def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.get(url, params=params)
        return response.ok
    except Exception as e:
        print("Telegram send error:", e)
        return False

# ----------------------------
# Screener Logic
# ----------------------------
def run_screener(assets, indicators, method, interval, period, bot_token=None, chat_id=None):
    results = []
    for symbol in assets:
        try:
            data = yf.download(symbol, interval=interval, period=period, progress=False)
            if data.empty or len(data) < 20:
                results.append({'Asset': symbol, 'Signal': 'No Data'})
                continue
            data = compute_indicators(data, indicators)

            last = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 2 else last

            ema8 = float(last.get('EMA8', 0))
            ema21 = float(last.get('EMA21', 0))
            ema50 = float(last.get('EMA50', 0))
            ema200 = float(last.get('EMA200', 0))
            macd = float(last.get('MACD', 0))
            macd_signal = float(last.get('Signal', 0))
            rsi = float(last.get('RSI', 50))
            rsi_prev = float(prev.get('RSI', 50))
            atr = float(last.get('ATR', 0))

            rsi_trend = '🔼 Rising' if rsi > rsi_prev else '🔽 Falling'

            if method == 'Scalping':
                if ema8 > ema21 and macd > macd_signal and 40 < rsi < 60:
                    signal = '🔼 Buy'
                elif ema8 < ema21 and macd < macd_signal and 40 < rsi < 60:
                    signal = '🔽 Sell'
                else:
                    signal = '❌ No Setup'
            elif method == 'Swing':
                if ema50 > ema200 and macd > macd_signal and 30 < rsi < 70:
                    signal = '🔼 Buy'
                elif ema50 < ema200 and macd < macd_signal and 30 < rsi < 70:
                    signal = '🔽 Sell'
                else:
                    signal = '❌ No Setup'
            else:
                signal = '❌ Invalid Strategy'

            result = {
                'Asset': symbol,
                'Signal': signal,
                'EMA8 > EMA21': '✅' if ema8 > ema21 else '❌',
                'EMA8': round(ema8, 2),
                'EMA21': round(ema21, 2),
                'EMA50 > EMA200': '✅' if ema50 > ema200 else '❌',
                'EMA50': round(ema50, 2),
                'EMA200': round(ema200, 2),
                'RSI': round(rsi, 2),
                'RSI Trend': rsi_trend,
                'ATR': round(atr, 4)
            }

            if signal in ['🔼 Buy', '🔽 Sell'] and bot_token and chat_id:
                msg = (
                    f"*Trade Signal*\n"
                    f"Asset: `{symbol}`\n"
                    f"Strategy: {method}\n"
                    f"Signal: {signal}\n"
                    f"EMA8: {ema8:.2f} | EMA21: {ema21:.2f}\n"
                    f"RSI: {rsi:.2f} ({rsi_trend})\n"
                    f"ATR: {atr:.4f}"
                )
                send_telegram_message(bot_token, chat_id, msg)

            results.append(result)

        except Exception as e:
            results.append({'Asset': symbol, 'Signal': f"⚠️ Error: {str(e)}"})
    return pd.DataFrame(results)

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Trading Screener", layout="wide")
st.title("📊 Multi-Market Trading Screener")

assets = st.text_area("Enter asset symbols (comma-separated)", "AAPL,INFY.NS,BTC-USD,ETH-USD").split(',')
assets = [x.strip() for x in assets if x.strip() != '']

indicators = ['EMA8', 'EMA21', 'EMA50', 'EMA200', 'MACD', 'RSI', 'ATR']
selected_indicators = indicators

method = st.selectbox("Strategy", ["Scalping", "Swing"])
interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=2)
period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=1)

st.sidebar.header("🔔 Telegram Alerts (Optional)")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

if st.button("Run Screener"):
    with st.spinner("Running strategy and scanning assets..."):
        df = run_screener(assets, selected_indicators, method, interval, period, 
                         bot_token=bot_token if bot_token else None, 
                         chat_id=chat_id if chat_id else None)
        st.dataframe(df, use_container_width=True)
