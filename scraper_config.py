"""
Configuration settings for Revolico scraper
"""

class ScraperConfig:
    """Configuration class for scraper settings"""
    
    # Website settings
    BASE_URL = "https://www.revolico.com"
    ALTERNATIVE_URLS = [
        "https://revolico.com",
        "https://m.revolico.com",
        "http://www.revolico.com"
    ]
    
    # Request timing settings (in seconds)
    MIN_DELAY = 3.0
    MAX_DELAY = 8.0
    TIMEOUT = 20
    RETRY_DELAY = 10.0
    
    # Scraping limits
    MAX_LISTINGS = 3
    MAX_RETRIES = 2
    
    # Enhanced user agent rotation with mobile agents
    USER_AGENTS = [
        # Desktop Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        # Mobile Chrome
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.138 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        # Firefox
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.128'
    ]
    
    # File settings
    OUTPUT_FILE = "revolico_data.json"
    LOG_FILE = "scraper.log"
    ERROR_LOG = "scraper_errors.log"
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 10
    BACKOFF_FACTOR = 2.0
    MAX_BACKOFF = 60.0
