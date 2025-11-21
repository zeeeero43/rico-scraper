#!/usr/bin/env python3
"""
Flask Web UI für Revolico Phone Number Scraper + WhatsApp Integration
Mit QR-Code Screenshot Anzeige und Session Persistierung
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any

from selenium_browser_scraper import SeleniumBrowserScraper
from utils import load_from_json, get_file_size
from models import db, Customer, ScrapedListing, ImageProxy, WhatsAppAccount, init_database
from whatsapp_simple import get_whatsapp_bot, SIMPLE_MESSAGES
from whatsapp_manager import WhatsAppAccountManager
from image_service import ImageProxyService
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'revolico_scraper_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///revolico_customers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False}
}
socketio = SocketIO(app, cors_allowed_origins="*")

# Datenbank initialisieren
init_database(app)

# Initialize WhatsApp Account Manager
wa_manager = WhatsAppAccountManager(db)

# Restore previously logged-in WhatsApp sessions on startup
with app.app_context():
    wa_manager.restore_logged_in_accounts()

# Global variables to track scraping state
scraping_active = False
current_scraper = None
scraping_results = {}

# Global variables for WhatsApp automation
whatsapp_active = False
current_whatsapp_bot = None
whatsapp_results = {}
whatsapp_qr_ready = False

class WebScrapeLogger:
    """Custom logger that emits to web interface"""

    def __init__(self, socketio):
        self.socketio = socketio

    def log(self, level: str, message: str):
        """Send log message to web interface"""
        self.socketio.emit('log_message', {
            'level': level,
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

        # Also print to console
        print(f"[{level}] {message}")

    def info(self, message: str):
        """Log info message"""
        self.log('INFO', message)

    def warning(self, message: str):
        """Log warning message"""
        self.log('WARNING', message)

    def error(self, message: str):
        """Log error message"""
        self.log('ERROR', message)

# Initialize logger
web_logger = WebScrapeLogger(socketio)

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get scraping status"""
    return jsonify({
        'scraping_active': scraping_active,
        'whatsapp_active': whatsapp_active,
        'results_available': bool(scraping_results),
        'data_file_size': get_file_size('revolico_data.json'),
        'whatsapp_qr_ready': whatsapp_qr_ready
    })

# ===== WHATSAPP API ENDPOINTS =====

@app.route('/api/whatsapp/setup', methods=['POST'])
def whatsapp_setup():
    """Setup WhatsApp Web automation with QR code"""
    global whatsapp_active, current_whatsapp_bot, whatsapp_qr_ready
    
    try:
        if whatsapp_active and current_whatsapp_bot:
            return jsonify({
                'success': False,
                'message': 'WhatsApp setup already running'
            }), 400
        
        # Start WhatsApp setup in background thread
        def run_whatsapp_setup():
            global whatsapp_active, current_whatsapp_bot, whatsapp_qr_ready
            
            try:
                whatsapp_active = True
                current_whatsapp_bot = get_whatsapp_bot()
                
                socketio.emit('whatsapp_log', {
                    'level': 'INFO',
                    'message': 'Starting WhatsApp Web setup...'
                })
                
                # Setup browser
                if current_whatsapp_bot.setup_browser():
                    result = current_whatsapp_bot.start_whatsapp_web()
                    
                    if result['status'] == 'qr_ready':
                        whatsapp_qr_ready = True
                        socketio.emit('whatsapp_log', {
                            'level': 'INFO',
                            'message': 'QR-Code bereit! Screenshot verfügbar.'
                        })
                        socketio.emit('whatsapp_qr_ready', {
                            'message': 'QR-Code Screenshot bereit',
                            'qr_url': '/api/whatsapp/qr-image'
                        })
                        
                        # Wait for login
                        wait_time = 0
                        while wait_time < 120:  # 2 minutes timeout
                            time.sleep(3)
                            wait_time += 3
                            
                            status = current_whatsapp_bot.check_login_status()
                            if status['status'] == 'logged_in':
                                socketio.emit('whatsapp_ready', {
                                    'message': 'WhatsApp Web ready for campaigns!'
                                })
                                break
                        
                        if wait_time >= 120:
                            socketio.emit('whatsapp_log', {
                                'level': 'ERROR',
                                'message': 'Login timeout - QR code not scanned within 2 minutes'
                            })
                            
                    elif result['status'] == 'logged_in':
                        socketio.emit('whatsapp_ready', {
                            'message': 'WhatsApp Web already logged in and ready!'
                        })
                    else:
                        socketio.emit('whatsapp_log', {
                            'level': 'ERROR',
                            'message': f'WhatsApp setup failed: {result["message"]}'
                        })
                        whatsapp_active = False
                        current_whatsapp_bot = None
                else:
                    socketio.emit('whatsapp_log', {
                        'level': 'ERROR',
                        'message': 'Failed to setup Firefox browser'
                    })
                    whatsapp_active = False
                    current_whatsapp_bot = None
                    
            except Exception as e:
                socketio.emit('whatsapp_log', {
                    'level': 'ERROR',
                    'message': f'WhatsApp setup error: {str(e)}'
                })
                whatsapp_active = False
                current_whatsapp_bot = None
        
        threading.Thread(target=run_whatsapp_setup, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp setup started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'WhatsApp setup failed: {str(e)}'
        }), 500

@app.route('/api/whatsapp/qr-image', methods=['GET'])
def get_qr_image():
    """Get QR code screenshot in original resolution"""
    global current_whatsapp_bot
    
    try:
        screenshot_path = os.path.join(os.getcwd(), 'whatsapp_qr_code.png')
        
        if os.path.exists(screenshot_path):
            # Return image with no cache headers for fresh QR codes
            response = send_file(screenshot_path, mimetype='image/png', as_attachment=False)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return jsonify({
                'success': False,
                'message': 'QR code screenshot not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get QR image: {str(e)}'
        }), 500

@app.route('/api/whatsapp/templates', methods=['GET'])
def get_whatsapp_templates():
    """Get available WhatsApp message templates"""
    return jsonify({
        'success': True,
        'templates': SIMPLE_MESSAGES
    })

@app.route('/api/whatsapp/status', methods=['GET'])
def whatsapp_status():
    """Get WhatsApp status"""
    global whatsapp_active, current_whatsapp_bot
    
    if not whatsapp_active or not current_whatsapp_bot:
        return jsonify({
            'success': True,
            'status': 'inactive',
            'logged_in': False
        })
    
    try:
        status = current_whatsapp_bot.check_login_status()
        return jsonify({
            'success': True,
            'status': 'active',
            'logged_in': status['status'] == 'logged_in',
            'message': status['message']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/whatsapp/start-campaign', methods=['POST'])
def start_whatsapp_campaign():
    """Start WhatsApp outreach campaign using multi-account system"""
    from whatsapp_simple import SIMPLE_MESSAGES

    try:
        # Get all active logged-in accounts
        active_accounts = wa_manager.get_active_accounts()
        logged_in_accounts = [acc for acc in active_accounts if acc.get('is_logged_in')]

        if not logged_in_accounts:
            return jsonify({
                'success': False,
                'message': 'No WhatsApp accounts are logged in. Please setup and login to a WhatsApp account first.'
            }), 400

        # Use first available logged-in account
        account = logged_in_accounts[0]
        account_id = account['id']

        # Get bot instance for this account
        bot = wa_manager.get_bot(account_id)

        # Validate that bot exists AND is actually logged in (both DB and runtime status)
        if not bot:
            return jsonify({
                'success': False,
                'message': f'WhatsApp bot for account "{account["account_name"]}" is not running. Please click Setup first.'
            }), 400

        if not bot.is_logged_in or not bot.driver:
            return jsonify({
                'success': False,
                'message': f'WhatsApp for account "{account["account_name"]}" is not logged in. Please scan the QR code first.'
            }), 400

        # Live session validation - check if WhatsApp Web session is still active
        try:
            live_status = bot.check_login_status()
            if live_status['status'] != 'logged_in':
                # Session expired - update DB and runtime status
                wa_manager.update_account_status(account_id, False)
                bot.is_logged_in = False

                return jsonify({
                    'success': False,
                    'message': f'WhatsApp session expired for account "{account["account_name"]}". Please scan QR code again.'
                }), 400
        except Exception as e:
            print(f"[ERROR] Live session check failed: {e}")
            # Continue anyway if check fails - let the actual send_message call handle it

        data = request.get_json() or {}
        message_template = data.get('message_template', SIMPLE_MESSAGES['simple'])
        daily_limit = int(data.get('daily_limit', 10))

        # Get uncontacted listings with phone numbers
        with app.app_context():
            listings = ScrapedListing.query.filter_by(whatsapp_contacted=False).limit(daily_limit).all()
            # Filter only listings that have phone numbers
            listings = [l for l in listings if l.phone_numbers and len(l.phone_numbers) > 0]

            if not listings:
                return jsonify({
                    'success': False,
                    'message': 'No uncontacted listings found'
                })

        def run_campaign():
            with app.app_context():
                sent_count = 0
                failed_count = 0

                socketio.emit('whatsapp_log', {
                    'level': 'INFO',
                    'message': f'Starting campaign with account: {account["account_name"]} ({sent_count}/{len(listings)} listings)'
                })

                for listing in listings:
                    try:
                        # Check if account can still send messages (daily limit)
                        can_send, reason = wa_manager.can_send_message(account_id)
                        if not can_send:
                            socketio.emit('whatsapp_log', {
                                'level': 'WARNING',
                                'message': f'Campaign stopped: {reason}'
                            })
                            break

                        # Send to first phone number in the listing
                        phone = listing.phone_numbers[0] if listing.phone_numbers else None
                        if not phone:
                            continue

                        result = bot.send_message(phone, message_template)

                        if result['status'] == 'success':
                            listing.whatsapp_contacted = True
                            listing.whatsapp_contacted_at = datetime.utcnow()
                            listing.whatsapp_status = 'sent'
                            listing.whatsapp_account_id = account_id
                            db.session.commit()

                            # Increment message counter for this account
                            wa_manager.increment_message_counter(account_id, success=True)

                            sent_count += 1
                            socketio.emit('whatsapp_log', {
                                'level': 'SUCCESS',
                                'message': f'Message sent to {phone} - {listing.title} ({sent_count}/{len(listings)})'
                            })
                        else:
                            listing.whatsapp_status = 'failed'
                            db.session.commit()

                            wa_manager.increment_message_counter(account_id, success=False)
                            failed_count += 1

                            socketio.emit('whatsapp_log', {
                                'level': 'ERROR',
                                'message': f'Failed to send to {phone}: {result["message"]}'
                            })

                        # Delay between messages (60-180 seconds)
                        import random
                        delay = random.randint(60, 180)
                        socketio.emit('whatsapp_log', {
                            'level': 'INFO',
                            'message': f'Waiting {delay} seconds before next message...'
                        })
                        time.sleep(delay)

                    except Exception as e:
                        failed_count += 1
                        socketio.emit('whatsapp_log', {
                            'level': 'ERROR',
                            'message': f'Error sending to listing {listing.id}: {str(e)}'
                        })

                socketio.emit('whatsapp_campaign_completed', {
                    'message': f'Campaign completed! {sent_count} sent, {failed_count} failed.'
                })
                socketio.emit('whatsapp_log', {
                    'level': 'SUCCESS',
                    'message': f'Campaign completed! {sent_count} messages sent, {failed_count} failed.'
                })

        threading.Thread(target=run_campaign, daemon=True).start()

        socketio.emit('whatsapp_campaign_started', {
            'message': f'Campaign started for {len(listings)} listings using {account["account_name"]}'
        })

        return jsonify({
            'success': True,
            'message': f'Campaign started for {len(listings)} listings using account {account["account_name"]}'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/whatsapp/stop', methods=['POST'])
def stop_whatsapp():
    """Stop WhatsApp automation"""
    global whatsapp_active, current_whatsapp_bot, whatsapp_qr_ready
    
    try:
        if current_whatsapp_bot:
            current_whatsapp_bot.close()
        
        whatsapp_active = False
        current_whatsapp_bot = None
        whatsapp_qr_ready = False
        
        socketio.emit('whatsapp_stopped', {
            'message': 'WhatsApp automation stopped'
        })
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp stopped successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/whatsapp/uncontacted', methods=['GET'])
def get_uncontacted_customers():
    """Get list of uncontacted listings with phone numbers"""
    try:
        listings = ScrapedListing.query.filter_by(whatsapp_contacted=False).all()
        # Filter only listings with phone numbers
        listings = [l for l in listings if l.phone_numbers and len(l.phone_numbers) > 0]

        return jsonify({
            'success': True,
            'count': len(listings),
            'customers': [{
                'id': l.id,
                'phone_number': l.phone_numbers[0] if l.phone_numbers else None,
                'source_title': l.title,
                'source_url': l.url,
                'created_at': l.created_at.isoformat()
            } for l in listings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# WhatsApp Account Management API Endpoints
# ============================================

@app.route('/api/whatsapp/accounts', methods=['GET'])
def get_whatsapp_accounts():
    """Get all WhatsApp accounts"""
    try:
        accounts = wa_manager.get_all_accounts()
        return jsonify({
            'success': True,
            'accounts': accounts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/whatsapp/accounts', methods=['POST'])
def create_whatsapp_account():
    """Create new WhatsApp account"""
    try:
        data = request.get_json()
        account_name = data.get('account_name')
        daily_limit = data.get('daily_limit', 100)

        if not account_name:
            return jsonify({
                'success': False,
                'message': 'account_name is required'
            }), 400

        account = wa_manager.create_account(account_name, daily_limit)
        if account:
            socketio.emit('whatsapp_log', {
                'level': 'SUCCESS',
                'message': f'WhatsApp Account erstellt: {account_name}'
            })
            return jsonify({
                'success': True,
                'account': account
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Account already exists or creation failed'
            }), 400

    except Exception as e:
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'Fehler beim Account-Erstellen: {str(e)}'
        })
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/whatsapp/accounts/<int:account_id>', methods=['DELETE'])
def delete_whatsapp_account(account_id):
    """Delete WhatsApp account"""
    try:
        success = wa_manager.delete_account(account_id)
        if success:
            socketio.emit('whatsapp_log', {
                'level': 'SUCCESS',
                'message': f'WhatsApp Account gelöscht: {account_id}'
            })
            return jsonify({
                'success': True,
                'message': 'Account deleted'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Account not found'
            }), 404

    except Exception as e:
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'Fehler beim Account-Löschen: {str(e)}'
        })
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/whatsapp/accounts/<int:account_id>/setup', methods=['POST'])
def setup_whatsapp_account(account_id):
    """Setup WhatsApp for specific account (show QR code)"""
    global whatsapp_active, whatsapp_qr_ready

    try:
        # Get or create bot for this account
        bot = wa_manager.get_or_create_bot(account_id)
        if not bot:
            return jsonify({
                'success': False,
                'message': 'Account not found or inactive'
            }), 404

        print(f"\n{'='*60}")
        print(f"[SETUP] WhatsApp Setup gestartet für Account {account_id}")
        print(f"[SETUP] Bot instance: {bot}")
        print(f"{'='*60}\n")
        import sys
        sys.stdout.flush()

        socketio.emit('whatsapp_log', {
            'level': 'INFO',
            'message': f'WhatsApp Setup gestartet für Account {account_id}...'
        })

        def setup_thread():
            global whatsapp_qr_ready
            import sys
            try:
                print(f"[DEBUG] Setup thread started for account {account_id}")
                sys.stdout.flush()
                socketio.emit('whatsapp_log', {
                    'level': 'INFO',
                    'message': f'🔧 Browser wird gestartet für Account {account_id}...'
                })

                # Setup browser
                if not bot.setup_browser():
                    raise Exception("Browser setup failed")

                print(f"[DEBUG] Browser setup complete")
                socketio.emit('whatsapp_status', {
                    'status': 'browser_ready',
                    'account_id': account_id
                })

                # Start WhatsApp Web and get QR code
                print(f"[DEBUG] Starting WhatsApp Web...")
                result = bot.start_whatsapp_web()
                print(f"[DEBUG] WhatsApp Web result: {result}")

                if result['status'] == 'qr_ready':
                    handle_qr_ready(account_id)
                elif result['status'] == 'logged_in':
                    handle_logged_in(account_id, bot)
                    return

                # Poll for login status
                print(f"[DEBUG] Polling for login status...")
                max_wait = 120  # 2 minutes
                poll_interval = 3  # seconds
                elapsed = 0

                while elapsed < max_wait:
                    time.sleep(poll_interval)
                    elapsed += poll_interval

                    status = bot.check_login_status()
                    print(f"[DEBUG] Login status: {status}")

                    if status['status'] == 'logged_in':
                        handle_logged_in(account_id, bot)
                        break
                    elif status['status'] == 'error':
                        raise Exception(status['message'])

            except Exception as e:
                print(f"[ERROR] Setup thread exception: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                socketio.emit('whatsapp_log', {
                    'level': 'ERROR',
                    'message': f'Setup Fehler: {str(e)}'
                })
                socketio.emit('whatsapp_status', {
                    'status': 'error',
                    'message': str(e),
                    'account_id': account_id
                })

        def handle_qr_ready(acc_id):
            global whatsapp_qr_ready
            whatsapp_qr_ready = True
            socketio.emit('whatsapp_log', {
                'level': 'SUCCESS',
                'message': f'QR-Code bereit für Account {acc_id}!'
            })
            qr_url = f'/api/whatsapp/accounts/{acc_id}/qr-image'
            socketio.emit('whatsapp_qr_ready', {
                'account_id': acc_id,
                'qr_url': qr_url
            })

        def handle_logged_in(acc_id, bot_instance):
            socketio.emit('whatsapp_log', {
                'level': 'SUCCESS',
                'message': f'WhatsApp erfolgreich verbunden für Account {acc_id}!'
            })
            # Use app context for database operations in thread
            with app.app_context():
                wa_manager.update_account_status(acc_id, True)
            socketio.emit('whatsapp_status', {
                'status': 'ready',
                'account_id': acc_id
            })

        thread = threading.Thread(target=setup_thread)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Setup started',
            'account_id': account_id
        })

    except Exception as e:
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'Setup Fehler: {str(e)}'
        })
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/whatsapp/accounts/<int:account_id>/qr-image', methods=['GET'])
def get_account_qr_image(account_id):
    """Get QR code image for specific account"""
    try:
        bot = wa_manager.get_bot(account_id)
        if not bot:
            return jsonify({
                'success': False,
                'message': 'Bot not found for this account'
            }), 404

        qr_file = bot.qr_screenshot_file
        if os.path.exists(qr_file):
            return send_file(qr_file, mimetype='image/png')
        else:
            return jsonify({
                'success': False,
                'message': 'QR code not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/whatsapp/accounts/<int:account_id>/status', methods=['GET'])
def get_account_status(account_id):
    """Get status for specific WhatsApp account"""
    try:
        account = db.session.get(WhatsAppAccount, account_id)
        if not account:
            return jsonify({
                'success': False,
                'message': 'Account not found'
            }), 404

        bot = wa_manager.get_bot(account_id)
        is_bot_active = bot is not None

        return jsonify({
            'success': True,
            'account': account.to_dict(),
            'bot_active': is_bot_active
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ===== SCRAPING AND CUSTOMER ENDPOINTS =====

@app.route('/api/scrape', methods=['POST'])
@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    """Start scraping process"""
    global scraping_active, current_scraper
    
    if scraping_active:
        return jsonify({
            'success': False,
            'message': 'Scraping is already running'
        }), 400
    
    def run_scraping():
        global scraping_active, current_scraper, scraping_results

        try:
            scraping_active = True
            web_logger.log('INFO', 'Initializing scraper...')

            try:
                current_scraper = SeleniumBrowserScraper(web_logger)
            except Exception as init_error:
                import traceback
                error_trace = traceback.format_exc()
                web_logger.log('ERROR', f'Failed to initialize scraper: {str(init_error)}')
                web_logger.log('ERROR', f'Traceback: {error_trace}')
                raise

            web_logger.log('INFO', 'Starting Firefox browser scraper...')

            try:
                results = current_scraper.scrape_revolico()
            except Exception as scrape_error:
                import traceback
                error_trace = traceback.format_exc()
                web_logger.log('ERROR', f'Scraping execution failed: {str(scrape_error)}')
                web_logger.log('ERROR', f'Traceback: {error_trace}')
                raise

            if results and 'results' in results:
                # Save to database
                with app.app_context():
                    saved_listings = 0

                    for result in results['results']:
                        # Save to ScrapedListing table
                        if result.get('revolico_id'):
                            # Check if listing already exists
                            existing_listing = ScrapedListing.query.filter_by(
                                revolico_id=result['revolico_id']
                            ).first()

                            if not existing_listing:
                                # Process images through proxy service
                                image_ids = ImageProxyService.process_image_urls(
                                    result.get('images', [])
                                )

                                # Process profile picture through proxy service
                                profile_picture_id = None
                                if result.get('profile_picture_url'):
                                    profile_url = result['profile_picture_url']

                                    # Revolico profile pictures: Use direct URL (no proxy/caching)
                                    # They are time-limited tokens that expire quickly, so caching doesn't help
                                    if 'pic.revolico.com/users' in profile_url:
                                        profile_picture_id = profile_url  # Direct URL as ID
                                        web_logger.log('INFO', f"📸 Revolico profile pic (direct): {profile_url[:80]}...")
                                    else:
                                        # Google profile pictures: Use proxy (they don't expire)
                                        profile_picture_id = ImageProxyService.get_or_create_proxy(profile_url)
                                        web_logger.log('INFO', f"📸 Saved profile picture: {profile_picture_id}")

                                # Create new listing
                                listing = ScrapedListing(
                                    revolico_id=result['revolico_id'],
                                    title=result.get('title', ''),
                                    description=result.get('description', ''),
                                    url=result.get('url', ''),
                                    price=result.get('price'),
                                    currency=result.get('currency', 'USD'),
                                    phone_numbers=result.get('phone_numbers', []),
                                    seller_name=result.get('seller_name'),
                                    profile_picture_id=profile_picture_id,
                                    image_ids=image_ids,
                                    category=result.get('category', ''),
                                    location=result.get('location', ''),
                                    condition=result.get('condition', 'used'),
                                    exported=False,
                                    whatsapp_contacted=False
                                )
                                db.session.add(listing)
                                saved_listings += 1

                    db.session.commit()
                    web_logger.log('SUCCESS', f'Saved {saved_listings} new listings to database')

            scraping_results = results
            web_logger.log('SUCCESS', 'Scraping completed successfully')

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            web_logger.log('ERROR', f'Scraping failed: {str(e)}')
            web_logger.log('ERROR', f'Full traceback: {error_trace}')
            scraping_results = {
                'error': str(e),
                'traceback': error_trace
            }
        finally:
            scraping_active = False
            if current_scraper:
                try:
                    current_scraper.close()
                except Exception as close_error:
                    web_logger.log('WARNING', f'Error closing scraper: {str(close_error)}')
                current_scraper = None
    
    threading.Thread(target=run_scraping, daemon=True).start()

    return jsonify({
        'success': True,
        'message': 'Scraping started'
    })

@app.route('/api/stop-scraping', methods=['POST'])
def stop_scraping():
    """Stop the scraping process"""
    global scraping_active, current_scraper

    try:
        scraping_active = False
        if current_scraper:
            # Try to stop the scraper if it has a stop method
            if hasattr(current_scraper, 'stop'):
                current_scraper.stop()
                web_logger.log('WARNING', 'Scraping gestoppt durch Benutzer')
            current_scraper = None

        return jsonify({
            'success': True,
            'message': 'Scraping stopped'
        })
    except Exception as e:
        web_logger.log('ERROR', f'Fehler beim Stoppen: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Fehler beim Stoppen: {str(e)}'
        }), 500

@app.route('/api/customers', methods=['GET'])
@app.route('/api/listings', methods=['GET'])
def get_customers():
    """Get all listings (with phone numbers for WhatsApp)"""
    try:
        listings = ScrapedListing.query.order_by(ScrapedListing.created_at.desc()).all()

        # Convert to frontend-compatible format
        customers_data = []
        for l in listings:
            # Get first phone number or None
            phone = l.phone_numbers[0] if l.phone_numbers and len(l.phone_numbers) > 0 else None

            customer_dict = {
                # Include full listing data first (includes profile_picture_id, seller_name, etc.)
                **l.to_dict(),
                # Override specific fields for frontend compatibility
                'phone_number': phone,  # Frontend expects singular phone_number
                'contacted': l.whatsapp_contacted,  # Frontend expects 'contacted'
                'contacted_at': l.whatsapp_contacted_at.isoformat() if l.whatsapp_contacted_at else None,
                'notes': l.whatsapp_notes,
                'source_title': l.title,  # Frontend expects source_title
                'source_url': l.url,  # Frontend expects source_url
            }
            customers_data.append(customer_dict)

        return jsonify({
            'success': True,
            'total_count': len(listings),
            'contacted_count': len([l for l in listings if l.whatsapp_contacted]),
            'pending_count': len([l for l in listings if not l.whatsapp_contacted]),
            'customers': customers_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/customers/<int:customer_id>/contact', methods=['POST'])
@app.route('/api/listings/<int:customer_id>/contact', methods=['POST'])
def mark_customer_contacted(customer_id):
    """Mark listing as contacted via WhatsApp"""
    try:
        listing = ScrapedListing.query.get_or_404(customer_id)
        data = request.get_json()

        listing.whatsapp_contacted = True
        listing.whatsapp_contacted_at = datetime.utcnow()
        listing.whatsapp_notes = data.get('notes', '')
        listing.whatsapp_status = data.get('status', 'sent')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Listing {listing.title} marked as contacted'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/customers/clear', methods=['POST'])
@app.route('/api/listings/clear', methods=['POST'])
def clear_customers():
    """Clear all listings and related data from database"""
    try:
        # Delete scraped listings
        listings_count = ScrapedListing.query.delete()

        # Delete image proxy mappings
        images_count = ImageProxy.query.delete()

        # Delete old customers table if exists
        try:
            customers_count = Customer.query.delete()
        except:
            customers_count = 0

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Deleted {listings_count} listings, {images_count} images, {customers_count} old customers from database'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/results')
def get_results():
    """Get scraping results"""
    global scraping_results
    return jsonify(scraping_results)

@app.route('/download/results')
def download_results():
    """Download results as JSON"""
    results_file = 'revolico_data.json'
    if os.path.exists(results_file):
        return send_file(results_file, as_attachment=True)
    else:
        return jsonify({'error': 'No results file found'}), 404

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

# ============================================================================
# RICO-CUBA INTEGRATION API ENDPOINTS
# ============================================================================

@app.route('/api/scraped-listings', methods=['GET'])
def get_scraped_listings():
    """
    API Endpoint für Rico-Cuba zum Abrufen aller gescrapten Listings
    Query params:
      - exported=false: nur nicht-exportierte
      - limit=50: max Anzahl
    """
    try:
        # Get query parameters
        only_unexported = request.args.get('exported') == 'false'
        limit = int(request.args.get('limit', 100))

        # Build query
        query = ScrapedListing.query

        if only_unexported:
            query = query.filter_by(exported=False)

        # Get listings
        listings = query.order_by(ScrapedListing.created_at.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'count': len(listings),
            'listings': [listing.to_dict() for listing in listings]
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scraped-listings/<int:listing_id>/mark-exported', methods=['POST'])
def mark_listing_exported(listing_id):
    """Markiert ein Listing als exportiert"""
    try:
        listing = ScrapedListing.query.get(listing_id)
        if not listing:
            return jsonify({'success': False, 'error': 'Listing not found'}), 404

        listing.exported = True
        listing.exported_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/image-proxy/<image_hash>', methods=['GET'])
def image_proxy(image_hash):
    """
    Image Proxy Endpoint - gibt Bild zurück ohne URL zu exposen
    Rico-Cuba ruft Bilder über diesen Endpoint ab
    """
    try:
        # Check if image is cached locally first
        from models import ImageProxy
        proxy = ImageProxy.query.filter_by(image_hash=image_hash).first()

        if not proxy:
            return jsonify({'error': 'Image not found'}), 404

        # If cached, serve from local file
        if proxy.cached and proxy.cache_path and os.path.exists(proxy.cache_path):
            # Determine MIME type from file extension
            import mimetypes
            mimetype, _ = mimetypes.guess_type(proxy.cache_path)
            if not mimetype:
                mimetype = 'image/jpeg'
            return send_file(proxy.cache_path, mimetype=mimetype, as_attachment=False)

        original_url = proxy.original_url

        # Prepare browser-like headers to bypass hotlinking protection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }

        # Add domain-specific referer for hotlinking protection
        if 'lh3.googleusercontent.com' in original_url:
            headers['Referer'] = 'https://www.google.com/'
        elif 'revolico.com' in original_url:
            headers['Referer'] = 'https://www.revolico.com/'

        # Fetch image from Revolico/Google with headers
        response = requests.get(original_url, headers=headers, timeout=10)

        if response.status_code != 200:
            # Return 1x1 transparent PNG as fallback (instead of 500 error)
            # This prevents broken image icons in the UI
            import base64
            transparent_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
            return transparent_png, 200, {
                'Content-Type': 'image/png',
                'Cache-Control': 'public, max-age=3600'  # Cache for 1h (shorter since it's fallback)
            }

        # Return image with proper content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')

        return response.content, 200, {
            'Content-Type': content_type,
            'Cache-Control': 'public, max-age=86400'  # Cache for 24h
        }

    except Exception as e:
        # Return 1x1 transparent PNG as fallback on error
        import base64
        transparent_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
        return transparent_png, 200, {
            'Content-Type': 'image/png',
            'Cache-Control': 'public, max-age=3600'
        }

if __name__ == '__main__':
    print("\n✅ Datenbank-Tabellen erstellt/aktualisiert")
    print("=" * 60)
    print("REVOLICO SCRAPER + WHATSAPP AUTOMATION")
    print("Mit QR-Code Screenshot und Session Persistierung")
    print("=" * 60)
    print("Starting web server on http://0.0.0.0:5000")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)