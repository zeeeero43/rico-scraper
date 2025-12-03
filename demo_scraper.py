#!/usr/bin/env python3
"""
Demo scraper for testing anti-detection with alternative targets
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import logging
from utils import setup_logging, get_random_user_agent

class DemoScraper:
    """Demo scraper that targets publicly accessible sites for testing"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.session = requests.Session()
        
        # Setup realistic headers
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_demo_site(self) -> dict:
        """Scrape a demo site to test our anti-detection measures"""
        
        # Use httpbin.org for testing (publicly accessible)
        test_urls = [
            "http://httpbin.org/headers",  # Shows our headers
            "http://httpbin.org/user-agent",  # Shows our user agent
            "http://httpbin.org/ip",  # Shows our IP
        ]
        
        results = {
            'scraping_date': datetime.now().isoformat(),
            'results': [],
            'headers_test': None,
            'user_agent_test': None,
            'ip_test': None
        }
        
        try:
            # Test headers
            response = self.session.get(test_urls[0], timeout=10)
            if response.status_code == 200:
                results['headers_test'] = response.json()
                self.logger.info("Headers test successful")
            
            # Test user agent
            response = self.session.get(test_urls[1], timeout=10)
            if response.status_code == 200:
                results['user_agent_test'] = response.json()
                self.logger.info("User-Agent test successful")
            
            # Test IP
            response = self.session.get(test_urls[2], timeout=10)
            if response.status_code == 200:
                results['ip_test'] = response.json()
                self.logger.info("IP test successful")
            
            # Try a real website that's more lenient (quotes.toscrape.com)
            try:
                demo_response = self.session.get("http://quotes.toscrape.com/", timeout=10)
                if demo_response.status_code == 200:
                    soup = BeautifulSoup(demo_response.content, 'html.parser')
                    quotes = soup.find_all('div', class_='quote')[:3]
                    
                    for i, quote in enumerate(quotes):
                        text = quote.find('span', class_='text')
                        author = quote.find('small', class_='author')
                        
                        if text and author:
                            results['results'].append({
                                'index': i + 1,
                                'text': text.get_text(strip=True),
                                'author': author.get_text(strip=True),
                                'scraped_at': datetime.now().isoformat()
                            })
                    
                    self.logger.info(f"Successfully scraped {len(results['results'])} quotes")
                else:
                    self.logger.warning(f"Demo site returned status: {demo_response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"Demo site scraping failed: {e}")
        
        except Exception as e:
            self.logger.error(f"Testing failed: {e}")
        
        return results


def main():
    """Test the demo scraper"""
    print("=" * 60)
    print("DEMO SCRAPER - ANTI-DETECTION TEST")
    print("Testing anti-detection measures with public sites")
    print("=" * 60)
    
    scraper = DemoScraper()
    results = scraper.scrape_demo_site()
    
    # Save results
    with open('demo_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Display results
    print(f"\n📊 DEMO RESULTS:")
    print(f"   • Headers test: {'✅ OK' if results['headers_test'] else '❌ Failed'}")
    print(f"   • User-Agent test: {'✅ OK' if results['user_agent_test'] else '❌ Failed'}")
    print(f"   • IP test: {'✅ OK' if results['ip_test'] else '❌ Failed'}")
    print(f"   • Demo quotes scraped: {len(results['results'])}")
    
    if results['user_agent_test']:
        print(f"   • Current User-Agent: {results['user_agent_test']['user-agent']}")
    
    if results['ip_test']:
        print(f"   • Current IP: {results['ip_test']['origin']}")
    
    print(f"\n💾 Results saved to: demo_results.json")


if __name__ == "__main__":
    main()