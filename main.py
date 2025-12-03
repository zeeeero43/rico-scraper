#!/usr/bin/env python3
"""
Revolico Phone Number Scraper
Educational/Testing purposes only - respects website terms
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional
import os

from scraper_config import ScraperConfig
from phone_parser import PhoneNumberParser
from utils import setup_logging, save_to_json, get_random_user_agent
from proxy_manager import ProxyManager
from bypass_detector import BypassDetector

class RevolicoScraper:
    def __init__(self, use_proxy: bool = False):
        self.config = ScraperConfig()
        self.phone_parser = PhoneNumberParser()
        self.session = requests.Session()
        self.results = []
        self.errors = []
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager() if use_proxy else None
        self.bypass_detector = BypassDetector()
        
        # Setup logging
        self.logger = setup_logging()
        
        # Setup session with enhanced anti-detection headers
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8,de;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })

    def make_request(self, url: str, timeout: int = 20, retries: int = 3) -> Optional[requests.Response]:
        """Make a HTTP request with enhanced anti-detection and retry logic"""
        
        for attempt in range(retries):
            try:
                self.logger.info(f"Making request to: {url} (Attempt {attempt + 1}/{retries})")
                
                # Random delay between requests (longer on retries)
                base_delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
                retry_multiplier = 1 + (attempt * 0.5)  # Increase delay on retries
                delay = base_delay * retry_multiplier
                
                self.logger.info(f"Waiting {delay:.2f} seconds before request...")
                time.sleep(delay)
                
                # Always rotate user agent on retries
                if attempt > 0 or random.random() < 0.4:
                    new_ua = get_random_user_agent()
                    self.session.headers['User-Agent'] = new_ua
                    self.logger.info(f"Rotated User-Agent: {new_ua[:50]}...")
                
                # Randomize some headers for each request
                self.randomize_headers()
                
                # Use proxy if enabled
                proxies = None
                if self.use_proxy and self.proxy_manager:
                    proxies = self.proxy_manager.get_random_proxy()
                    if proxies:
                        self.logger.info(f"Using proxy: {proxies['http']}")
                
                response = self.session.get(url, timeout=timeout, allow_redirects=True, proxies=proxies)
                
                # Check for captcha or blocking
                if self.is_blocked_response(response):
                    self.logger.warning(f"Detected potential blocking/captcha on attempt {attempt + 1}")
                    if attempt < retries - 1:
                        backoff_delay = self.config.RETRY_DELAY * (2 ** attempt)
                        self.logger.info(f"Backing off for {backoff_delay} seconds...")
                        time.sleep(backoff_delay)
                        continue
                    else:
                        self.errors.append({
                            'url': url,
                            'error': 'Blocked after all retry attempts',
                            'timestamp': datetime.now().isoformat()
                        })
                        return None
                    
                response.raise_for_status()
                self.logger.info(f"Successfully fetched {url} (Status: {response.status_code}, Size: {len(response.content)} bytes)")
                return response
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # Analyze why we were blocked
                    blocking_reason = self.bypass_detector.analyze_blocking_reason(e.response)
                    self.logger.warning(f"403 Forbidden on attempt {attempt + 1} for {url}: {blocking_reason}")
                    
                    # Detect protection systems
                    protection = self.bypass_detector.detect_protection(e.response)
                    strategies = self.bypass_detector.suggest_bypass_strategy(protection)
                    
                    if strategies:
                        self.logger.info(f"Suggested bypass strategies: {strategies}")
                    
                    # Try bypass on last attempt
                    if attempt == retries - 1 and protection.get('cloudflare'):
                        self.logger.info("Attempting Cloudflare bypass...")
                        bypass_response = self.bypass_detector.simple_cloudflare_bypass(self.session, url)
                        if bypass_response and bypass_response.status_code == 200:
                            self.logger.info("Bypass successful!")
                            return bypass_response
                    
                    if attempt < retries - 1:
                        backoff_delay = self.config.RETRY_DELAY * (2 ** attempt)
                        self.logger.info(f"Retrying after {backoff_delay} seconds...")
                        time.sleep(backoff_delay)
                        continue
                
                error_msg = f"HTTP error for {url}: {e}"
                self.logger.error(error_msg)
                self.errors.append({
                    'url': url,
                    'error': f'HTTP {e.response.status_code}',
                    'timestamp': datetime.now().isoformat()
                })
                
                if attempt == retries - 1:
                    return None
                    
            except requests.exceptions.Timeout:
                error_msg = f"Timeout error for {url} on attempt {attempt + 1}"
                self.logger.error(error_msg)
                if attempt == retries - 1:
                    self.errors.append({
                        'url': url,
                        'error': 'Timeout after all retries',
                        'timestamp': datetime.now().isoformat()
                    })
                    return None
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Request error for {url} on attempt {attempt + 1}: {e}"
                self.logger.error(error_msg)
                if attempt == retries - 1:
                    self.errors.append({
                        'url': url,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    return None
        
        return None

    def is_blocked_response(self, response: requests.Response) -> bool:
        """Check if response indicates blocking or captcha"""
        # Check for common blocking indicators
        blocking_indicators = [
            'captcha', 'blocked', 'access denied', 'forbidden',
            'too many requests', 'rate limit', 'suspicious activity'
        ]
        
        response_text = response.text.lower()
        for indicator in blocking_indicators:
            if indicator in response_text:
                return True
                
        # Check for redirect to captcha pages
        if 'captcha' in response.url.lower():
            return True
            
        return False

    def randomize_headers(self):
        """Randomize some headers to avoid detection"""
        # Randomize accept-language
        languages = [
            'en-US,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-US,en;q=0.9,de;q=0.8,es;q=0.7',
            'es-ES,es;q=0.9,en;q=0.8',
            'de-DE,de;q=0.9,en;q=0.8'
        ]
        self.session.headers['Accept-Language'] = random.choice(languages)
        
        # Randomize viewport size for sec-ch headers
        viewports = ['1920', '1366', '1536', '1440', '2560']
        platforms = ['"Windows"', '"macOS"', '"Linux"']
        
        self.session.headers['sec-ch-ua-platform'] = random.choice(platforms)
        
        # Sometimes include referer
        if random.random() < 0.3:
            self.session.headers['Referer'] = 'https://www.google.com/'
        elif 'Referer' in self.session.headers:
            del self.session.headers['Referer']

    def try_alternative_urls(self) -> Optional[requests.Response]:
        """Try alternative URLs if main URL fails"""
        self.logger.info("Trying alternative URLs...")
        
        for url in self.config.ALTERNATIVE_URLS:
            self.logger.info(f"Trying alternative URL: {url}")
            response = self.make_request(url)
            if response and response.status_code == 200:
                self.logger.info(f"Success with alternative URL: {url}")
                self.config.BASE_URL = url  # Update base URL for future requests
                return response
            
        return None

    def get_homepage_listings(self) -> List[Dict[str, str]]:
        """Extract first 3 product listings from Revolico homepage"""
        self.logger.info("Starting to scrape Revolico homepage...")
        
        # First try main URL
        response = self.make_request(self.config.BASE_URL)
        
        # If main URL fails, try alternatives
        if not response:
            self.logger.warning("Main URL failed, trying alternatives...")
            response = self.try_alternative_urls()
            
        if not response:
            self.logger.error("All URLs failed")
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        listings = []
        
        try:
            # Look for common listing patterns on Revolico
            # Try multiple selectors as website structure may vary
            listing_selectors = [
                'div.listing-item',
                'div.ad-item',
                'div.classified-ad',
                'article',
                'div[class*="listing"]',
                'div[class*="ad"]'
            ]
            
            found_listings = []
            for selector in listing_selectors:
                elements = soup.select(selector)
                if elements:
                    found_listings = elements
                    self.logger.info(f"Found {len(elements)} listings using selector: {selector}")
                    break
            
            # If no specific selectors work, try finding links that look like listings
            if not found_listings:
                self.logger.info("Trying fallback method to find listings...")
                # Look for links that might be listings
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if any(keyword in href.lower() for keyword in ['anuncio', 'ad', 'listing', 'clasificado']):
                        found_listings.append(link.parent if link.parent else link)
                        if len(found_listings) >= 3:
                            break
            
            # Extract information from found listings
            for i, listing in enumerate(found_listings[:3]):
                try:
                    # Find the main link
                    link_element = listing.find('a', href=True)
                    if not link_element:
                        link_element = listing if listing.name == 'a' else None
                    
                    if link_element:
                        href = link_element.get('href', '')
                        
                        # Make URL absolute if it's relative
                        if href.startswith('/'):
                            href = self.config.BASE_URL.rstrip('/') + href
                        elif not href.startswith('http'):
                            href = self.config.BASE_URL.rstrip('/') + '/' + href
                        
                        # Extract title
                        title = link_element.get_text(strip=True)
                        if not title:
                            title = link_element.get('title', f'Listing {i+1}')
                        
                        listing_data = {
                            'title': title[:100],  # Limit title length
                            'url': href,
                            'found_at': datetime.now().isoformat()
                        }
                        
                        listings.append(listing_data)
                        self.logger.info(f"Found listing {i+1}: {title[:50]}...")
                        
                except Exception as e:
                    self.logger.error(f"Error processing listing {i+1}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error parsing homepage: {e}")
            
        self.logger.info(f"Successfully extracted {len(listings)} listings from homepage")
        return listings

    def scrape_listing_details(self, listing: Dict[str, str]) -> Dict[str, any]:
        """Scrape phone numbers and details from a listing page"""
        self.logger.info(f"Scraping details for: {listing['title']}")
        
        response = self.make_request(listing['url'])
        if not response:
            return {
                'title': listing['title'],
                'url': listing['url'],
                'phone_numbers': [],
                'scraped_at': datetime.now().isoformat(),
                'error': 'Failed to fetch page'
            }
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract phone numbers from the page
        phone_numbers = self.phone_parser.extract_phone_numbers(response.text)
        
        # Also try to extract from specific elements that commonly contain contact info
        contact_selectors = [
            'div[class*="contact"]',
            'div[class*="phone"]',
            'div[class*="telefono"]',
            'span[class*="phone"]',
            'p[class*="contact"]',
            '.contact-info',
            '.seller-info',
            '.ad-contact'
        ]
        
        for selector in contact_selectors:
            elements = soup.select(selector)
            for element in elements:
                element_text = element.get_text()
                element_phones = self.phone_parser.extract_phone_numbers(element_text)
                phone_numbers.extend(element_phones)
        
        # Remove duplicates while preserving order
        unique_phones = []
        seen = set()
        for phone in phone_numbers:
            if phone not in seen:
                unique_phones.append(phone)
                seen.add(phone)
        
        result = {
            'title': listing['title'],
            'url': listing['url'],
            'phone_numbers': unique_phones,
            'scraped_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"Found {len(unique_phones)} phone numbers for: {listing['title']}")
        return result

    def run_scraping(self) -> Dict[str, any]:
        """Main scraping workflow"""
        start_time = datetime.now()
        self.logger.info("Starting Revolico scraping session...")
        
        try:
            # Get homepage listings
            listings = self.get_homepage_listings()
            
            if not listings:
                self.logger.warning("No listings found on homepage")
                return self.generate_final_report(start_time)
            
            # Scrape details from each listing
            for listing in listings:
                try:
                    result = self.scrape_listing_details(listing)
                    self.results.append(result)
                    
                    # Add extra delay between listing scrapes
                    if listing != listings[-1]:  # Not the last item
                        extra_delay = random.uniform(1, 3)
                        self.logger.info(f"Extra delay between listings: {extra_delay:.2f}s")
                        time.sleep(extra_delay)
                        
                except Exception as e:
                    error_msg = f"Error scraping listing {listing['title']}: {e}"
                    self.logger.error(error_msg)
                    self.errors.append({
                        'url': listing['url'],
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
            
        except Exception as e:
            self.logger.error(f"Critical error in scraping workflow: {e}")
            self.errors.append({
                'error': f'Critical workflow error: {e}',
                'timestamp': datetime.now().isoformat()
            })
        
        return self.generate_final_report(start_time)

    def generate_final_report(self, start_time: datetime) -> Dict[str, any]:
        """Generate final scraping report"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        total_phones = sum(len(result.get('phone_numbers', [])) for result in self.results)
        
        report = {
            'scraping_date': start_time.isoformat(),
            'duration_seconds': duration,
            'results': self.results,
            'total_listings_found': len(self.results),
            'total_phone_numbers': total_phones,
            'errors': self.errors,
            'success_rate': len(self.results) / max(1, len(self.results) + len(self.errors)) * 100
        }
        
        self.logger.info(f"Scraping completed in {duration:.2f} seconds")
        self.logger.info(f"Found {len(self.results)} listings with {total_phones} total phone numbers")
        self.logger.info(f"Success rate: {report['success_rate']:.1f}%")
        
        return report


def main():
    """Main execution function"""
    print("=" * 60)
    print("REVOLICO PHONE NUMBER SCRAPER")
    print("Educational/Testing purposes only")
    print("=" * 60)
    
    scraper = RevolicoScraper()
    
    try:
        # Run the scraping
        report = scraper.run_scraping()
        
        # Save results to JSON
        output_file = "revolico_data.json"
        save_to_json(report, output_file)
        
        # Display results
        print(f"\n📊 SCRAPING RESULTS:")
        print(f"   • Total listings: {report['total_listings_found']}")
        print(f"   • Total phone numbers: {report['total_phone_numbers']}")
        print(f"   • Success rate: {report['success_rate']:.1f}%")
        print(f"   • Duration: {report['duration_seconds']:.2f} seconds")
        print(f"   • Errors: {len(report['errors'])}")
        
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
