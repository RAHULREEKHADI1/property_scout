from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
import re
from tools.search_tool import search_properties, fetch_property_details
from tools.browser_tool import BrowserTool
from tools.bash_tool import create_directory, write_file, move_file
from tools.mongo_tool import MongoDBTool
from tools.cloudinary_tool import CloudinaryTool

try:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, model_kwargs={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")})
except Exception as e:
    print(f"Warning: Could not initialize OpenAI: {e}")
    llm = None

mongo_tool = MongoDBTool()
cloudinary_tool = CloudinaryTool()

FRONTEND_URL = os.getenv("FRONTEND_URL")

def extract_criteria_simple(message: str) -> dict:
    """Extract search criteria with intelligent location detection"""
    message_lower = message.lower()
    criteria = {}
    
    location_patterns = [
        r'in\s+([A-Za-z\s]+?)(?:\s+under|\s+apartment|\s+for|\s*,|$)',
        r'at\s+([A-Za-z\s]+?)(?:\s+under|\s+apartment|\s+for|\s*,|$)',
        r'near\s+([A-Za-z\s]+?)(?:\s+under|\s+apartment|\s+for|\s*,|$)',
    ]
    
    location = None
    for pattern in location_patterns:
        match = re.search(pattern, message_lower)
        if match:
            location = match.group(1).strip()
            location = re.sub(r'\s+(under|apartment|for|the)\s*$', '', location).strip()
            break
    
    if not location:
        cities = ["brooklyn", "austin", "zurich", "switzerland", "london", 
                  "paris", "tokyo", "berlin", "madrid", "rome", "boston",
                  "seattle", "chicago", "miami", "denver", "new york",
                  "san francisco", "los angeles", "toronto", "vancouver"]
        for city in cities:
            if city in message_lower:
                location = city.title()
                break
    
    criteria["location"] = location if location else "Not specified"
    
    price_match = re.search(r'\$?(\d+)k?', message)
    if price_match:
        price = int(price_match.group(1))
        if price < 100:
            price = price * 1000
        criteria["max_price"] = price
    else:
        criteria["max_price"] = 2500
    
    if "studio" in message_lower or "1" in message_lower:
        criteria["bedrooms"] = "1"
    elif "2" in message_lower:
        criteria["bedrooms"] = "2"
    elif "3" in message_lower:
        criteria["bedrooms"] = "3"
    else:
        criteria["bedrooms"] = "1"
    
    return criteria

def scout_node(state: Dict) -> Dict:

    messages = state.get("messages", [])
    user_prefs = state.get("user_preferences", {})
    
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            last_message = last_msg.get("content", "")
        else:
            last_message = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    else:
        last_message = ""
    
    print(f"\n{'='*60}")
    print(f" SCOUT AGENT - Research Node")
    print(f"{'='*60}")
    print(f"User Query: {last_message}")
    print(f"User Preferences: {json.dumps(user_prefs)}")
    
    if llm:
        try:
            system_prompt = f"""You are a property scout. Extract search criteria from the user's message.
User preferences: {json.dumps(user_prefs)}

Analyze the message and extract:
- Location (city/neighborhood) - extract ANY location mentioned, not just Austin or Brooklyn
- Max price
- Bedrooms
- Any special requirements (pet friendly, etc.)

Return ONLY a JSON object with these fields: {{"location": "...", "max_price": ..., "bedrooms": "...", "requirements": "..."}}"""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=last_message)
            ])
            
            criteria = json.loads(response.content)
            print(f" AI extracted criteria: {criteria}")
        except Exception as e:
            print(f" LLM extraction failed: {e}, using simple extraction")
            criteria = extract_criteria_simple(last_message)
    else:
        criteria = extract_criteria_simple(last_message)
    
    query = f"{criteria.get('bedrooms', '1')} bedroom apartment in {criteria.get('location', 'Austin')} under ${criteria.get('max_price', 2500)}"
    print(f"\n Search Query: {query}")
    
    print(f"\n Step 1: Searching for properties...")
    properties = search_properties(query)
    print(f" Found {len(properties)} properties from search")
    
    print(f"\n Step 2: Fetching detailed property information...")
    for idx, prop in enumerate(properties):
        if prop.get('url'):
            print(f"  Fetching details for property {idx + 1}: {prop.get('title', 'Unknown')}")
            try:
                details = fetch_property_details(prop['url'])
                if details.get('success'):
                    print(f"   Successfully fetched additional details")
            except Exception as e:
                print(f"  Failed to fetch details: {e}")
    
    if user_prefs.get("has_pet"):
        print(f"\n Filtering for pet-friendly properties (user has pet)")
        properties = [p for p in properties if p.get("pet_friendly", False)]
        print(f" {len(properties)} pet-friendly properties remain")
    
    print(f"\n{'='*60}")
    print(f" SCOUT COMPLETE - Passing {len(properties)} properties to Inspector")
    print(f"{'='*60}\n")
    
    return {
        **state,
        "properties": properties,
        "current_step": "scout_complete"
    }

async def inspector_node(state: Dict) -> Dict:

    properties = state.get("properties", [])
    screenshots = []

    print(f"\n{'='*60}")
    print(f" INSPECTOR AGENT - Computer Use Node")
    print(f"{'='*60}")
    print(f"Properties to verify: {len(properties)}")

    if not properties:
        print(" No properties to verify. Skipping inspector node.")
        return {**state, "screenshots": screenshots, "current_step": "inspector_complete"}

    browser = BrowserTool()
    try:
        print("\n Starting browser automation...")
        await browser.start(headless=True)
        print("Browser launched successfully")

        for idx, prop in enumerate(properties):
            try:
                address = prop['address']
                print(f"\n{'─'*50}")
                print(f" Property {idx + 1}/{len(properties)}")
                print(f"   Address: {address}")
                print(f"{'─'*50}")
                
                print("  Step 1: Navigating to map simulator...")
                await browser.navigate(f"{FRONTEND_URL}/map-simulator")
                print("   Map simulator loaded")

                print(f"  Step 2: Entering address: {address}")
                success = await browser.type_text("#address-input", address)
                if not success:
                    print("   Failed to find address input field")
                    continue
                print("   Address entered")

                print("  Step 3: Clicking search button...")
                success = await browser.click("#search-button")
                if not success:
                    print("   Failed to find search button")
                    continue
                print("   Search button clicked")

                print("  Step 4: Waiting for map to load...")
                import asyncio
                await asyncio.sleep(2) 
                print("   Map loaded")

                print("  Step 5: Capturing screenshot...")
                screenshot_path = f"data/screenshots/property_{idx + 1}_{address.replace(' ', '_').replace(',', '')[:30]}.png"
                os.makedirs("data/screenshots", exist_ok=True)
                
                success = await browser.screenshot(screenshot_path)
                if success:
                    print(f"   Screenshot saved locally: {screenshot_path}")
                    
                    print("  Step 6: Uploading to Cloudinary...")
                    public_id = f"property_{idx + 1}_{prop.get('id', idx)}"
                    cloudinary_result = cloudinary_tool.upload_image(
                        screenshot_path,
                        folder="estate_scout/properties",
                        public_id=public_id
                    )
                    
                    if cloudinary_result["success"]:
                        print(f"   Uploaded to Cloudinary: {cloudinary_result['url']}")
                        prop["cloudinary_url"] = cloudinary_result["url"]
                        prop["cloudinary_public_id"] = cloudinary_result["public_id"]
                        screenshots.append(cloudinary_result["url"])
                    else:
                        print(f"   Cloudinary upload failed, using local path")
                        screenshots.append(screenshot_path)
                else:
                    print(f"   Failed to save screenshot")
                    screenshots.append(None)
                
            except Exception as e:
                print(f"   Error processing property {idx + 1}: {e}")
                screenshots.append(None)
                continue

        await browser.close()
        print("\n Browser closed")

    except Exception as e:
        print(f" Browser automation error: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")
    print(f" INSPECTOR COMPLETE - {len([s for s in screenshots if s])} screenshots captured")
    print(f"{'='*60}\n")

    return {
        **state,
        "screenshots": screenshots,
        "current_step": "inspector_complete"
    }

def broker_node(state: Dict) -> Dict:
    """
    BROKER AGENT - File Creation Node
    Role: Organize property data and create comprehensive dossiers
    Tools: Bash Tool (mkdir, mv, write files)
    Task: Create folders, move screenshots, generate lease drafts and info files
    """
    properties = state.get("properties", [])
    screenshots = state.get("screenshots", [])
    folders = []
    
    print(f"\n{'='*60}")
    print(f"📄 BROKER AGENT - File Creation Node")
    print(f"{'='*60}")
    print(f"Properties to process: {len(properties)}")
    print(f"Screenshots available: {len([s for s in screenshots if s])}")
    
    base_path = "data/listings"
    os.makedirs(base_path, exist_ok=True)
    
    for idx, prop in enumerate(properties):
        try:
            address = prop['address']
            print(f"\n{'─'*50}")
            print(f"📁 Creating dossier for property {idx + 1}/{len(properties)}")
            print(f"   Address: {address}")
            print(f"{'─'*50}")
            
            address_clean = re.sub(r'[^\w\s-]', '', address)
            address_clean = re.sub(r'[\s]+', '_', address_clean)
            folder_name = f"{address_clean}_{idx}"
            folder_path = os.path.join(base_path, folder_name)
            
            print(f"  Step 1: Creating folder...")
            print(f"  mkdir -p {folder_path}")
            create_directory(folder_path)
            print(f"   Folder created: {folder_name}")
            
            if idx < len(screenshots) and screenshots[idx] and os.path.exists(screenshots[idx]):
                new_screenshot_path = os.path.join(folder_path, "street_view.png")
                print(f"  Step 2: Moving screenshot...")
                print(f"  mv {screenshots[idx]} → {new_screenshot_path}")
                move_file(screenshots[idx], new_screenshot_path)
                
                if os.path.exists(new_screenshot_path):
                    file_size = os.path.getsize(new_screenshot_path)
                    print(f"   Screenshot moved successfully ({file_size} bytes)")
                else:
                    print(f"   Screenshot move failed")
            else:
                print(f"   No screenshot available for property {idx + 1}")
            
            print(f"  Step 3: Generating lease agreement...")
            lease_content = f"""═══════════════════════════════════════════════════════════
                    DRAFT LEASE AGREEMENT
═══════════════════════════════════════════════════════════

Property Address: {prop['address']}
Monthly Rent: ${prop['price']}
Bedrooms: {prop['bedrooms']}
Bathrooms: {prop['bathrooms']}
Pet Policy: {'Pets Allowed' if prop.get('pet_friendly') else 'No Pets'}

Property Description:
{prop['description']}

───────────────────────────────────────────────────────────
TERMS AND CONDITIONS
───────────────────────────────────────────────────────────

1. Lease Term: 12 months
2. Security Deposit: ${prop['price']}
3. Move-in Date: [To be determined]
4. Tenant Responsibilities: Utilities, maintenance, property care

═══════════════════════════════════════════════════════════
IMPORTANT NOTICE
═══════════════════════════════════════════════════════════

This is an automatically generated DRAFT lease agreement.
This document is NOT legally binding.

Please consult with:
- A licensed real estate attorney
- The property owner/landlord
- Local housing authorities

Before signing any legally binding lease agreement.

═══════════════════════════════════════════════════════════
Generated by Estate-Scout AI Agent
═══════════════════════════════════════════════════════════
"""
            
            lease_path = os.path.join(folder_path, "lease_draft.txt")
            write_file(lease_path, lease_content)
            print(f"   Lease draft created")
            
            print(f"  Step 4: Generating property info file...")
            info_content = f"""═══════════════════════════════════════════════════════════
                    PROPERTY INFORMATION
═══════════════════════════════════════════════════════════

Title: {prop['title']}
Price: ${prop['price']}/month
Address: {prop['address']}

Specifications:
• Bedrooms: {prop['bedrooms']}
• Bathrooms: {prop['bathrooms']}
• Pet Policy: {'✓ Pets Allowed' if prop.get('pet_friendly') else '✗ No Pets'}

Description:
{prop['description']}

{'URL: ' + prop.get('url', 'N/A') if prop.get('url') else ''}

═══════════════════════════════════════════════════════════
Files in this folder:
═══════════════════════════════════════════════════════════

1. street_view.png - Screenshot of property location
2. lease_draft.txt - Draft lease agreement
3. info.txt - This file (property information)

═══════════════════════════════════════════════════════════
Generated by Estate-Scout AI Agent
═══════════════════════════════════════════════════════════
"""
            
            info_path = os.path.join(folder_path, "info.txt")
            write_file(info_path, info_content)
            print(f"   Property info created")
            
            relative_folder = os.path.join("data", "listings", folder_name)
            folders.append(relative_folder)
            
            print(f"   Complete dossier created: {relative_folder}")
            
        except Exception as e:
            print(f"   Error creating folder for property {idx + 1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print(f" BROKER COMPLETE - {len(folders)} property dossiers created")
    print(f"{'='*60}\n")
    
    return {
        **state,
        "folders_created": folders,
        "current_step": "broker_complete"
    }

def crm_node(state: Dict) -> Dict:
    properties = state.get("properties", [])
    folders = state.get("folders_created", [])
    messages = state.get("messages", [])
    
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            last_message = last_msg.get("content", "")
        else:
            last_message = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    else:
        last_message = ""
    
    print(f"\n{'='*60}")
    print(f" CRM AGENT - Persistence Node")
    print(f"{'='*60}")
    print(f"Properties to save: {len(properties)}")
    
    user_prefs = state.get("user_preferences", {})
    
    print(f"\n Step 1: Analyzing user preferences...")
    preference_updated = False
    
    if "dog" in last_message.lower() or "cat" in last_message.lower() or "pet" in last_message.lower():
        user_prefs["has_pet"] = True
        preference_updated = True
        print(f"   Detected: User has pets")
    
    if preference_updated:
        try:
            mongo_tool.update_user_preference("default", user_prefs)
            print(f"   User preferences updated in database")
        except Exception as e:
            print(f"   Error updating preferences: {e}")
    else:
        print(f"   No new preferences detected")
    
    print(f"\n Step 2: Saving properties to database...")
    saved_count = 0
    
    for idx, prop in enumerate(properties):
        try:
            folder_path = folders[idx] if idx < len(folders) else ""
            
            if prop.get("cloudinary_url"):
                image_url = prop["cloudinary_url"]
                print(f"   Using Cloudinary URL: {image_url}")
            else:
                screenshot_path = f"{folder_path}/street_view.png" if folder_path else ""
                image_url = f"{FRONTEND_URL}/{screenshot_path}" if screenshot_path else None
                print(f"   Using local URL: {image_url}")
            
            listing_data = {
                **prop,
                "folder_path": folder_path,
                "screenshot_path": f"{folder_path}/street_view.png" if folder_path else "",
                "image_url": image_url,
                "cloudinary_url": prop.get("cloudinary_url"),
                "cloudinary_public_id": prop.get("cloudinary_public_id"),
                "lease_path": f"{folder_path}/lease_draft.txt" if folder_path else "",
                "info_path": f"{folder_path}/info.txt" if folder_path else ""
            }
            
            mongo_tool.insert_listing(listing_data)
            saved_count += 1
            print(f"   Property {idx + 1} saved to listings collection")
            print(f"     Address: {prop['address']}")
            print(f"     Image URL: {image_url}")
            
        except Exception as e:
            print(f"   Error saving property {idx + 1}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f" CRM COMPLETE - {saved_count}/{len(properties)} properties saved")
    print(f"{'='*60}\n")
    
    return {
        **state,
        "user_preferences": user_prefs,
        "current_step": "crm_complete"
    }