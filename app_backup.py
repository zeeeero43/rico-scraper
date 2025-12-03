#!/usr/bin/env python3
"""
Flask Web UI for Revolico Phone Number Scraper - Firefox Selenium Only
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
from models import db, Customer, init_database
from whatsapp_simple import get_whatsapp_bot, SIMPLE_MESSAGES

app = Flask(__name__)
app.config['SECRET_KEY'] = 'revolico_scraper_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Datenbank initialisieren
init_database(app)

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

def save_results_to_database(results: Dict[str, Any]):
    """Save scraping results to the database"""
    try:
        if not results.get('success') or not results.get('listings'):
            return
        
        # Use Flask application context for database operations
        with app.app_context():
            saved_count = 0
            updated_count = 0
            
            for listing in results['listings']:
                for phone in listing.get('phones', []):
                    
                    # Check if customer already exists by phone number (avoid duplicates)
                    existing_customer = Customer.query.filter_by(phone_number=phone).first()
                    
                    if existing_customer:
                        # Update existing customer with latest source info if different
                        if existing_customer.source_url != listing['url']:
                            existing_customer.source_url = listing['url']
                            existing_customer.source_title = listing['title']
                            updated_count += 1
                        # Skip if phone number already exists - no duplicate
                    else:
                        # Create new customer only if phone doesn't exist
                        new_customer = Customer()
                        new_customer.phone_number = phone
                        new_customer.contacted = False
                        new_customer.source_url = listing['url']
                        new_customer.source_title = listing['title']
                        db.session.add(new_customer)
                        saved_count += 1
            
            # Commit all changes
            db.session.commit()
            print(f"✅ Datenbank aktualisiert: {saved_count} neue Kunden, {updated_count} aktualisiert")
        
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        print(f"❌ Fehler beim Speichern in Datenbank: {e}")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current scraping status"""
    return jsonify({
        'scraping_active': scraping_active,
        'has_results': os.path.exists('revolico_data.json'),
        'results_size': get_file_size('revolico_data.json') if os.path.exists('revolico_data.json') else 0
    })

@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    """Start the scraping process"""
    global scraping_active, current_scraper
    
    if scraping_active:
        return jsonify({'error': 'Scraping already in progress'}), 400
    
    try:
        # Get configuration from request
        config = request.get_json() or {}
        max_listings = config.get('max_listings', 3)
        
        # Start scraping in background thread - always use Firefox Selenium
        thread = threading.Thread(target=run_scraping_thread, args=(max_listings,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'Scraping started successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to start scraping: {str(e)}'}), 500

@app.route('/api/stop-scraping', methods=['POST'])
def stop_scraping():
    """Stop the scraping process"""
    global scraping_active, current_scraper
    
    scraping_active = False
    if current_scraper:
        # Try to stop the scraper if it has a stop method
        if hasattr(current_scraper, 'stop'):
            current_scraper.stop()
        current_scraper = None
        
    # Emit stop signal to UI
    socketio.emit('scraping_stopped', {
        'message': 'Scraping wurde gestoppt',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    socketio.emit('log_message', {
        'level': 'WARNING',
        'message': 'Scraping gestoppt durch Benutzer',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    return jsonify({'message': 'Scraping gestoppt'})

@app.route('/api/results')
def get_results():
    """Get detailed scraping results"""
    if os.path.exists('revolico_data.json'):
        results = load_from_json('revolico_data.json')
        return jsonify(results)
    else:
        return jsonify({'error': 'No results available'}), 404

@app.route('/api/download-results')
def download_results():
    """Download results as JSON file"""
    if os.path.exists('revolico_data.json'):
        return send_file('revolico_data.json', as_attachment=True, 
                        download_name=f'revolico_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    else:
        return jsonify({'error': 'No results file found'}), 404

@app.route('/api/customers')
def api_customers():
    """API endpoint to get all customers from database"""
    try:
        customers = Customer.query.order_by(Customer.created_at.desc()).all()
        return jsonify({
            'success': True,
            'customers': [customer.to_dict() for customer in customers],
            'total_count': len(customers),
            'contacted_count': sum(1 for c in customers if c.contacted),
            'pending_count': sum(1 for c in customers if not c.contacted)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/customers/<int:customer_id>/contact', methods=['POST'])
def mark_customer_contacted(customer_id):
    """Mark a customer as contacted"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.get_json()
        
        customer.contacted = True
        customer.contacted_at = datetime.utcnow()
        customer.notes = data.get('notes', customer.notes)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Kunde {customer.name} als kontaktiert markiert',
            'customer': customer.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/customers/clear', methods=['POST'])
def clear_customers():
    """Clear all customers from database"""
    try:
        deleted_count = Customer.query.count()
        Customer.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} Kunden aus der Datenbank gelöscht',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# WHATSAPP AUTOMATION API ENDPOINTS
# =====================================================

@app.route('/api/whatsapp/status')
def whatsapp_status():
    """Get WhatsApp automation status"""
    global whatsapp_active, current_whatsapp_bot
    
    # Get campaign stats if bot is available
    stats = {}
    if current_whatsapp_bot:
        stats = current_whatsapp_bot.get_campaign_stats()
    
    return jsonify({
        'active': whatsapp_active,
        'logged_in': current_whatsapp_bot.is_logged_in if current_whatsapp_bot else False,
        'stats': stats
    })

@app.route('/api/whatsapp/start-campaign', methods=['POST'])
def start_whatsapp_campaign():
    """Start WhatsApp outreach campaign"""
    global whatsapp_active, current_whatsapp_bot
    
    if whatsapp_active:
        return jsonify({'error': 'WhatsApp campaign already running'}), 400
    
    try:
        data = request.get_json()
        message_template = data.get('message_template', DEFAULT_MESSAGES['rico_cuba_promotion'])
        
        # Start campaign in background thread
        thread = threading.Thread(
            target=run_whatsapp_campaign_thread,
            args=(message_template,)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'WhatsApp campaign started successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to start WhatsApp campaign: {str(e)}'}), 500

@app.route('/api/whatsapp/setup', methods=['POST'])
def setup_whatsapp():
    """Setup WhatsApp Web browser for QR code login"""
    global current_whatsapp_bot, whatsapp_active
    
    if whatsapp_active:
        return jsonify({'error': 'WhatsApp setup already in progress'}), 400
    
    try:
        # Start setup in background thread
        thread = threading.Thread(target=setup_whatsapp_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'WhatsApp setup started - please scan QR code'})
        
    except Exception as e:
        return jsonify({'error': f'Failed to setup WhatsApp: {str(e)}'}), 500

@app.route('/api/whatsapp/stop', methods=['POST'])
def stop_whatsapp():
    """Stop WhatsApp automation"""
    global whatsapp_active, current_whatsapp_bot
    
    whatsapp_active = False
    if current_whatsapp_bot:
        current_whatsapp_bot.cleanup()
        current_whatsapp_bot = None
    
    socketio.emit('whatsapp_stopped', {
        'message': 'WhatsApp automation stopped',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    return jsonify({'message': 'WhatsApp automation stopped'})

@app.route('/api/whatsapp/templates')
def get_message_templates():
    """Get available message templates"""
    return jsonify({
        'templates': DEFAULT_MESSAGES,
        'success': True
    })

@app.route('/api/whatsapp/uncontacted')
def get_uncontacted_numbers():
    """Get numbers that haven't been contacted via WhatsApp"""
    try:
        if current_whatsapp_bot:
            uncontacted = current_whatsapp_bot.get_uncontacted_numbers()
            return jsonify({
                'success': True,
                'uncontacted_numbers': uncontacted,
                'count': len(uncontacted)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'WhatsApp bot not initialized'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# WHATSAPP BACKGROUND THREADS
# =====================================================

def setup_whatsapp_thread():
    """Setup WhatsApp Web in background thread"""
    global current_whatsapp_bot, whatsapp_active
    
    try:
        whatsapp_active = True
        socketio.emit('whatsapp_log', {
            'level': 'INFO',
            'message': '🚀 Starting WhatsApp Web setup...',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        current_whatsapp_bot = WhatsAppBot()
        
        # Setup Chrome browser (visible for QR code)
        if current_whatsapp_bot.setup_driver():
            socketio.emit('whatsapp_log', {
                'level': 'INFO',
                'message': '🖥️ Browser started - please scan QR code',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            # Login to WhatsApp Web
            if current_whatsapp_bot.login_whatsapp():
                socketio.emit('whatsapp_log', {
                    'level': 'SUCCESS',
                    'message': '✅ Successfully logged in to WhatsApp Web!',
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                
                socketio.emit('whatsapp_ready', {
                    'message': 'WhatsApp Web ready for campaigns',
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
            else:
                socketio.emit('whatsapp_log', {
                    'level': 'ERROR',
                    'message': '❌ WhatsApp login failed - QR code not scanned',
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
        else:
            socketio.emit('whatsapp_log', {
                'level': 'ERROR',
                'message': '❌ Failed to setup browser',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
    
    except Exception as e:
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'❌ WhatsApp setup error: {str(e)}',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    finally:
        whatsapp_active = False

def run_whatsapp_campaign_thread(message_template: str):
    """Run WhatsApp outreach campaign in background thread"""
    global whatsapp_active, current_whatsapp_bot, whatsapp_results
    
    try:
        whatsapp_active = True
        
        if not current_whatsapp_bot:
            socketio.emit('whatsapp_log', {
                'level': 'ERROR',
                'message': '❌ WhatsApp bot not initialized - please setup first',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            return
        
        if not current_whatsapp_bot.is_logged_in:
            socketio.emit('whatsapp_log', {
                'level': 'ERROR',
                'message': '❌ Not logged in to WhatsApp - please login first',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            return
        
        # Start the campaign
        socketio.emit('whatsapp_campaign_started', {
            'message': 'Starting WhatsApp outreach campaign...',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        # Run campaign with socketio for real-time updates
        results = current_whatsapp_bot.start_outreach_campaign(message_template, socketio)
        whatsapp_results = results
        
        # Update database with WhatsApp contact status
        if results['success']:
            update_whatsapp_database_status(results.get('results', []))
        
        # Emit completion
        socketio.emit('whatsapp_campaign_completed', {
            'message': f'Campaign completed: {results["successful_sends"]}/{results["total_processed"]} messages sent',
            'results': results,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        error_message = f"Critical error during WhatsApp campaign: {e}"
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'❌ {error_message}',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        whatsapp_results = {
            'success': False,
            'error': error_message,
            'total_processed': 0,
            'successful_sends': 0
        }
        
        socketio.emit('whatsapp_campaign_completed', {
            'message': 'WhatsApp campaign failed',
            'results': whatsapp_results,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    finally:
        whatsapp_active = False

def update_whatsapp_database_status(results: list):
    """Update database with WhatsApp contact status"""
    try:
        for result in results:
            customer = Customer.query.filter_by(phone_number=result['phone']).first()
            if customer:
                customer.whatsapp_contacted = result['status'] == 'sent'
                customer.whatsapp_message_sent = result.get('message', '')
                customer.whatsapp_sent_at = datetime.fromisoformat(result['timestamp']) if result.get('timestamp') else None
                customer.whatsapp_status = result['status']
                
                # Also update general contacted status if WhatsApp was successful
                if result['status'] == 'sent' and not customer.contacted:
                    customer.contacted = True
                    customer.contacted_at = datetime.utcnow()
        
        db.session.commit()
        
        socketio.emit('whatsapp_log', {
            'level': 'INFO',
            'message': f'✅ Database updated with WhatsApp contact status',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        db.session.rollback()
        socketio.emit('whatsapp_log', {
            'level': 'ERROR',
            'message': f'❌ Failed to update database: {str(e)}',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

def run_scraping_thread(max_listings: int):
    """Run Firefox Selenium scraping in background thread with real-time updates"""
    global scraping_active, current_scraper, scraping_results
    
    try:
        scraping_active = True
        
        # Emit start message
        socketio.emit('scraping_started', {
            'message': 'Starting Revolico scraping with Firefox...',
            'config': {
                'max_listings': max_listings,
                'method': 'CloudScraper (Profile Area Focus)'
            }
        })
        
        # Create CloudScraper (most reliable method)
        socketio.emit('log_message', {
            'level': 'INFO',
            'message': 'Using CloudScraper (Recommended Method)',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        from cloudscraper_revolico import CloudScraperRevolico
        current_scraper = CloudScraperRevolico()
        
        # Override scraper's logger to emit to web interface
        web_logger = WebScrapeLogger(socketio)
        
        # Set up web logging for Firefox browser scraper
        def web_log_info(message):
            if scraping_active:  # Only log if still active
                web_logger.log('INFO', message)
        def web_log_warning(message):
            if scraping_active:  # Only log if still active
                web_logger.log('WARNING', message)
        def web_log_error(message):
            if scraping_active:  # Only log if still active
                web_logger.log('ERROR', message)
        
        # Patch Firefox scraper logger
        original_info = current_scraper.logger.info
        original_warning = current_scraper.logger.warning  
        original_error = current_scraper.logger.error
        
        def patched_info(msg):
            original_info(msg)
            web_log_info(msg)
        def patched_warning(msg):
            original_warning(msg)
            web_log_warning(msg)
        def patched_error(msg):
            original_error(msg)
            web_log_error(msg)
            
        current_scraper.logger.info = patched_info
        current_scraper.logger.warning = patched_warning
        current_scraper.logger.error = patched_error
        
        # Run CloudScraper scraping  
        results = current_scraper.scrape_revolico(max_listings=max_listings)
        
        # Convert results to expected format (CloudScraper direct format)
        if results['success']:
            scraping_results = {
                'listings': results.get('listings', []),
                'total_phones': results.get('total_phones', 0),
                'total_listings': results.get('total_listings', 0),
                'method': results['method'],
                'url': results['url'],
                'duration': results['duration'],
                'success': True
            }
        else:
            scraping_results = {
                'listings': [],
                'error': results.get('error', 'Unknown error'),
                'method': results.get('method', 'CloudScraper'),
                'success': False
            }
        
        # Save results to file
        if scraping_results.get('success') and scraping_results.get('listings'):
            with open('revolico_data.json', 'w', encoding='utf-8') as f:
                json.dump(scraping_results, f, indent=2, ensure_ascii=False)
            
            # Save to database
            save_results_to_database(scraping_results)
        
        # Emit completion signal
        socketio.emit('scraping_completed', {
            'message': 'Scraping completed',
            'results': scraping_results,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        # Handle any errors during scraping
        error_message = f"Critical error during scraping: {e}"
        
        scraping_results = {
            'listings': [],
            'error': error_message,
            'success': False
        }
        
        socketio.emit('log_message', {
            'level': 'ERROR',
            'message': error_message,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        socketio.emit('scraping_completed', {
            'message': 'Scraping failed',
            'results': scraping_results,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    finally:
        scraping_active = False
        current_scraper = None

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("=" * 60)
    print("REVOLICO SCRAPER - FIREFOX BROWSER")
    print("Educational/Testing purposes only")
    print("=" * 60)
    print("Starting web server on http://0.0.0.0:5000")
    print("=" * 60)
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)