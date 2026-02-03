import re
from dataclasses import dataclass


@dataclass
class CurrencyInfo:
    code: str      
    symbol: str   


_CURRENCY_PATTERNS = [
    # Indian Rupee
    (r'₹|INR\b|(?:indian\s+)?rupees?', "INR", "₹"),
    # Euro
    (r'€|EUR\b|euros?', "EUR", "€"),
    # British Pound
    (r'£|GBP\b|(?:british\s+)?pounds?(?:\s+sterling)?', "GBP", "£"),
    # Brazilian Real
    (r'R\$|BRL\b|reais|real(?:\s+brazil)', "BRL", "R$"),
    # Japanese Yen
    (r'¥|JPY\b|(?:japanese\s+)?yen', "JPY", "¥"),
    # Chinese Yuan / Renminbi
    (r'CNY\b|RMB\b|(?:chinese\s+)?yuan|renminbi', "CNY", "¥"),
    # Swiss Franc
    (r'CHF\b|(?:swiss\s+)?franc', "CHF", "CHF"),
    # Canadian Dollar  (must come BEFORE generic "dollar")
    (r'CAD\b|(?:canadian\s+)?dollars?', "CAD", "CA$"),
    # Australian Dollar
    (r'AUD\b|(?:australian\s+)?dollars?', "AUD", "A$"),
    # South-African Rand
    (r'ZAR\b|(?:south[\s-]*african\s+)?rand', "ZAR", "R"),
    # Korean Won
    (r'KRW\b|(?:korean\s+)?won', "KRW", "₩"),
    # Mexican Peso
    (r'MXN\b|(?:mexican\s+)?pesos?', "MXN", "MX$"),
    # Singapore Dollar
    (r'SGD\b|(?:singapore\s+)?dollars?', "SGD", "S$"),
    # US Dollar  — intentionally last among dollar-variants
    (r'\$|USD\b|(?:us\s+)?dollars?', "USD", "$"),
]


def detect_currency(user_message: str) -> CurrencyInfo:

    text = user_message.strip()
    if not text:
        return CurrencyInfo(code="USD", symbol="$")

    for pattern, code, symbol in _CURRENCY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return CurrencyInfo(code=code, symbol=symbol)

    return CurrencyInfo(code="USD", symbol="$")