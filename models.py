"""
Datenbank-Modelle für den Revolico Scraper
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Customer(db.Model):
    """Kunden-Modell für extrahierte Telefonnummern"""
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)

    phone_number = db.Column(db.String(20), nullable=False, unique=True, comment='Telefonnummer (+53XXXXXXXX)')
    contacted = db.Column(db.Boolean, default=False, nullable=False, comment='Bereits kontaktiert?')
    source_url = db.Column(db.String(500), nullable=True, comment='Original Revolico Angebots-URL')
    source_title = db.Column(db.String(300), nullable=True, comment='Original Angebots-Titel')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='Datum der Erfassung')
    contacted_at = db.Column(db.DateTime, nullable=True, comment='Datum des Kontakts')
    notes = db.Column(db.Text, nullable=True, comment='Notizen zum Kunden')
    seller_name = db.Column(db.String(200), nullable=True, comment='Name des Verkäufers')
    profile_picture_id = db.Column(db.String(64), nullable=True, comment='Profile picture image hash')

    # WhatsApp integration fields
    whatsapp_contacted = db.Column(db.Boolean, default=False, nullable=False, comment='Via WhatsApp kontaktiert?')
    whatsapp_message_sent = db.Column(db.Text, nullable=True, comment='Gesendete WhatsApp Nachricht')
    whatsapp_sent_at = db.Column(db.DateTime, nullable=True, comment='WhatsApp Versand-Datum')
    whatsapp_status = db.Column(db.String(50), nullable=True, comment='WhatsApp Status (sent/failed/pending)')

    def __repr__(self):
        return f'<Customer {self.phone_number}>'

    def to_dict(self):
        """Konvertiert den Kunden zu einem Dictionary für JSON"""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'contacted': self.contacted,
            'source_url': self.source_url,
            'source_title': self.source_title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'contacted_at': self.contacted_at.isoformat() if self.contacted_at else None,
            'notes': self.notes,
            'seller_name': self.seller_name,
            'profile_picture_id': self.profile_picture_id,
            'whatsapp_contacted': self.whatsapp_contacted,
            'whatsapp_message_sent': self.whatsapp_message_sent,
            'whatsapp_sent_at': self.whatsapp_sent_at.isoformat() if self.whatsapp_sent_at else None,
            'whatsapp_status': self.whatsapp_status
        }


class ScrapedListing(db.Model):
    """Vollständige gescrapte Anzeigen mit allen Details"""
    __tablename__ = 'scraped_listings'

    id = db.Column(db.Integer, primary_key=True)
    revolico_id = db.Column(db.String(50), nullable=False, unique=True, comment='Revolico Listing ID')

    # Basic info
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=False)

    # Price
    price = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), nullable=True, default='USD')

    # Contact
    phone_numbers = db.Column(db.JSON, nullable=False, comment='Array of phone numbers')
    seller_name = db.Column(db.String(200), nullable=True, comment='Name des Verkäufers')

    # Images (stored as image_ids that reference ImageProxy table)
    image_ids = db.Column(db.JSON, nullable=True, comment='Array of image proxy IDs')
    profile_picture_id = db.Column(db.String(64), nullable=True, comment='Profile picture image hash')

    # Location & Category
    category = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    condition = db.Column(db.String(50), nullable=True, default='used')

    # Status
    exported = db.Column(db.Boolean, default=False, comment='Bereits zu Rico-Cuba exportiert?')
    exported_at = db.Column(db.DateTime, nullable=True)

    # WhatsApp integration fields
    whatsapp_contacted = db.Column(db.Boolean, default=False, nullable=False, comment='Via WhatsApp kontaktiert?')
    whatsapp_contacted_at = db.Column(db.DateTime, nullable=True, comment='WhatsApp Kontakt-Datum')
    whatsapp_notes = db.Column(db.Text, nullable=True, comment='Notizen zum WhatsApp Kontakt')
    whatsapp_status = db.Column(db.String(50), nullable=True, comment='WhatsApp Status (sent/failed/pending)')
    whatsapp_account_id = db.Column(db.Integer, db.ForeignKey('whatsapp_accounts.id'), nullable=True, comment='Verwendeter WhatsApp Account')

    # Timestamps
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ScrapedListing {self.revolico_id}: {self.title[:50]}>'

    def to_dict(self):
        """Konvertiert Listing zu Dictionary für JSON/API"""
        # Format price: show as int if no decimal places, otherwise keep decimals
        formatted_price = None
        if self.price is not None:
            if self.price == int(self.price):
                formatted_price = int(self.price)
            else:
                formatted_price = self.price

        return {
            'id': self.id,
            'revolico_id': self.revolico_id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'price': formatted_price,
            'currency': self.currency,
            'phone_numbers': self.phone_numbers,
            'seller_name': self.seller_name,
            'image_ids': self.image_ids,
            'profile_picture_id': self.profile_picture_id,
            'category': self.category,
            'location': self.location,
            'condition': self.condition,
            'exported': self.exported,
            'exported_at': self.exported_at.isoformat() if self.exported_at else None,
            'whatsapp_contacted': self.whatsapp_contacted,
            'whatsapp_contacted_at': self.whatsapp_contacted_at.isoformat() if self.whatsapp_contacted_at else None,
            'whatsapp_notes': self.whatsapp_notes,
            'whatsapp_status': self.whatsapp_status,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ImageProxy(db.Model):
    """Image Proxy Mapping - versteckt Revolico URLs"""
    __tablename__ = 'image_proxy'

    id = db.Column(db.Integer, primary_key=True)
    image_hash = db.Column(db.String(64), unique=True, nullable=False, index=True, comment='SHA256 hash of URL')
    original_url = db.Column(db.String(1000), nullable=False, comment='Original Revolico image URL')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: Cache the image locally
    cached = db.Column(db.Boolean, default=False)
    cache_path = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<ImageProxy {self.image_hash}>'

    def to_dict(self):
        return {
            'id': self.id,
            'image_hash': self.image_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WhatsAppAccount(db.Model):
    """WhatsApp Account Management für Multi-Account Support"""
    __tablename__ = 'whatsapp_accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False, unique=True, comment='Eindeutiger Account Name')
    phone_number = db.Column(db.String(20), nullable=True, comment='Verknüpfte Telefonnummer')
    session_name = db.Column(db.String(100), nullable=False, unique=True, comment='Eindeutiger Session-Ordner Name')

    # Status
    is_logged_in = db.Column(db.Boolean, default=False, nullable=False, comment='Ist eingeloggt?')
    last_login_at = db.Column(db.DateTime, nullable=True, comment='Letzte erfolgreiche Anmeldung')
    last_seen_at = db.Column(db.DateTime, nullable=True, comment='Zuletzt aktiv')

    # Message limits & tracking
    daily_message_limit = db.Column(db.Integer, default=100, nullable=False, comment='Maximale Nachrichten pro Tag')
    messages_sent_today = db.Column(db.Integer, default=0, nullable=False, comment='Heute gesendete Nachrichten')
    last_reset_date = db.Column(db.Date, nullable=True, comment='Letztes Reset-Datum für Tages-Counter')

    # Total statistics
    total_messages_sent = db.Column(db.Integer, default=0, nullable=False, comment='Gesamt gesendete Nachrichten')
    total_messages_failed = db.Column(db.Integer, default=0, nullable=False, comment='Gesamt fehlgeschlagene Nachrichten')

    # Account metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment='Account aktiv?')
    notes = db.Column(db.Text, nullable=True, comment='Notizen zum Account')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<WhatsAppAccount {self.account_name} ({self.phone_number})>'

    def to_dict(self):
        """Konvertiert Account zu Dictionary für JSON/API"""
        return {
            'id': self.id,
            'account_name': self.account_name,
            'phone_number': self.phone_number,
            'session_name': self.session_name,
            'is_logged_in': self.is_logged_in,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'daily_message_limit': self.daily_message_limit,
            'messages_sent_today': self.messages_sent_today,
            'last_reset_date': self.last_reset_date.isoformat() if self.last_reset_date else None,
            'total_messages_sent': self.total_messages_sent,
            'total_messages_failed': self.total_messages_failed,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def reset_daily_counter_if_needed(self):
        """Reset daily counter if it's a new day"""
        from datetime import date
        today = date.today()
        if not self.last_reset_date or self.last_reset_date < today:
            self.messages_sent_today = 0
            self.last_reset_date = today
            return True
        return False
    


def init_database(app):
    """Initialisiert die Datenbank mit der Flask App"""
    # Konfiguration - nur setzen wenn nicht bereits gesetzt
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///revolico_customers.db")

    if not app.config.get("SQLALCHEMY_ENGINE_OPTIONS"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }

    if not app.config.get("SQLALCHEMY_TRACK_MODIFICATIONS"):
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # SQLAlchemy mit App initialisieren
    db.init_app(app)

    # Tabellen erstellen
    with app.app_context():
        db.create_all()

        # Manual migration: Add whatsapp_account_id column if missing
        from sqlalchemy import inspect, text
        try:
            inspector = inspect(db.engine)

            # Check if column exists
            columns = [col['name'] for col in inspector.get_columns('scraped_listings')]

            migrations_run = False

            if 'whatsapp_account_id' not in columns:
                print("⚠️  Adding missing whatsapp_account_id column...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE scraped_listings ADD COLUMN whatsapp_account_id INTEGER"
                    ))
                    conn.commit()
                print("✅ Migration complete: whatsapp_account_id column added")
                migrations_run = True

            if 'profile_picture_id' not in columns:
                print("⚠️  Adding missing profile_picture_id column to scraped_listings...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE scraped_listings ADD COLUMN profile_picture_id VARCHAR(64)"
                    ))
                    conn.commit()
                print("✅ Migration complete: profile_picture_id column added to scraped_listings")
                migrations_run = True

            # Check customers table
            customer_columns = [col['name'] for col in inspector.get_columns('customers')]

            if 'seller_name' not in customer_columns:
                print("⚠️  Adding missing seller_name column to customers...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE customers ADD COLUMN seller_name VARCHAR(200)"
                    ))
                    conn.commit()
                print("✅ Migration complete: seller_name column added to customers")
                migrations_run = True

            if 'profile_picture_id' not in customer_columns:
                print("⚠️  Adding missing profile_picture_id column to customers...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE customers ADD COLUMN profile_picture_id VARCHAR(64)"
                    ))
                    conn.commit()
                print("✅ Migration complete: profile_picture_id column added to customers")
                migrations_run = True

            if not migrations_run:
                print("✅ Datenbank-Tabellen erstellt/aktualisiert")
        except Exception as e:
            print(f"⚠️  Migration check/execution failed: {e}")
            print("✅ Datenbank-Tabellen erstellt/aktualisiert")