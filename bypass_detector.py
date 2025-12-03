"""
Simple bypass detection and cloudflare detector
"""

import requests
import time
from typing import Dict, Optional
import re

class BypassDetector:
    """Detects and attempts to bypass common anti-bot measures"""
    
    def __init__(self):
        self.cloudflare_indicators = [
            'cloudflare',
            'cf-ray',
            'checking your browser',
            'please wait while we check',
            'ddos protection',
            'security check'
        ]
        
    def detect_protection(self, response: requests.Response) -> Dict[str, bool]:
        """Detect what protection systems are in place"""
        content = response.text.lower()
        headers = {k.lower(): v.lower() for k, v in response.headers.items()}
        
        protection = {
            'cloudflare': False,
            'captcha': False,
            'rate_limit': False,
            'js_challenge': False
        }
        
        # Check for Cloudflare
        if any(indicator in content for indicator in self.cloudflare_indicators):
            protection['cloudflare'] = True
        
        if 'cf-ray' in headers or 'server' in headers and 'cloudflare' in headers['server']:
            protection['cloudflare'] = True
            
        # Check for CAPTCHA
        if any(word in content for word in ['captcha', 'recaptcha', 'hcaptcha']):
            protection['captcha'] = True
            
        # Check for rate limiting
        if response.status_code == 429 or 'rate limit' in content:
            protection['rate_limit'] = True
            
        # Check for JavaScript challenge
        if 'javascript' in content and 'enable' in content:
            protection['js_challenge'] = True
            
        return protection
    
    def suggest_bypass_strategy(self, protection: Dict[str, bool]) -> Dict[str, str]:
        """Suggest bypass strategies based on detected protection"""
        strategies = {}
        
        if protection['cloudflare']:
            strategies['cloudflare'] = "Try different User-Agents, longer delays, and alternative URLs"
            
        if protection['captcha']:
            strategies['captcha'] = "Manual intervention required or CAPTCHA solving service"
            
        if protection['rate_limit']:
            strategies['rate_limit'] = "Increase delays between requests, use proxy rotation"
            
        if protection['js_challenge']:
            strategies['js_challenge'] = "Use browser automation tools like Selenium"
            
        return strategies
    
    def simple_cloudflare_bypass(self, session: requests.Session, url: str) -> Optional[requests.Response]:
        """Attempt simple Cloudflare bypass techniques"""
        
        # Try with minimal headers that mimic a real browser
        minimal_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Clear existing headers and set minimal ones
        session.headers.clear()
        session.headers.update(minimal_headers)
        
        try:
            # First request - might trigger challenge
            response = session.get(url, timeout=15)
            
            # If we get a challenge page, wait and try again
            protection = self.detect_protection(response)
            
            if protection['cloudflare'] and not protection['captcha']:
                print("Cloudflare detected, waiting 5 seconds...")
                time.sleep(5)
                
                # Second attempt with same session (should have cookies)
                response = session.get(url, timeout=15)
                
            return response
            
        except Exception as e:
            print(f"Bypass attempt failed: {e}")
            return None
    
    def analyze_blocking_reason(self, response: requests.Response) -> str:
        """Analyze why the request was blocked"""
        if response.status_code == 403:
            content = response.text.lower()
            
            if 'cloudflare' in content:
                return "Blocked by Cloudflare protection"
            elif 'bot' in content or 'robot' in content:
                return "Detected as bot/crawler"
            elif 'access denied' in content:
                return "General access denied"
            elif 'captcha' in content:
                return "CAPTCHA verification required"
            else:
                return "403 Forbidden - reason unclear"
                
        elif response.status_code == 429:
            return "Rate limited - too many requests"
        elif response.status_code == 503:
            return "Service unavailable - temporary blocking"
        else:
            return f"HTTP {response.status_code} error"