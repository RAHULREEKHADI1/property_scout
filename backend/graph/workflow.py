from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from graph.state import AgentState
from graph.nodes import scout_node, inspector_node, broker_node, crm_node
from tools.mongo_tool import MongoDBTool
import os

mongo_tool = MongoDBTool()
FRONTEND_URL = os.getenv("FRONTEND_URL")

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
    try:
        user_prefs = mongo_tool.get_user_preferences("default")
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        user_prefs = {"user_id": "default", "preferences": {}}
    
    try:
        graph = create_agent_graph()
        
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "properties": [],
            "user_preferences": user_prefs.get("preferences", {}),
            "current_step": "start",
            "screenshots": [],
            "folders_created": []
        }
        
        result = await graph.ainvoke(initial_state)
        
        properties_with_urls = []
        folders = result.get("folders_created", [])
        
        for idx, prop in enumerate(result.get("properties", [])):
            prop_copy = dict(prop)
            
            if idx < len(folders):
                folder_path = folders[idx]
                screenshot_path = f"{folder_path}/street_view.png"
                prop_copy["image_url"] = f"{FRONTEND_URL}/{screenshot_path}"
                prop_copy["screenshot_path"] = screenshot_path
                prop_copy["folder_path"] = folder_path
                
                print(f" Added image URL to property {idx + 1}: {prop_copy['image_url']}")
            
            properties_with_urls.append(prop_copy)
        
        num_properties = len(properties_with_urls)
        
        if num_properties > 0:
            response = f"I found {num_properties} properties matching your criteria and saved their complete dossiers with screenshots and draft contracts."
        else:
            response = "I didn't find any properties matching your exact criteria. Try adjusting your search parameters."
        
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