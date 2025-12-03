#!/usr/bin/env python3
"""
Enhanced Selenium-based Revolico scraper with Cloudflare bypass
"""

import time
import random
import json
import os
import pickle
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from phone_parser import PhoneNumberParser
from utils import setup_logging, save_to_json

class CloudflareBypasser:
    """Advanced Cloudflare bypass using Selenium"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.phone_parser = PhoneNumberParser()
        self.driver = None
        self.session_cookies_file = "session_cookies.pkl"
        
        # Enhanced configuration
        self.config = {
            'main_urls': [
                'https://m.revolico.com',
                'https://mobile.revolico.com', 
                'https://www.revolico.com',
                'https://revolico.com'
            ],
            'fallback_urls': [
                'https://www.revolico.com/rss',
                'https://www.revolico.com/feed',
                'https://www.revolico.com/api/listings',
                'https://www.revolico.com/clasificados',
                'https://www.revolico.com/anuncios'
            ],
            'alternative_sites': [
                'https://www.porlalivre.com',
                'https://www.encuentra24.com/cuba',
                'https://cuba.clasificados.com'
            ],
            'delays': {
                'min_request': 10,
                'max_request': 15,
                'jitter': 3,
                'page_load': 3,
                'scroll_delay': 2
            }
        }
        
    def setup_driver(self, mobile_mode: bool = True) -> webdriver.Chrome:
        """Setup Chrome driver with anti-detection options"""
        self.logger.info(f"Setting up Chrome driver (mobile_mode: {mobile_mode})")
        
        chrome_options = Options()
        
        # Essential options for headless environments like Replit
        chrome_options.add_argument('--headless=new')  # Use new headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # Memory and performance optimization for cloud environments
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--disable-background-networking')
        
        # Anti-detection (more conservative approach)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Essential security options for cloud environments
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-default-apps')
        
        # Mobile emulation if requested
        if mobile_mode:
            mobile_emulation = {
                "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
            }
            chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        else:
            # Desktop user agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        # Window size
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            # Try to use system Chrome first, then fall back to webdriver-manager
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/snap/bin/chromium'
            ]
            
            chrome_binary = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break
            
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                self.logger.info(f"Using system Chrome at: {chrome_binary}")
                
                # Try different service approaches
                try:
                    # Try system chromedriver first
                    service = Service()
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                except:
                    # Fall back to webdriver-manager
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Fall back to webdriver-manager
                self.logger.info("No system Chrome found, using webdriver-manager")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Test if driver is working
            driver.get("data:text/html,<html><body>Test</body></html>")
            
            # Execute script to hide webdriver property (only if not in strict mode)
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass  # Ignore if this fails in some environments
            
            self.logger.info("Chrome driver initialized successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            # Log more details for debugging
            self.logger.error(f"Chrome paths checked: {chrome_paths}")
            self.logger.error(f"Working directory: {os.getcwd()}")
            raise Exception(f"Chrome setup failed: {e}. This might be due to missing Chrome installation in the environment.")
    
    def load_session_cookies(self, driver: webdriver.Chrome, domain: str):
        """Load saved session cookies"""
        if os.path.exists(self.session_cookies_file):
            try:
                with open(self.session_cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                
                # Navigate to domain first
                driver.get(f"https://{domain}")
                time.sleep(2)
                
                for cookie in cookies:
                    if cookie.get('domain') in domain:
                        try:
                            driver.add_cookie(cookie)
                        except Exception as e:
                            self.logger.warning(f"Could not add cookie: {e}")
                
                self.logger.info(f"Loaded {len(cookies)} session cookies")
                
            except Exception as e:
                self.logger.warning(f"Failed to load session cookies: {e}")
    
    def save_session_cookies(self, driver: webdriver.Chrome):
        """Save current session cookies"""
        try:
            cookies = driver.get_cookies()
            with open(self.session_cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info(f"Saved {len(cookies)} session cookies")
        except Exception as e:
            self.logger.warning(f"Failed to save session cookies: {e}")
    
    def build_session_with_google_referer(self, driver: webdriver.Chrome) -> bool:
        """Build session by coming from Google"""
        try:
            self.logger.info("Building session with Google referer...")
            
            # First visit Google
            driver.get("https://www.google.com")
            time.sleep(random.uniform(2, 4))
            
            # Search for Revolico
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                
                # Type search query slowly
                search_query = "revolico cuba clasificados"
                for char in search_query:
                    search_box.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.3))
                
                time.sleep(random.uniform(1, 2))
                search_box.submit()
                
                # Wait for results
                time.sleep(random.uniform(3, 5))
                
                self.logger.info("Google search completed, session established")
                return True
                
            except TimeoutException:
                self.logger.warning("Could not find Google search box, continuing without search")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to build Google session: {e}")
            return False
    
    def simulate_human_behavior(self, driver: webdriver.Chrome):
        """Simulate human-like behavior on the page"""
        try:
            # Get page height for scrolling
            page_height = driver.execute_script("return document.body.scrollHeight")
            
            # Simulate reading behavior with slow scrolling
            scroll_pause_time = random.uniform(1, 3)
            current_position = 0
            scroll_increment = random.randint(300, 500)
            
            actions = ActionChains(driver)
            
            # Random mouse movements
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.5, 1.5))
            
            actions.perform()
            
            # Scroll through page slowly
            while current_position < page_height * 0.7:  # Scroll 70% of page
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                current_position += scroll_increment
                time.sleep(scroll_pause_time)
                
                # Occasionally pause longer (reading simulation)
                if random.random() < 0.3:
                    time.sleep(random.uniform(2, 4))
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
            self.logger.info("Human behavior simulation completed")
            
        except Exception as e:
            self.logger.warning(f"Error during behavior simulation: {e}")
    
    def detect_cloudflare_challenge(self, driver: webdriver.Chrome) -> Dict[str, bool]:
        """Detect Cloudflare protection and challenges"""
        protection_detected = {
            'cloudflare': False,
            'challenge': False,
            'captcha': False,
            'rate_limit': False,
            'success': False
        }
        
        try:
            page_source = driver.page_source.lower()
            title = driver.title.lower()
            current_url = driver.current_url.lower()
            
            # Check for Cloudflare indicators
            cf_indicators = [
                'cloudflare',
                'checking your browser',
                'please wait while we check',
                'ddos protection',
                'security check',
                'cf-ray',
                'just a moment'
            ]
            
            for indicator in cf_indicators:
                if indicator in page_source or indicator in title:
                    protection_detected['cloudflare'] = True
                    break
            
            # Check for active challenge
            if any(phrase in page_source for phrase in ['checking your browser', 'please wait', 'just a moment']):
                protection_detected['challenge'] = True
            
            # Check for CAPTCHA
            if any(phrase in page_source for phrase in ['captcha', 'recaptcha', 'hcaptcha']):
                protection_detected['captcha'] = True
            
            # Check for rate limiting
            if '429' in page_source or 'rate limit' in page_source:
                protection_detected['rate_limit'] = True
            
            # Check if we successfully loaded the page
            if 'revolico' in title and not any(protection_detected.values()):
                protection_detected['success'] = True
            
            self.logger.info(f"Protection detection: {protection_detected}")
            return protection_detected
            
        except Exception as e:
            self.logger.error(f"Error detecting protection: {e}")
            return protection_detected
    
    def wait_for_cloudflare_challenge(self, driver: webdriver.Chrome, max_wait: int = 30) -> bool:
        """Wait for Cloudflare challenge to complete"""
        self.logger.info("Waiting for Cloudflare challenge to complete...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            protection = self.detect_cloudflare_challenge(driver)
            
            if protection['success']:
                self.logger.info("Cloudflare challenge completed successfully")
                return True
            elif protection['captcha']:
                self.logger.warning("CAPTCHA detected - manual intervention required")
                return False
            elif protection['challenge']:
                self.logger.info("Challenge in progress, waiting...")
                time.sleep(2)
            else:
                # Unknown state, continue waiting
                time.sleep(1)
        
        self.logger.warning("Cloudflare challenge wait timeout")
        return False
    
    def try_url_with_retry(self, driver: webdriver.Chrome, url: str, max_retries: int = 3) -> Tuple[bool, Dict]:
        """Try to access URL with retry logic and detailed analysis"""
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempting {url} (attempt {attempt + 1}/{max_retries})")
                
                # Add delay with jitter
                if attempt > 0:
                    delay = self.config['delays']['min_request'] * (2 ** attempt)
                    jitter = random.uniform(-self.config['delays']['jitter'], self.config['delays']['jitter'])
                    total_delay = delay + jitter
                    self.logger.info(f"Waiting {total_delay:.2f} seconds before retry...")
                    time.sleep(total_delay)
                
                # Load saved cookies if available
                domain = url.split('//')[1].split('/')[0]
                self.load_session_cookies(driver, domain)
                
                # Navigate to URL
                driver.get(url)
                
                # Wait for initial page load
                time.sleep(self.config['delays']['page_load'])
                
                # Detect protection
                protection = self.detect_cloudflare_challenge(driver)
                
                if protection['challenge']:
                    # Wait for challenge to complete
                    if self.wait_for_cloudflare_challenge(driver):
                        protection = self.detect_cloudflare_challenge(driver)
                
                if protection['success']:
                    # Simulate human behavior
                    self.simulate_human_behavior(driver)
                    
                    # Save cookies for future use
                    self.save_session_cookies(driver)
                    
                    self.logger.info(f"Successfully accessed {url}")
                    return True, {
                        'url': url,
                        'status': 'success',
                        'protection': protection,
                        'page_title': driver.title,
                        'page_length': len(driver.page_source)
                    }
                
                elif protection['captcha']:
                    self.logger.warning(f"CAPTCHA detected on {url} - skipping")
                    return False, {
                        'url': url,
                        'status': 'captcha',
                        'protection': protection
                    }
                
                else:
                    self.logger.warning(f"Access blocked on {url}: {protection}")
                    
                    if attempt == max_retries - 1:
                        return False, {
                            'url': url,
                            'status': 'blocked',
                            'protection': protection
                        }
                
            except TimeoutException:
                self.logger.warning(f"Timeout accessing {url}")
                if attempt == max_retries - 1:
                    return False, {
                        'url': url,
                        'status': 'timeout'
                    }
                    
            except WebDriverException as e:
                self.logger.error(f"WebDriver error accessing {url}: {e}")
                if attempt == max_retries - 1:
                    return False, {
                        'url': url,
                        'status': 'webdriver_error',
                        'error': str(e)
                    }
        
        return False, {'url': url, 'status': 'failed'}
    
    def find_working_url(self, driver: webdriver.Chrome) -> Tuple[Optional[str], Dict]:
        """Find a working URL from available options"""
        results = {
            'attempts': [],
            'working_url': None,
            'strategy_used': None
        }
        
        # Strategy 1: Try main URLs (prioritize mobile)
        self.logger.info("Strategy 1: Trying main URLs (mobile first)")
        for url in self.config['main_urls']:
            success, result = self.try_url_with_retry(driver, url)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'main_url'
                return url, results
        
        # Strategy 2: Try with Google referer
        self.logger.info("Strategy 2: Building session with Google referer")
        if self.build_session_with_google_referer(driver):
            for url in self.config['main_urls'][:2]:  # Try top 2 again
                success, result = self.try_url_with_retry(driver, url, max_retries=2)
                results['attempts'].append(result)
                
                if success:
                    results['working_url'] = url
                    results['strategy_used'] = 'google_referer'
                    return url, results
        
        # Strategy 3: Try fallback URLs
        self.logger.info("Strategy 3: Trying fallback URLs")
        for url in self.config['fallback_urls']:
            success, result = self.try_url_with_retry(driver, url, max_retries=2)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'fallback_url'
                return url, results
        
        # Strategy 4: Try alternative sites
        self.logger.info("Strategy 4: Trying alternative Cuban classified sites")
        for url in self.config['alternative_sites']:
            success, result = self.try_url_with_retry(driver, url, max_retries=1)
            results['attempts'].append(result)
            
            if success:
                results['working_url'] = url
                results['strategy_used'] = 'alternative_site'
                return url, results
        
        self.logger.error("All URLs failed - no working URL found")
        return None, results
    
    def extract_listings(self, driver: webdriver.Chrome, max_listings: int = 3) -> List[Dict]:
        """Extract listings from the current page"""
        listings = []
        
        try:
            self.logger.info("Extracting listings from current page...")
            
            # Multiple selectors to try for listings
            listing_selectors = [
                'div[class*="listing"]',
                'div[class*="ad"]',
                'article',
                'div[class*="anuncio"]',
                'div[class*="clasificado"]',
                '.listing-item',
                '.ad-item',
                'a[href*="anuncio"]',
                'a[href*="ad"]'
            ]
            
            found_elements = []
            
            for selector in listing_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        found_elements = elements
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except Exception as e:
                    continue
            
            # If no specific selectors work, try finding links
            if not found_elements:
                self.logger.info("Trying fallback method: looking for relevant links")
                all_links = driver.find_elements(By.TAG_NAME, 'a')
                found_elements = [link for link in all_links 
                                if link.get_attribute('href') and 
                                any(keyword in link.get_attribute('href').lower() 
                                    for keyword in ['anuncio', 'ad', 'listing', 'clasificado'])]
            
            # Extract information from found elements
            for i, element in enumerate(found_elements[:max_listings]):
                try:
                    # Get link URL
                    if element.tag_name == 'a':
                        link_url = element.get_attribute('href')
                        title_element = element
                    else:
                        link_element = element.find_element(By.TAG_NAME, 'a')
                        link_url = link_element.get_attribute('href')
                        title_element = link_element
                    
                    # Get title
                    title = title_element.text.strip()
                    if not title:
                        title = title_element.get_attribute('title') or f'Listing {i+1}'
                    
                    # Make URL absolute
                    if link_url and link_url.startswith('/'):
                        current_url = driver.current_url
                        base_url = '/'.join(current_url.split('/')[:3])
                        link_url = base_url + link_url
                    
                    listing_data = {
                        'title': title[:100],
                        'url': link_url,
                        'found_at': datetime.now().isoformat(),
                        'source_page': driver.current_url
                    }
                    
                    listings.append(listing_data)
                    self.logger.info(f"Extracted listing {i+1}: {title[:50]}...")
                    
                except Exception as e:
                    self.logger.warning(f"Error extracting listing {i+1}: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(listings)} listings")
            return listings
            
        except Exception as e:
            self.logger.error(f"Error extracting listings: {e}")
            return []
    
    def scrape_listing_details(self, driver: webdriver.Chrome, listing: Dict) -> Dict:
        """Scrape phone numbers from a listing detail page"""
        self.logger.info(f"Scraping details for: {listing['title']}")
        
        try:
            # Navigate to listing page
            driver.get(listing['url'])
            
            # Wait for page load
            time.sleep(self.config['delays']['page_load'])
            
            # Check for protection again
            protection = self.detect_cloudflare_challenge(driver)
            if not protection['success'] and protection['challenge']:
                if not self.wait_for_cloudflare_challenge(driver):
                    return {
                        'title': listing['title'],
                        'url': listing['url'],
                        'phone_numbers': [],
                        'scraped_at': datetime.now().isoformat(),
                        'error': 'Cloudflare challenge failed'
                    }
            
            # Simulate human behavior
            self.simulate_human_behavior(driver)
            
            # Extract phone numbers from page source
            page_text = driver.page_source
            phone_numbers = self.phone_parser.extract_phone_numbers(page_text)
            
            # Also try to find contact elements specifically
            contact_selectors = [
                '*[class*="contact"]',
                '*[class*="phone"]',
                '*[class*="telefono"]',
                '*[class*="celular"]',
                '*[class*="movil"]'
            ]
            
            for selector in contact_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        element_text = element.text
                        if element_text:
                            element_phones = self.phone_parser.extract_phone_numbers(element_text)
                            phone_numbers.extend(element_phones)
                except Exception:
                    continue
            
            # Remove duplicates
            unique_phones = list(dict.fromkeys(phone_numbers))
            
            result = {
                'title': listing['title'],
                'url': listing['url'],
                'phone_numbers': unique_phones,
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Found {len(unique_phones)} phone numbers for: {listing['title']}")
            
            # Add delay before next request
            delay = random.uniform(
                self.config['delays']['min_request'],
                self.config['delays']['max_request']
            )
            jitter = random.uniform(-self.config['delays']['jitter'], self.config['delays']['jitter'])
            total_delay = delay + jitter
            
            self.logger.info(f"Waiting {total_delay:.2f} seconds before next request...")
            time.sleep(total_delay)
            
            return result
            
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
        self.logger.info("Starting enhanced Selenium scraping session...")
        
        results = {
            'scraping_date': start_time.isoformat(),
            'results': [],
            'url_attempts': [],
            'strategy_used': None,
            'working_url': None,
            'errors': [],
            'total_listings_found': 0,
            'total_phone_numbers': 0,
            'duration_seconds': 0
        }
        
        driver = None
        
        try:
            # Setup driver (try mobile first)
            driver = self.setup_driver(mobile_mode=True)
            
            # Find working URL
            working_url, url_results = self.find_working_url(driver)
            
            results['url_attempts'] = url_results['attempts']
            results['strategy_used'] = url_results['strategy_used']
            results['working_url'] = working_url
            
            if not working_url:
                raise Exception("No working URL found - all attempts failed")
            
            # Extract listings from homepage
            listings = self.extract_listings(driver, max_listings)
            
            if not listings:
                self.logger.warning("No listings found on homepage")
                # Try desktop mode as fallback
                self.logger.info("Trying desktop mode as fallback...")
                driver.quit()
                driver = self.setup_driver(mobile_mode=False)
                
                success, _ = self.try_url_with_retry(driver, working_url)
                if success:
                    listings = self.extract_listings(driver, max_listings)
            
            # Scrape details from each listing
            for listing in listings:
                try:
                    result = self.scrape_listing_details(driver, listing)
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
        
        finally:
            if driver:
                driver.quit()
                self.logger.info("Chrome driver closed")
        
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
    print("ENHANCED SELENIUM REVOLICO SCRAPER")
    print("Advanced Cloudflare bypass with browser automation")
    print("=" * 60)
    
    scraper = CloudflareBypasser()
    
    try:
        # Run the scraping
        report = scraper.run_scraping(max_listings=3)
        
        # Save results to JSON
        output_file = "selenium_revolico_data.json"
        save_to_json(report, output_file)
        
        # Display results
        print(f"\n📊 SCRAPING RESULTS:")
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