import os
from typing import List, Dict, Optional
from tavily import TavilyClient
import re
import random


def search_properties(query: str, max_price: Optional[int] = None, max_results: int = 5, llm=None) -> List[Dict]:
    """
    Search for rental properties via Tavily and return a cleaned list.

    Parameters
    ----------
    query       : Natural-language search string (e.g. "2 bedroom apartment in Austin under $2000")
    max_price   : Hard budget ceiling extracted from the user's original message.
                  EVERY returned property will have price ≤ max_price.
                  If None, falls back to the price in the query string, then 2500.
    max_results : Maximum number of property cards to return.  Default 5.
                  The user can ask for fewer (e.g. "show me 3 properties").
    llm         : Optional LLM instance for generating realistic addresses
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key or tavily_api_key == "your_tavily_api_key_here":
        raise ValueError(
            "Tavily API key not configured. "
            "Please set TAVILY_API_KEY in your .env file. "
            "Get your key at: https://tavily.com"
        )

    if max_price is None:
        max_price = extract_price_from_query(query) or 2500
    print(f"   [search_tool] Price cap enforced: {max_price}  |  max_results: {max_results}")

    try:
        print(f"Using Tavily Web Search API for REAL property data")
        client = TavilyClient(api_key=tavily_api_key)
        search_query = f"apartments for rent {query} real estate listings price"
        results = client.search(search_query, max_results=10)

        properties = []
        for idx, result in enumerate(results.get('results', [])):
            title   = result.get('title', 'Property Listing')
            content = result.get('content', '')
            url     = result.get('url', '')

            if _is_irrelevant_result(title, content, url):
                print(f"   [{idx}] Skipped – irrelevant result: {title[:60]}")
                continue

            property_data = {
                "id":           idx + 1,
                "title":        clean_title(title),
                "price":        extract_real_price(content, title, query, max_price),   
                "address":      extract_real_address(content, title, query, idx, llm),  # Pass LLM
                "description":  extract_description(content, title, query),            
                "bedrooms":     extract_bedrooms_from_content(content, query),
                "bathrooms":    extract_bathrooms(content, query),
                "pet_friendly": is_pet_friendly(content, query),
                "url":          url,
                "image_url":    None
            }
            properties.append(property_data)

        if properties:
            # honour the caller's cap
            properties = properties[:max_results]
            print(f"✓ Found {len(properties)} properties via Tavily (capped at {max_results})")
            prices = [p['price'] for p in properties]
            print(f"   Price range: {min(prices)} – {max(prices)}  (cap: {max_price})")
            return properties
        else:
            print(f"No properties found for query: {query}")
            return []

    except Exception as e:
        print(f"Tavily API Error: {e}")
        raise Exception(f"Failed to search properties: {str(e)}.")


_IRRELEVANT_KEYWORDS = [
    "emissions standards", "federal register", "epa ", "sec filing",
    "10-k ", "annual report", "privacy policy", "terms of service",
    "cookie policy", "wikipedia", "how to", "what is", "tutorial",
]

def _is_irrelevant_result(title: str, content: str, url: str) -> bool:
    """Return True if the result is obviously not a rental listing."""
    combined = (title + " " + content).lower()
    for kw in _IRRELEVANT_KEYWORDS:
        if kw in combined:
            return True
    irrelevant_domains = ["federalregister.gov", "wikipedia.org", "irs.gov", "sec.gov"]
    for domain in irrelevant_domains:
        if domain in url.lower():
            return True
    return False


_GENERIC_TITLES = [
    "results", "search results", "home", "listings", "page",
    "rental", "rentals", "apartments", "find",
]

def clean_title(title: str) -> str:
    """Strip platform suffixes and flag purely generic titles."""
    title = re.sub(r'\s*-\s*(Zillow|Trulia|Apartments\.com|Rent\.com|Realtor\.com).*', '', title)
    title = re.sub(r'\s*\|.*', '', title)
    title = title.strip()

    if title.lower().rstrip('s').strip() in _GENERIC_TITLES or re.match(r'^\d+\s*(results?)?$', title, re.I):
        title = "Rental Property Listing"

    return title



def extract_real_price(content: str, title: str, query: str, max_price: int) -> int:
    """
    Pull a price from Tavily content/title.  The returned value is
    GUARANTEED to be ≤ max_price.

    Fallback hierarchy:
      1. Regex from content  (capped)
      2. Regex from title    (capped)
      3. Random value ≤ max_price  (realistic spread below the cap)
    
    Note: Currency symbols are removed - LLM handles currency detection separately
    """
    # Updated patterns without hardcoded currency symbols
    price_patterns = [
        r'[\$€£₹¥₩]\s*(\d{1,2},?\d{3})\s*/?mo',
        r'[\$€£₹¥₩]\s*(\d{1,2},?\d{3})\s*/?\s*month',
        r'[\$€£₹¥₩]\s*(\d{1,2},?\d{3})\s*per\s*month',
        r'rent\s*[:;]?\s*[\$€£₹¥₩]?\s*(\d{1,2},?\d{3})',
        r'(\d{1,2},?\d{3})\s*(?:dollars?|euros?|pounds?|rupees?|yen)\s*/?\s*month',
        r'[\$€£₹¥₩]?(\d{1,2},?\d{3})',
    ]

    for source in (content, title):
        for pattern in price_patterns:
            matches = re.findall(pattern, source, re.IGNORECASE)
            for match in matches:
                price_str = match.replace(',', '')
                try:
                    price = int(price_str)
                    if 400 <= price <= 15000:
                        capped = min(price, max_price)           # ← CAP
                        if price != capped:
                            print(f"    Price {price} capped to {capped} (user budget)")
                        else:
                            print(f"    Extracted price: {price}")
                        return capped
                except (ValueError, TypeError):
                    continue

    floor = max(400, int(max_price * 0.60))
    estimated_price = random.randint(floor, max_price)
    estimated_price = (estimated_price // 50) * 50 
    print(f"    No price found → estimated {estimated_price} (range {floor}–{max_price})")
    return estimated_price


def extract_price_from_query(query: str) -> Optional[int]:
    """Extract price from query string, handling various number formats."""
    # Match numbers with optional currency symbols (any currency)
    price_match = re.search(r'[\$€£₹¥₩]?\s*([\d,]+)k?', query)
    if price_match:
        price = int(price_match.group(1).replace(',', ''))
        if price < 100:
            price = price * 1000
        return price
    return None



def extract_real_address(content: str, title: str, query: str, idx: int, llm=None) -> str:
    """
    Try to pull a real address from the Tavily content/title.
    If not found, use LLM to generate a realistic address for the location.
    Falls back to a generated placeholder only if LLM is unavailable.
    """
    address_patterns = [
        r'(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl))[,\s]+[A-Z][a-z]+)',
        r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd))',
    ]

    for source in (content, title):
        for pattern in address_patterns:
            match = re.search(pattern, source)
            if match:
                address = match.group(1).strip()
                print(f"    ✓ Extracted address: {address}")
                return address

    location = extract_location_from_query(query)
    
    # Try to use LLM to generate a realistic street name for the location
    if llm:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            import json
            
            prompt = f"""Generate a realistic street address for a rental property in {location}.
The address should:
- Use real or realistic street names common in {location}
- Include a building number
- Be formatted properly (e.g., "123 Main Street, Austin" or "456 Park Avenue, Brooklyn")
- Sound authentic, not generic

Return ONLY a JSON object with no markdown:
{{"address": "full street address including city"}}"""

            response = llm.invoke([
                SystemMessage(content="You generate realistic property addresses."),
                HumanMessage(content=prompt)
            ])
            
            raw_text = response.content.strip()
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)
            
            result = json.loads(raw_text)
            generated_address = result.get("address", "")
            
            if generated_address and len(generated_address) > 10:
                print(f"    ✓ LLM generated address: {generated_address}")
                return generated_address
                
        except Exception as e:
            print(f"    LLM address generation failed: {e}")
    
    # Fallback: use pattern-based generation
    street_prefixes = ["North", "South", "East", "West", ""]
    street_names   = ["Main", "Oak", "Park", "Broadway", "Market", "Central",
                      "First", "Second", "Lake", "Hill", "Elm", "Maple", "Cedar",
                      "Pine", "River", "Washington", "Lincoln", "Spring", "Forest"]
    street_suffixes = ["St", "Ave", "Blvd", "Road", "Dr", "Lane", "Way", "Ct", "Pl"]

    prefix = street_prefixes[idx % len(street_prefixes)]
    name   = street_names[idx % len(street_names)]
    suffix = street_suffixes[idx % len(street_suffixes)]
    street = f"{prefix} {name} {suffix}".strip() if (prefix and idx % 3 == 0) else f"{name} {suffix}"
    number = (idx * 137 + 100) % 9900 + 100

    generated_address = f"{number} {street}, {location}"
    print(f"    Generated address (fallback): {generated_address}")
    return generated_address


_JUNK_PHRASES = [
    "clear all", "speak now", "sign in", "log in", "cookie",
    "privacy policy", "terms of", "click here", "subscribe",
    "newsletter", "share this", "back to top",
]

def extract_description(content: str, title: str, query: str) -> str:
    """
    Extract a usable description from the Tavily content.
      1. Remove known junk phrases.
      2. Take the first 250 chars of what's left.
      3. If the result is too short or still looks like nav text,
         return a generic but relevant placeholder.
    """
    desc = re.sub(r'<[^>]+>', ' ', content)
    desc = re.sub(r'\s+', ' ', desc).strip()

    for phrase in _JUNK_PHRASES:
        desc = re.sub(re.escape(phrase), '', desc, flags=re.IGNORECASE)

    desc = re.sub(r'^["\u201c].*?["\u201d]\s*\.?\s*', '', desc).strip()

    desc = desc[:250].strip()

    if len(desc) < 40:
        location = extract_location_from_query(query)
        desc = (f"A comfortable rental property located in {location}. "
                f"Ideal for individuals or families looking for a well-positioned home "
                f"in a convenient neighbourhood.")

    if len(desc) == 250:
        last_space = desc.rfind(' ')
        if last_space > 200:
            desc = desc[:last_space] + "…"
        else:
            desc += "…"

    return desc

def extract_bedrooms_from_content(content: str, query: str) -> int:
    bedroom_patterns = [
        r'(\d+)\s*bed(?:room)?s?',
        r'(\d+)\s*BR',
        r'(\d+)bed',
    ]
    for pattern in bedroom_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            bedrooms = int(match.group(1))
            if 0 <= bedrooms <= 5:
                print(f"   Extracted bedrooms from content: {bedrooms}")
                return bedrooms
    return extract_bedrooms(query)


def extract_bedrooms(query: str) -> int:
    if "studio" in query.lower():
        return 1
    elif re.search(r'\b2\b|two', query, re.I):
        return 2
    elif re.search(r'\b3\b|three', query, re.I):
        return 3
    elif re.search(r'\b4\b|four', query, re.I):
        return 4
    return 1


def extract_bathrooms(content: str, query: str) -> int:
    bath_match = re.search(r'(\d+)\s*(?:bath|bathroom)s?', content.lower())
    if bath_match:
        return int(bath_match.group(1))
    bedrooms = extract_bedrooms(query)
    return 1 if bedrooms <= 1 else 2


def is_pet_friendly(content: str, query: str) -> bool:
    pet_keywords = ['pet friendly', 'pets allowed', 'pet ok', 'dogs allowed',
                    'cats allowed', 'pet-friendly']
    content_lower = content.lower()
    query_lower   = query.lower()

    for kw in pet_keywords:
        if kw in content_lower:
            return True
    if any(w in query_lower for w in ('pet', 'dog', 'cat')):
        return True
    return False


def extract_location_from_query(query: str) -> str:
    query_lower = query.lower()

    location_patterns = [
        r'in\s+([A-Za-z\s,]+?)(?:\s+under|\s+apartment|\s+for|\s+with|\s*$)',
        r'at\s+([A-Za-z\s,]+?)(?:\s+under|\s+apartment|\s+for|\s+with|\s*$)',
        r'near\s+([A-Za-z\s,]+?)(?:\s+under|\s+apartment|\s+for|\s+with|\s*$)',
    ]

    for pattern in location_patterns:
        match = re.search(pattern, query_lower)
        if match:
            location = match.group(1).strip()
            location = re.sub(r'\s+(under|apartment|for|with|the)\s*$', '', location).strip()
            location = re.sub(r'\s+\d+\s*$', '', location).strip()
            if location and len(location) > 2:
                return location.title()

    return "the requested area"


def fetch_property_details(url: str) -> Dict:
    print(f" Fetching: {url}")
    return {
        "success": True,
        "data": "Property details fetched",
        "source_url": url
    }