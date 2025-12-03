"""
Utility functions for the Revolico scraper
"""

import json
import logging
import random
from datetime import datetime
from typing import Dict, Any
import os

def setup_logging() -> logging.Logger:
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create logger for scraper
    logger = logging.getLogger('revolico_scraper')
    
    # Add error-only file handler
    error_handler = logging.FileHandler('logs/scraper_errors.log')
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)
    
    return logger

def save_to_json(data: Dict[str, Any], filename: str) -> bool:
    """Save data to JSON file with error handling"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Data successfully saved to {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving to {filename}: {e}")
        logging.error(f"Failed to save JSON file {filename}: {e}")
        return False

def load_from_json(filename: str) -> Dict[str, Any]:
    """Load data from JSON file with error handling"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
        
    except FileNotFoundError:
        print(f"⚠️  File {filename} not found")
        return {}
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        logging.error(f"Failed to load JSON file {filename}: {e}")
        return {}

def get_random_user_agent() -> str:
    """Get a random user agent string"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ]
    
    return random.choice(user_agents)

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = ' '.join(text.split())
    
    # Remove or replace problematic characters
    cleaned = cleaned.replace('\xa0', ' ')  # Non-breaking space
    cleaned = cleaned.replace('\u200b', '')  # Zero-width space
    
    return cleaned.strip()

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    if not url:
        return False
    
    return url.startswith(('http://', 'https://'))

def make_absolute_url(base_url: str, relative_url: str) -> str:
    """Convert relative URL to absolute URL"""
    if not relative_url:
        return base_url
    
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    
    base_url = base_url.rstrip('/')
    
    if relative_url.startswith('/'):
        return base_url + relative_url
    else:
        return base_url + '/' + relative_url

def create_backup_filename(original_filename: str) -> str:
    """Create a backup filename with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(original_filename)
    return f"{name}_backup_{timestamp}{ext}"

def safe_get_text(element, default: str = "") -> str:
    """Safely extract text from BeautifulSoup element"""
    if element is None:
        return default
    
    try:
        text = element.get_text(strip=True)
        return clean_text(text) if text else default
    except Exception:
        return default

def print_separator(char: str = "=", length: int = 60) -> None:
    """Print a separator line"""
    print(char * length)

def print_status(message: str, status: str = "INFO") -> None:
    """Print a status message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "PROGRESS": "🔄"
    }
    
    icon = status_icons.get(status, "•")
    print(f"[{timestamp}] {icon} {message}")

def validate_phone_format(phone: str) -> bool:
    """Basic validation for phone number format"""
    if not phone:
        return False
    
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone))
    
    # Should have at least 7 digits and at most 12 (including country code)
    return 7 <= len(digits_only) <= 12

def get_file_size(filename: str) -> str:
    """Get human-readable file size"""
    try:
        size = os.path.getsize(filename)
        
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{size/1024:.1f} KB"
        elif size < 1024**3:
            return f"{size/(1024**2):.1f} MB"
        else:
            return f"{size/(1024**3):.1f} GB"
            
    except OSError:
        return "Unknown size"
