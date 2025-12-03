#!/usr/bin/env python3
"""
Test single listing scraping with detailed debug logs
"""
import sys
import logging
from selenium_browser_scraper import SeleniumBrowserScraper

# Configure logging to show INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_listing(url):
    """Test scraping a single listing"""
    print(f"\n{'='*80}")
    print(f"Testing URL: {url}")
    print(f"{'='*80}\n")

    scraper = SeleniumBrowserScraper()
    scraper.create_driver()

    try:
        # Create a fake listing dict
        listing = {
            'url': url,
            'title': 'Test Listing'
        }

        # Navigate to page
        print("Loading page...")
        scraper.driver.get(url)
        import time
        time.sleep(5)  # Wait for page to load
        print("Page loaded, extracting details...")

        # Extract details
        details = scraper.extract_listing_details(url)

        print(f"\n{'='*80}")
        print(f"RESULTS:")
        print(f"{'='*80}")
        print(f"Title: {details.get('title')}")
        print(f"Seller Name: {details.get('seller_name')}")
        print(f"Price: {details.get('price')} {details.get('currency')}")
        print(f"Description: {details.get('description', '')[:100]}...")
        print(f"{'='*80}\n")

    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    # Test the problematic listings
    urls = [
        "https://www.revolico.com/item/caja-de-herramientas-juego-3piezas-51305140",
        "https://www.revolico.com/item/olla-reina-milexus-6l-ahora-a-7500-antes-8000-con-1-mes-de-garantia-47726781"
    ]

    for url in urls:
        test_listing(url)
        print("\n" + "="*80 + "\n")
