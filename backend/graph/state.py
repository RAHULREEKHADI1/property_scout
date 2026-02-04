from typing import TypedDict, List, Dict, Annotated, Optional
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    properties: List[Dict]
    user_preferences: Dict
    current_step: str
    screenshots: List[str]
    folders_created: List[str]
    currency_code: str       
    currency_symbol: str
    conversation_memory: Dict  # Stores last search criteria and context
    intent: Optional[str]  # conversation, search, or invalid