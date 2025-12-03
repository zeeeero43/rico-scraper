#!/usr/bin/env python3
"""
WhatsApp Web Automation System for Rico-Cuba Outreach
Selenium-based automation for sending personalized messages to scraped phone numbers
"""

import time
import json
import logging
import os
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        self.messages_sent_today = 0
        self.daily_limit = 50
        self.min_delay = 60  # seconds
        self.max_delay = 180  # seconds
        self.contacts_file = 'whatsapp_contacts.json'
        self.logger = logger
        self.profile_dir = os.path.join(os.getcwd(), 'whatsapp_firefox_profile')
        self.qr_code_image = None
        self.setup_callback = None
        
    def setup_driver(self):
        """Setup Firefox driver for WhatsApp Web (non-headless for QR code)"""
        try:
            firefox_options = FirefoxOptions()

            # Explicitly set Firefox binary location
            firefox_options.binary_location = '/usr/lib/firefox-esr/firefox-esr'

            # Essential options for WhatsApp Web compatibility
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)

            # User agent to appear more like a real browser
            firefox_options.set_preference("general.useragent.override",
                                         "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")

            # Media permissions for WhatsApp
            firefox_options.set_preference("media.navigator.enabled", True)
            firefox_options.set_preference("media.navigator.permission.disabled", True)

            # Window size for better QR code visibility
            firefox_options.add_argument('--width=1200')
            firefox_options.add_argument('--height=800')

            # Use headless mode since we'll capture QR code image
            firefox_options.add_argument('--headless')

            # Keep browser open for QR code scanning
            self.logger.info("🖥️  Setting up Firefox browser (headless for QR code capture)...")

            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.wait = WebDriverWait(self.driver, 30)
            
            self.logger.info("✅ Firefox browser initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup Firefox driver: {e}")
            return False
    
    def capture_qr_code(self):
        """Capture QR code as base64 image"""
        try:
            # Wait for QR code to appear
            time.sleep(3)
            
            # Find QR code element
            qr_elements = self.driver.find_elements(By.XPATH, "//canvas[@role='img']")
            if not qr_elements:
                qr_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-ref] canvas")
            
            if qr_elements:
                qr_element = qr_elements[0]
                
                # Get QR code as base64 image
                qr_base64 = self.driver.execute_script("""
                    var canvas = arguments[0];
                    return canvas.toDataURL('image/png').substring(22);
                """, qr_element)
                
                self.qr_code_image = qr_base64
                self.logger.info("✅ QR code captured successfully")
                return qr_base64
            else:
                # Fallback: screenshot of the page
                screenshot = self.driver.get_screenshot_as_base64()
                self.qr_code_image = screenshot
                self.logger.info("📸 Page screenshot captured as fallback")
                return screenshot
                
        except Exception as e:
            self.logger.error(f"❌ Failed to capture QR code: {e}")
            return None

    def login_whatsapp(self, callback=None):
        """Login to WhatsApp Web and wait for QR code scan"""
        try:
            self.setup_callback = callback
            self.logger.info("🌐 Loading WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            
            # Capture QR code
            qr_image = self.capture_qr_code()
            
            if qr_image and self.setup_callback:
                self.setup_callback('qr_ready', {'qr_image': qr_image})
            
            self.logger.info("📱 Please scan the QR code with your phone to login...")
            self.logger.info("⏳ Waiting up to 90 seconds for login...")
            
            # Wait for QR code to disappear (indicates successful login)
            try:
                # Wait for the chat list to appear (sign of successful login)
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
                )
                
                self.is_logged_in = True
                logger.info("✅ Successfully logged in to WhatsApp Web!")
                
                # Wait a bit more for full page load
                time.sleep(3)
                return True
                
            except TimeoutException:
                logger.error("❌ Login timeout - QR code not scanned within 60 seconds")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def format_phone_for_whatsapp(self, phone: str) -> str:
        """Format Cuban phone number for WhatsApp"""
        # Remove any existing formatting
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        
        # Ensure it starts with 53 for Cuba
        if clean_phone.startswith('53') and len(clean_phone) >= 10:
            return f"+{clean_phone}"
        else:
            logger.warning(f"Invalid Cuban phone number format: {phone}")
            return None
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send message to a specific phone number via WhatsApp Web"""
        result = {
            'phone': phone_number,
            'status': 'failed',
            'message': '',
            'timestamp': datetime.now().isoformat(),
            'error': None
        }
        
        try:
            formatted_phone = self.format_phone_for_whatsapp(phone_number)
            if not formatted_phone:
                result['error'] = 'Invalid phone number format'
                return result
            
            logger.info(f"📤 Sending message to {formatted_phone}...")
            
            # Create WhatsApp Web direct message URL
            wa_url = f"https://web.whatsapp.com/send?phone={formatted_phone.replace('+', '')}"
            
            self.driver.get(wa_url)
            time.sleep(5)  # Wait for page load
            
            # Wait for message input box
            try:
                message_box = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]'))
                )
                
                # Clear any existing text and type message
                message_box.clear()
                message_box.send_keys(message)
                
                # Wait a moment before sending
                time.sleep(2)
                
                # Send message (Enter key)
                message_box.send_keys(Keys.ENTER)
                
                # Wait for message to be sent
                time.sleep(3)
                
                result['status'] = 'sent'
                result['message'] = message[:50] + '...' if len(message) > 50 else message
                logger.info(f"✅ Message sent successfully to {formatted_phone}")
                
                self.messages_sent_today += 1
                
            except TimeoutException:
                result['error'] = 'Message input box not found - number may not be on WhatsApp'
                logger.warning(f"⚠️ Could not find message input for {formatted_phone}")
            
            except Exception as send_error:
                result['error'] = f'Send error: {str(send_error)}'
                logger.error(f"❌ Failed to send to {formatted_phone}: {send_error}")
                
        except Exception as e:
            result['error'] = f'General error: {str(e)}'
            logger.error(f"❌ Error processing {phone_number}: {e}")
        
        return result
    
    def load_contacts_data(self) -> Dict[str, Any]:
        """Load contacts data from JSON file"""
        try:
            with open(self.contacts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("📄 No existing contacts file found, creating new one...")
            return {'contacts': [], 'stats': {'total_sent': 0, 'last_reset': datetime.now().date().isoformat()}}
        except Exception as e:
            logger.error(f"❌ Error loading contacts data: {e}")
            return {'contacts': [], 'stats': {'total_sent': 0, 'last_reset': datetime.now().date().isoformat()}}
    
    def save_contacts_data(self, data: Dict[str, Any]):
        """Save contacts data to JSON file"""
        try:
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error saving contacts data: {e}")
    
    def get_uncontacted_numbers(self) -> List[Dict[str, str]]:
        """Get list of phone numbers that haven't been contacted yet"""
        try:
            # Load scraped phone numbers from database or revolico_data.json
            scraped_data = []
            
            # Try to load from revolico_data.json first
            try:
                with open('revolico_data.json', 'r', encoding='utf-8') as f:
                    revolico_results = json.load(f)
                    if 'listings' in revolico_results:
                        for listing in revolico_results['listings']:
                            for phone in listing.get('phones', []):
                                scraped_data.append({
                                    'phone': phone,
                                    'source_title': listing.get('title', 'Unknown'),
                                    'source_url': listing.get('url', '')
                                })
            except FileNotFoundError:
                logger.warning("📄 No revolico_data.json found")
            
            # Load WhatsApp contacts data
            contacts_data = self.load_contacts_data()
            contacted_phones = {contact['phone'] for contact in contacts_data['contacts'] if contact.get('contacted', False)}
            
            # Filter uncontacted numbers
            uncontacted = [item for item in scraped_data if item['phone'] not in contacted_phones]
            
            logger.info(f"📊 Found {len(uncontacted)} uncontacted numbers out of {len(scraped_data)} total")
            return uncontacted
            
        except Exception as e:
            logger.error(f"❌ Error getting uncontacted numbers: {e}")
            return []
    
    def start_outreach_campaign(self, message_template: str, socketio=None) -> Dict[str, Any]:
        """Start automated WhatsApp outreach campaign"""
        def emit_log(level: str, message: str):
            """Emit log message to web interface"""
            if socketio:
                socketio.emit('whatsapp_log', {
                    'level': level,
                    'message': message,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
            logger.log(getattr(logging, level.upper()), message)
        
        emit_log('info', "🚀 Starting WhatsApp Outreach Campaign...")
        
        # Check daily limit
        if self.messages_sent_today >= self.daily_limit:
            emit_log('warning', f"⚠️ Daily limit of {self.daily_limit} messages reached")
            return {'success': False, 'error': 'Daily limit reached'}
        
        # Get uncontacted numbers
        uncontacted_numbers = self.get_uncontacted_numbers()
        if not uncontacted_numbers:
            emit_log('info', "ℹ️ No uncontacted numbers found")
            return {'success': True, 'sent': 0, 'message': 'No numbers to contact'}
        
        remaining_quota = self.daily_limit - self.messages_sent_today
        numbers_to_process = uncontacted_numbers[:remaining_quota]
        
        emit_log('info', f"📱 Processing {len(numbers_to_process)} numbers (Daily quota: {remaining_quota})")
        
        # Load contacts data
        contacts_data = self.load_contacts_data()
        results = []
        successful_sends = 0
        
        for i, contact in enumerate(numbers_to_process, 1):
            emit_log('info', f"📤 [{i}/{len(numbers_to_process)}] Contacting {contact['phone']}...")
            
            # Personalize message if needed
            personalized_message = message_template.replace('{phone}', contact['phone'])
            personalized_message = personalized_message.replace('{source}', contact.get('source_title', 'Revolico'))
            
            # Send message
            result = self.send_message(contact['phone'], personalized_message)
            results.append(result)
            
            # Update contacts data
            contact_entry = {
                'phone': contact['phone'],
                'contacted': result['status'] == 'sent',
                'last_contact_date': result['timestamp'],
                'message_sent': result.get('message', ''),
                'status': result['status'],
                'error': result.get('error'),
                'source_title': contact.get('source_title', ''),
                'source_url': contact.get('source_url', '')
            }
            
            # Add or update contact in data
            existing_contact = next((c for c in contacts_data['contacts'] if c['phone'] == contact['phone']), None)
            if existing_contact:
                existing_contact.update(contact_entry)
            else:
                contacts_data['contacts'].append(contact_entry)
            
            if result['status'] == 'sent':
                successful_sends += 1
                emit_log('success', f"✅ Message sent to {contact['phone']}")
            else:
                emit_log('error', f"❌ Failed to send to {contact['phone']}: {result.get('error', 'Unknown error')}")
            
            # Save progress after each message
            self.save_contacts_data(contacts_data)
            
            # Random delay between messages (avoid being flagged)
            if i < len(numbers_to_process):  # Don't delay after last message
                delay = random.randint(self.min_delay, self.max_delay)
                emit_log('info', f"⏳ Waiting {delay} seconds before next message...")
                time.sleep(delay)
        
        # Update stats
        contacts_data['stats']['total_sent'] += successful_sends
        contacts_data['stats']['last_campaign'] = datetime.now().isoformat()
        self.save_contacts_data(contacts_data)
        
        campaign_result = {
            'success': True,
            'total_processed': len(numbers_to_process),
            'successful_sends': successful_sends,
            'failed_sends': len(numbers_to_process) - successful_sends,
            'remaining_quota': self.daily_limit - self.messages_sent_today,
            'results': results
        }
        
        emit_log('info', f"✅ Campaign completed: {successful_sends}/{len(numbers_to_process)} messages sent")
        
        return campaign_result
    
    def get_campaign_stats(self) -> Dict[str, Any]:
        """Get statistics about WhatsApp campaigns"""
        contacts_data = self.load_contacts_data()
        
        total_contacts = len(contacts_data['contacts'])
        contacted_today = sum(1 for c in contacts_data['contacts'] 
                            if c.get('last_contact_date', '').startswith(datetime.now().date().isoformat()))
        successful_contacts = sum(1 for c in contacts_data['contacts'] if c.get('contacted', False))
        
        return {
            'total_contacts': total_contacts,
            'contacted_today': contacted_today,
            'successful_contacts': successful_contacts,
            'daily_limit': self.daily_limit,
            'messages_sent_today': self.messages_sent_today,
            'remaining_quota': self.daily_limit - self.messages_sent_today
        }
    
    def cleanup(self):
        """Clean shutdown of browser"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("🧹 Browser closed successfully")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

# Default message templates
DEFAULT_MESSAGES = {
    'rico_cuba_promotion': """¡Hola! 👋

Encontré tu número en Revolico y me pareció interesante tu anuncio.

Te quería comentar sobre Rico-Cuba, una plataforma que está ayudando a muchos cubanos a conectar mejor con el mercado.

¿Te interesaría saber más sobre cómo podríamos colaborar?

Saludos desde Cuba 🇨🇺""",
    
    'business_opportunity': """¡Buenas! 🤝

Vi tu publicación en Revolico y creo que podrías estar interesado en una oportunidad de negocio.

Rico-Cuba está buscando colaboradores activos para expandir nuestra red.

¿Tienes unos minutos para una conversación rápida?

¡Gracias! 📱""",
    
    'simple_intro': """Hola, vi tu anuncio en Revolico.

¿Podrías darme más información?

Gracias."""
}

if __name__ == "__main__":
    # Test the WhatsApp bot
    bot = WhatsAppBot()
    
    if bot.setup_driver():
        if bot.login_whatsapp():
            print("✅ Ready for WhatsApp automation!")
            # Test with a small campaign
            # result = bot.start_outreach_campaign(DEFAULT_MESSAGES['simple_intro'])
            # print(json.dumps(result, indent=2, ensure_ascii=False))
        bot.cleanup()