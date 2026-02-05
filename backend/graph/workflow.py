from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from graph.state import AgentState
from graph.nodes import scout_node, inspector_node, broker_node, crm_node
from tools.mongo_tool import MongoDBTool
from tools.currency_tool import detect_currency
from tools.intent_classifier import classify_intent, generate_response, format_memory_response
from langchain_openai import ChatOpenAI
import os
import re

mongo_tool = MongoDBTool()
FRONTEND_URL = os.getenv("FRONTEND_URL")

# Initialize LLM for intent classification
try:
    intent_llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
except Exception as e:
    print(f"Warning: Could not initialize intent classifier LLM: {e}")
    intent_llm = None


def extract_search_index_from_query(query: str) -> tuple:
    """
    Extract search index from queries like:
    - "my last search" -> -1
    - "my first search" -> 0
    - "my 3rd search" -> 2 (0-indexed)
    - "search number 2" -> 1 (0-indexed)
    
    Returns: (has_index, index_value)
    """
    query_lower = query.lower()
    
    # Check for "last" or "latest" or "recent"
    if any(word in query_lower for word in ["last", "latest", "recent", "previous"]):
        return (True, -1)
    
    # Check for "first"
    if "first" in query_lower:
        return (True, 0)
    
    # Check for numbered searches (1st, 2nd, 3rd, 4th, etc.)
    ordinal_pattern = r'(\d+)(?:st|nd|rd|th)\s+search'
    match = re.search(ordinal_pattern, query_lower)
    if match:
        num = int(match.group(1))
        return (True, num - 1)  # Convert to 0-indexed
    
    # Check for "search number N"
    number_pattern = r'search\s+(?:number\s+)?(\d+)'
    match = re.search(number_pattern, query_lower)
    if match:
        num = int(match.group(1))
        return (True, num - 1)  # Convert to 0-indexed
    
    return (False, None)


def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("scout", scout_node)
    workflow.add_node("inspector", inspector_node)
    workflow.add_node("broker", broker_node)
    workflow.add_node("crm", crm_node)
    
    workflow.set_entry_point("scout")
    
    workflow.add_edge("scout", "inspector")
    workflow.add_edge("inspector", "broker")
    workflow.add_edge("broker", "crm")
    workflow.add_edge("crm", END)
    
    return workflow.compile()


async def run_agent(user_message: str, user_id: str = "default"):
    """
    Enhanced workflow with:
    1. Intent classification (greetings vs search vs invalid vs memory retrieval)
    2. Memory of last search for quick follow-ups
    3. Currency detection AND persistence in database
    4. Smart caching to avoid redundant searches
    5. Support for "my first search", "my last search" queries
    """
    
    # Step 1: Classify user intent
    print(f"\n{'='*60}")
    print(f" INTENT CLASSIFICATION")
    print(f"{'='*60}")
    intent_result = classify_intent(user_message, intent_llm)
    print(f"Intent: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")
    print(f"Reason: {intent_result['reason']}")
    
    # Step 2: Load user preferences and conversation memory
    try:
        user_prefs = mongo_tool.get_user_preferences(user_id)
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        user_prefs = {"user_id": user_id, "preferences": {}}
    
    try:
        conversation_memory = mongo_tool.get_conversation_memory(user_id)
    except Exception as e:
        print(f"Error getting conversation memory: {e}")
        conversation_memory = {}
    
    # Step 3: Handle specific search history queries ("my first search", "my last search")
    has_search_index, search_index = extract_search_index_from_query(user_message)
    if has_search_index:
        print(f"\n{'='*60}")
        print(f" RETRIEVING SPECIFIC SEARCH FROM HISTORY (index: {search_index})")
        print(f"{'='*60}")
        
        historical_search = mongo_tool.get_search_by_index(user_id, search_index)
        
        if historical_search:
            index_desc = "last" if search_index == -1 else "first" if search_index == 0 else f"search #{search_index + 1}"
            response = f"Here's your {index_desc} search:\n\n"
            response += f"Query: {historical_search.get('last_query', 'N/A')}\n"
            response += f"Location: {historical_search.get('criteria', {}).get('location', 'N/A')}\n"
            response += f"Budget: {historical_search.get('currency', {}).get('symbol', '$')}{historical_search.get('criteria', {}).get('max_price', 'N/A')}\n"
            response += f"Properties found: {historical_search.get('property_count', 0)}\n"
            
            if historical_search.get('searched_at'):
                response += f"Searched at: {historical_search['searched_at']}"
            
            return {
                "response": response,
                "properties": [],
                "state": "history_retrieval",
                "historical_search": historical_search
            }
        else:
            index_desc = "last" if search_index == -1 else "first" if search_index == 0 else f"#{search_index + 1}"
            return {
                "response": f"I couldn't find your {index_desc} search. You may not have performed enough searches yet.",
                "properties": [],
                "state": "history_not_found"
            }
    
    # Step 4: Handle memory retrieval (generic "what did I search")
    if intent_result['intent'] == 'memory_retrieval':
        print(f"\n{'='*60}")
        print(f" MEMORY RETRIEVAL - NO SEARCH TRIGGERED")
        print(f"{'='*60}")
        
        preferences = user_prefs.get("preferences", {})
        response = format_memory_response(conversation_memory, preferences)
        
        print(f"\nReturning stored memory and preferences to user")
        print(f"Memory: {conversation_memory}")
        print(f"Preferences: {preferences}")
        
        return {
            "response": response,
            "properties": [],
            "state": "memory_retrieval"
        }
    
    # Step 5: Handle non-search intents (greetings, invalid)
    if intent_result['intent'] in ['greeting', 'invalid']:
        response = generate_response(intent_result)
        return {
            "response": response,
            "properties": [],
            "state": "conversation"
        }
    
    # Step 6: Currency Detection and Persistence
    print(f"\n{'='*60}")
    print(f" CURRENCY DETECTION & PERSISTENCE")
    print(f"{'='*60}")
    
    # First, check if user has a saved currency preference
    saved_currency = mongo_tool.get_user_currency(user_id)
    
    # Use LLM-based currency detection (much smarter than regex patterns)
    detected_currency = detect_currency(user_message, intent_llm)
    
    # If user mentions a currency in this message, it overrides their saved preference
    # Check if the detected currency is different from default USD
    if detected_currency.code != "USD" or detected_currency.code != saved_currency.get('code', 'USD'):
        # User explicitly mentioned currency - update their preference
        currency = detected_currency
        mongo_tool.save_user_currency(user_id, currency.code, currency.symbol)
        print(f"✓ Detected currency: {currency.code} ({currency.symbol})")
        print(f"✓ Saved as user preference")
    else:
        # Use saved preference
        currency = type('Currency', (), {
            'code': saved_currency['code'],
            'symbol': saved_currency['symbol']
        })()
        print(f"✓ Using saved currency preference: {currency.code} ({currency.symbol})")
    
    # Step 7: Extract search criteria for caching
    # This will be done in scout_node, but we need to check cache BEFORE running the full pipeline
    
    # For now, let's proceed with the search
    # The caching will be handled in scout_node
    
    # Step 8: Handle follow-up queries using memory
    if intent_result['intent'] == 'follow_up' and conversation_memory:
        print(f"\n{'='*60}")
        print(f" USING MEMORY FROM LAST SEARCH")
        print(f"{'='*60}")
        print(f"Last criteria: {conversation_memory}")
    
    # Step 9: Execute property search (with caching handled in scout_node)
    try:
        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "properties": [],
            "user_preferences": user_prefs.get("preferences", {}),
            "current_step": "start",
            "screenshots": [],
            "folders_created": [],
            "currency_code": currency.code,
            "currency_symbol": currency.symbol,
            "conversation_memory": conversation_memory,
            "intent": intent_result['intent'],
            "user_id": user_id  # Pass user_id for cache lookup
        }
        
        result = await graph.ainvoke(initial_state)
        
        # Check for validation errors (e.g., missing location)
        if result.get("current_step") == "validation_error":
            error_type = result.get("error", "unknown")
            error_message = result.get("error_message", "Invalid search criteria")
            
            print(f"\n{'='*60}")
            print(f" VALIDATION ERROR: {error_type}")
            print(f"{'='*60}")
            
            return {
                "response": error_message,
                "properties": [],
                "state": "validation_error",
                "error": error_type
            }
        
        # Check if result came from cache
        from_cache = result.get("from_cache", False)
        
        # Prepare properties with correct currency formatting
        properties_with_urls = []
        folders = result.get("folders_created", [])
        cur_code   = result.get("currency_code", "USD")
        cur_symbol = result.get("currency_symbol", "$")
        
        for idx, prop in enumerate(result.get("properties", [])):
            prop_copy = dict(prop)
            
            # Add currency info to each property
            prop_copy["currency_code"]   = cur_code
            prop_copy["currency_symbol"] = cur_symbol
            
            if idx < len(folders):
                folder_path = folders[idx]
                screenshot_path = f"{folder_path}/street_view.png"
                prop_copy["image_url"] = f"{FRONTEND_URL}/{screenshot_path}"
                prop_copy["screenshot_path"] = screenshot_path
                prop_copy["folder_path"] = folder_path
                
                print(f"✓ Added image URL to property {idx + 1}: {prop_copy['image_url']}")
            
            properties_with_urls.append(prop_copy)
        
        # Save conversation memory for future queries (only if not from cache)
        if properties_with_urls and not from_cache:
            memory = {
                "last_query": user_message,
                "criteria": result.get("search_criteria", {}),
                "currency": {"code": cur_code, "symbol": cur_symbol},
                "property_count": len(properties_with_urls)
            }
            try:
                mongo_tool.save_conversation_memory(user_id, memory)
                print(f"\n✓ Conversation memory saved for future queries")
            except Exception as e:
                print(f"Error saving memory: {e}")
        
        num_properties = len(properties_with_urls)
        
        if num_properties > 0:
            cache_note = " (from cache)" if from_cache else ""
            response = f"I found {num_properties} {'property' if num_properties == 1 else 'properties'} matching your criteria{cache_note}. Each listing includes detailed information, street view images, and draft lease agreements."
        else:
            response = "I didn't find any properties matching your exact criteria. Try adjusting your search parameters like budget, location, or number of bedrooms."
        
        return {
            "response": response,
            "properties": properties_with_urls,  
            "state": result.get("current_step", "complete"),
            "from_cache": from_cache
        }
    except Exception as e:
        print(f"Error in agent workflow: {e}")
        import traceback
        traceback.print_exc()
        raise e