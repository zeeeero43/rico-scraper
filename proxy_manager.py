"""
Proxy management for enhanced anti-detection
"""

import requests
import random
from typing import List, Optional, Dict
import time

class ProxyManager:
    """Manages proxy rotation for anti-detection"""
    
    def __init__(self):
        # Free proxy APIs (for testing purposes)
        self.proxy_sources = [
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&format=json",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        ]
        self.working_proxies = []
        self.proxy_index = 0
        
    def fetch_free_proxies(self) -> List[str]:
        """Fetch free proxies from public sources"""
        proxies = []
        
        # Note: These are public proxies and may not be reliable
        # For production use, consider paid proxy services
        try:
            # Try different proxy list sources
            proxy_lists = [
                # Some common free proxy formats
                "8.8.8.8:8080",  # Example - replace with actual working proxies
                "1.1.1.1:8080",
            ]
            
            # In real implementation, you would fetch from actual proxy APIs
            # For educational purposes, we'll use a simulated approach
            
            return proxy_lists[:5]  # Limit to 5 for testing
            
        except Exception as e:
            print(f"Failed to fetch proxies: {e}")
            return []
    
    def test_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """Test if a proxy is working"""
        try:
            test_url = "http://httpbin.org/ip"
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            response = requests.get(test_url, proxies=proxy_dict, timeout=timeout)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_working_proxies(self, max_proxies: int = 3) -> List[str]:
        """Get a list of working proxies"""
        if not self.working_proxies:
            raw_proxies = self.fetch_free_proxies()
            
            print(f"Testing {len(raw_proxies)} proxies...")
            for proxy in raw_proxies[:max_proxies]:
                if self.test_proxy(proxy):
                    self.working_proxies.append(proxy)
                    print(f"Working proxy found: {proxy}")
                time.sleep(1)  # Avoid rate limiting
        
        return self.working_proxies
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy in rotation"""
        if not self.working_proxies:
            self.get_working_proxies()
        
        if not self.working_proxies:
            return None
        
        proxy = self.working_proxies[self.proxy_index % len(self.working_proxies)]
        self.proxy_index += 1
        
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy"""
        if not self.working_proxies:
            self.get_working_proxies()
        
        if not self.working_proxies:
            return None
        
        proxy = random.choice(self.working_proxies)
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }