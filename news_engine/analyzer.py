# news_engine/analyzer.py
import requests
import logging

class MarketSentiment:
    @staticmethod
    def get_fear_and_greed():
        """
        Fetches the current Crypto Fear & Greed Index.
        0-24: Extreme Fear
        25-46: Fear
        47-54: Neutral
        55-74: Greed
        75-100: Extreme Greed
        """
        try:
            # We use the open Alternative.me API. No keys required.
            response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            data = response.json()
            
            if data and 'data' in data:
                score = int(data['data'][0]['value'])
                classification = data['data'][0]['value_classification']
                return {'score': score, 'classification': classification}
        except Exception as e:
            logging.warning(f"[News Engine] Failed to fetch Fear & Greed Index: {e}")
        
        # If the API fails or times out, fail open (Neutral) so trading doesn't halt
        return {'score': 50, 'classification': 'Neutral'}