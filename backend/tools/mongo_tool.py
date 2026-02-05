from pymongo import MongoClient
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import hashlib
import json

load_dotenv()


class MongoDBTool:
    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB", "estate_scout")
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.listings = self.db.listings
        self.user_profiles = self.db.user_profiles
        self.conversation_memory = self.db.conversation_memory
        self.search_cache = self.db.search_cache  # New collection for caching
        self.user_currencies = self.db.user_currencies  # New collection for storing user currency preferences
    
    # ============================================
    # CURRENCY MANAGEMENT
    # ============================================
    
    def save_user_currency(self, user_id: str, currency_code: str, currency_symbol: str):
        """Save user's preferred currency to database"""
        self.user_currencies.update_one(
            {"user_id": user_id},
            {"$set": {
                "currency_code": currency_code,
                "currency_symbol": currency_symbol,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"✓ Saved currency preference: {currency_code} ({currency_symbol}) for user {user_id}")
    
    def get_user_currency(self, user_id: str = "default") -> Dict:
        """Retrieve user's preferred currency from database"""
        currency = self.user_currencies.find_one({"user_id": user_id})
        if currency:
            return {
                "code": currency.get("currency_code", "USD"),
                "symbol": currency.get("currency_symbol", "$")
            }
        # Default to USD if not found
        return {"code": "USD", "symbol": "$"}
    
    # ============================================
    # SEARCH CACHE MANAGEMENT
    # ============================================
    
    def _generate_search_hash(self, criteria: Dict) -> str:
        """Generate a unique hash for search criteria"""
        # Normalize criteria to ensure consistent hashing
        normalized = {
            "location": criteria.get("location", "").lower().strip(),
            "bedrooms": str(criteria.get("bedrooms", "1")),
            "max_price": int(criteria.get("max_price", 2500)),
            "requirements": criteria.get("requirements", "").lower().strip()
        }
        # Create hash from normalized criteria
        criteria_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(criteria_str.encode()).hexdigest()
    
    def get_cached_search(self, criteria: Dict, max_results: int = 5) -> Optional[List[Dict]]:
        """
        Retrieve cached search results if available and fresh.
        Returns None if no cache found or cache is stale.
        """
        search_hash = self._generate_search_hash(criteria)
        
        # Find cache entry
        cache_entry = self.search_cache.find_one({"search_hash": search_hash})
        
        if not cache_entry:
            print(f"✗ No cache found for search criteria")
            return None
        
        # Check if cache is still fresh (24 hours)
        cache_age = datetime.utcnow() - cache_entry.get("created_at", datetime.utcnow())
        if cache_age > timedelta(hours=24):
            print(f"✗ Cache expired (age: {cache_age})")
            return None
        
        cached_properties = cache_entry.get("properties", [])
        
        # Return only the requested number of results
        # This handles cases like "5 properties" then "2 properties" with same criteria
        if len(cached_properties) >= max_results:
            results = cached_properties[:max_results]
            print(f"✓ Cache HIT - Returning {len(results)} properties from cache (total cached: {len(cached_properties)})")
            print(f"   Search criteria: {criteria}")
            print(f"   Cache age: {cache_age}")
            return results
        else:
            print(f"✗ Cache has only {len(cached_properties)} properties, need {max_results}")
            return None
    
    def save_search_cache(self, criteria: Dict, properties: List[Dict]):
        """Save search results to cache"""
        search_hash = self._generate_search_hash(criteria)
        
        # Store in cache
        self.search_cache.update_one(
            {"search_hash": search_hash},
            {"$set": {
                "criteria": criteria,
                "properties": properties,
                "created_at": datetime.utcnow(),
                "search_count": 1
            }},
            upsert=True
        )
        
        # Increment search count if updating existing cache
        self.search_cache.update_one(
            {"search_hash": search_hash},
            {"$inc": {"search_count": 1}}
        )
        
        print(f"✓ Cached {len(properties)} properties for future queries")
        print(f"   Cache key: {search_hash}")
    
    def clear_search_cache(self, user_id: str = None):
        """Clear search cache (optionally for specific user)"""
        if user_id:
            # Could be extended to support user-specific caches
            pass
        else:
            result = self.search_cache.delete_many({})
            print(f"✓ Cleared {result.deleted_count} cache entries")
    
    # ============================================
    # LISTING MANAGEMENT
    # ============================================
    
    def insert_listing(self, property_data: Dict) -> str:
        """Insert a single property listing"""
        property_data["created_at"] = datetime.utcnow()
        result = self.listings.insert_one(property_data)
        return str(result.inserted_id)
    
    def get_all_listings(self) -> List[Dict]:
        """Get all listings sorted by creation date"""
        listings = list(self.listings.find().sort("created_at", -1))
        for listing in listings:
            listing["_id"] = str(listing["_id"])
        return listings
    
    def get_listing_by_address(self, address: str) -> Optional[Dict]:
        """Get a specific listing by address"""
        listing = self.listings.find_one({"address": address})
        if listing:
            listing["_id"] = str(listing["_id"])
        return listing
    
    def clear_listings(self):
        """Clear all listings"""
        self.listings.delete_many({})
    
    # ============================================
    # USER PREFERENCES
    # ============================================
    
    def update_user_preference(self, user_id: str, preferences: Dict):
        """Update user preferences"""
        self.user_profiles.update_one(
            {"user_id": user_id},
            {"$set": {**preferences, "updated_at": datetime.utcnow()}},
            upsert=True
        )
    
    def get_user_preferences(self, user_id: str = "default") -> Dict:
        """Get user preferences"""
        profile = self.user_profiles.find_one({"user_id": user_id})
        if profile:
            profile["_id"] = str(profile["_id"])
            return profile
        return {"user_id": user_id, "preferences": {}}
    
    # ============================================
    # CONVERSATION MEMORY WITH HISTORY
    # ============================================
    
    def save_conversation_memory(self, user_id: str, memory: Dict):
        """
        Save conversation memory with full history support.
        Allows tracking of "first search", "last search", etc.
        """
        # Get existing memory
        existing = self.conversation_memory.find_one({"user_id": user_id})
        
        if existing:
            # Move current last_search to history
            history = existing.get("search_history", [])
            if "last_search" in existing:
                history.append({
                    **existing["last_search"],
                    "searched_at": existing.get("updated_at", datetime.utcnow())
                })
            
            # Keep only last 10 searches in history
            history = history[-10:]
            
            self.conversation_memory.update_one(
                {"user_id": user_id},
                {"$set": {
                    "last_search": memory,
                    "search_history": history,
                    "updated_at": datetime.utcnow(),
                    "total_searches": existing.get("total_searches", 0) + 1
                }}
            )
        else:
            # First search
            self.conversation_memory.insert_one({
                "user_id": user_id,
                "last_search": memory,
                "search_history": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "total_searches": 1
            })
    
    def get_conversation_memory(self, user_id: str = "default") -> Dict:
        """Retrieve the last search context"""
        memory = self.conversation_memory.find_one({"user_id": user_id})
        if memory:
            return memory.get("last_search", {})
        return {}
    
    def get_search_by_index(self, user_id: str, index: int) -> Optional[Dict]:
        """
        Get a specific search from history by index.
        index = 0 means first search, -1 means last search
        """
        memory = self.conversation_memory.find_one({"user_id": user_id})
        if not memory:
            return None
        
        history = memory.get("search_history", [])
        total = len(history) + 1  # +1 for current last_search
        
        # Handle "first search"
        if index == 0 and history:
            return history[0]
        
        # Handle "last search"
        if index == -1:
            return memory.get("last_search")
        
        # Handle numeric index (1-based for user convenience)
        if 0 < index <= len(history):
            return history[index - 1]
        
        return None
    
    def get_search_history(self, user_id: str = "default", limit: int = 10) -> List[Dict]:
        """Get full search history for a user"""
        memory = self.conversation_memory.find_one({"user_id": user_id})
        if not memory:
            return []
        
        history = memory.get("search_history", [])
        if "last_search" in memory:
            history.append({
                **memory["last_search"],
                "searched_at": memory.get("updated_at")
            })
        
        return history[-limit:]  # Return most recent N searches
    
    def clear_conversation_memory(self, user_id: str = "default"):
        """Clear conversation memory for a user"""
        self.conversation_memory.delete_one({"user_id": user_id})
        print(f"✓ Cleared conversation memory for user: {user_id}")


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    # Example usage
    mongo = MongoDBTool()
    
    # 1. Save user currency preference
    mongo.save_user_currency("user123", "INR", "₹")
    
    # 2. Get user currency
    currency = mongo.get_user_currency("user123")
    print(f"User currency: {currency}")
    
    # 3. Cache search results
    search_criteria = {
        "location": "Noida",
        "bedrooms": "2",
        "max_price": 25000,
        "requirements": "pet friendly"
    }
    
    # First search - no cache
    cached = mongo.get_cached_search(search_criteria, max_results=5)
    print(f"First search cached result: {cached}")
    
    # Simulate saving properties
    properties = [{"address": f"Property {i}", "price": 20000} for i in range(5)]
    mongo.save_search_cache(search_criteria, properties)
    
    # Second search - should hit cache
    cached = mongo.get_cached_search(search_criteria, max_results=2)
    print(f"Second search (2 properties) cached result: {len(cached) if cached else 0}")
    
    # 4. Track search history
    memory = {
        "last_query": "2 bedroom apartment in Noida under 25000",
        "criteria": search_criteria,
        "property_count": 5
    }
    mongo.save_conversation_memory("user123", memory)
    
    # Get last search
    last = mongo.get_conversation_memory("user123")
    print(f"Last search: {last}")
    
    # Get search history
    history = mongo.get_search_history("user123")
    print(f"Search history: {len(history)} searches")