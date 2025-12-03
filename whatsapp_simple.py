#!/usr/bin/env python3
"""
Vereinfachte WhatsApp Web Automation für Replit
Mit QR-Code Screenshot und Session-Persistierung
"""

import time
import os
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import base64

logger = logging.getLogger(__name__)

class SimpleWhatsAppBot:
    def __init__(self, profile_dir=None, account_id=None):
        """
        Initialize WhatsApp Bot

        Args:
            profile_dir: Custom profile directory (for multi-account support)
            account_id: WhatsApp account ID from database
        """
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        self.account_id = account_id

        # Use custom profile_dir or default
        if profile_dir:
            self.profile_dir = profile_dir
        else:
            self.profile_dir = os.path.join(os.getcwd(), 'whatsapp_profile')

        # QR code file in account-specific directory
        self.qr_screenshot_file = os.path.join(self.profile_dir, 'whatsapp_qr_code.png')
        
    def setup_browser(self):
        """Setup Firefox mit Session-Persistierung"""
        try:
            # Profile directory für Session-Persistierung erstellen
            os.makedirs(self.profile_dir, exist_ok=True)

            logger.info(f"🖥️  Setting up Firefox browser with profile: {self.profile_dir}")

            firefox_options = FirefoxOptions()

            # KRITISCHER FIX: Direktes Profile-Verzeichnis verwenden statt FirefoxProfile-Objekt
            # Dies stellt sicher, dass Firefox das Profil direkt nutzt und Session-Daten dort speichert
            firefox_options.add_argument('-profile')
            firefox_options.add_argument(self.profile_dir)

            # Headless Mode für Replit
            firefox_options.add_argument('--headless')
            firefox_options.add_argument('--width=1200')
            firefox_options.add_argument('--height=800')

            # Explicitly set Firefox binary location
            firefox_options.binary_location = '/usr/lib/firefox-esr/firefox-esr'

            # Anti-detection
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)

            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.wait = WebDriverWait(self.driver, 30)

            logger.info("✅ Firefox browser initialized successfully with persistent profile")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup Firefox: {e}")
            return False
    
    def start_whatsapp_web(self):
        """Startet WhatsApp Web und erstellt QR-Code Screenshot"""
        import sys
        try:
            print(f"[WHATSAPP] Loading WhatsApp Web...")
            sys.stdout.flush()
            logger.info("🌐 Loading WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")

            # Warten, dass die Seite geladen ist
            print(f"[WHATSAPP] Waiting 5 seconds for page load...")
            time.sleep(5)

            # Prüfen ob bereits eingeloggt
            print(f"[WHATSAPP] Checking if already logged in...")
            try:
                # Wenn Chat-Liste vorhanden, bereits eingeloggt (mit kürzerem Timeout)
                short_wait = WebDriverWait(self.driver, 3)  # Nur 3 Sekunden warten
                short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]')))
                print(f"[WHATSAPP] Already logged in!")
                logger.info("✅ Already logged in to WhatsApp Web!")
                self.is_logged_in = True
                return {'status': 'logged_in', 'message': 'Already logged in'}
            except TimeoutException:
                # QR-Code ist vorhanden, Screenshot erstellen
                print(f"[WHATSAPP] Not logged in, QR code should be visible")
                pass

            # Screenshot der gesamten Seite für QR-Code
            screenshot_path = os.path.join(os.getcwd(), self.qr_screenshot_file)
            print(f"[WHATSAPP] Taking screenshot: {screenshot_path}")
            self.driver.save_screenshot(screenshot_path)

            print(f"[WHATSAPP] Screenshot saved successfully!")
            logger.info(f"📸 QR-Code Screenshot gespeichert: {screenshot_path}")

            return {
                'status': 'qr_ready',
                'message': 'QR-Code bereit zum Scannen',
                'screenshot_path': screenshot_path
            }

        except Exception as e:
            print(f"[WHATSAPP ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"❌ Failed to start WhatsApp Web: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def check_login_status(self):
        """Prüft ob QR-Code gescannt wurde und Login erfolgreich"""
        try:
            # Prüfen ob QR-Code noch sichtbar ist (bedeutet NICHT eingeloggt)
            qr_elements = self.driver.find_elements(By.CSS_SELECTOR, 'canvas[aria-label="Scan me!"]')
            if qr_elements:
                return {'status': 'waiting', 'message': 'QR code still visible - waiting for scan'}

            # Nur spezifische Post-Login-Elemente prüfen (chat-list erscheint NUR nach Login)
            selectors = [
                '[data-testid="chat-list"]',  # Nur nach Login vorhanden
                '#side'  # Sidebar erscheint nur nach Login
            ]

            logged_in = False
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logged_in = True
                    break
            
            if logged_in:
                if not self.is_logged_in:  # Nur beim ersten Login
                    self.is_logged_in = True
                    logger.info("✅ WhatsApp Login successful!")
                    
                    # Send socket notification
                    try:
                        from app import socketio
                        socketio.emit('whatsapp_log', {
                            'level': 'SUCCESS',
                            'message': '🎉 Erfolgreich bei WhatsApp Web angemeldet!'
                        })
                        socketio.emit('whatsapp_ready', {
                            'message': 'WhatsApp ist bereit für Kampagnen'
                        })
                    except:
                        pass
                
                return {'status': 'logged_in', 'message': 'Login successful'}
            else:
                return {'status': 'waiting', 'message': 'Waiting for QR code scan'}
                
        except Exception as e:
            logger.error(f"❌ Failed to check login status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_qr_code_image(self):
        """Gibt QR-Code als Base64 zurück"""
        try:
            screenshot_path = os.path.join(os.getcwd(), self.qr_screenshot_file)
            
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    return encoded_string
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get QR code image: {e}")
            return None
    
    def send_message(self, phone_number: str, message: str):
        """Sendet Nachricht an Telefonnummer"""
        try:
            # Re-validate login status before sending
            current_status = self.check_login_status()
            if current_status['status'] != 'logged_in':
                logger.warning(f"⚠️ Session expired, re-login required")
                return {'status': 'error', 'message': 'Session expired, please re-login'}

            # Format phone number for WhatsApp
            clean_phone = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            if not clean_phone.startswith('53'):
                return {'status': 'error', 'message': 'Invalid Cuban phone number'}

            wa_url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            logger.info(f"📤 Sending message to {phone_number}...")

            self.driver.get(wa_url)
            time.sleep(12)  # Increased wait time for page load

            # Check for error dialogs first
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-animate-modal-popup="true"]')
                if error_elements:
                    logger.warning(f"⚠️ Error dialog detected for {phone_number}")
                    return {'status': 'error', 'message': 'Phone number not found or invalid'}
            except:
                pass  # No error dialog, continue

            # Try multiple selectors for message input box
            message_box = None
            selectors = [
                '[data-testid="conversation-compose-box-input"]',  # Primary selector
                'div[contenteditable="true"][data-tab="10"]',      # Alternative
                'div[role="textbox"][contenteditable="true"]',     # Fallback
                'footer div[contenteditable="true"]'               # Generic fallback
            ]

            for selector in selectors:
                try:
                    message_box = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Found message box with selector: {selector}")
                    break
                except TimeoutException:
                    continue

            if not message_box:
                # Take screenshot for debugging
                screenshot_dir = os.path.join(os.getcwd(), 'error_screenshots')
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, f'send_fail_{clean_phone}_{int(time.time())}.png')
                self.driver.save_screenshot(screenshot_path)
                logger.error(f"❌ Message input not found, screenshot saved: {screenshot_path}")
                return {'status': 'error', 'message': 'Message input not found', 'screenshot': screenshot_path}

            # Send the message
            message_box.clear()
            message_box.send_keys(message)
            time.sleep(2)

            # Send message with Enter key
            from selenium.webdriver.common.keys import Keys
            message_box.send_keys(Keys.ENTER)

            logger.info(f"✅ Message sent to {phone_number}")
            return {'status': 'success', 'message': f'Message sent to {phone_number}'}

        except Exception as e:
            # Take screenshot on any exception
            try:
                screenshot_dir = os.path.join(os.getcwd(), 'error_screenshots')
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, f'error_{clean_phone}_{int(time.time())}.png')
                self.driver.save_screenshot(screenshot_path)
                logger.error(f"❌ Exception during send, screenshot: {screenshot_path}")
            except:
                pass

            logger.error(f"❌ Failed to send message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def close(self):
        """Schließt Browser"""
        if self.driver:
            self.driver.quit()
            logger.info("🔌 WhatsApp browser closed")

# Global instance
whatsapp_bot = None

def get_whatsapp_bot():
    """Returns global WhatsApp bot instance"""
    global whatsapp_bot
    if whatsapp_bot is None:
        whatsapp_bot = SimpleWhatsAppBot()
    return whatsapp_bot

# Default message templates
SIMPLE_MESSAGES = {
    "rico_promo": """🏝️ Hola! Soy de Rico-Cuba, una nueva Plattform für kubanische Dienstleistungen.

Wir helfen kubanischen Unternehmern dabei, ihre Services online anzubieten. Würden Sie gerne mehr über unsere kostenlosen Marketing-Services erfahren?

🔗 Rico-Cuba.com""",
    
    "business_intro": """¡Hola! Ich habe Ihre Anzeige auf Revolico gesehen.

Wir von Rico-Cuba helfen kubanischen Geschäftsinhabern dabei, online mehr Kunden zu erreichen. Kostenlose Beratung verfügbar.

Hätten Sie 5 Minuten für ein kurzes Gespräch? 📞""",
    
    "simple": """Hola! Ich habe Ihre Anzeige gesehen und würde gerne mehr über Ihre Services erfahren. Könnten wir kurz sprechen? Vielen Dank! 😊"""
}