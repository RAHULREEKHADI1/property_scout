from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict
import os
import sys
import traceback
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import run_agent
from tools.mongo_tool import MongoDBTool

load_dotenv()

app = FastAPI(title="Estate-Scout API")
FRONTEND_URL = os.getenv("FRONTEND_URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("./data/listings", exist_ok=True)
app.mount("/data", StaticFiles(directory="./data"), name="data")

mongo_tool = MongoDBTool()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    properties: List[Dict]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print(f"Received message: {request.message}")
        result = await run_agent(request.message)
        print(f"Agent result: {result}")
        return ChatResponse(
            response=result["response"],
            properties=result["properties"]
        )
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        traceback.print_exc()
        
        error_msg = str(e)
        if "401" in error_msg or "API key" in error_msg or "Unauthorized" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Invalid OpenAI API key. Please check your .env file and ensure OPENAI_API_KEY is set correctly."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")

@app.get("/api/listings")
async def get_listings():
    try:
        listings = mongo_tool.get_all_listings()
        
        for listing in listings:
            if listing.get("screenshot_path") and not listing.get("image_url"):
                listing["image_url"] = f"{FRONTEND_URL}/{listing['screenshot_path']}"
        
        return {"listings": listings}
    except Exception as e:
        print(f"Error getting listings: {e}")
        return {"listings": []}

@app.get("/api/preferences")
async def get_preferences():
    try:
        prefs = mongo_tool.get_user_preferences("default")
        return prefs
    except Exception as e:
        print(f"Error getting preferences: {e}")
        return {"user_id": "default", "preferences": {}}

@app.get("/health")
async def health():
    api_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    mongo_uri = os.getenv("MONGODB_URI")
    
    status = {
        "status": "healthy",
        "openai_configured": bool(api_key and api_key != "your_openai_api_key_here"),
        "tavily_configured": bool(tavily_key and tavily_key != "your_tavily_api_key_here"),
        "mongodb_configured": bool(mongo_uri)
    }
    return status

if __name__ == "__main__":
    import uvicorn
    
    api_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    mongo_uri = os.getenv("MONGODB_URI")
    
    print("\n" + "="*60)
    print("Estate-Scout Backend Starting...")
    print("="*60)
    
    missing_keys = []
    
    if not api_key or api_key == "your_openai_api_key_here":
        missing_keys.append("OPENAI_API_KEY")
        print("OpenAI API key not configured!")
    else:
        print("OpenAI API key configured")
    
    if not tavily_key or tavily_key == "your_tavily_api_key_here":
        missing_keys.append("TAVILY_API_KEY")
        print("Tavily API key not configured!")
    else:
        print("Tavily API key configured")
    
    if not mongo_uri:
        print("WARNING: MongoDB URI not configured!")
        print("   Set MONGODB_URI in backend/.env file")
    else:
        print("MongoDB URI configured")
    
    if missing_keys:
        print("\n" + "="*60)
        print("CRITICAL: Missing required API keys!")
        print("="*60)
        print(f"Missing: {', '.join(missing_keys)}")
        print("\nPlease set these in your backend/.env file:")
        for key in missing_keys:
            print(f"  {key}=your_actual_key_here")
        print("\nThe application will start but may not function correctly.")
        print("="*60 + "\n")
    else:
        print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
