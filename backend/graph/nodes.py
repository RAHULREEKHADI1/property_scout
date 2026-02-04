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
from tools.currency_tool import detect_currency
from dotenv import load_dotenv
load_dotenv()

try:
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY") 
    )
except Exception as e:
    print(f"Warning: Could not initialize OpenAI: {e}")
    llm = None

mongo_tool = MongoDBTool()
cloudinary_tool = CloudinaryTool()

FRONTEND_URL = os.getenv("FRONTEND_URL")

def extract_criteria_simple(message: str) -> dict:
    """Regex-based fallback extraction — used only when the LLM call fails."""
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

    price_match = re.search(r'\$?([\d,]+)k?', message)
    if price_match:
        price = int(price_match.group(1).replace(',', ''))
        if price < 100:
            price = price * 1000
        criteria["max_price"] = price
    else:
        criteria["max_price"] = 2500

    if "studio" in message_lower:
        criteria["bedrooms"] = "1"
    elif re.search(r'\b2\b|two\s*bed', message_lower):
        criteria["bedrooms"] = "2"
    elif re.search(r'\b3\b|three\s*bed', message_lower):
        criteria["bedrooms"] = "3"
    else:
        criteria["bedrooms"] = "1"

    reqs = []
    if any(w in message_lower for w in ["pet", "dog", "cat"]):
        reqs.append("pet friendly")
    criteria["requirements"] = ", ".join(reqs) if reqs else "none"

    return criteria


def _validate_criteria(raw: dict, user_message: str) -> dict:
    """
    Post-process LLM output:
      • Ensure max_price is an int and is the EXACT number the user typed.
      • If the LLM invented or changed the price, override with regex extraction.
      • Fill in missing keys with safe defaults.
    """
    price_match = re.search(r'\$?([\d,]+)k?', user_message)
    if price_match:
        user_price = int(price_match.group(1).replace(',', ''))
        if user_price < 100:
            user_price = user_price * 1000
        raw["max_price"] = user_price         
    else:
        raw.setdefault("max_price", 2500)

    try:
        raw["max_price"] = int(raw["max_price"])
    except (TypeError, ValueError):
        raw["max_price"] = 2500

    raw.setdefault("location", "Not specified")
    raw.setdefault("bedrooms", "1")
    raw.setdefault("requirements", "none")
    return raw


def extract_max_results(message: str) -> int:
    """
    If the user asked for a specific number of properties (e.g. "show me 3",
    "I want 4 properties", "give me 5 listings") return that number.
    Otherwise default to 5.

    Only values 1-10 are honoured; anything outside that range is clamped.
    """
    patterns = [
        r'(?:show|give|find|get|list|return)\s+(?:me\s+)?(\d+)\s*(?:propert|apartment|listing|result|option)',
        r'(\d+)\s*(?:propert|apartment|listing|result|option)',
        r'(?:only|just|top|around|about)\s+(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            return max(1, min(n, 10))   
    return 5  


def scout_node(state: Dict) -> Dict:
    messages = state.get("messages", [])
    user_prefs = state.get("user_preferences", {})
    conversation_memory = state.get("conversation_memory", {})

    if messages:
        last_msg = messages[-1]
        last_message = (last_msg.get("content", "") if isinstance(last_msg, dict)
                        else getattr(last_msg, 'content', str(last_msg)))
    else:
        last_message = ""

    print(f"\n{'=' * 60}")
    print(f" SCOUT AGENT - Research Node")
    print(f"{'=' * 60}")
    print(f"User Query: {last_message}")
    print(f"User Preferences: {json.dumps(user_prefs)}")
    print(f"Conversation Memory: {json.dumps(conversation_memory)}")

    criteria = None
    if llm:
        try:
            # Enhanced prompt with memory context
            memory_context = ""
            if conversation_memory:
                memory_context = f"\n\nLast search context: {json.dumps(conversation_memory)}\nUse this to inform the current search if relevant."
            
            system_prompt = f"""You are a property-search assistant. Your ONLY job is to read the user's message and pull out their exact search criteria.

RULES (follow every one):
1. location   – the city or neighbourhood the user typed.  If none, use "Not specified".
2. max_price  – the EXACT dollar amount the user stated as their budget ceiling.
                DO NOT round, guess, or invent a number.  If the user wrote "$2 000" return 2000.
                If no price is mentioned, return 2500.
3. bedrooms   – the number of bedrooms requested (as a string).  Default "1".
4. requirements – any extras like "pet friendly", "parking", "gym", etc.  If none, "none".

User stored preferences (merge if relevant): {json.dumps(user_prefs)}{memory_context}

Return ONLY a single valid JSON object — no markdown, no explanation:
{{"location": "...", "max_price": <integer>, "bedrooms": "<string>", "requirements": "..."}}"""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=last_message)
            ])

            raw_text = response.content.strip()
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)

            criteria = json.loads(raw_text)
            criteria = _validate_criteria(criteria, last_message)
            print(f" ✓ AI extracted criteria: {criteria}")

        except Exception as e:
            print(f" LLM extraction failed: {e} → using simple extraction")
            criteria = extract_criteria_simple(last_message)
    else:
        criteria = extract_criteria_simple(last_message)

    query = (f"{criteria.get('bedrooms', '1')} bedroom apartment in "
             f"{criteria.get('location', 'Austin')} under {criteria.get('max_price', 2500)}")
    print(f"\n ✓ Search Query: {query}")

    wanted_count = extract_max_results(last_message)
    print(f" ✓ User requested up to {wanted_count} results")

    print(f"\n Step 1: Searching for properties…")
    properties = search_properties(query, max_price=criteria.get("max_price"), max_results=wanted_count, llm=llm)
    print(f" ✓ Found {len(properties)} properties from search")

    print(f"\n Step 2: Fetching detailed property information…")
    for idx, prop in enumerate(properties):
        if prop.get('url'):
            print(f"  Fetching details for property {idx + 1}: {prop.get('title', 'Unknown')}")
            try:
                fetch_property_details(prop['url'])
            except Exception as e:
                print(f"  Failed to fetch details: {e}")

    if llm and properties:
        print(f"\n Step 3: Cleaning titles & descriptions with LLM…")
        for idx, prop in enumerate(properties):
            try:
                clean_prompt = f"""You are a real-estate listing editor.  Given the raw data below, produce:
1. title        – A short (≤ 12 words), professional property title.
                  It MUST mention bedrooms and the city.  Example: "Spacious 2BR Apartment in Austin".
                  NEVER use generic phrases like "50 Results" or anything unrelated to real estate.
2. description  – A polished 2-3 sentence description suitable for a property listing.
                  Base it on the raw description if it contains useful info; otherwise compose a
                  realistic description for a {prop.get('bedrooms', 1)}-bedroom apartment in {criteria.get('location', 'Austin')}
                  priced at {prop.get('price', 0)}/month.
                  Do NOT include SEO spam, nav links, or unrelated content.

Raw input:
  title       : {prop.get('title', '')}
  description : {prop.get('description', '')}
  bedrooms    : {prop.get('bedrooms', 1)}
  bathrooms   : {prop.get('bathrooms', 1)}
  price       : {prop.get('price', 0)}/month
  location    : {criteria.get('location', 'Austin')}

Return ONLY valid JSON, no markdown:
{{"title": "...", "description": "..."}}"""

                resp = llm.invoke([
                    SystemMessage(content=clean_prompt),
                    HumanMessage(content="Clean this listing.")
                ])
                raw = resp.content.strip()
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
                cleaned = json.loads(raw)

                prop["title"] = cleaned.get("title", prop["title"])
                prop["description"] = cleaned.get("description", prop["description"])
                print(f"   [{idx + 1}] title   → {prop['title']}")
                print(f"   [{idx + 1}] desc    → {prop['description'][:80]}…")
            except Exception as e:
                print(f"   [{idx + 1}] LLM clean failed: {e} — keeping original")

    if user_prefs.get("has_pet"):
        print(f"\n Filtering for pet-friendly properties (user has pet)")
        properties = [p for p in properties if p.get("pet_friendly", False)]
        print(f" {len(properties)} pet-friendly properties remain")

    print(f"\n{'=' * 60}")
    print(f" SCOUT COMPLETE – {len(properties)} properties → Inspector")
    print(f"{'=' * 60}\n")

    return {
        **state,
        "properties": properties,
        "current_step": "scout_complete",
        "search_criteria": criteria  # Save for memory
    }



async def inspector_node(state: Dict) -> Dict:
    properties = state.get("properties", [])
    screenshots = []

    print(f"\n{'=' * 60}")
    print(f" INSPECTOR AGENT - Computer Use Node")
    print(f"{'=' * 60}")
    print(f"Properties to verify: {len(properties)}")

    if not properties:
        print(" No properties to verify. Skipping inspector node.")
        return {**state, "screenshots": screenshots, "current_step": "inspector_complete"}

    browser = BrowserTool()
    try:
        print("\n Starting browser automation…")
        await browser.start(headless=True)
        print("Browser launched successfully")

        for idx, prop in enumerate(properties):
            try:
                address = prop['address']
                print(f"\n{'─' * 50}")
                print(f" Property {idx + 1}/{len(properties)}")
                print(f"   Address: {address}")
                print(f"{'─' * 50}")

                print("  Step 1: Navigating to map simulator…")
                await browser.navigate(f"{FRONTEND_URL}/map-simulator")
                print("   Map simulator loaded")

                print(f"  Step 2: Entering address: {address}")
                success = await browser.type_text("#address-input", address)
                if not success:
                    print("   Failed to find address input field")
                    continue
                print("   Address entered")

                print("  Step 3: Clicking search button…")
                success = await browser.click("#search-button")
                if not success:
                    print("   Failed to find search button")
                    continue
                print("   Search button clicked")

                print("  Step 4: Waiting for map to load…")
                import asyncio
                await asyncio.sleep(2)
                print("   Map loaded")

                print("  Step 5: Capturing screenshot…")
                screenshot_path = f"data/screenshots/property_{idx + 1}_{address.replace(' ', '_').replace(',', '')[:30]}.png"
                os.makedirs("data/screenshots", exist_ok=True)

                success = await browser.screenshot(screenshot_path)
                if success:
                    print(f"   Screenshot saved locally: {screenshot_path}")

                    print("  Step 6: Uploading to Cloudinary…")
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

    print(f"\n{'=' * 60}")
    print(f" INSPECTOR COMPLETE – {len([s for s in screenshots if s])} screenshots captured")
    print(f"{'=' * 60}\n")

    return {
        **state,
        "screenshots": screenshots,
        "current_step": "inspector_complete"
    }



def broker_node(state: Dict) -> Dict:
    """
    BROKER AGENT – File Creation Node
    • Creates per-property folders under data/listings/
    • Moves screenshots into each folder
    • Uses the LLM to write a professional description AND
      a detailed, property-specific draft lease for every listing.
    """
    properties = state.get("properties", [])
    screenshots = state.get("screenshots", [])
    folders = []
    cur_symbol = state.get("currency_symbol", "$") 

    print(f"\n{'=' * 60}")
    print(f"📄 BROKER AGENT – File Creation Node")
    print(f"{'=' * 60}")
    print(f"Properties to process: {len(properties)}")
    print(f"Screenshots available: {len([s for s in screenshots if s])}")

    base_path = "data/listings"
    os.makedirs(base_path, exist_ok=True)

    for idx, prop in enumerate(properties):
        try:
            address = prop['address']
            print(f"\n{'─' * 50}")
            print(f"📁 Creating dossier for property {idx + 1}/{len(properties)}")
            print(f"   Address: {address}")
            print(f"{'─' * 50}")

            address_clean = re.sub(r'[^\w\s-]', '', address)
            address_clean = re.sub(r'[\s]+', '_', address_clean)
            folder_name = f"{address_clean}_{idx}"
            folder_path = os.path.join(base_path, folder_name)

            print(f"  Step 1: Creating folder…")
            create_directory(folder_path)
            print(f"   Folder created: {folder_name}")

            if idx < len(screenshots) and screenshots[idx] and os.path.exists(screenshots[idx]):
                new_screenshot_path = os.path.join(folder_path, "street_view.png")
                print(f"  Step 2: Moving screenshot…")
                move_file(screenshots[idx], new_screenshot_path)
                if os.path.exists(new_screenshot_path):
                    print(f"   Screenshot moved ({os.path.getsize(new_screenshot_path)} bytes)")
                else:
                    print(f"   Screenshot move failed")
            else:
                print(f"   No screenshot available for property {idx + 1}")

            professional_description = prop.get("description", "")
            lease_terms = _default_lease_terms(prop, cur_symbol)

            if llm:
                try:
                    print(f"  Step 3a: Generating professional description via LLM…")
                    desc_prompt = f"""Write a professional, engaging 3-4 sentence property listing description for:

Address  : {prop['address']}
Price    : {cur_symbol}{prop['price']}/month
Bedrooms : {prop['bedrooms']}
Bathrooms: {prop['bathrooms']}
Pet Policy: {'Pets Allowed' if prop.get('pet_friendly') else 'No Pets'}
Existing notes: {prop.get('description', 'none')}

Highlight lifestyle benefits, neighbourhood feel, and key amenities.
Do NOT make up specific amenity names (e.g. "The Sunrise Pool") unless they were in the existing notes.
Return ONLY the description text — no JSON, no title, no extra commentary."""

                    desc_resp = llm.invoke([
                        SystemMessage(content=desc_prompt),
                        HumanMessage(content="Write the listing description.")
                    ])
                    professional_description = desc_resp.content.strip()
                    print(f"   Description generated ({len(professional_description)} chars)")

                except Exception as e:
                    print(f"   Description LLM call failed: {e} — using existing")

                try:
                    print(f"  Step 3b: Generating detailed lease draft via LLM…")
                    lease_prompt = f"""Draft a detailed but realistic DRAFT lease agreement for the following rental property.
Include standard clauses that a real residential lease would have.
Make it property-specific — weave in the actual address, rent, bedrooms, and pet policy.

Property details:
  Address       : {prop['address']}
  Monthly Rent  : {cur_symbol}{prop['price']}
  Bedrooms      : {prop['bedrooms']}
  Bathrooms     : {prop['bathrooms']}
  Pet Policy    : {'Pets Allowed' if prop.get('pet_friendly') else 'No Pets'}

Include these sections (write in plain prose, NOT bullet points):
  1. Parties & Property
  2. Lease Term & Rent
  3. Security Deposit
  4. Tenant Obligations
  5. Landlord Responsibilities
  6. Pet Policy (expand if pets allowed — fees, rules)
  7. Termination & Notice
  8. General Conditions

End with a clear disclaimer that this is a NON-BINDING auto-generated draft.
Return ONLY the lease text — no JSON wrapper."""

                    lease_resp = llm.invoke([
                        SystemMessage(content=lease_prompt),
                        HumanMessage(content="Write the draft lease.")
                    ])
                    lease_terms = lease_resp.content.strip()
                    print(f"   Lease draft generated ({len(lease_terms)} chars)")

                except Exception as e:
                    print(f"   Lease LLM call failed: {e} — using template")

            print(f"  Step 4: Writing lease_draft.txt…")
            lease_content = f"""═══════════════════════════════════════════════════════════
                    DRAFT LEASE AGREEMENT
═══════════════════════════════════════════════════════════

Property Address : {prop['address']}
Monthly Rent     : {cur_symbol}{prop['price']}
Bedrooms         : {prop['bedrooms']}
Bathrooms        : {prop['bathrooms']}
Pet Policy       : {'Pets Allowed' if prop.get('pet_friendly') else 'No Pets'}

───────────────────────────────────────────────────────────

{lease_terms}

═══════════════════════════════════════════════════════════
⚠  IMPORTANT NOTICE
═══════════════════════════════════════════════════════════

This is an automatically generated DRAFT lease agreement.
This document is NOT legally binding.

Please consult with:
  • A licensed real estate attorney
  • The property owner / landlord
  • Your local housing authority

before signing any legally binding lease agreement.

═══════════════════════════════════════════════════════════
Generated by Estate-Scout AI Agent
═══════════════════════════════════════════════════════════
"""
            lease_path = os.path.join(folder_path, "lease_draft.txt")
            write_file(lease_path, lease_content)
            print(f"   lease_draft.txt written")

            print(f"  Step 5: Writing info.txt…")
            info_content = f"""═══════════════════════════════════════════════════════════
                    PROPERTY INFORMATION
═══════════════════════════════════════════════════════════

Title       : {prop['title']}
Price       : {cur_symbol}{prop['price']}/month
Address     : {prop['address']}

Specifications:
  • Bedrooms  : {prop['bedrooms']}
  • Bathrooms : {prop['bathrooms']}
  • Pet Policy: {'✓ Pets Allowed' if prop.get('pet_friendly') else '✗ No Pets'}

───────────────────────────────────────────────────────────
Description
───────────────────────────────────────────────────────────

{professional_description}

{'Source URL: ' + prop.get('url', '') if prop.get('url') else ''}

═══════════════════════════════════════════════════════════
Files in this dossier
═══════════════════════════════════════════════════════════

  1. street_view.png   – Map / street-view screenshot
  2. lease_draft.txt   – Draft lease agreement
  3. info.txt          – This file (property information)

═══════════════════════════════════════════════════════════
Generated by Estate-Scout AI Agent
═══════════════════════════════════════════════════════════
"""
            info_path = os.path.join(folder_path, "info.txt")
            write_file(info_path, info_content)
            print(f"   info.txt written")

            relative_folder = os.path.join("data", "listings", folder_name)
            folders.append(relative_folder)
            print(f"   ✓ Complete dossier: {relative_folder}")

        except Exception as e:
            print(f"   Error creating dossier for property {idx + 1}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'=' * 60}")
    print(f" BROKER COMPLETE – {len(folders)} dossiers created")
    print(f"{'=' * 60}\n")

    return {
        **state,
        "folders_created": folders,
        "current_step": "broker_complete"
    }


def _default_lease_terms(prop: dict, cur_symbol: str = "$") -> str:
    """Static fallback lease when LLM is unavailable."""
    pet_clause = (
        f"Pets are permitted subject to a one-time pet deposit of {cur_symbol}500 and a "
        f"monthly pet fee of {cur_symbol}50.  Tenant must provide proof of renter's "
        "insurance that covers pet liability."
        if prop.get("pet_friendly") else
        "No pets of any kind are permitted on the premises without prior "
        "written consent from the Landlord."
    )
    return f"""1. PARTIES & PROPERTY
This Draft Lease Agreement ("Agreement") is entered into between the Landlord and the Tenant (details to be finalised at signing) for the residential property located at {prop['address']}.

2. LEASE TERM & RENT
The lease term shall be twelve (12) months commencing on a date mutually agreed upon.  The monthly rent is {cur_symbol}{prop['price']}, payable on or before the 1st of each calendar month.  Late payments beyond a grace period of five (5) days will incur a late fee of 5 % of the monthly rent.

3. SECURITY DEPOSIT
A security deposit equal to one (1) month's rent ({cur_symbol}{prop['price']}) is due prior to move-in.  The deposit will be returned within 30 days of vacating, less any deductions for damages beyond normal wear and tear.

4. TENANT OBLIGATIONS
The Tenant is responsible for keeping the property clean and in good repair, paying all utilities unless otherwise agreed, and complying with all local housing and health codes.

5. LANDLORD RESPONSIBILITIES
The Landlord shall maintain the structural integrity of the building, ensure functioning heating/cooling systems, and address any emergency repairs within 24 hours of written notice.

6. PET POLICY
{pet_clause}

7. TERMINATION & NOTICE
Either party may terminate this Agreement by providing at least 30 days' written notice before the end of the lease term.  Early termination by the Tenant is subject to a fee equal to two (2) months' rent.

8. GENERAL CONDITIONS
This Agreement shall be governed by the laws of the state in which the property is located.  Any disputes shall first be attempted through mediation before legal action is pursued."""


def crm_node(state: Dict) -> Dict:
    properties = state.get("properties", [])
    folders = state.get("folders_created", [])
    messages = state.get("messages", [])

    if messages:
        last_msg = messages[-1]
        last_message = (last_msg.get("content", "") if isinstance(last_msg, dict)
                        else getattr(last_msg, 'content', str(last_msg)))
    else:
        last_message = ""

    print(f"\n{'=' * 60}")
    print(f" CRM AGENT – Persistence & Learning Node")
    print(f"{'=' * 60}")
    print(f"Properties to save: {len(properties)}")

    user_prefs = state.get("user_preferences", {})

    print(f"\n Step 1: Learning from user conversation…")
    preference_updated = False
    
    # Learn pet preferences
    if any(w in last_message.lower() for w in ("dog", "cat", "pet")):
        user_prefs["has_pet"] = True
        preference_updated = True
        print(f"   ✓ Learned: User has pets")
    
    # Learn location preferences
    search_criteria = state.get("search_criteria", {})
    if search_criteria.get("location") and search_criteria["location"] != "Not specified":
        if "preferred_locations" not in user_prefs:
            user_prefs["preferred_locations"] = []
        if search_criteria["location"] not in user_prefs["preferred_locations"]:
            user_prefs["preferred_locations"].append(search_criteria["location"])
            preference_updated = True
            print(f"   ✓ Learned: User interested in {search_criteria['location']}")
    
    # Learn budget range
    if search_criteria.get("max_price"):
        if "budget_history" not in user_prefs:
            user_prefs["budget_history"] = []
        user_prefs["budget_history"].append(search_criteria["max_price"])
        if len(user_prefs["budget_history"]) > 5:
            user_prefs["budget_history"] = user_prefs["budget_history"][-5:]  # Keep last 5
        avg_budget = sum(user_prefs["budget_history"]) // len(user_prefs["budget_history"])
        user_prefs["typical_budget"] = avg_budget
        preference_updated = True
        print(f"   ✓ Learned: User's typical budget ~{avg_budget}")
    
    # Learn bedroom preferences
    if search_criteria.get("bedrooms"):
        if "preferred_bedrooms" not in user_prefs:
            user_prefs["preferred_bedrooms"] = []
        if search_criteria["bedrooms"] not in user_prefs["preferred_bedrooms"]:
            user_prefs["preferred_bedrooms"].append(search_criteria["bedrooms"])
            preference_updated = True
            print(f"   ✓ Learned: User interested in {search_criteria['bedrooms']} bedroom properties")

    if preference_updated:
        try:
            mongo_tool.update_user_preference("default", user_prefs)
            print(f"   ✓ Preferences updated in database")
        except Exception as e:
            print(f"   ✗ Error updating preferences: {e}")
    else:
        print(f"   No new preferences detected this session")

    print(f"\n Step 2: Saving properties to database…")
    saved_count = 0
    cur_symbol = state.get("currency_symbol", "$")
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
            print(f"   ✓ Property {idx + 1} saved – {prop['address']}  |  {cur_symbol}{prop['price']}")

        except Exception as e:
            print(f"   ✗ Error saving property {idx + 1}: {e}")
            continue

    print(f"\n{'=' * 60}")
    print(f" CRM COMPLETE – {saved_count}/{len(properties)} saved")
    print(f" User preferences learned and stored for future queries")
    print(f"{'=' * 60}\n")

    return {
        **state,
        "user_preferences": user_prefs,
        "current_step": "crm_complete"
    }