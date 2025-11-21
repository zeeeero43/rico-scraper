from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import time
import re
import json
from datetime import datetime

class SeleniumBrowserScraper:
    """Real browser scraper using Selenium"""

    def __init__(self, logger=None):
        self.driver = None
        self.results = []
        self.stop_requested = False
        self.logger = logger if logger else SimpleLogger()
        
    def create_driver(self):
        """Create Firefox driver to bypass Cloudflare"""
        try:
            self.logger.info("Setting up Firefox driver...")

            # Create options for Firefox
            options = FirefoxOptions()

            # Try different Firefox binary locations (Snap, ESR, or standard)
            import os
            firefox_paths = [
                '/snap/bin/firefox',              # Snap installation (Ubuntu 22.04+)
                '/usr/lib/firefox-esr/firefox-esr', # Firefox ESR (Debian/Ubuntu)
                '/usr/bin/firefox',                 # Standard Firefox
            ]

            firefox_binary = None
            for path in firefox_paths:
                if os.path.exists(path):
                    firefox_binary = path
                    self.logger.info(f"Found Firefox binary at: {path}")
                    break

            if firefox_binary:
                options.binary_location = firefox_binary
            else:
                self.logger.warning("Firefox binary not found, using system default")

            # Basic settings
            options.add_argument('--headless')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')  # Important for VPS

            # Anti-detection settings
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            options.set_preference("general.useragent.override",
                                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")

            # Setup service with geckodriver (prefer xvfb wrapper if available)
            geckodriver_path = None
            if os.path.exists('/usr/local/bin/xvfb-geckodriver'):
                geckodriver_path = '/usr/local/bin/xvfb-geckodriver'
                self.logger.info("Using xvfb-geckodriver for headless display")
            elif os.path.exists('/usr/local/bin/geckodriver'):
                geckodriver_path = '/usr/local/bin/geckodriver'
                self.logger.info("Using standard geckodriver")
            else:
                self.logger.info("Using webdriver-manager for geckodriver")
                geckodriver_path = GeckoDriverManager().install()

            service = FirefoxService(geckodriver_path)

            # Create driver
            self.driver = webdriver.Firefox(service=service, options=options)

            self.logger.info("✅ Firefox driver ready")
            return True

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"❌ Failed to setup Firefox driver: {e}")
            self.logger.error(f"Traceback: {error_details}")
            return False
    
    def stop(self):
        """Stop the scraping process"""
        self.stop_requested = True
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error quitting driver in stop(): {e}")
        self.logger.info("Stop requested by user")
    
    def should_stop(self):
        """Check if scraping should stop"""
        return self.stop_requested

    def close(self):
        """Close the browser and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")

    def scrape_revolico(self, max_listings=3):
        """Main scraping function using Selenium"""
        start_time = time.time()

        # Validate input
        if max_listings < 1:
            return self._create_error_response("max_listings must be at least 1")

        try:
            if not self.create_driver():
                return self._create_error_response("Failed to setup browser")
            
            self.logger.info("🌐 Loading www.revolico.com with real browser...")

            # Navigate to homepage (use www to avoid redirect)
            self.driver.get("https://www.revolico.com")
            time.sleep(8)  # Longer wait for Cloudflare check
            
            self.logger.info(f"✅ Success: {self.driver.title}")
            
            if self.should_stop():
                return self._create_stopped_response()
            
            # Find listing links
            self.logger.info("Searching for listing links...")
            
            # Debug: Print page title and source length
            self.logger.info(f"Page loaded: {self.driver.title}")
            self.logger.info(f"Page source length: {len(self.driver.page_source)} characters")
            
            # Try multiple CSS selectors to find listings
            listing_urls = []
            
            # Try different selectors for Revolico listings
            selectors_to_try = [
                'a[href*="/item/"]:not([href*="/item/publish"])',  # Product links but not publish
                'a[href*="/item/"][href*="-"]',                    # Item links with dashes (product names)
                'a[href*="/item/"]',                              # All item links
            ]
            
            for selector in selectors_to_try:
                if self.should_stop():
                    return self._create_stopped_response()
                
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"Selector '{selector}' found {len(elements)} elements")
                    
                    for element in elements[:10]:  # Check first 10 for each selector
                        try:
                            href = element.get_attribute('href')
                            text = element.text.strip()
                            
                            if href and href.startswith('http') and 'revolico.com' in href:
                                listing_urls.append({
                                    'url': href,
                                    'title': text[:100] if text else 'No title'
                                })
                                self.logger.info(f"✓ Found listing: {href}")

                                if len(listing_urls) >= max_listings:
                                    break
                        except Exception as e:
                            self.logger.info(f"Error extracting URL from element: {e}")
                            continue
                            
                    if len(listing_urls) >= max_listings:
                        break
                except Exception as e:
                    self.logger.info(f"Selector '{selector}' failed: {e}")
                    continue
            
            # If no specific selectors worked, try generic approach
            if len(listing_urls) == 0:
                self.logger.info("Trying generic link search...")
                links = self.driver.find_elements(By.TAG_NAME, "a")
                self.logger.info(f"Found {len(links)} total links on page")
                
                for link in links[:100]:  # Check more links
                    try:
                        href = link.get_attribute('href')
                        text = link.text.strip()
                        
                        # Look for Revolico product patterns
                        if (href and '/item/' in href and 
                            'revolico.com' in href and 
                            '/item/publish' not in href and
                            href.split('/')[-1] and  # Has product slug
                            any(char.isdigit() for char in href.split('/')[-1])):
                            listing_urls.append({
                                'url': href,
                                'title': text[:100] if text else 'No title'
                            })
                            self.logger.info(f"✓ Generic pattern match: {href}")

                            if len(listing_urls) >= max_listings:
                                break
                    except Exception as e:
                        self.logger.info(f"Selector '{selector}' failed: {e}")
                        continue
            
            self.logger.info(f"Found {len(listing_urls)} listings to scrape")
            
            # Scrape each listing
            for i, listing in enumerate(listing_urls):
                if self.should_stop():
                    return self._create_stopped_response()
                    
                try:
                    self.logger.info(f"📄 Visiting listing {i+1}: {listing['title']}")
                    
                    # Navigate to listing page with Cloudflare handling
                    self.driver.get(listing['url'])
                    initial_title = self.driver.title
                    self.logger.info(f"Initial page title: {initial_title}")
                    
                    # Wait for page to load naturally (no Cloudflare protection)
                    if "just a moment" in initial_title.lower():
                        self.logger.info("Page loading, waiting for content...")
                        # Wait for the page to finish loading
                        for attempt in range(15):
                            time.sleep(2)
                            current_title = self.driver.title
                            # Check if we have real content
                            if ("revolico" in current_title.lower() or 
                                "anuncio" in current_title.lower() or 
                                current_title != initial_title):
                                self.logger.info(f"✅ Page loaded after {(attempt+1)*2} seconds: {current_title}")
                                break
                        else:
                            self.logger.info("Continuing with current page content")
                                
                    # Additional wait and interaction to ensure content loads
                    time.sleep(3)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)
                    
                    final_title = self.driver.title
                    self.logger.info(f"Final page title: {final_title}")
                    
                    # Extract phone numbers from WhatsApp buttons
                    found_phones = []
                    
                    # Method 1: Focus on USER PROFILE AREA (where contact info is located)
                    try:
                        # Search specifically in user profile sections
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
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            profile_elements.extend(elements)
                            self.logger.info(f"Profile selector '{selector}' found {len(elements)} elements")
                        
                        self.logger.info(f"Total profile elements found: {len(profile_elements)}")
                        
                        # Look for WhatsApp links within profile areas
                        for element in profile_elements:
                            try:
                                # ONLY extract WhatsApp links (not regular phone numbers)
                                whatsapp_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="wa.me"], a[href*="whatsapp"]')
                                for link in whatsapp_links:
                                    href = link.get_attribute('href')
                                    if href and ('wa.me' in href or 'whatsapp.com' in href):
                                        self.logger.info(f"📱 Profile WhatsApp link: {href}")
                                        phone_match = re.search(r'(?:wa\.me/|phone=)(\+?53\d{8})\b', href)
                                        if phone_match:
                                            phone = phone_match.group(1)
                                            if not phone.startswith('+'):
                                                phone = '+' + phone
                                            if phone not in found_phones:
                                                found_phones.append(phone)
                                                self.logger.info(f"✅ Found WhatsApp number: {phone}")
                                
                            except Exception as e:
                                self.logger.info(f"Error processing profile element: {e}")
                                
                    except Exception as e:
                        self.logger.error(f"Error finding profile areas: {e}")
                    
                    # Method 2: Search page source for WhatsApp links (regex fallback)
                    try:
                        page_source = self.driver.page_source
                        self.logger.info(f"Page source length: {len(page_source)} characters")
                        
                        # Debug: Check if we can find any wa.me references at all
                        basic_wa_count = page_source.lower().count('wa.me')
                        whatsapp_count = page_source.lower().count('whatsapp')
                        self.logger.info(f"Found {basic_wa_count} 'wa.me' and {whatsapp_count} 'whatsapp' text references")
                        
                        # Focus ONLY on WhatsApp links with phone numbers (EXACTLY 8 digits after 53)
                        whatsapp_patterns = [
                            r'wa\.me/(\+?53\d{8})\b',                    # wa.me/53xxxxxxxx or wa.me/+53xxxxxxxx
                            r'whatsapp\.com/send\?phone=(\+?53\d{8})\b', # whatsapp.com/send?phone=53xxxxxxxx
                            r'api\.whatsapp\.com/send\?phone=(\+?53\d{8})\b', # api.whatsapp.com variant
                        ]

                        for pattern in whatsapp_patterns:
                            matches = re.findall(pattern, page_source, re.IGNORECASE)
                            self.logger.info(f"WhatsApp pattern '{pattern}' found {len(matches)} matches: {matches}")

                            for phone in matches:
                                # Clean and format
                                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                                if clean_phone.startswith('53') and len(clean_phone) == 10:
                                    formatted_phone = f"+{clean_phone}"
                                    if formatted_phone not in found_phones:
                                        found_phones.append(formatted_phone)
                                        self.logger.info(f"✅ Extracted from page source: {formatted_phone}")
                                
                        # If still no phones found, save page for debugging
                        if len(found_phones) == 0:
                            # Save full page for debugging
                            with open(f"debug_page_{i+1}.html", "w", encoding="utf-8") as f:
                                f.write(page_source)
                                self.logger.info(f"💾 Saved page source to debug_page_{i+1}.html")
                            
                            # Show sample of what we actually got
                            sample_text = page_source[:2000] + "..." if len(page_source) > 2000 else page_source
                            self.logger.info(f"Page content sample: {sample_text}")
                            
                            # Last resort: look for any phone-like patterns in text (EXACTLY 8 digits)
                            any_phones = re.findall(r'53\d{8}\b', page_source)
                            self.logger.info(f"Any 53xxxxxxxx patterns found: {any_phones[:5]}")
                                
                    except Exception as e:
                        self.logger.error(f"Error searching page source: {e}")
                    
                    # Remove duplicates
                    found_phones = list(set(found_phones))
                    
                    if found_phones:
                        # Extract additional listing details
                        listing_details = self.extract_listing_details(listing['url'])

                        result = {
                            'title': listing_details.get('title', listing['title']),
                            'url': listing['url'],
                            'phone_numbers': found_phones,
                            'description': listing_details.get('description', ''),
                            'price': listing_details.get('price', None),
                            'currency': listing_details.get('currency', 'USD'),
                            'seller_name': listing_details.get('seller_name'),
                            'profile_picture_url': listing_details.get('profile_picture_url'),
                            'images': listing_details.get('images', []),
                            'category': listing_details.get('category', ''),
                            'location': listing_details.get('location', ''),
                            'condition': listing_details.get('condition', 'used'),
                            'revolico_id': listing_details.get('revolico_id', ''),
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.results.append(result)
                        self.logger.info(f"✅ Found phones: {found_phones}")
                    else:
                        self.logger.info("❌ No phone numbers found")
                    
                    time.sleep(2)  # Delay between requests
                    
                except Exception as e:
                    self.logger.error(f"Error scraping listing {i+1}: {e}")
                    continue
            
            # Create successful response
            duration = round(time.time() - start_time, 2)
            total_phones = sum(len(r['phone_numbers']) for r in self.results)

            return {
                'success': True,
                'method': 'Selenium Real Browser',
                'url': 'https://revolico.com',
                'results': self.results,
                'total_phone_numbers': total_phones,
                'total_listings_found': len(self.results),
                'duration_seconds': duration,
                'success_rate': (len(self.results) / max(max_listings, 1)) * 100
            }
            
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            self.logger.error(f"Critical error during scraping: {e}")
            return {
                'success': False,
                'method': 'Selenium Real Browser',
                'url': 'https://revolico.com',
                'results': {'error': f'Critical error: {e}'},
                'duration': f'{duration}s'
            }
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error cleaning up driver in finally: {e}")
    
    def extract_phone_numbers(self, text):
        """Extract Cuban phone numbers from text - including WhatsApp links"""
        found_phones = []
        
        # Pattern 1: WhatsApp links (handle both +53 and 53 formats)
        whatsapp_pattern = r'wa\.me/(\+?53\d{8})'
        whatsapp_matches = re.findall(whatsapp_pattern, text, re.IGNORECASE)
        self.logger.info(f"WhatsApp regex found {len(whatsapp_matches)} matches")
        
        for match in whatsapp_matches:
            self.logger.info(f"Processing WhatsApp match: {match}")
            # Handle both +53xxxxxxxx and 53xxxxxxxx formats
            if match.startswith('+53'):
                found_phones.append(match)
                self.logger.info(f"📞 Found WhatsApp number with +: {match}")
            elif match.startswith('53') and len(match) == 10:
                formatted_phone = f"+{match}"
                found_phones.append(formatted_phone)
                self.logger.info(f"📞 Found WhatsApp number without +: {formatted_phone}")
        
        # Pattern 2: Direct phone number patterns
        phone_patterns = [
            r'\+53[-\s]?\d{8}',                # +53 12345678 or +53-12345678
            r'\+53[-\s]?\d{4}[-\s]?\d{4}',     # +53 1234-5678
            r'\+53[-\s]?\(\d{4}\)[-\s]?\d{4}', # +53 (1234) 5678
            r'53[-\s]?\d{8}',                  # 53 12345678
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text, re.IGNORECASE)
            for phone in phones:
                # Clean and format phone number
                clean_phone = re.sub(r'[^\d+]', '', phone)
                if clean_phone.startswith('53') and len(clean_phone) == 10:
                    formatted_phone = f"+{clean_phone}"
                    found_phones.append(formatted_phone)
                    self.logger.info(f"📞 Found direct number: {formatted_phone}")
                elif clean_phone.startswith('+53') and len(clean_phone) == 11:
                    found_phones.append(phone.strip())
                    self.logger.info(f"📞 Found formatted number: {phone.strip()}")
        
        # Remove duplicates
        unique_phones = list(set(found_phones))
        self.logger.info(f"📱 Total unique phones found: {len(unique_phones)}")
        return unique_phones

    def extract_profile_picture(self):
        """
        Extract seller profile picture URL from current page
        Supports both Google OAuth avatars and Revolico CDN uploads
        Uses explicit wait for JavaScript-loaded profile pictures
        Returns: profile_picture_url (str) or None
        """
        try:
            # Priority-ordered CSS selectors
            selectors = [
                '[data-cy="user-avatar"] img',                    # data-cy is most stable
                '.AvatarImage__Wrapper-sc-c54cfbd7-0 img',       # Specific avatar wrapper class
                'div.avatar[data-cy="user-avatar"] img',         # Combined selector
                '.AdOwner__Wrapper img[alt="Avatar"]',           # Specific class + alt
                '.avatar img',                                    # Generic avatar class
                'a[data-cy="adUser"] img'                         # Within user link
            ]

            # Try each selector with explicit wait (for JavaScript-loaded images)
            for selector in selectors:
                try:
                    # Wait up to 8 seconds for the profile picture to load
                    # (Revolico loads profile pictures dynamically via JavaScript)
                    wait = WebDriverWait(self.driver, 8)
                    img_elem = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )

                    profile_pic_url = img_elem.get_attribute('src')

                    if profile_pic_url:
                        # Upgrade image quality based on source
                        if 'lh3.googleusercontent.com' in profile_pic_url:
                            # Google User Content - upgrade from s96-c to s400-c
                            profile_pic_url = profile_pic_url.replace('=s96-c', '=s400-c')
                            self.logger.info(f"📸 Google profile pic (s400): {profile_pic_url}")

                        elif 'pic.revolico.com/users' in profile_pic_url:
                            # Revolico CDN - keep original quality (thumb)
                            # DO NOT upgrade - the tokens are tied to the specific quality parameter
                            self.logger.info(f"📸 Revolico profile pic (thumb): {profile_pic_url}")

                        else:
                            self.logger.info(f"📸 Profile picture: {profile_pic_url}")

                        return profile_pic_url

                except TimeoutException:
                    # Timeout = this selector didn't find an image, try next one
                    continue
                except Exception:
                    # Other error, try next selector
                    continue

            self.logger.info("ℹ️  No profile picture found (seller may have default SVG avatar)")
            return None

        except Exception as e:
            self.logger.error(f"Error extracting profile picture: {e}")
            return None

    def extract_listing_details(self, url):
        """Extract detailed information from listing page (assumes page is already loaded)"""
        details = {
            'description': '',
            'price': None,
            'currency': 'USD',
            'images': [],
            'category': '',
            'location': '',
            'condition': 'used',
            'revolico_id': '',
            'title': ''
        }

        try:
            # Verify we're on the correct page
            current_url = self.driver.current_url
            if current_url == "about:blank" or not current_url or "revolico.com" not in current_url:
                self.logger.error(f"❌ Page not loaded correctly! Current URL: {current_url}")
                self.logger.error(f"❌ Expected URL: {url}")
                self.logger.error("❌ Attempting to reload...")
                self.driver.get(url)
                time.sleep(5)
                # Scroll to trigger lazy loading
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

            # Check if we're on an error page
            page_source = self.driver.page_source
            if "Ha ocurrido un error" in page_source or "error" in self.driver.title.lower():
                self.logger.error("❌ Error page detected! Attempting to reload...")
                self.driver.get(url)
                time.sleep(5)
                # Scroll to trigger lazy loading
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

                # Check again
                if "Ha ocurrido un error" in self.driver.page_source:
                    self.logger.error("❌ Still error page after reload. Skipping this listing.")
                    return details
                else:
                    self.logger.info("✅ Page reloaded successfully")

            # Extract Revolico ID from URL
            # Example: https://www.revolico.com/item/titulo-123456
            id_match = re.search(r'/item/[^/]+-(\d+)', url)
            if id_match:
                details['revolico_id'] = id_match.group(1)
                self.logger.info(f"📋 Revolico ID: {details['revolico_id']}")

            # Extract title from detail page
            try:
                title_elem = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="adTitle"]'))
                )
                details['title'] = title_elem.text.strip()
                self.logger.info(f"📌 Title: {details['title'][:100]}")
            except Exception as e:
                self.logger.error(f"❌ Could not extract title: {e}")
                self.logger.error(f"Current URL: {self.driver.current_url}")
                self.logger.error(f"Page title: {self.driver.title}")
                details['title'] = ''

            # Extract description
            try:
                # Wait for description element to be present (up to 15 seconds)
                desc_elem = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="adDescription"]'))
                )
                text = desc_elem.text.strip()

                # Footer patterns to cut off (these appear at the end of descriptions)
                footer_cutoff_patterns = [
                    'teléfono',
                    'más información por whatsapp',
                    'puntos de venta',
                    'llama al',
                    'contacta por',
                    'escríbenos',
                    'para más información'
                ]

                # Remove footer sections (contact info, etc.)
                text_lower = text.lower()
                for pattern in footer_cutoff_patterns:
                    # Find where the footer pattern starts
                    pattern_pos = text_lower.find(pattern)
                    if pattern_pos > 50:  # Only cut if there's content before it
                        # Cut off everything from this pattern onwards
                        text = text[:pattern_pos].strip()
                        text_lower = text.lower()

                details['description'] = text
                self.logger.info(f"📝 Description ({len(details['description'])} chars): {details['description'][:100]}...")
            except Exception as e:
                self.logger.error(f"Could not extract description: {e}")

            # Extract seller name - try DOM first, then JSON fallback
            seller_name = None
            dom_success = False

            # Method 1: Try DOM element (longer timeout for slow loading pages)
            try:
                name_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="userFullname"]'))
                )
                seller_name = name_elem.text.strip()
                if seller_name:
                    details['seller_name'] = seller_name
                    self.logger.info(f"👤 Seller name (DOM): {seller_name}")
                    dom_success = True
            except Exception as e:
                self.logger.warning(f"DOM seller name extraction failed: {type(e).__name__}: {e}")

            # Try JSON fallback if DOM failed or returned empty text
            if not dom_success:
                # Method 2: Fallback to JSON data (more reliable)
                try:
                    # Wait for the __NEXT_DATA__ script to be present
                    json_script = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "__NEXT_DATA__"))
                    )
                    json_text = json_script.get_attribute('textContent')

                    if not json_text:
                        raise Exception("__NEXT_DATA__ script is empty")

                    json_data = json.loads(json_text)
                    apollo_state = json_data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})

                    if not apollo_state:
                        raise Exception("No __APOLLO_STATE__ found in JSON")

                    # Find AdType entry (contains seller info)
                    for key, value in apollo_state.items():
                        if key.startswith('AdType:') and isinstance(value, dict):
                            seller_name = value.get('name')
                            if seller_name:
                                details['seller_name'] = seller_name
                                self.logger.info(f"👤 Seller name (JSON): {seller_name}")
                                break

                except Exception as json_error:
                    self.logger.error(f"Could not extract seller name from JSON: {type(json_error).__name__}: {json_error}")

            # If still no name found, log error
            if not seller_name:
                details['seller_name'] = None
                self.logger.error(f"❌ No seller name found - this should not happen!")

            # Extract profile picture
            try:
                profile_pic_url = self.extract_profile_picture()
                details['profile_picture_url'] = profile_pic_url
            except Exception as e:
                self.logger.error(f"Error extracting profile picture: {e}")
                details['profile_picture_url'] = None

            # Extract price and currency from adPrice element
            try:
                # Try to find the price element
                price_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="adPrice"]'))
                )
                price_text = price_elem.text.strip()
                self.logger.info(f"💰 Raw price text: {price_text}")

                # Parse price and currency (e.g., "8.000 CUP" or "400 USD")
                # Pattern handles: "8.000 CUP", "400 USD", "1.200,50 USD", etc.
                price_match = re.search(r'([\d.,]+)\s*(CUP|USD|EUR|MLC)', price_text, re.IGNORECASE)

                if price_match:
                    price_str = price_match.group(1)
                    currency = price_match.group(2).upper()

                    # Clean price handling both European and Cuban formats
                    # "1,300" (thousand separator, no decimals) → "1300"
                    # "8.000" (thousand separator with periods) → "8000"
                    # "1.200,50" (European: thousand . decimal ,) → "1200.50"
                    # "1,300.50" (US: thousand , decimal .) → "1300.50"

                    # If comma followed by exactly 3 digits at end: it's a thousand separator
                    if re.match(r'^[\d.,]+,\d{3}$', price_str):
                        # "1,300" or "10,000" - comma is thousand separator
                        price_clean = price_str.replace(',', '').replace('.', '')
                    # If comma followed by 1-2 digits at end: it's a decimal separator
                    elif re.match(r'^[\d.,]+,\d{1,2}$', price_str):
                        # "1.200,50" - period is thousand, comma is decimal
                        price_clean = price_str.replace('.', '').replace(',', '.')
                    # If period followed by 1-2 digits at end: it's a decimal separator
                    elif re.match(r'^[\d.,]+\.\d{1,2}$', price_str):
                        # "1,300.50" - comma is thousand, period is decimal
                        price_clean = price_str.replace(',', '')
                    # Otherwise just remove all thousand separators
                    else:
                        # "8.000" or "100" - remove periods
                        price_clean = price_str.replace('.', '').replace(',', '')

                    try:
                        details['price'] = float(price_clean)
                        details['currency'] = currency
                        self.logger.info(f"💰 Price: {details['price']} {details['currency']}")
                    except ValueError:
                        self.logger.info(f"⚠️  Could not parse price: {price_str}")
                        details['price'] = None
                        details['currency'] = 'USD'
                else:
                    self.logger.info("⚠️  Price element found but no price/currency pattern matched")
                    details['price'] = None
                    details['currency'] = 'USD'

            except Exception as e:
                self.logger.info(f"ℹ️  No price found (element not present): {e}")
                details['price'] = None
                details['currency'] = 'USD'

            # Extract images - PRIORITIZE high quality gallery images
            try:
                # Find the image gallery container first (scoped search)
                gallery = self.driver.find_element(By.CSS_SELECTOR, '[data-cy="adImages"]')

                # Find all slides within the gallery
                slides = gallery.find_elements(By.CSS_SELECTOR, '.swiper-slide')

                found_images = set()
                for slide in slides:
                    try:
                        # PRIORITY 1: Gallery high-quality images (_high.jpg) from swiper-zoom-container
                        zoom_containers = slide.find_elements(By.CSS_SELECTOR, '.swiper-zoom-container img')
                        if zoom_containers:
                            for img in zoom_containers:
                                src = img.get_attribute('src')
                                if src and '_high.jpg' in src and 'revolico' in src:
                                    found_images.add(src)
                                    self.logger.info(f"🖼️  Found HIGH quality gallery image: {src}")

                        # If high quality images found, skip fallbacks for this slide
                        if zoom_containers and any('_high.jpg' in img.get_attribute('src') or '' for img in zoom_containers):
                            continue

                        # FALLBACK 1: Try to get source from <source> tag (desktop quality)
                        sources = slide.find_elements(By.TAG_NAME, 'source')
                        best_url = None
                        if sources:
                            # Prioritize desktop version (_detail_desktop.jpg)
                            for source in sources:
                                srcset = source.get_attribute('srcSet')
                                if srcset:
                                    url = srcset.split(',')[0].strip().split(' ')[0]
                                    # Prefer desktop quality
                                    if '_detail_desktop.jpg' in url:
                                        best_url = url
                                        self.logger.info(f"📸 Found desktop quality: {url}")
                                        break
                                    elif not best_url:  # Store first option as fallback
                                        best_url = url

                            if best_url:
                                found_images.add(best_url)
                                continue

                        # FALLBACK 2: Regular img tag
                        img = slide.find_element(By.TAG_NAME, 'img')
                        src = img.get_attribute('src')
                        if src and 'revolico' in src:
                            found_images.add(src)
                            self.logger.info(f"📷 Found regular image: {src}")
                    except Exception as e:
                        self.logger.info(f"Error extracting image from slide: {e}")
                        continue

                # Convert all image URLs to highest quality (_high.jpg)
                high_quality_images = []
                for img_url in found_images:
                    # Convert _detail_desktop.jpg or any other variant to _high.jpg
                    if 'pic.revolico.com/pics/' in img_url:
                        # Extract hash and convert to _high.jpg
                        high_url = re.sub(r'(https://pic\.revolico\.com/pics/[a-f0-9]+)_.*?\.jpg', r'\1_high.jpg', img_url)
                        high_quality_images.append(high_url)
                        self.logger.info(f"🖼️  Converted to HIGH quality: {high_url}")
                    else:
                        high_quality_images.append(img_url)

                details['images'] = high_quality_images[:10]
                self.logger.info(f"🖼️  Total HIGH quality images: {len(details['images'])}")
            except Exception as e:
                self.logger.info(f"Could not extract images: {e}")

            # Extract category from breadcrumbs or URL
            try:
                # Look for breadcrumbs
                breadcrumb_selectors = [
                    'nav[aria-label="breadcrumb"]',
                    '.breadcrumb',
                    '[data-cy="breadcrumb"]'
                ]

                for selector in breadcrumb_selectors:
                    breadcrumbs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if breadcrumbs:
                        text = breadcrumbs[0].text
                        # Usually format: Home > Category > Subcategory
                        parts = [p.strip() for p in text.split('>')]
                        if len(parts) > 1:
                            details['category'] = parts[-1] if len(parts) > 2 else parts[1]
                            self.logger.info(f"📁 Category: {details['category']}")
                            break
            except Exception as e:
                self.logger.info(f"Could not extract category: {e}")

            # Extract location
            try:
                # Wait for location element to be present (up to 15 seconds)
                loc_elem = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="adLocation"]'))
                )
                details['location'] = loc_elem.text.strip()
                self.logger.info(f"📍 Location: {details['location']}")
            except Exception as e:
                self.logger.error(f"❌ Could not extract location: {e}")
                self.logger.error(f"Current URL: {self.driver.current_url}")
                self.logger.error(f"Page title: {self.driver.title}")
                # Fallback: extract from title or URL
                try:
                    # Common Cuban provinces
                    provinces = ['La Habana', 'Habana', 'Santiago', 'Camagüey', 'Holguín',
                                'Guantánamo', 'Granma', 'Las Tunas', 'Cienfuegos', 'Villa Clara',
                                'Sancti Spíritus', 'Ciego de Ávila', 'Matanzas', 'Pinar del Río',
                                'Artemisa', 'Mayabeque', 'Isla de la Juventud']

                    title_and_url = self.driver.title + ' ' + url
                    for province in provinces:
                        if province.lower() in title_and_url.lower():
                            details['location'] = province
                            self.logger.info(f"📍 Location (from title): {details['location']}")
                            break
                except:
                    pass

            # Extract condition (new/used)
            try:
                page_text = self.driver.page_source.lower()
                if 'nuevo' in page_text or 'new' in page_text:
                    details['condition'] = 'new'
                elif 'usado' in page_text or 'used' in page_text:
                    details['condition'] = 'used'
                self.logger.info(f"🏷️  Condition: {details['condition']}")
            except Exception as e:
                self.logger.info(f"Could not extract condition: {e}")

        except Exception as e:
            self.logger.error(f"Error extracting listing details: {e}")

        return details

    def _create_stopped_response(self):
        """Create response when scraping is stopped"""
        return {
            'success': False,
            'method': 'Selenium Real Browser',
            'url': 'https://revolico.com',
            'results': {'error': 'Scraping was stopped by user'},
            'duration': '0s'
        }
    
    def _create_error_response(self, error_msg):
        """Create error response"""
        return {
            'success': False,
            'method': 'Selenium Real Browser', 
            'url': 'https://revolico.com',
            'results': {'error': error_msg},
            'duration': '0s'
        }

class SimpleLogger:
    """Simple logger replacement"""
    def info(self, msg):
        print(f"[INFO] {msg}")
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

# Test function
def test_scraper():
    scraper = SeleniumBrowserScraper()
    try:
        print("Testing Firefox driver...")
        if scraper.create_driver():
            scraper.driver.get("https://www.revolico.com")
            time.sleep(8)
            print(f"✅ Success: {scraper.driver.title}")
            scraper.close()
        else:
            print("❌ Failed to create driver")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scraper()