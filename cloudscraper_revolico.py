#!/usr/bin/env python3
"""
CloudScraper approach for Revolico.com - specifically designed to bypass Cloudflare
"""

import cloudscraper
import json
import time
import random
import re
import gzip
import brotli
import io
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudScraperRevolico:
    def __init__(self):
        # CloudScraper automatically handles Cloudflare challenges
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10  # Wait between requests
        )
        
        # Add logger attribute for web app compatibility
        self.logger = logger
        
        # Enhanced scraping settings
        self.retry_delay = 5  # Seconds to wait for dynamic content
        
        # Additional headers
        self.scraper.headers.update({
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_listing_links(self, max_listings: int = 3) -> List[Dict[str, str]]:
        """Get listing links from homepage using CloudScraper"""
        try:
            logger.info("🌐 Loading revolico.com with CloudScraper...")
            response = self.scraper.get('https://www.revolico.com', timeout=60)
            
            logger.info(f"✅ Homepage response: {response.status_code}, {len(response.content)} bytes")
            logger.info(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            logger.info(f"Content-Encoding: {response.headers.get('content-encoding', 'none')}")
            
            # Handle compressed content safely
            content_text = ""
            try:
                content_encoding = response.headers.get('content-encoding', '').lower()
                
                if content_encoding == 'br':
                    try:
                        decompressed = brotli.decompress(response.content)
                        content_text = decompressed.decode('utf-8')
                        logger.info(f"✅ Brotli decompression successful: {len(content_text)} chars")
                    except Exception:
                        # Silent fallback to original content
                        content_text = response.text
                        logger.info(f"Using fallback content: {len(content_text)} chars")
                elif content_encoding == 'gzip' or response.content.startswith(b'\x1f\x8b'):
                    try:
                        decompressed = gzip.decompress(response.content)
                        content_text = decompressed.decode('utf-8')
                        logger.info(f"✅ Gzip decompression successful: {len(content_text)} chars")
                    except Exception:
                        content_text = response.text
                        logger.info(f"Using fallback content: {len(content_text)} chars")
                else:
                    content_text = response.text
                    logger.info(f"Using regular content: {len(content_text)} chars")
                    
            except Exception as decompress_error:
                logger.info(f"Content handling fallback: {len(response.text)} chars")
                content_text = response.text
            
            if 'just a moment' in response.text.lower():
                logger.warning("Still getting challenge page, waiting longer...")
                time.sleep(30)
                response = self.scraper.get('https://www.revolico.com', timeout=60)
                logger.info(f"Second attempt: {response.status_code}, {len(response.text)} chars")
            
            # Save homepage for analysis
            with open('homepage_debug.html', 'w', encoding='utf-8') as f:
                f.write(content_text)
            logger.info("💾 Saved homepage to homepage_debug.html")
            
            soup = BeautifulSoup(content_text, 'html.parser')
            
            # Find listing links
            listing_links = []
            
            # First, let's see what we have
            all_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(all_links)} total links")
            
            # Check for any item links at all
            item_links = [link for link in all_links if '/item/' in str(link.get('href', ''))]
            logger.info(f"Found {len(item_links)} links containing '/item/'")
            
            # Try multiple selectors (broad to narrow)
            selectors = [
                'a[href*="/item/"]',  # Any item link
                'a[href*="/item/"]:not([href*="/item/publish"])',
                'a[href^="/item/"]',
                '[data-cy="adName"] a',
                'a[data-cy="adName"]',
                '.listing-title a',
                '.ad-title a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                logger.info(f"Selector '{selector}' found {len(links)} elements")
                
                for link in links:
                    if len(listing_links) >= max_listings:
                        break
                        
                    href = link.get('href') if hasattr(link, 'get') else None
                    if href and '/item/' in str(href) and '/item/publish' not in str(href):
                        href_str = str(href)
                        if not href_str.startswith('http'):
                            href_str = 'https://www.revolico.com' + href_str
                        
                        # Avoid duplicates
                        if href_str not in [existing['url'] for existing in listing_links]:
                            title_elem = link.get_text(strip=True) if hasattr(link, 'get_text') else str(link)
                            
                            listing_links.append({
                                'url': href_str,
                                'title': title_elem
                            })
                            logger.info(f"✓ Found listing: {href_str}")
                
                # Keep trying selectors until we have enough listings
                if len(listing_links) >= max_listings:
                    break
            
            return listing_links[:max_listings]
            
        except Exception as e:
            logger.error(f"Error getting listing links: {e}")
            return []
    
    def extract_phones_from_listing(self, url: str, emit_log=None) -> tuple:
        """Extract phone numbers and customer name from a listing page, focusing on profile areas"""
        try:
            logger.info(f"📄 Visiting: {url}")
            
            # Random delay
            time.sleep(random.uniform(3, 7))
            
            response = self.scraper.get(url, timeout=60)
            logger.info(f"Page loaded: {response.status_code}, {len(response.text)} chars")
            
            if 'just a moment' in response.text.lower():
                logger.warning("Got challenge page, retrying...")
                time.sleep(20)
                response = self.scraper.get(url, timeout=60)
                logger.info(f"Retry: {response.status_code}, {len(response.text)} chars")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            found_phones = []
            
            # Save page content for debugging (only for first few listings)
            if not hasattr(self, '_debug_pages_saved'):
                self._debug_pages_saved = 0
            
            if self._debug_pages_saved < 3:  # Save first 3 pages for debugging
                debug_filename = f"debug_page_{self._debug_pages_saved + 1}.html"
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"💾 Saved page content to {debug_filename} ({len(response.text)} chars)")
                self._debug_pages_saved += 1
            
            # Extract real customer name with comprehensive strategy
            customer_name = None
            
            # ENHANCED: Check page completeness and try multiple strategies
            has_profile_section = len(soup.select('div[class*="sc-3b03e06d"]')) > 0
            logger.info(f"🔍 Profile section available: {has_profile_section}")
            
            # Strategy A: Try to find any user-related elements (from user's real HTML)
            user_elements_check = [
                '[data-cy="userFullname"]',      # Direct target
                '[data-cy="adUser"]',            # Profile link container
                'div[class*="sc-3b03e06d"]',     # Profile container class
                'p[class*="bxTJTW"]'             # Name text class
            ]
            
            elements_found = {}
            for selector in user_elements_check:
                elements = soup.select(selector)
                elements_found[selector] = len(elements)
                logger.info(f"🔍 '{selector}': {len(elements)} elements")
            
            # Debug: Check if userFullname elements exist
            userFullname_debug = soup.select('[data-cy="userFullname"]')
            logger.info(f"🔍 Found {len(userFullname_debug)} [data-cy='userFullname'] elements")
            for i, elem in enumerate(userFullname_debug):
                text = elem.get_text(strip=True)
                logger.info(f"  Element {i+1}: '{text}' (tag: {elem.name}, class: {elem.get('class', 'no-class')})")
            
            # Strategy 1: Look for specific name elements with exact CSS patterns
            name_selectors = [
                'p[data-cy="userFullname"]',  # Most specific first
                '[data-cy="userFullname"]',   # Any element with userFullname
                'p.sc-3b03e06d-2.bxTJTW',     # Specific class combination
                '.sc-3b03e06d-2.bxTJTW',      # Class fallback
                'div.sc-3b03e06d-0 p',        # Container-based search
                'a[data-cy="adUser"] p',      # Profile link approach
                'div[class*="sc-3b03e06d"] p[data-cy="userFullname"]'  # Combined approach
            ]
            
            for selector in name_selectors:
                try:
                    name_elements = soup.select(selector)
                    logger.info(f"🔍 Selector '{selector}' found {len(name_elements)} elements")
                    
                    if name_elements:
                        for elem in name_elements:
                            text = elem.get_text(strip=True)
                            logger.info(f"  Checking text: '{text}'")
                            
                            # Better validation for real names
                            if (text and 
                                len(text) > 2 and 
                                not text.isdigit() and 
                                'seguir' not in text.lower() and
                                not text.lower().startswith('$') and
                                not text.lower().startswith('cup') and
                                not text.lower().startswith('usd')):
                                
                                customer_name = text
                                logger.info(f"✅ FOUND REAL CUSTOMER NAME via '{selector}': '{customer_name}'")
                                break
                        if customer_name:
                            break
                except Exception as e:
                    logger.info(f"❌ Error with selector '{selector}': {e}")
                    continue
            
            # Strategy 2: Parse from WhatsApp or contact areas
            if not customer_name:
                # Look for names near phone numbers in profile areas
                profile_text = ""
                for profile_elem in soup.select('div[class*="sc-7ea21534"], div[class*="sc-2a048850"]'):
                    profile_text += profile_elem.get_text() + " "
                
                # Look for name patterns near phone numbers
                import re
                name_patterns = [
                    r'(?:contactar?|llamar|escribir)\s+a\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[:\-]\s*\+?53\d+',
                    r'\+?53\d+\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
                ]
                
                for pattern in name_patterns:
                    match = re.search(pattern, profile_text)
                    if match:
                        potential_name = match.group(1).strip()
                        if len(potential_name) > 2 and not potential_name.isdigit():
                            customer_name = potential_name
                            logger.info(f"✅ Found customer name via pattern: {customer_name}")
                            break
            
            # Final assessment
            if not customer_name:
                logger.info("ℹ️  Kein Kundenname verfügbar - JavaScript-geladene Profildaten nicht in Server-Response")
                logger.info("ℹ️  Verwende intelligente Titel-basierte Namensextraktion als professionellen Fallback")
                customer_name = None  # Will be handled by fallback in app.py
            
            # Focus on user profile areas (from user's example)
            profile_selectors = [
                'div[class*="sc-7ea21534"]',  # From user's example
                'div[class*="sc-2a048850"]', 
                'div[class*="kMsUxE"]',
                '[data-cy="adUser"]',
                'div[class*="sc-3b03e06d"]',
                '.user-profile',
                '.contact-info',
                '.seller-contact'
            ]
            
            profile_elements = []
            for selector in profile_selectors:
                elements = soup.select(selector)
                profile_elements.extend(elements)
                logger.info(f"Profile selector '{selector}' found {len(elements)} elements")
            
            logger.info(f"Total profile elements found: {len(profile_elements)}")
            
            # Search within profile elements for WhatsApp links and phone numbers
            for element in profile_elements:
                element_html = str(element)
                
                # WhatsApp link patterns
                whatsapp_patterns = [
                    r'wa\.me/(\+?53\d+)',
                    r'whatsapp\.com/send\?phone=(\+?53\d+)',
                    r'api\.whatsapp\.com/send\?phone=(\+?53\d+)',
                    r'href=["\']https://wa\.me/(\+?53\d+)["\']',
                    r'href=["\']https://api\.whatsapp\.com/send\?phone=(\+?53\d+)["\']',
                    # Phone data attributes
                    r'data-phone=["\'](\+?53\d+)["\']',
                    r'tel:(\+?53\d+)',
                    # Text patterns in profile context
                    r'(?:phone|telefono|tel|contact).*?(\+?53\d{8,})',
                ]
                
                for pattern in whatsapp_patterns:
                    matches = re.findall(pattern, element_html, re.IGNORECASE)
                    if matches:
                        logger.info(f"Profile pattern '{pattern}' found: {matches}")
                        for phone in matches:
                            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                            if clean_phone.startswith('53') and len(clean_phone) >= 10:
                                formatted_phone = f"+{clean_phone}"
                                if formatted_phone not in found_phones:
                                    found_phones.append(formatted_phone)
                                    logger.info(f"✅ Found WhatsApp phone in profile: {formatted_phone}")
            
            # Fallback: search entire page for WhatsApp patterns
            if not found_phones:
                logger.info("No phones in profile areas, searching entire page...")
                page_text = response.text
                
                fallback_patterns = [
                    r'wa\.me/(\+?53\d+)',
                    r'whatsapp\.com/send\?phone=(\+?53\d+)',
                    r'href=["\']https://wa\.me/(\+?53\d+)["\']'
                ]
                
                for pattern in fallback_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    logger.info(f"Fallback pattern '{pattern}' found {len(matches)} matches: {matches}")
                    
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
    
    def scrape(self, max_listings: int = 3, socketio=None) -> Dict[str, Any]:
        """Main scraping function with optional real-time updates"""
        start_time = time.time()
        
        def emit_log(level, message):
            if socketio:
                socketio.emit('log_message', {
                    'level': level.upper(),
                    'message': message,
                    'timestamp': time.strftime('%H:%M:%S')
                })
            logger.log(getattr(logging, level.upper()), message)
        
        emit_log('info', f"🚀 Starting CloudScraper for {max_listings} listings")
        
        # Get listing links  
        emit_log('info', f"🌐 Loading revolico.com homepage...")
        listings = self.get_listing_links(max_listings)
        if not listings:
            emit_log('error', 'No listings found on homepage')
            return {
                'success': False,
                'error': 'No listings found',
                'total_listings': 0,
                'total_phones': 0
            }
        
        emit_log('info', f"✅ Found {len(listings)} listings to scrape")
        
        # Scrape each listing
        results = []
        total_phones = 0
        
        for i, listing in enumerate(listings, 1):
            emit_log('info', f"📄 Processing listing {i}/{len(listings)}: {listing['title'][:60]}...")
            
            phones = self.extract_phones_from_listing(listing['url'])
            
            if phones:
                results.append({
                    'title': listing['title'],
                    'url': listing['url'],
                    'phones': phones,
                    'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                total_phones += len(phones)
                emit_log('info', f"✅ Found {len(phones)} phones: {phones}")
            else:
                emit_log('warning', f"❌ No phones found in listing {i}")
        
        duration = time.time() - start_time
        
        duration_text = f"{duration:.2f}s"
        
        final_results = {
            'success': True,
            'method': 'CloudScraper (Profile Area Focus)',
            'url': 'https://revolico.com',
            'total_listings': len(results),
            'total_phones': total_phones,
            'listings': results,
            'duration': duration_text
        }
        
        emit_log('info', f"✅ Scraping completed: {len(results)} listings, {total_phones} phones in {duration_text}")
        
        return final_results
    
    def scrape_revolico(self, max_listings: int = 3) -> Dict[str, Any]:
        """Web app compatible wrapper for scrape method"""
        results = self.scrape(max_listings)
        
        # Convert to expected web app format (direct format, no nested 'results')
        return {
            'success': results['success'],
            'method': results['method'],
            'url': results['url'],
            'duration': results['duration'],
            'total_listings': results['total_listings'],
            'total_phones': results['total_phones'],
            'listings': results['listings']
        }


if __name__ == "__main__":
    scraper = CloudScraperRevolico()
    results = scraper.scrape(max_listings=1)
    
    # Save results
    with open('cloudscraper_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))