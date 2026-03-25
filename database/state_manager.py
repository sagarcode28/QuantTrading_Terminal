# database/state_manager.py
import os
from pymongo import MongoClient
from config import config

class StateManager:
    def __init__(self):
        # Connect to MongoDB Atlas
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables.")
            
        self.client = MongoClient(mongo_uri)
        self.db = self.client['apex_terminal']
        self.collection = self.db['portfolio_state']
        
        # Initialize state on the very first boot if it doesn't exist
        if self.collection.count_documents({"type": "portfolio"}) == 0:
            self.collection.insert_one({
                "type": "portfolio",
                "live_capital": config.PAPER_TRADING_BALANCE,
                "open_positions": {},
                "milestone_hit": False
            })

    def get_state(self):
        return self.collection.find_one({"type": "portfolio"})

    def update_capital(self, new_capital):
        self.collection.update_one({"type": "portfolio"}, {"$set": {"live_capital": new_capital}})

    def update_positions(self, open_positions):
        self.collection.update_one({"type": "portfolio"}, {"$set": {"open_positions": open_positions}})
        
    def set_milestone_hit(self):
        self.collection.update_one({"type": "portfolio"}, {"$set": {"milestone_hit": True}})