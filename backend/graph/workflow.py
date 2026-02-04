from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from graph.state import AgentState
from graph.nodes import scout_node, inspector_node, broker_node, crm_node
from tools.mongo_tool import MongoDBTool
from tools.currency_tool import detect_currency
from tools.intent_classifier import classify_intent, generate_response
from langchain_openai import ChatOpenAI
import os

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

async def run_agent(user_message: str):
    """
    Enhanced workflow with:
    1. Intent classification (greetings vs search vs invalid)
    2. Memory of last search for quick follow-ups
    3. Currency detection from query
    """
    
    # Step 1: Classify user intent
    print(f"\n{'='*60}")
    print(f" INTENT CLASSIFICATION")
    print(f"{'='*60}")
    intent_result = classify_intent(user_message, intent_llm)
    print(f"Intent: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")
    print(f"Reason: {intent_result['reason']}")
    
    # Handle non-search intents
    if intent_result['intent'] in ['greeting', 'invalid']:
        response = generate_response(intent_result)
        return {
            "response": response,
            "properties": [],
            "state": "conversation"
        }
    
    # Step 2: Load user preferences and conversation memory
    try:
        user_prefs = mongo_tool.get_user_preferences("default")
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        user_prefs = {"user_id": "default", "preferences": {}}
    
    try:
        conversation_memory = mongo_tool.get_conversation_memory("default")
    except Exception as e:
        print(f"Error getting conversation memory: {e}")
        conversation_memory = {}
    
    # Step 3: Handle follow-up queries using memory
    if intent_result['intent'] == 'follow_up' and conversation_memory:
        print(f"\n{'='*60}")
        print(f" USING MEMORY FROM LAST SEARCH")
        print(f"{'='*60}")
        print(f"Last criteria: {conversation_memory}")
        # Merge last search criteria with new query modifications
        # This allows "show me more" or "similar but cheaper" type queries
    
    try:
        graph = create_agent_graph()
        
        # Step 4: Detect currency from user message
        currency = detect_currency(user_message)
        print(f"\n{'='*60}")
        print(f" CURRENCY DETECTION")
        print(f"{'='*60}")
        print(f"Detected: {currency.code} ({currency.symbol})")

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
            "intent": intent_result['intent']
        }
        
        result = await graph.ainvoke(initial_state)
        
        # Step 5: Prepare properties with correct currency formatting
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
        
        # Step 6: Save conversation memory for future queries
        if properties_with_urls:
            memory = {
                "last_query": user_message,
                "criteria": result.get("search_criteria", {}),
                "currency": {"code": cur_code, "symbol": cur_symbol},
                "property_count": len(properties_with_urls)
            }
            try:
                mongo_tool.save_conversation_memory("default", memory)
                print(f"\n✓ Conversation memory saved for future queries")
            except Exception as e:
                print(f"Error saving memory: {e}")
        
        num_properties = len(properties_with_urls)
        
        if num_properties > 0:
            response = f"I found {num_properties} {'property' if num_properties == 1 else 'properties'} matching your criteria. Each listing includes detailed information, street view images, and draft lease agreements."
        else:
            response = "I didn't find any properties matching your exact criteria. Try adjusting your search parameters like budget, location, or number of bedrooms."
        
        return {
            "response": response,
            "properties": properties_with_urls,  
            "state": result.get("current_step", "complete")
        }
    except Exception as e:
        print(f"Error in agent workflow: {e}")
        import traceback
        traceback.print_exc()
        raise e