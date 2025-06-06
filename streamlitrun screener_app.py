import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import feedparser

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
# Screener Logic
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

        # Latest indicator values
        latest = df.iloc[-1]
        results.append({
            "Asset": asset,
            "Signal": signal,
            "EMA8": round(latest['EMA8'], 4) if 'EMA8' in df.columns else None,
            "EMA21": round(latest['EMA21'], 4) if 'EMA21' in df.columns else None,
            "RSI": round(latest['RSI'], 2) if 'RSI' in df.columns else None,
            "ATR": round(latest['ATR'], 4) if 'ATR' in df.columns else None,
            "MACD": round(latest['MACD'], 4) if 'MACD' in df.columns else None,
            "Signal Line": round(latest['Signal'], 4) if 'Signal' in df.columns else None
        })
        data_map[asset] = df
    return pd.DataFrame(results), data_map

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
