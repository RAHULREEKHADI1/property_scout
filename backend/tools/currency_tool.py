"""
Currency detection tool that uses LLM for intelligent currency extraction
instead of hardcoded patterns and symbols.
"""

from typing import Optional
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re
import os


@dataclass
class CurrencyInfo:
    code: str      
    symbol: str   


def detect_currency_with_llm(user_message: str, llm: Optional[ChatOpenAI] = None) -> CurrencyInfo:
    """
    Use LLM to intelligently detect currency from user message.
    
    The LLM understands context better than regex patterns:
    - Recognizes currency codes (USD, EUR, INR, etc.)
    - Understands written currency names (dollars, euros, rupees)
    - Detects currency symbols ($, €, ₹, £, etc.)
    - Handles multi-language and regional variations
    
    Args:
        user_message: The user's search query
        llm: Optional LLM instance (will create one if not provided)
        
    Returns:
        CurrencyInfo with detected currency code and symbol
    """
    
    if not user_message or not user_message.strip():
        return CurrencyInfo(code="USD", symbol="$")
    
    # Initialize LLM if not provided
    if llm is None:
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        except Exception as e:
            print(f"Warning: Could not initialize LLM for currency detection: {e}")
            return _fallback_currency_detection(user_message)
    
    try:
        system_prompt = """You are a currency detection expert. Analyze the user's message and identify any currency mentioned.

Detect currency from:
- Currency codes: USD, EUR, GBP, INR, JPY, CNY, CHF, CAD, AUD, etc.
- Currency names: dollars, euros, pounds, rupees, yen, yuan, francs, etc.
- Currency symbols: $, €, £, ₹, ¥, ₩, etc.
- Context clues: "in New York" → USD, "in London" → GBP, "in Mumbai" → INR

Return ONLY valid JSON with no markdown:
{"code": "<3-letter ISO code>", "symbol": "<unicode symbol>"}

Examples:
- "apartment in Brooklyn under $2000" → {"code": "USD", "symbol": "$"}
- "flat in London under £1500" → {"code": "GBP", "symbol": "£"}
- "apartment in Mumbai under 50000 rupees" → {"code": "INR", "symbol": "₹"}
- "property in Tokyo under ¥200000" → {"code": "JPY", "symbol": "¥"}
- "apartment in Paris under 1500 euros" → {"code": "EUR", "symbol": "€"}

If no currency is mentioned, infer from location or default to USD."""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        raw_text = response.content.strip()
        # Remove markdown code blocks if present
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)
        
        result = json.loads(raw_text)
        
        # Validate response
        if "code" in result and "symbol" in result:
            code = result["code"].upper()
            symbol = result["symbol"]
            
            # Basic validation
            if len(code) == 3 and code.isalpha() and len(symbol) <= 5:
                print(f"✓ LLM detected currency: {code} ({symbol})")
                return CurrencyInfo(code=code, symbol=symbol)
        
        print(f"⚠ LLM returned invalid currency format, using fallback")
        return _fallback_currency_detection(user_message)
        
    except Exception as e:
        print(f"⚠ LLM currency detection failed: {e}, using fallback")
        return _fallback_currency_detection(user_message)


def _fallback_currency_detection(user_message: str) -> CurrencyInfo:
    """
    Lightweight fallback for common currencies when LLM is unavailable.
    Only handles the most obvious cases.
    """
    text = user_message.lower()
    
    # Direct symbol matches (most reliable)
    if '₹' in user_message:
        return CurrencyInfo(code="INR", symbol="₹")
    if '€' in user_message:
        return CurrencyInfo(code="EUR", symbol="€")
    if '£' in user_message:
        return CurrencyInfo(code="GBP", symbol="£")
    if '¥' in user_message or '¥' in user_message:
        # Could be JPY or CNY, default to JPY
        return CurrencyInfo(code="JPY", symbol="¥")
    if '₩' in user_message:
        return CurrencyInfo(code="KRW", symbol="₩")
    
    if re.search(r'\bINR\b', text, re.IGNORECASE):
        return CurrencyInfo(code="INR", symbol="₹")
    if re.search(r'\bEUR\b', text, re.IGNORECASE):
        return CurrencyInfo(code="EUR", symbol="€")
    if re.search(r'\bGBP\b', text, re.IGNORECASE):
        return CurrencyInfo(code="GBP", symbol="£")
    if re.search(r'\bJPY\b', text, re.IGNORECASE):
        return CurrencyInfo(code="JPY", symbol="¥")
    
    if re.search(r'\brupees?\b', text, re.IGNORECASE):
        return CurrencyInfo(code="INR", symbol="₹")
    if re.search(r'\beuros?\b', text, re.IGNORECASE):
        return CurrencyInfo(code="EUR", symbol="€")
    if re.search(r'\bpounds?\b', text, re.IGNORECASE):
        return CurrencyInfo(code="GBP", symbol="£")
    if re.search(r'\byen\b', text, re.IGNORECASE):
        return CurrencyInfo(code="JPY", symbol="¥")
    
    location_currency_map = {
        'india': ('INR', '₹'),
        'mumbai': ('INR', '₹'),
        'delhi': ('INR', '₹'),
        'bangalore': ('INR', '₹'),
        'london': ('GBP', '£'),
        'paris': ('EUR', '€'),
        'berlin': ('EUR', '€'),
        'tokyo': ('JPY', '¥'),
        'zurich': ('CHF', 'CHF'),
    }
    
    for location, (code, symbol) in location_currency_map.items():
        if location in text:
            return CurrencyInfo(code=code, symbol=symbol)
    
    return CurrencyInfo(code="USD", symbol="$")


def detect_currency(user_message: str, llm: Optional[ChatOpenAI] = None) -> CurrencyInfo:
    """
    Main currency detection function.
    Uses LLM for intelligent detection, falls back to pattern matching if needed.
    """
    return detect_currency_with_llm(user_message, llm)