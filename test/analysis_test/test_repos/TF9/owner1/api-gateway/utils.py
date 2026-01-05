"""Utility functions."""
def clean_text(text):
    """Remove whitespace and convert to lowercase."""
    return text.strip().lower()

def validate_email(email):
    """Basic email validation."""
    return '@' in email and '.' in email
