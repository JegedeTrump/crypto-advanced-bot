import os
import requests
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
from telegram import Bot
from datetime import datetime
import asyncio

# Load API keys
CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# Fetch historical data (free CoinGecko API)
def get_historical_data(symbol, days=30):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart?vs_currency=usd&days={days}"
    data = requests.get(url).json()
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    return prices

# Advanced signal generation
def analyze_with_indicators(df):
    # Calculate indicators
    df["rsi"] = RSIIndicator(df["price"], window=14).rsi()
    macd = MACD(df["price"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    bb = BollingerBands(df["price"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    
    # Generate signals
    last = df.iloc[-1]
    signal = None
    confidence = 0
    
    # Strategy 1: RSI + Bollinger Bands
    if last["price"] < last["bb_lower"] and last["rsi"] < 30:
        signal = "BUY"
        confidence = 80
    elif last["price"] > last["bb_upper"] and last["rsi"] > 70:
        signal = "SELL"
        confidence = 75
        
    # Strategy 2: MACD Crossover
    if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
        if signal == "BUY":  # Boost confidence if both strategies agree
            confidence = 90
        else:
            signal = "BUY"
            confidence = 75
            
    return signal, last["price"], confidence

async def send_signal(coin, signal, price, confidence):
    message = (
        f"🚀 **ADVANCED FLASH SIGNAL** 🚀\n"
        f"• Coin: {coin['name']} ({coin['symbol']})\n"
        f"• Signal: {signal}\n"
        f"• Price: ${price:.2f}\n"
        f"• Confidence: {confidence}%\n"
        f"• Indicators: RSI + MACD + Bollinger Bands\n\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")

async def main():
    # Step 1: Fetch top 10 coins from CoinMarketCap
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=10"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    coins = requests.get(url, headers=headers).json()["data"]
    
    signals_sent = 0
    for coin in coins:
        if signals_sent >= 5:  # Max 5 signals per run
            break
            
        # Step 2: Get historical data
        symbol = coin["symbol"].lower()
        try:
            df = get_historical_data(symbol)
            signal, price, confidence = analyze_with_indicators(df)
            
            # Only send high-confidence signals
            if signal and confidence >= 70:
                await send_signal(coin, signal, price, confidence)
                signals_sent += 1
                await asyncio.sleep(1)  # Avoid API rate limits
                
        except Exception as e:
            print(f"⚠️ Error analyzing {symbol}: {e}")

if __name__ == "__main__":
    print("🚀 Starting Advanced Crypto Signal Bot...")
    asyncio.run(main())
    print("✅ Bot run completed! Check Telegram for signals.")
