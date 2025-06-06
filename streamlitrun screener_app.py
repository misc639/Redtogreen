import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import feedparser
from datetime import datetime

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
        ema_fast = df['Close'].ewm(span=24).mean()
        ema_slow = df['Close'].ewm(span=60).mean()
        df['MACD'] = ema_fast - ema_slow
        df['Signal'] = df['MACD'].ewm(span=18).mean()
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
# High Impact News (RSS)
# ----------------------------
def get_high_impact_news():
    feed = feedparser.parse("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
    news_items = []
    for entry in feed.entries:
        if 'High' in entry.title:
            news_items.append({
                "Time": entry.published,
                "Title": entry.title,
                "Link": entry.link
            })
    return news_items[:10]

# ----------------------------
# Check valid tickers
# ----------------------------
def is_valid_ticker(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        return not df.empty
    except:
        return False

# ----------------------------
# Screener Logic (placeholder logic)
# ----------------------------
def run_screener(assets, indicators, method, interval, period, macd_buy_level, macd_sell_level, bot_token=None, chat_id=None):
    results = []
    data_map = {}
    for asset in assets:
        if not is_valid_ticker(asset, interval, period):
            continue
        df = yf.download(asset, interval=interval, period=period)
        df = compute_indicators(df, indicators)
        signal = ""
        if 'MACD' in df.columns:
            if df['MACD'].iloc[-1] > macd_buy_level:
                signal = "Buy Chance"
            elif df['MACD'].iloc[-1] < macd_sell_level:
                signal = "Sell Chance"
        results.append({"Asset": asset, "MACD Signal": signal})
        data_map[asset] = df
    return pd.DataFrame(results), data_map

# ----------------------------
# Multi-timeframe Screener
# ----------------------------
def run_screener_multi_tf(assets, indicators, method, timeframes, periods, macd_buy_level, macd_sell_level, bot_token=None, chat_id=None):
    combined_results = []
    for tf_idx, interval in enumerate(timeframes):
        period = periods[tf_idx]
        st.subheader(f"🕒 Results for {interval} timeframe")
        df, data_map = run_screener(
            assets, indicators, method, interval, period,
            macd_buy_level, macd_sell_level,
            bot_token, chat_id
        )
        st.dataframe(df, use_container_width=True)
        combined_results.append((interval, df, data_map))
    return combined_results

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Trading Screener", layout="wide")
st.title("📊 Multi-Market Trading Screener")

assets = st.text_area("Enter asset symbols (comma-separated)", "AAPL,INFY.NS,BTC-USD,ETH-USD,EURUSD=X,USDJPY=X").split(',')
assets = [x.strip() for x in assets if x.strip() != '']

indicators = ['EMA8', 'EMA21', 'EMA50', 'EMA200', 'MACD', 'RSI', 'ATR']
selected_indicators = indicators

method = st.selectbox("Strategy", ["Scalping", "Swing"])

multi_tf = st.checkbox("Enable Multi-Timeframe Analysis", value=True)
if multi_tf:
    timeframes = st.multiselect("Select Timeframes", ["5m", "15m", "1h", "1d"], default=["15m", "1h"])
    periods = ["5d" if tf in ["5m", "15m"] else "1mo" for tf in timeframes]
else:
    interval = st.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=2)
    period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=1)

macd_buy_level = st.number_input("MACD Buy Threshold", value=0.0, step=0.1)
macd_sell_level = st.number_input("MACD Sell Threshold", value=0.0, step=0.1)

st.sidebar.header("🔔 Telegram Alerts (Optional)")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

st.sidebar.header("📰 High Impact News")
for item in get_high_impact_news():
    st.sidebar.markdown(f"**{item['Time']}** — [{item['Title']}]({item['Link']})")

if st.button("Run Screener"):
    with st.spinner("Running strategy and scanning assets..."):
        if multi_tf:
            run_screener_multi_tf(
                assets, selected_indicators, method, timeframes, periods,
                macd_buy_level, macd_sell_level,
                bot_token if bot_token else None,
                chat_id if chat_id else None
            )
        else:
            df, data_map = run_screener(
                assets, selected_indicators, method, interval, period,
                macd_buy_level, macd_sell_level,
                bot_token=bot_token if bot_token else None,
                chat_id=chat_id if chat_id else None
            )
            st.dataframe(df, use_container_width=True)

            st.subheader("📈 Chart Previews")
            for asset in df['Asset']:
                if asset in data_map:
                    st.markdown(f"### {asset} Chart")
                    chart_data = data_map[asset]

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=chart_data.index,
                        open=chart_data['Open'],
                        high=chart_data['High'],
                        low=chart_data['Low'],
                        close=chart_data['Close'],
                        name='Price'))

                    for ema in ['EMA8', 'EMA21', 'EMA50', 'EMA200']:
                        if ema in chart_data.columns:
                            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data[ema], mode='lines', name=ema))

                    fig.update_layout(
                        xaxis_title="Time",
                        yaxis_title="Price",
                        xaxis_rangeslider_visible=False,
                        height=400
                    )
                    with st.expander(f"📈 Preview Chart: {asset}"):
                        st.plotly_chart(fig, use_container_width=True)
