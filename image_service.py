"""
Image Proxy Service
Verwaltet Image-URLs und erstellt Hash-basierte IDs
"""
import hashlib
import os
import requests
from models import db, ImageProxy


class ImageProxyService:
    """Service zum Verwalten von Image-Proxies"""

    @staticmethod
    def create_hash(url):
        """Erstellt SHA256 Hash von URL"""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    @staticmethod
    def get_or_create_proxy(url):
        """
        Holt oder erstellt einen Image Proxy Eintrag
        Returns: image_hash (str)
        """
        image_hash = ImageProxyService.create_hash(url)

        # Check if already exists
        existing = ImageProxy.query.filter_by(image_hash=image_hash).first()
        if existing:
            return existing.image_hash

        # Create new proxy entry
        proxy = ImageProxy(
            image_hash=image_hash,
            original_url=url
        )
        db.session.add(proxy)
        db.session.commit()

        return proxy.image_hash

    @staticmethod
    def get_url_by_hash(image_hash):
        """
        Holt die Original URL anhand des Hash
        Returns: original_url (str) or None
        """
        proxy = ImageProxy.query.filter_by(image_hash=image_hash).first()
        return proxy.original_url if proxy else None

    @staticmethod
    def process_image_urls(image_urls):
        """
        Konvertiert Liste von URLs zu Hash-IDs
        Returns: list of image_hashes
        """
        if not image_urls:
            return []

        hashes = []
        for url in image_urls:
            try:
                image_hash = ImageProxyService.get_or_create_proxy(url)
                hashes.append(image_hash)
            except Exception as e:
                print(f"Error processing image URL {url}: {e}")
                continue

        return hashes

    @staticmethod
    def download_and_cache_image(url, cache_dir='cached_images'):
        """
        Lädt Bild herunter und speichert es lokal (für zeitbegrenzte URLs)
        Returns: image_hash (str) or None
        """
        try:
            # Create cache directory if needed
            os.makedirs(cache_dir, exist_ok=True)

            # Generate hash for this URL
            image_hash = ImageProxyService.create_hash(url)

            # Check if already cached
            existing = ImageProxy.query.filter_by(image_hash=image_hash).first()
            if existing and existing.cached and os.path.exists(existing.cache_path):
                print(f"Image already cached: {existing.cache_path}")
                return existing.image_hash

            # Download image with browser headers (for Revolico)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://www.revolico.com/' if 'revolico.com' in url else None
            }

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to download image from {url}: HTTP {response.status_code}")
                return None

            # Determine file extension from content type
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            ext = 'jpg'
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            elif 'gif' in content_type:
                ext = 'gif'

            # Save to cache directory
            cache_filename = f"{image_hash}.{ext}"
            cache_path = os.path.join(cache_dir, cache_filename)

            with open(cache_path, 'wb') as f:
                f.write(response.content)

            print(f"✅ Cached image: {cache_path} ({len(response.content)} bytes)")

            # Update or create database entry
            if existing:
                existing.cached = True
                existing.cache_path = cache_path
            else:
                proxy = ImageProxy(
                    image_hash=image_hash,
                    original_url=url,
                    cached=True,
                    cache_path=cache_path
                )
                db.session.add(proxy)

            db.session.commit()
            return image_hash

        except Exception as e:
            print(f"Error downloading/caching image {url}: {e}")
            # Fall back to regular proxy (without cache)
            return ImageProxyService.get_or_create_proxy(url)
