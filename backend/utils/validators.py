import html
import re

def sanitize(value):
    """Escapes HTML characters in the given value."""
    if value is None:
        return None
    return html.escape(str(value))

def sanitize_input(value, max_length=500):
    """Strips whitespace, escapes HTML, and truncates to max_length."""
    if value is None:
        return None
    cleaned = html.escape(str(value).strip())
    return cleaned[:max_length] if cleaned else None

def is_valid_email(email):
    """Validates email format using standard regex pattern."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))
