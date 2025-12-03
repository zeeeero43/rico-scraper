#!/usr/bin/env python3
"""
Script to cache existing Revolico profile pictures from database
"""
import os
import sys
from app import app
from models import db, ImageProxy
from image_service import ImageProxyService

def cache_existing_profiles():
    """Cache all uncached Revolico profile pictures"""
    with app.app_context():
        # Find all Revolico profile pictures that are not cached
        revolico_profiles = ImageProxy.query.filter(
            ImageProxy.original_url.like('%pic.revolico.com/users%'),
            ImageProxy.cached == False
        ).all()

        print(f"Found {len(revolico_profiles)} Revolico profile pictures to cache")

        success_count = 0
        fail_count = 0

        for proxy in revolico_profiles:
            print(f"\nCaching: {proxy.original_url[:80]}...")

            # Try to download and cache
            result = ImageProxyService.download_and_cache_image(proxy.original_url)

            if result:
                success_count += 1
                print(f"✅ Success ({success_count}/{len(revolico_profiles)})")
            else:
                fail_count += 1
                print(f"❌ Failed ({fail_count}/{len(revolico_profiles)})")

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  ✅ Successfully cached: {success_count}")
        print(f"  ❌ Failed to cache: {fail_count}")
        print(f"{'='*60}")

if __name__ == '__main__':
    cache_existing_profiles()
