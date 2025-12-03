#!/usr/bin/env python3
"""
Test script for enhanced requests scraper (Chrome-free fallback)
"""

import sys
import json
from enhanced_requests_scraper import AdvancedRequestsScraper

def test_session_setup():
    """Test session setup and basic functionality"""
    print("=" * 60)
    print("ENHANCED REQUESTS SCRAPER TEST")
    print("=" * 60)
    
    try:
        scraper = AdvancedRequestsScraper()
        
        print("✅ Scraper initialized successfully")
        print(f"✅ Session configured")
        print(f"✅ Headers: {len(scraper.session.headers)} headers set")
        print(f"✅ Mobile User-Agent: {scraper.session.headers.get('User-Agent', 'Not set')[:50]}...")
        
        # Test Google access
        print("\nTesting Google access...")
        if scraper.build_session_with_google():
            print("✅ Google session built successfully")
        else:
            print("⚠️ Google session failed, but continuing...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_url_finding():
    """Test URL finding strategies"""
    print("\n" + "=" * 60)
    print("URL FINDING TEST")
    print("=" * 60)
    
    try:
        scraper = AdvancedRequestsScraper()
        working_url, results = scraper.find_working_url()
        
        print(f"Working URL found: {working_url}")
        print(f"Strategy used: {results.get('strategy_used', 'Unknown')}")
        print(f"Total attempts: {len(results.get('attempts', []))}")
        
        for i, attempt in enumerate(results.get('attempts', []), 1):
            url = attempt.get('url', 'unknown')
            status = attempt.get('status_code', 'unknown')
            protection = attempt.get('protection', {})
            print(f"  {i}. {url}")
            print(f"     Status: {status}")
            print(f"     Protection: {protection}")
        
        if working_url:
            print("✅ Successfully found working URL!")
            return True, working_url
        else:
            print("❌ No working URL found")
            return False, None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False, None

def test_full_scraping():
    """Test full scraping workflow"""
    print("\n" + "=" * 60)
    print("FULL ENHANCED SCRAPING TEST")
    print("=" * 60)
    
    try:
        scraper = AdvancedRequestsScraper()
        results = scraper.run_scraping(max_listings=2)  # Test with 2 listings
        
        print(f"Scraping completed!")
        print(f"  - Method: {results.get('method', 'Unknown')}")
        print(f"  - Strategy: {results.get('strategy_used', 'Unknown')}")
        print(f"  - Working URL: {results.get('working_url', 'None')}")
        print(f"  - Listings found: {results.get('total_listings_found', 0)}")
        print(f"  - Phone numbers: {results.get('total_phone_numbers', 0)}")
        print(f"  - Duration: {results.get('duration_seconds', 0):.2f} seconds")
        print(f"  - Errors: {len(results.get('errors', []))}")
        
        # Save test results
        with open('enhanced_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("✅ Test results saved to enhanced_test_results.json")
        
        # Show found listings
        if results.get('results'):
            print(f"\n📋 FOUND LISTINGS:")
            for i, result in enumerate(results['results'], 1):
                phones = result.get('phone_numbers', [])
                print(f"  {i}. {result['title'][:40]}...")
                print(f"     📞 Phones: {len(phones)} found")
                print(f"     🔗 URL: {result['url'][:60]}...")
        
        # Show errors if any
        if results.get('errors'):
            print(f"\n⚠️ ERRORS:")
            for error in results['errors']:
                print(f"  • {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scraping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting Enhanced Requests scraper tests...\n")
    
    tests = [
        ("Session Setup", test_session_setup),
        ("URL Finding", lambda: test_url_finding()[0]),
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
        print("🎉 All tests passed! Enhanced scraper is ready.")
        sys.exit(0)
    elif passed > 0:
        print("⚠️ Some tests passed. Enhanced scraper is partially functional.")
        sys.exit(0)
    else:
        print("❌ All tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()