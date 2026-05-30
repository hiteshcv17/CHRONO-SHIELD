import re
import html

# Regular expression matching any HTML tag structure
_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")


def sanitize_text(v: str) -> str:
    """
    Cleanses a raw string input to mitigate Cross-Site Scripting (XSS).
    1. Removes all raw HTML/XML tags.
    2. HTML-escapes all other characters (like <, >, &, ", ').
    3. Strips leading/trailing whitespaces.
    """
    if not isinstance(v, str):
        return v
        
    # Step A: Strip any raw HTML tags
    cleaned = _HTML_TAG_PATTERN.sub("", v)
    
    # Step B: Escape HTML characters and strip whitespace
    return html.escape(cleaned.strip())
