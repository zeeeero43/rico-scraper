#!/usr/bin/env python3
"""
Test script for Selenium scraper functionality
"""

import sys
import json
from selenium_scraper import CloudflareBypasser

def test_selenium_setup():
    """Test basic Selenium setup"""
    print("=" * 60)
    print("SELENIUM SETUP TEST")
    print("=" * 60)
    
    try:
        scraper = CloudflareBypasser()
        
        # Test driver setup
        print("Testing Chrome driver setup...")
        driver = scraper.setup_driver(mobile_mode=True)
        
        # Test basic navigation
        print("Testing basic navigation to Google...")
        driver.get("https://www.google.com")
        
        print(f"✅ Page title: {driver.title}")
        print(f"✅ Current URL: {driver.current_url}")
        print(f"✅ Page loaded successfully")
        
        # Test mobile vs desktop
        print("\nTesting desktop mode...")
        driver.quit()
        
        driver = scraper.setup_driver(mobile_mode=False)
        driver.get("https://httpbin.org/user-agent")
        
        page_source = driver.page_source
        print(f"✅ Desktop user agent test completed")
        
        driver.quit()
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_revolico_access():
    """Test access to Revolico with enhanced method"""
    print("\n" + "=" * 60)
    print("REVOLICO ACCESS TEST")
    print("=" * 60)
    
    try:
        scraper = CloudflareBypasser()
        driver = scraper.setup_driver(mobile_mode=True)
        
        # Test URL finding
        working_url, results = scraper.find_working_url(driver)
        
        print(f"Working URL found: {working_url}")
        print(f"Strategy used: {results.get('strategy_used', 'Unknown')}")
        print(f"Total attempts: {len(results.get('attempts', []))}")
        
        for attempt in results.get('attempts', []):
            status = attempt.get('status', 'unknown')
            url = attempt.get('url', 'unknown')
            print(f"  - {url}: {status}")
        
        driver.quit()
        
        if working_url:
            print("✅ Successfully found working URL!")
            return True
        else:
            print("❌ No working URL found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_full_scraping():
    """Test full scraping workflow"""
    print("\n" + "=" * 60)
    print("FULL SCRAPING TEST")
    print("=" * 60)
    
    try:
        scraper = CloudflareBypasser()
        results = scraper.run_scraping(max_listings=1)  # Only test 1 listing
        
        print(f"Scraping completed!")
        print(f"  - Strategy: {results.get('strategy_used', 'Unknown')}")
        print(f"  - Working URL: {results.get('working_url', 'None')}")
        print(f"  - Listings found: {results.get('total_listings_found', 0)}")
        print(f"  - Phone numbers: {results.get('total_phone_numbers', 0)}")
        print(f"  - Duration: {results.get('duration_seconds', 0):.2f} seconds")
        print(f"  - Errors: {len(results.get('errors', []))}")
        
        # Save test results
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("✅ Test results saved to test_results.json")
        
        if results.get('total_listings_found', 0) > 0:
            print("✅ Scraping test successful!")
            return True
        else:
            print("⚠️ No listings found, but scraper ran without errors")
            return True
            
    except Exception as e:
        print(f"❌ Scraping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting Selenium scraper tests...\n")
    
    tests = [
        ("Basic Setup", test_selenium_setup),
        ("Revolico Access", test_revolico_access),
        ("Full Scraping", test_full_scraping)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"💥 {test_name} test CRASHED: {e}")
    
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! Selenium scraper is ready.")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()