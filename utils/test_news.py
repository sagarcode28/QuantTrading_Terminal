# utils/test_news.py
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from news_engine.analyzer import MarketSentiment

print("🌍 Pinging Crypto Fear & Greed API...")
sentiment = MarketSentiment.get_fear_and_greed()

print("\n--- LIVE SENTIMENT DATA ---")
print(f"Score: {sentiment['score']} / 100")
print(f"Classification: {sentiment['classification']}")
print("---------------------------\n")