import re

def validate_url(url):
    """Ensure URL has a protocol and is valid."""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    pattern = re.compile(
        r'^(?:http|https)://'  # protocol
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(pattern, url) is not None
