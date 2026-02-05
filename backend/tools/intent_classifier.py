import re
from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
import json

def classify_intent(message: str, llm: Optional[ChatOpenAI] = None) -> Dict:
    """
    Classify user intent into:
    - 'greeting': Simple greetings like "hi", "hello", "how are you"
    - 'search': Property search queries
    - 'follow_up': Follow-up questions about previous search
    - 'memory_retrieval': Asking about preferences or last search
    - 'invalid': Unclear or irrelevant queries
    
    Returns:
        {
            'intent': str,  # greeting, search, follow_up, memory_retrieval, or invalid
            'confidence': float,  # 0-1
            'reason': str  # Explanation
        }
    """
    message_lower = message.lower().strip()
    
    # Quick pattern matching for common cases
    greeting_patterns = [
        r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening)',
        r'^(what\'s up|whats up|how are you|how\'s it going)',
        r'^(yo|sup|howdy)'
    ]
    
    for pattern in greeting_patterns:
        if re.match(pattern, message_lower):
            return {
                'intent': 'greeting',
                'confidence': 0.95,
                'reason': 'Detected greeting pattern'
            }
    
    # Memory retrieval patterns
    memory_patterns = [
        r'(what|show|tell|give).*?(my|last|previous|recent).*(preference|search|query|criteria)',
        r'(what did i|remind me what i).*(search|look|ask)',
        r'my (last|previous|recent) (search|query|preference|criteria)',
        r'what was (my|the) last',
        r'show me my (preference|history|last search)',
        r'what (am i|was i) looking for',
        r'recall my',
        r'my search history'
    ]
    
    for pattern in memory_patterns:
        if re.search(pattern, message_lower):
            return {
                'intent': 'memory_retrieval',
                'confidence': 0.95,
                'reason': 'Detected memory retrieval request'
            }
    
    # Property search keywords
    search_keywords = [
        'apartment', 'property', 'house', 'room', 'bedroom', 'studio',
        'rent', 'rental', 'lease', 'find', 'search', 'looking for',
        'need', 'want', 'show me', 'under', 'budget', 'price'
    ]
    
    location_keywords = [
        'in', 'at', 'near', 'around', 'city', 'area', 'neighborhood',
        'brooklyn', 'austin', 'new york', 'san francisco', 'london'
    ]
    
    # Count search indicators
    search_score = sum(1 for kw in search_keywords if kw in message_lower)
    location_score = sum(1 for kw in location_keywords if kw in message_lower)
    
    # If strong indicators, classify as search
    if search_score >= 2 or (search_score >= 1 and location_score >= 1):
        return {
            'intent': 'search',
            'confidence': 0.9,
            'reason': f'Found {search_score} search keywords and {location_score} location indicators'
        }
    
    # Follow-up patterns
    follow_up_patterns = [
        r'(show|tell|give|find) me (more|another|different)',
        r'what about',
        r'how about',
        r'similar to',
        r'like (the|that) (last|previous)',
        r'(same|similar) (but|with)',
        r'more like',
        r'^(again|more)$',
        r'show (more|again)'
    ]
    
    for pattern in follow_up_patterns:
        if re.search(pattern, message_lower):
            return {
                'intent': 'follow_up',
                'confidence': 0.85,
                'reason': 'Detected follow-up pattern'
            }
    
    # Use LLM for ambiguous cases
    if llm and len(message.split()) > 3:
        try:
            system_prompt = """You are an intent classifier for a property search assistant.
Classify the user's message into ONE of these categories:

1. "greeting" - Simple greetings, pleasantries, or general conversation
2. "search" - Property/apartment search queries with criteria
3. "follow_up" - Questions about previous searches or modifications
4. "memory_retrieval" - Asking about their preferences, last search, or search history
5. "invalid" - Unclear, off-topic, or irrelevant queries

Respond ONLY with valid JSON:
{"intent": "<category>", "confidence": <0-1>, "reason": "<brief explanation>"}"""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ])
            
            raw_text = response.content.strip()
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)
            
            result = json.loads(raw_text)
            return result
            
        except Exception as e:
            print(f"LLM intent classification failed: {e}")
    
    # Default: if message is very short and no clear indicators
    if len(message.split()) <= 2 and search_score == 0:
        return {
            'intent': 'invalid',
            'confidence': 0.7,
            'reason': 'Message too vague or unclear'
        }
    
    # Weak search signal
    if search_score >= 1 or location_score >= 1:
        return {
            'intent': 'search',
            'confidence': 0.6,
            'reason': 'Possible search intent with weak indicators'
        }
    
    # Default to invalid
    return {
        'intent': 'invalid',
        'confidence': 0.5,
        'reason': 'Unable to determine clear intent'
    }


def generate_response(intent_result: Dict, user_name: str = "there") -> str:
    """Generate appropriate response based on intent"""
    intent = intent_result['intent']
    
    if intent == 'greeting':
        responses = [
            f"Hello! I'm Estate-Scout, your property search assistant. How can I help you find a place today?",
            f"Hi {user_name}! Ready to find your perfect rental? Tell me what you're looking for.",
            f"Hey! I'm here to help you search for apartments and properties. What are you looking for?"
        ]
        import random
        return random.choice(responses)
    
    elif intent == 'follow_up':
        return "I'd be happy to help with that! However, I need a bit more information. Could you please specify your full search criteria again? For example: 'Find me a 2 bedroom apartment in Austin under $2000'."
    
    elif intent == 'memory_retrieval':
        return None  # Will be handled in workflow to show actual memory
    
    elif intent == 'invalid':
        return "I'm not quite sure I understand what you're looking for. I'm Estate-Scout, and I help find rental properties. Try something like: 'Find me a 2 bedroom apartment in Brooklyn under $2500' or 'Show me studios in Austin under $1500'."
    
    return None


def format_memory_response(memory: Dict, preferences: Dict) -> str:
    """Format the memory and preferences for display"""
    if not memory and not preferences:
        return "I don't have any search history or preferences saved yet. Start by telling me what you're looking for!"
    
    response_parts = []
    
    # Format last search
    if memory and memory.get('last_query'):
        response_parts.append("📋 **Your Last Search:**")
        response_parts.append(f"Query: \"{memory['last_query']}\"")
        
        if memory.get('criteria'):
            criteria = memory['criteria']
            if criteria.get('location'):
                response_parts.append(f"• Location: {criteria['location']}")
            if criteria.get('bedrooms'):
                response_parts.append(f"• Bedrooms: {criteria['bedrooms']}")
            if criteria.get('max_price'):
                currency = memory.get('currency', {})
                symbol = currency.get('symbol', '$')
                response_parts.append(f"• Max Budget: {symbol}{criteria['max_price']}")
            if criteria.get('requirements') and criteria['requirements'] != 'none':
                response_parts.append(f"• Requirements: {criteria['requirements']}")
        
        if memory.get('property_count'):
            response_parts.append(f"• Found: {memory['property_count']} properties")
        
        response_parts.append("")
    
    # Format learned preferences
    if preferences:
        response_parts.append("🎯 **What I've Learned About You:**")
        
        if preferences.get('has_pet'):
            response_parts.append("• You have a pet")
        
        if preferences.get('preferred_locations'):
            locations = ', '.join(preferences['preferred_locations'])
            response_parts.append(f"• Interested in: {locations}")
        
        if preferences.get('typical_budget'):
            response_parts.append(f"• Typical budget: ${preferences['typical_budget']}")
        
        if preferences.get('preferred_bedrooms'):
            bedrooms = ', '.join(preferences['preferred_bedrooms'])
            response_parts.append(f"• Preferred sizes: {bedrooms} bedroom(s)")
        
        if preferences.get('budget_history'):
            budgets = preferences['budget_history']
            response_parts.append(f"• Recent budgets: {', '.join(f'${b}' for b in budgets[-3:])}")
        
        response_parts.append("")
    
    if response_parts:
        response_parts.append("Would you like me to search again with these criteria, or would you like to adjust something?")
    
    return "\n".join(response_parts)