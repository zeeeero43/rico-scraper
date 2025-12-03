import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from datetime import datetime

class SimpleBrowserScraper:
    """Simple browser simulation scraper for Revolico.com"""
    
    def __init__(self):
        self.session = self.create_session()
        self.results = []
        self.stop_requested = False
        # Simple logger replacement
        self.logger = SimpleLogger()
        
    def create_session(self):
        """Create session with normal browser headers"""
        session = requests.Session()
        
        # Simple browser headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def stop(self):
        """Stop the scraping process"""
        self.stop_requested = True
        self.logger.info("Stop requested by user")
    
    def should_stop(self):
        """Check if scraping should stop"""
        return self.stop_requested
        
    def extract_phone_numbers(self, text):
        """Extract Cuban phone numbers from text"""
        # Simple phone extraction
        phone_patterns = [
            r'\+?53\s?\d{8}',     # +53 12345678 or 53 12345678
            r'\d{8}'              # 12345678
        ]
        
        found_phones = []
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            found_phones.extend(phones)
        
        # Remove duplicates
        return list(set([phone.strip() for phone in found_phones if phone.strip()]))
        
    def scrape_revolico(self, max_listings=3):
        """Main scraping function"""
        start_time = time.time()
        
        try:
            self.logger.info("🔍 Accessing revolico.com like normal browser...")
            
            # Step 1: Visit homepage like normal user
            if self.should_stop():
                return self._create_stopped_response()
                
            response = self.session.get('https://revolico.com', timeout=30)
            self.logger.info(f"Homepage status: {response.status_code}")
            
            if response.status_code != 200:
                self.logger.error("❌ Homepage blocked")
                return self._create_error_response("Homepage access failed")
            
            # Parse homepage  
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find listing links - simplified approach
            listing_links = []
            for link in soup.find_all('a', href=True)[:50]:  # Check first 50 links
                if self.should_stop():
                    return self._create_stopped_response()
                    
                href = link.get('href')
                if href and 'anunc' in href:  # Simplified check
                    if href.startswith('/'):
                        href = 'https://revolico.com' + href
                    listing_links.append({
                        'url': href,
                        'title': link.get_text(strip=True)[:100]  # Limit title length
                    })
                    if len(listing_links) >= max_listings:
                        break
            
            self.logger.info(f"Found {len(listing_links)} listings")
            
            if not listing_links:
                self.logger.warning("No listings found on homepage")
                return self._create_error_response("No listings found")
            
            # Visit each listing like normal user
            for i, listing in enumerate(listing_links):
                if self.should_stop():
                    return self._create_stopped_response()
                    
                try:
                    self.logger.info(f"📄 Visiting listing {i+1}: {listing['title'][:50]}...")
                    
                    # Wait like human user (2-5 seconds)
                    delay = random.uniform(2, 5)
                    self.logger.info(f"Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
                    
                    if self.should_stop():
                        return self._create_stopped_response()
                    
                    # Visit listing page
                    response = self.session.get(listing['url'], timeout=30)
                    self.logger.info(f"Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        # Extract phone numbers
                        found_phones = self.extract_phone_numbers(response.text)
                        
                        if found_phones:
                            result = {
                                'title': listing['title'],
                                'url': listing['url'],
                                'phones': found_phones,
                                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            self.results.append(result)
                            self.logger.info(f"✅ Found phones: {found_phones}")
                        else:
                            self.logger.info("❌ No phone numbers found")
                    else:
                        self.logger.warning(f"❌ Failed to load listing: {response.status_code}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error with listing {i+1}: {e}")
                    continue
            
            # Create successful response
            duration = round(time.time() - start_time, 2)
            total_phones = sum(len(r['phones']) for r in self.results)
            
            return {
                'success': True,
                'method': 'Simple Browser Simulation',
                'url': 'https://revolico.com',
                'results': {
                    'listings': self.results,
                    'total_phones': total_phones,
                    'total_listings': len(self.results)
                },
                'duration': f'{duration}s'
            }
            
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            self.logger.error(f"Critical error during scraping: {e}")
            return {
                'success': False,
                'method': 'Simple Browser Simulation',
                'url': 'https://revolico.com',
                'results': {'error': f'Critical error: {e}'},
                'duration': f'{duration}s'
            }
    
    def _create_stopped_response(self):
        """Create response when scraping is stopped"""
        return {
            'success': False,
            'method': 'Simple Browser Simulation',
            'url': 'https://revolico.com',
            'results': {'error': 'Scraping was stopped by user'},
            'duration': '0s'
        }
    
    def _create_error_response(self, error_msg):
        """Create error response"""
        return {
            'success': False,
            'method': 'Simple Browser Simulation', 
            'url': 'https://revolico.com',
            'results': {'error': error_msg},
            'duration': '0s'
        }
    
    def save_results(self, filename='revolico_phones.json'):
        """Save results to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            # Print summary
            self.logger.info(f"📊 RESULTS SUMMARY:")
            self.logger.info(f"Total listings scraped: {len(self.results)}")
            total_phones = sum(len(r['phones']) for r in self.results)
            self.logger.info(f"Total phone numbers found: {total_phones}")
            
            for i, result in enumerate(self.results, 1):
                self.logger.info(f"{i}. {result['title'][:60]}...")
                self.logger.info(f"   Phones: {result['phones']}")
                
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")

class SimpleLogger:
    """Simple logger replacement to avoid dependencies"""
    def info(self, msg):
        print(f"[INFO] {msg}")
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

if __name__ == "__main__":
    scraper = SimpleBrowserScraper()
    results = scraper.scrape_revolico()
    scraper.save_results()
    print("✅ Scraping completed!")