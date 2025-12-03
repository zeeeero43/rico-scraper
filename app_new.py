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
        
        # Also print to console
        print(f"[{level}] {message}")

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
    """Get QR code screenshot as image"""
    global current_whatsapp_bot
    
    try:
        if current_whatsapp_bot:
            screenshot_path = os.path.join(os.getcwd(), 'whatsapp_qr_code.png')
            
            if os.path.exists(screenshot_path):
                return send_file(screenshot_path, mimetype='image/png')
            else:
                return jsonify({
                    'success': False,
                    'message': 'QR code screenshot not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'message': 'WhatsApp not initialized'
            }), 400
            
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
    """Start WhatsApp outreach campaign"""
    global current_whatsapp_bot
    
    try:
        if not current_whatsapp_bot or not current_whatsapp_bot.is_logged_in:
            return jsonify({
                'success': False,
                'message': 'WhatsApp not logged in'
            }), 400
        
        data = request.get_json()
        message_template = data.get('message_template', SIMPLE_MESSAGES['simple'])
        daily_limit = int(data.get('daily_limit', 10))
        
        # Get uncontacted customers
        with app.app_context():
            customers = Customer.query.filter_by(contacted=False).limit(daily_limit).all()
            
            if not customers:
                return jsonify({
                    'success': False,
                    'message': 'No uncontacted customers found'
                })
        
        def run_campaign():
            sent_count = 0
            for customer in customers:
                try:
                    result = current_whatsapp_bot.send_message(
                        customer.phone_number, 
                        message_template
                    )
                    
                    if result['status'] == 'success':
                        with app.app_context():
                            customer.contacted = True
                            customer.contacted_at = datetime.utcnow()
                            db.session.commit()
                        
                        sent_count += 1
                        socketio.emit('whatsapp_log', {
                            'level': 'INFO',
                            'message': f'Message sent to {customer.phone_number} ({sent_count}/{len(customers)})'
                        })
                    else:
                        socketio.emit('whatsapp_log', {
                            'level': 'ERROR',
                            'message': f'Failed to send to {customer.phone_number}: {result["message"]}'
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
                    socketio.emit('whatsapp_log', {
                        'level': 'ERROR',
                        'message': f'Error sending to {customer.phone_number}: {str(e)}'
                    })
            
            socketio.emit('whatsapp_campaign_completed', {
                'message': f'Campaign completed! {sent_count} messages sent.'
            })
        
        threading.Thread(target=run_campaign, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': f'Campaign started for {len(customers)} customers'
        })
        
    except Exception as e:
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
    """Get list of uncontacted customers"""
    try:
        customers = Customer.query.filter_by(contacted=False).all()
        return jsonify({
            'success': True,
            'count': len(customers),
            'customers': [{
                'id': c.id,
                'phone_number': c.phone_number,
                'source_title': c.source_title,
                'created_at': c.created_at.isoformat()
            } for c in customers]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ===== EXISTING SCRAPING AND CUSTOMER ENDPOINTS =====
# (Keep all existing endpoints from the original app.py)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    print("\n✅ Datenbank-Tabellen erstellt/aktualisiert")
    print("=" * 60)
    print("REVOLICO SCRAPER + WHATSAPP AUTOMATION")
    print("Mit QR-Code Screenshot und Session Persistierung")
    print("=" * 60)
    print("Starting web server on http://0.0.0.0:5000")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)