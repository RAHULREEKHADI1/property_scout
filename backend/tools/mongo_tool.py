from pymongo import MongoClient
from typing import Dict, List, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

class MongoDBTool:
    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB", "estate_scout")
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.listings = self.db.listings
        self.user_profiles = self.db.user_profiles
    
    def insert_listing(self, property_data: Dict) -> str:
        property_data["created_at"] = datetime.utcnow()
        result = self.listings.insert_one(property_data)
        return str(result.inserted_id)
    
    def get_all_listings(self) -> List[Dict]:
        listings = list(self.listings.find().sort("created_at", -1))
        for listing in listings:
            listing["_id"] = str(listing["_id"])
        return listings
    
    def get_listing_by_address(self, address: str) -> Optional[Dict]:
        listing = self.listings.find_one({"address": address})
        if listing:
            listing["_id"] = str(listing["_id"])
        return listing
    
    def update_user_preference(self, user_id: str, preferences: Dict):
        self.user_profiles.update_one(
            {"user_id": user_id},
            {"$set": {**preferences, "updated_at": datetime.utcnow()}},
            upsert=True
        )
    
    def get_user_preferences(self, user_id: str = "default") -> Dict:
        profile = self.user_profiles.find_one({"user_id": user_id})
        if profile:
            profile["_id"] = str(profile["_id"])
            return profile
        return {"user_id": user_id, "preferences": {}}
    
    def clear_listings(self):
        self.listings.delete_many({})
