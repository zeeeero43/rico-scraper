#!/usr/bin/env python3
"""
Simple requests-based scraper for Revolico.com
Focuses on WhatsApp link extraction without triggering protection
"""

import requests
import re
import json
import time
import random
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleRevolicoScraper:
    def __init__(self):
        self.session = requests.Session()
        
        # Real browser headers to avoid detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def get_listing_links(self, max_listings: int = 3) -> List[Dict[str, str]]:
        """Get listing links from homepage"""
        try:
            logger.info("🌐 Loading revolico.com homepage...")
            response = self.session.get('https://www.revolico.com', timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ Homepage loaded: {response.status_code}, {len(response.text)} chars")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find listing links
            listing_links = []
            
            # Try multiple selectors
            selectors = [
                'a[href*="/item/"]:not([href*="/item/publish"])',
                'a[href^="/item/"]',
                '.listing-link',
                '[data-cy="adName"] a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                logger.info(f"Selector '{selector}' found {len(links)} elements")
                
                for link in links[:max_listings]:
                    href = link.get('href')
                    if href and '/item/' in str(href) and '/item/publish' not in str(href):
                        href_str = str(href)
                        if not href_str.startswith('http'):
                            href_str = 'https://www.revolico.com' + href_str
                        
                        title_elem = link.get_text(strip=True) or link.get('title', 'Sin título')
                        
                        listing_links.append({
                            'url': href_str,
                            'title': title_elem
                        })
                        logger.info(f"✓ Found listing: {href_str}")
                        
                        if len(listing_links) >= max_listings:
                            break
                
                if len(listing_links) >= max_listings:
                    break
            
            return listing_links[:max_listings]
            
        except Exception as e:
            logger.error(f"Error getting listing links: {e}")
            return []
    
    def extract_phones_from_page(self, url: str) -> List[str]:
        """Extract phone numbers from a listing page"""
        try:
            logger.info(f"📄 Visiting: {url}")
            
            # Random delay
            time.sleep(random.uniform(2, 5))
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Page loaded: {response.status_code}, {len(response.text)} chars")
            
            # Check if we got a challenge page
            if 'just a moment' in response.text.lower() or 'challenge-platform' in response.text:
                logger.warning("⚠️ Got challenge page, trying different approach...")
                
                # Try with mobile user agent
                mobile_headers = dict(self.session.headers)
                mobile_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
                
                response = self.session.get(url, headers=mobile_headers, timeout=30)
                logger.info(f"Mobile attempt: {response.status_code}, {len(response.text)} chars")
            
            # Focus on user profile area where contact info is located
            found_phones = []
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for user profile section (like the one you showed)
            profile_selectors = [
                'div[class*="sc-7ea21534"]',  # Based on your example
                'div[class*="sc-2a048850"]', 
                'div[class*="kMsUxE"]',
                '[data-cy="adUser"]',
                '.user-profile',
                '.contact-info',
                '.seller-info'
            ]
            
            profile_areas = []
            for selector in profile_selectors:
                elements = soup.select(selector)
                profile_areas.extend(elements)
                logger.info(f"Profile selector '{selector}' found {len(elements)} elements")
            
            # Also search entire page text for WhatsApp links
            text = response.text
            
            # WhatsApp patterns - more comprehensive
            whatsapp_patterns = [
                r'wa\.me/(\+?53\d+)',
                r'whatsapp\.com/send\?phone=(\+?53\d+)',
                r'api\.whatsapp\.com/send\?phone=(\+?53\d+)',
                r'href=["\']https://wa\.me/(\+?53\d+)["\']',
                r'href=["\']https://api\.whatsapp\.com/send\?phone=(\+?53\d+)["\']',
                # Look for phone numbers in user profile context
                r'data-phone=["\'](\+?53\d+)["\']',
                r'tel:(\+?53\d+)',
                # Raw phone numbers in profile areas
                r'(?:phone|telefono|tel|contact).*?(\+?53\d{8,})',
            ]
            
            # First search in profile areas specifically
            for area in profile_areas:
                area_text = str(area)
                for pattern in whatsapp_patterns:
                    matches = re.findall(pattern, area_text, re.IGNORECASE)
                    if matches:
                        logger.info(f"Profile area pattern '{pattern}' found: {matches}")
                        for phone in matches:
                            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                            if clean_phone.startswith('53') and len(clean_phone) >= 10:
                                formatted_phone = f"+{clean_phone}"
                                if formatted_phone not in found_phones:
                                    found_phones.append(formatted_phone)
                                    logger.info(f"✅ Found WhatsApp phone in profile: {formatted_phone}")
            
            # Fallback: search entire page
            if not found_phones:
                for pattern in whatsapp_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    logger.info(f"Page pattern '{pattern}' found {len(matches)} matches: {matches}")
                    
                    for phone in matches:
                        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                        if clean_phone.startswith('53') and len(clean_phone) >= 10:
                            formatted_phone = f"+{clean_phone}"
                            if formatted_phone not in found_phones:
                                found_phones.append(formatted_phone)
                                logger.info(f"✅ Found WhatsApp phone: {formatted_phone}")
            
            return found_phones
            
        except Exception as e:
            logger.error(f"Error extracting phones from {url}: {e}")
            return []
    
    def scrape(self, max_listings: int = 3) -> Dict[str, Any]:
        """Main scraping function"""
        start_time = time.time()
        
        logger.info(f"🚀 Starting simple scraper for {max_listings} listings")
        
        # Get listing links
        listings = self.get_listing_links(max_listings)
        if not listings:
            return {
                'success': False,
                'error': 'No listings found',
                'total_listings': 0,
                'total_phones': 0
            }
        
        logger.info(f"Found {len(listings)} listings to scrape")
        
        # Scrape each listing
        results = []
        total_phones = 0
        
        for i, listing in enumerate(listings, 1):
            logger.info(f"📄 Processing listing {i}: {listing['title']}")
            
            phones = self.extract_phones_from_page(listing['url'])
            
            if phones:
                results.append({
                    'title': listing['title'],
                    'url': listing['url'],
                    'phones': phones,
                    'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                total_phones += len(phones)
                logger.info(f"✅ Found {len(phones)} phones: {phones}")
            else:
                logger.info(f"❌ No phones found")
        
        duration = time.time() - start_time
        
        return {
            'success': True,
            'method': 'Simple Requests',
            'url': 'https://revolico.com',
            'total_listings': len(results),
            'total_phones': total_phones,
            'listings': results,
            'duration': f"{duration:.2f}s"
        }


if __name__ == "__main__":
    scraper = SimpleRevolicoScraper()
    results = scraper.scrape(max_listings=1)
    
    # Save results
    with open('simple_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))