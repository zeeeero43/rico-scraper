#!/usr/bin/env python3
"""
Test Firefox setup for Selenium scraper
"""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import time

def test_firefox_basic():
    """Test basic Firefox setup"""
    print("Testing Firefox driver...")

    try:
        # Setup Firefox options
        options = FirefoxOptions()
        options.add_argument('--headless')
        options.add_argument('--width=1920')
        options.add_argument('--height=1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # Explicitly set Firefox binary location
        options.binary_location = '/usr/lib/firefox-esr/firefox-esr'

        # Setup service with geckodriver
        service = FirefoxService(GeckoDriverManager().install())

        # Create driver
        print("Creating Firefox driver...")
        driver = webdriver.Firefox(service=service, options=options)

        # Test navigation
        print("Navigating to revolico.com...")
        driver.get("https://www.revolico.com")
        time.sleep(8)

        print(f"✅ Success: {driver.title}")
        print(f"✅ URL: {driver.current_url}")

        driver.quit()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_firefox_basic()
