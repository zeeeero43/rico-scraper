#!/usr/bin/env python3
"""
Enhanced requests-based scraper with advanced Cloudflare bypass
Fallback solution when Selenium/Chrome is not available
"""

import requests
import time
import random
import json
import os
import pickle
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from phone_parser import PhoneNumberParser
from utils import setup_logging, save_to_json

class AdvancedRequestsScraper:
    """Advanced requests-based scraper with enhanced anti-detection"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.phone_parser = PhoneNumberParser()
        self.session = requests.Session()
        self.cookies_file = "session_cookies.json"
        
        # Enhanced configuration
        self.config = {
            'urls': {
                'main': [
                    'https://m.revolico.com',
                    'https://mobile.revolico.com', 
                    'https://www.revolico.com',
                    'https://revolico.com'
                ],
                'fallback': [
                    'https://www.revolico.com/rss',
                    'https://www.revolico.com/feed.xml',
                    'https://www.revolico.com/sitemap.xml',
                    'https://www.revolico.com/clasificados',
                    'https://www.revolico.com/anuncios'
                ],
                'alternatives': [
                    'https://www.porlalivre.com',
                    'https://www.encuentra24.com/cuba-es',
                    'https://cuba.clasificados.com'
                ]
            },
            'delays': {
                'min_request': 12,
                'max_request': 18,
                'jitter': 4,
                'session_build': 5,
                'retry_backoff': 15
            },
            'headers': {
                'base': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8,de;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                },
                'mobile_agents': [
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                    'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.138 Mobile/15E148 Safari/604.1',
                    'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
                ],
                'desktop_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
                ]
            }
        }
        
        self.setup_session()
    
    def setup_session(self, mobile_mode: bool = True):
        """Setup session with anti-detection headers"""
        self.logger.info(f"Setting up session (mobile_mode: {mobile_mode})")
        
        # Choose user agent
        if mobile_mode:
            user_agent = random.choice(self.config['headers']['mobile_agents'])
            self.session.headers['sec-ch-ua-mobile'] = '?1'
        else:
            user_agent = random.choice(self.config['headers']['desktop_agents'])
            self.session.headers['sec-ch-ua-mobile'] = '?0'
        
        # Set headers
        self.session.headers.update(self.config['headers']['base'])
        self.session.headers['User-Agent'] = user_agent
        
        # Load saved cookies if available
        self.load_session_cookies()
        
        # Configure session
        self.session.max_redirects = 10
        
        self.logger.info(f"Session configured with User-Agent: {user_agent[:50]}...")
    
    def save_session_cookies(self):
        """Save current session cookies"""
        try:
            cookies_dict = {}
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = {
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path
                }
            
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies_dict, f, indent=2)
                
            self.logger.info(f"Saved {len(cookies_dict)} cookies to {self.cookies_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save cookies: {e}")
    
    def load_session_cookies(self):
        """Load saved session cookies"""
        if not os.path.exists(self.cookies_file):
            return
            
        try:
            with open(self.cookies_file, 'r') as f:
                cookies_dict = json.load(f)
            
            for name, cookie_data in cookies_dict.items():
                self.session.cookies.set(
                    name=name,
                    value=cookie_data['value'],
                    domain=cookie_data.get('domain'),
                    path=cookie_data.get('path', '/')
                )
            
            self.logger.info(f"Loaded {len(cookies_dict)} cookies from {self.cookies_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load cookies: {e}")
    
    def randomize_headers(self):
        """Randomize headers for each request"""
        # Randomize Accept-Language
        languages = [
            'es-ES,es;q=0.9,en;q=0.8',
            'es-CU,es;q=0.9,en;q=0.8',
            'es-AR,es;q=0.9,en;q=0.8,fr;q=0.7',
            'en-US,en;q=0.9,es;q=0.8',
            'es;q=0.9,en;q=0.8,de;q=0.7'
        ]
        self.session.headers['Accept-Language'] = random.choice(languages)
        
        # Sometimes add/remove referer
        if random.random() < 0.4:
            referers = [
                'https://www.google.com/',
                'https://www.google.es/search?q=revolico+cuba',
                'https://duckduckgo.com/',
                'https://www.bing.com/'
            ]
            self.session.headers['Referer'] = random.choice(referers)
        elif 'Referer' in self.session.headers:
            del self.session.headers['Referer']
        
        # Occasionally modify sec-ch-ua
        if random.random() < 0.3:
            brands = [
                '"Not_A Brand";v="8", "Chromium";v="120"',
                '"Chromium";v="120", "Not_A Brand";v="8"',
                '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="8"'
            ]
            self.session.headers['sec-ch-ua'] = random.choice(brands)
    
    def build_session_with_google(self) -> bool:
        """Build session by visiting Google first"""
        try:
            self.logger.info("Building session with Google referer...")
            
            # Visit Google first
            google_response = self.session.get(
                'https://www.google.com/search',
                params={'q': 'revolico cuba clasificados'},
                timeout=15
            )
            
            if google_response.status_code == 200:
                self.logger.info("Successfully visited Google")
                time.sleep(random.uniform(2, 4))
                return True
            else:
                self.logger.warning(f"Google returned status: {google_response.status_code}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Failed to build Google session: {e}")
            return False
    
    def detect_protection(self, response: requests.Response) -> Dict[str, bool]:
        """Detect protection mechanisms"""
        content = response.text.lower()
        headers = {k.lower(): v.lower() for k, v in response.headers.items()}
        
        protection = {
            'cloudflare': False,
            'captcha': False,
            'rate_limit': False,
            'js_challenge': False,
            'access_denied': False,
            'success': False
        }
        
        # Cloudflare detection
        cf_indicators = [
            'cloudflare', 'cf-ray', 'checking your browser',
            'please wait while we check', 'ddos protection',
            'security check', 'just a moment'
        ]
        
        if any(indicator in content for indicator in cf_indicators):
            protection['cloudflare'] = True
        
        if 'cf-ray' in headers or (response.status_code == 503 and 'cloudflare' in content):
            protection['cloudflare'] = True
            
        # CAPTCHA detection
        if any(word in content for word in ['captcha', 'recaptcha', 'hcaptcha']):
            protection['captcha'] = True
            
        # Rate limiting
        if response.status_code == 429 or 'rate limit' in content:
            protection['rate_limit'] = True
            
        # JavaScript challenge
        if 'javascript' in content and ('enable' in content or 'disabled' in content):
            protection['js_challenge'] = True
            
        # Access denied
        if response.status_code in [403, 406] or 'access denied' in content:
            protection['access_denied'] = True
        
        # Success detection
        if (response.status_code == 200 and 
            'revolico' in content and 
            not any([protection['cloudflare'], protection['captcha'], 
                    protection['access_denied'], protection['js_challenge']])):
            protection['success'] = True
        
        return protection
    
    def make_enhanced_request(self, url: str, max_retries: int = 3) -> Tuple[bool, Dict]:
        """Make request with enhanced anti-detection"""
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Requesting {url} (attempt {attempt + 1}/{max_retries})")
                
                # Add delay with exponential backoff
                if attempt > 0:
                    backoff_delay = self.config['delays']['retry_backoff'] * (2 ** (attempt - 1))
                    jitter = random.uniform(-self.config['delays']['jitter'], 
                                          self.config['delays']['jitter'])
                    total_delay = backoff_delay + jitter
                    self.logger.info(f"Backing off for {total_delay:.2f} seconds...")
                    time.sleep(total_delay)
                else:
                    # Normal delay for first attempt
                    delay = random.uniform(self.config['delays']['min_request'],
                                         self.config['delays']['max_request'])
                    jitter = random.uniform(-self.config['delays']['jitter'],
                                          self.config['delays']['jitter'])
                    total_delay = delay + jitter
                    self.logger.info(f"Waiting {total_delay:.2f} seconds...")
                    time.sleep(total_delay)
                
                # Randomize headers for each attempt
                self.randomize_headers()
                
                # Make the request
                response = self.session.get(url, timeout=20, allow_redirects=True)
                
                # Analyze response
                protection = self.detect_protection(response)
                
                result = {
                    'url': url,
                    'status_code': response.status_code,
                    'protection': protection,
                    'content_length': len(response.content),
                    'headers': dict(response.headers),
                    'attempt': attempt + 1
                }
                
                if protection['success']:
                    self.logger.info(f"Successfully accessed {url}")
                    self.save_session_cookies()
                    return True, result
                
                elif protection['cloudflare'] or protection['js_challenge']:
                    self.logger.warning(f"Cloudflare/JS challenge detected: {url}")
                    # Try session rebuilding on next attempt
                    if attempt < max_retries - 1:
                        self.logger.info("Rebuilding session...")
                        self.build_session_with_google()
                        
                elif protection['rate_limit']:
                    self.logger.warning(f"Rate limited: {url}")
                    if attempt < max_retries - 1:
                        longer_delay = self.config['delays']['retry_backoff'] * 2
                        self.logger.info(f"Rate limited, waiting {longer_delay} seconds...")
                        time.sleep(longer_delay)
                        
                elif protection['access_denied']:
                    self.logger.warning(f"Access denied: {url}")
                    
                elif protection['captcha']:
                    self.logger.warning(f"CAPTCHA required: {url}")
                    return False, result
                
                else:
                    self.logger.warning(f"Unknown blocking: {url} - {protection}")
                
                if attempt == max_retries - 1:
                    return False, result
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout for {url}")
                if attempt == max_retries - 1:
                    return False, {'url': url, 'error': 'timeout', 'attempt': attempt + 1}
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {url}: {e}")
                if attempt == max_retries - 1:
                    return False, {'url': url, 'error': str(e), 'attempt': attempt + 1}
        
        return False, {'url': url, 'error': 'max_retries_exceeded'}
    
    def find_working_url(self) -> Tuple[Optional[str], Dict]:
        """Find a working URL using multiple strategies"""
        results = {
            'attempts': [],
            'working_url': None,
            'strategy_used': None
        }
        
        # Strategy 1: Try main URLs with mobile session
        self.logger.info("Strategy 1: Mobile URLs with session")
        self.setup_session(mobile_mode=True)
        
        for url in self.config['urls']['main']:
            success, result = self.make_enhanced_request(url)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'mobile_main'
                return url, results
        
        # Strategy 2: Desktop session with Google referer
        self.logger.info("Strategy 2: Desktop session with Google referer")
        self.setup_session(mobile_mode=False)
        
        if self.build_session_with_google():
            for url in self.config['urls']['main'][:2]:  # Try top 2
                success, result = self.make_enhanced_request(url, max_retries=2)
                results['attempts'].append(result)
                
                if success:
                    results['working_url'] = url
                    results['strategy_used'] = 'desktop_google'
                    return url, results
        
        # Strategy 3: Try fallback URLs
        self.logger.info("Strategy 3: Fallback URLs")
        for url in self.config['urls']['fallback']:
            success, result = self.make_enhanced_request(url, max_retries=2)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'fallback'
                return url, results
        
        # Strategy 4: Alternative sites
        self.logger.info("Strategy 4: Alternative Cuban sites")
        for url in self.config['urls']['alternatives']:
            success, result = self.make_enhanced_request(url, max_retries=1)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'alternative'
                return url, results
        
        self.logger.error("All strategies failed")
        return None, results
    
    def extract_listings_from_html(self, html_content: str, base_url: str) -> List[Dict]:
        """Extract listings from HTML content"""
        listings = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Multiple selectors for different site layouts
            selectors = [
                'div[class*="listing"]',
                'div[class*="ad"]',
                'article',
                'div[class*="anuncio"]',
                'div[class*="clasificado"]',
                '.listing-item',
                '.ad-item',
                'a[href*="/anuncio"]',
                'a[href*="/ad/"]',
                'a[href*="clasificado"]'
            ]
            
            found_elements = []
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    found_elements = elements
                    self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    break
            
            # Fallback: look for any relevant links
            if not found_elements:
                all_links = soup.find_all('a', href=True)
                found_elements = [
                    link for link in all_links
                    if any(keyword in link.get('href', '').lower()
                          for keyword in ['anuncio', 'ad', 'listing', 'clasificado'])
                ]
            
            # Extract listing information
            for i, element in enumerate(found_elements[:5]):  # Limit to 5 listings
                try:
                    if element.name == 'a':
                        link_url = element.get('href')
                        title = element.get_text(strip=True)
                    else:
                        link_element = element.find('a', href=True)
                        if link_element:
                            link_url = link_element.get('href')
                            title = link_element.get_text(strip=True)
                        else:
                            continue
                    
                    if not title:
                        title = element.get('title') or f'Listing {i+1}'
                    
                    # Make URL absolute
                    if link_url:
                        if link_url.startswith('/'):
                            link_url = urljoin(base_url, link_url)
                        elif not link_url.startswith('http'):
                            link_url = urljoin(base_url, link_url)
                    
                    listing = {
                        'title': title[:100],
                        'url': link_url,
                        'found_at': datetime.now().isoformat(),
                        'source_page': base_url
                    }
                    
                    listings.append(listing)
                    self.logger.info(f"Extracted listing {i+1}: {title[:50]}...")
                    
                except Exception as e:
                    self.logger.warning(f"Error extracting listing {i+1}: {e}")
                    continue
            
            return listings
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
            return []
    
    def scrape_listing_details(self, listing: Dict) -> Dict:
        """Scrape phone numbers from listing detail page"""
        self.logger.info(f"Scraping details for: {listing['title']}")
        
        try:
            success, result = self.make_enhanced_request(listing['url'])
            
            if not success:
                return {
                    'title': listing['title'],
                    'url': listing['url'],
                    'phone_numbers': [],
                    'scraped_at': datetime.now().isoformat(),
                    'error': f"Failed to access page: {result.get('error', 'Unknown')}"
                }
            
            # Extract phone numbers from page
            response = self.session.get(listing['url'])  # Get fresh response
            phone_numbers = self.phone_parser.extract_phone_numbers(response.text)
            
            # Remove duplicates
            unique_phones = list(dict.fromkeys(phone_numbers))
            
            result_data = {
                'title': listing['title'],
                'url': listing['url'],
                'phone_numbers': unique_phones,
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Found {len(unique_phones)} phone numbers")
            return result_data
            
        except Exception as e:
            self.logger.error(f"Error scraping listing details: {e}")
            return {
                'title': listing['title'],
                'url': listing['url'],
                'phone_numbers': [],
                'scraped_at': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def run_scraping(self, max_listings: int = 3) -> Dict:
        """Main scraping workflow"""
        start_time = datetime.now()
        self.logger.info("Starting enhanced requests scraping session...")
        
        results = {
            'scraping_date': start_time.isoformat(),
            'method': 'enhanced_requests',
            'results': [],
            'url_attempts': [],
            'strategy_used': None,
            'working_url': None,
            'errors': [],
            'total_listings_found': 0,
            'total_phone_numbers': 0,
            'duration_seconds': 0
        }
        
        try:
            # Find working URL
            working_url, url_results = self.find_working_url()
            
            results['url_attempts'] = url_results['attempts']
            results['strategy_used'] = url_results['strategy_used']
            results['working_url'] = working_url
            
            if not working_url:
                raise Exception("No working URL found - all strategies failed")
            
            # Get homepage content
            response = self.session.get(working_url)
            
            # Extract listings
            listings = self.extract_listings_from_html(response.text, working_url)
            
            if not listings:
                self.logger.warning("No listings found on homepage")
                # Try a different approach or URL
                results['errors'].append({
                    'error': 'No listings found on homepage',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Limit to requested number
            listings = listings[:max_listings]
            
            # Scrape details from each listing
            for listing in listings:
                try:
                    result = self.scrape_listing_details(listing)
                    results['results'].append(result)
                    
                except Exception as e:
                    error_msg = f"Error scraping listing {listing['title']}: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append({
                        'url': listing['url'],
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
            
        except Exception as e:
            error_msg = f"Critical error in scraping workflow: {e}"
            self.logger.error(error_msg)
            results['errors'].append({
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
        
        # Calculate final statistics
        end_time = datetime.now()
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        results['total_listings_found'] = len(results['results'])
        results['total_phone_numbers'] = sum(len(r.get('phone_numbers', [])) for r in results['results'])
        
        self.logger.info(f"Scraping completed in {results['duration_seconds']:.2f} seconds")
        self.logger.info(f"Found {results['total_listings_found']} listings with {results['total_phone_numbers']} total phone numbers")
        
        return results


def main():
    """Main execution function"""
    print("=" * 60)
    print("ENHANCED REQUESTS REVOLICO SCRAPER")
    print("Advanced Cloudflare bypass without browser dependencies")
    print("=" * 60)
    
    scraper = AdvancedRequestsScraper()
    
    try:
        # Run the scraping
        report = scraper.run_scraping(max_listings=3)
        
        # Save results to JSON
        output_file = "enhanced_requests_data.json"
        save_to_json(report, output_file)
        
        # Display results
        print(f"\n📊 SCRAPING RESULTS:")
        print(f"   • Method: {report.get('method', 'unknown')}")
        print(f"   • Strategy used: {report.get('strategy_used', 'Unknown')}")
        print(f"   • Working URL: {report.get('working_url', 'None')}")
        print(f"   • Total listings: {report['total_listings_found']}")
        print(f"   • Total phone numbers: {report['total_phone_numbers']}")
        print(f"   • Duration: {report['duration_seconds']:.2f} seconds")
        print(f"   • Errors: {len(report['errors'])}")
        print(f"   • URL attempts: {len(report['url_attempts'])}")
        
        if report['results']:
            print(f"\n📋 FOUND LISTINGS:")
            for i, result in enumerate(report['results'], 1):
                phones = result.get('phone_numbers', [])
                print(f"   {i}. {result['title'][:50]}...")
                print(f"      📞 Phones: {phones if phones else 'None found'}")
                print(f"      🔗 URL: {result['url']}")
                print()
        
        if report['errors']:
            print(f"\n⚠️  ERRORS ENCOUNTERED:")
            for error in report['errors']:
                print(f"   • {error}")
        
        print(f"\n💾 Results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\n\n❌ Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Critical error: {e}")
        logging.error(f"Critical error in main: {e}")


if __name__ == "__main__":
    main()