"""
Text processing utilities for the bot.
"""

def normalize_text(text: str) -> str:
    """
    Normalizes text by converting Latin lookalikes to Cyrillic
    and handling common OCR misreads.
    Useful for comparing OCR results with expected item names.
    """
    if not text:
        return ""
        
    text = text.upper()
    
    # Mapping Latin -> Cyrillic (Visual Lookalikes)
    mapping = {
        'A': 'А', 'B': 'В', 'E': 'Е', 'K': 'К', 'M': 'М', 
        'H': 'Н', 'O': 'О', 'P': 'Р', 'C': 'С', 'T': 'Т', 
        'X': 'Х', 'Y': 'У'
    }
    
    # Common OCR misreads for specific fonts (Albion)
    misreads = {
        'N': 'П',   # "NOCOX" -> "ПОСОХ"
        'II': 'П',  # "IIOCOX" -> "ПОСОХ"
        '3': 'З',   # Digit 3 to Cyrillic Ze
        '0': 'О'    # Digit 0 to Cyrillic O
    }
    
    res = []
    i = 0
    while i < len(text):
        # Check 2-char sequences first (e.g. 'II')
        if i < len(text) - 1 and text[i:i+2] in misreads:
            res.append(misreads[text[i:i+2]])
            i += 2
            continue
            
        char = text[i]
        
        # Check misreads first, then mapping
        if char in misreads:
            res.append(misreads[char])
        elif char in mapping:
            res.append(mapping[char])
        else:
            res.append(char)
        i += 1
        
    return "".join(res)
