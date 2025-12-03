"""
WhatsApp Account Manager - Manages multiple WhatsApp accounts
"""
import os
import logging
from datetime import datetime, date
from typing import Dict, Optional
from whatsapp_simple import SimpleWhatsAppBot

logger = logging.getLogger(__name__)


class WhatsAppAccountManager:
    """Manages multiple WhatsApp bot instances"""

    def __init__(self, db):
        """
        Initialize the WhatsApp Account Manager

        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.active_bots: Dict[int, SimpleWhatsAppBot] = {}  # account_id -> bot instance
        self.base_profile_dir = "whatsapp_profiles"

        # Create base profile directory if it doesn't exist
        os.makedirs(self.base_profile_dir, exist_ok=True)
        logger.info(f"WhatsApp Account Manager initialized with base dir: {self.base_profile_dir}")

    def get_or_create_bot(self, account_id: int) -> Optional[SimpleWhatsAppBot]:
        """
        Get existing bot instance or create new one for account

        Args:
            account_id: WhatsApp account ID from database

        Returns:
            SimpleWhatsAppBot instance or None if account not found
        """
        from models import WhatsAppAccount

        # Return existing bot if already active
        if account_id in self.active_bots:
            logger.info(f"Returning existing bot for account {account_id}")
            return self.active_bots[account_id]

        # Load account from database
        account = self.db.session.get(WhatsAppAccount, account_id)
        if not account:
            logger.error(f"Account {account_id} not found in database")
            return None

        if not account.is_active:
            logger.warning(f"Account {account_id} is not active")
            return None

        # Create profile directory for this account
        profile_dir = os.path.join(self.base_profile_dir, account.session_name)
        os.makedirs(profile_dir, exist_ok=True)

        # Create bot instance with account-specific profile
        try:
            bot = SimpleWhatsAppBot(profile_dir=profile_dir, account_id=account_id)
            self.active_bots[account_id] = bot
            logger.info(f"Created new bot instance for account {account_id} ({account.account_name})")
            return bot
        except Exception as e:
            logger.error(f"Failed to create bot for account {account_id}: {e}")
            return None

    def get_bot(self, account_id: int) -> Optional[SimpleWhatsAppBot]:
        """Get existing bot instance (does not create new one)"""
        return self.active_bots.get(account_id)

    def remove_bot(self, account_id: int):
        """Remove and cleanup bot instance"""
        if account_id in self.active_bots:
            bot = self.active_bots[account_id]
            try:
                bot.close()
            except:
                pass
            del self.active_bots[account_id]
            logger.info(f"Removed bot instance for account {account_id}")

    def update_account_status(self, account_id: int, is_logged_in: bool, phone_number: str = None):
        """
        Update account status in database

        Args:
            account_id: WhatsApp account ID
            is_logged_in: Login status
            phone_number: Phone number (if detected)
        """
        from models import WhatsAppAccount

        try:
            account = self.db.session.get(WhatsAppAccount, account_id)
            if account:
                account.is_logged_in = is_logged_in
                account.last_seen_at = datetime.utcnow()

                if is_logged_in:
                    account.last_login_at = datetime.utcnow()

                if phone_number and not account.phone_number:
                    account.phone_number = phone_number

                self.db.session.commit()
                logger.info(f"Updated account {account_id} status: logged_in={is_logged_in}")
        except Exception as e:
            logger.error(f"Failed to update account status: {e}")
            self.db.session.rollback()

    def increment_message_counter(self, account_id: int, success: bool = True):
        """
        Increment message counter for account

        Args:
            account_id: WhatsApp account ID
            success: Whether message was sent successfully
        """
        from models import WhatsAppAccount

        try:
            account = self.db.session.get(WhatsAppAccount, account_id)
            if account:
                # Reset daily counter if needed
                account.reset_daily_counter_if_needed()

                if success:
                    account.messages_sent_today += 1
                    account.total_messages_sent += 1
                else:
                    account.total_messages_failed += 1

                account.last_seen_at = datetime.utcnow()
                self.db.session.commit()
                logger.info(f"Account {account_id}: messages_sent_today={account.messages_sent_today}/{account.daily_message_limit}")
        except Exception as e:
            logger.error(f"Failed to increment message counter: {e}")
            self.db.session.rollback()

    def can_send_message(self, account_id: int) -> tuple[bool, str]:
        """
        Check if account can send message (within daily limit)

        Args:
            account_id: WhatsApp account ID

        Returns:
            Tuple of (can_send, reason)
        """
        from models import WhatsAppAccount

        try:
            account = self.db.session.get(WhatsAppAccount, account_id)
            if not account:
                return False, "Account not found"

            if not account.is_active:
                return False, "Account is not active"

            if not account.is_logged_in:
                return False, "Account is not logged in"

            # Reset daily counter if needed
            account.reset_daily_counter_if_needed()

            if account.messages_sent_today >= account.daily_message_limit:
                return False, f"Daily limit reached ({account.messages_sent_today}/{account.daily_message_limit})"

            return True, "OK"
        except Exception as e:
            logger.error(f"Failed to check message limit: {e}")
            return False, str(e)

    def get_all_accounts(self):
        """Get all WhatsApp accounts from database"""
        from models import WhatsAppAccount

        try:
            accounts = WhatsAppAccount.query.all()
            return [account.to_dict() for account in accounts]
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []

    def get_active_accounts(self):
        """Get all active WhatsApp accounts"""
        from models import WhatsAppAccount

        try:
            accounts = WhatsAppAccount.query.filter_by(is_active=True).all()
            return [account.to_dict() for account in accounts]
        except Exception as e:
            logger.error(f"Failed to get active accounts: {e}")
            return []

    def create_account(self, account_name: str, daily_limit: int = 100) -> Optional[dict]:
        """
        Create new WhatsApp account

        Args:
            account_name: Display name for account
            daily_limit: Daily message limit

        Returns:
            Account dict or None if creation failed
        """
        from models import WhatsAppAccount
        import re

        try:
            # Generate session name from account name (alphanumeric only)
            session_name = re.sub(r'[^a-zA-Z0-9_]', '_', account_name.lower())
            session_name = f"wa_{session_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Check if account name already exists
            existing = WhatsAppAccount.query.filter_by(account_name=account_name).first()
            if existing:
                logger.warning(f"Account with name '{account_name}' already exists")
                return None

            # Create new account
            account = WhatsAppAccount(
                account_name=account_name,
                session_name=session_name,
                daily_message_limit=daily_limit,
                is_active=True,
                is_logged_in=False
            )

            self.db.session.add(account)
            self.db.session.commit()

            logger.info(f"Created new WhatsApp account: {account_name} (ID: {account.id})")
            return account.to_dict()
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            self.db.session.rollback()
            return None

    def delete_account(self, account_id: int) -> bool:
        """
        Delete WhatsApp account

        Args:
            account_id: Account ID to delete

        Returns:
            True if deleted successfully
        """
        from models import WhatsAppAccount
        import shutil

        try:
            account = self.db.session.get(WhatsAppAccount, account_id)
            if not account:
                return False

            # Remove bot instance if active
            self.remove_bot(account_id)

            # Delete profile directory
            profile_dir = os.path.join(self.base_profile_dir, account.session_name)
            if os.path.exists(profile_dir):
                shutil.rmtree(profile_dir)
                logger.info(f"Deleted profile directory: {profile_dir}")

            # Delete from database
            self.db.session.delete(account)
            self.db.session.commit()

            logger.info(f"Deleted WhatsApp account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            self.db.session.rollback()
            return False

    def restore_logged_in_accounts(self):
        """
        Restore WhatsApp sessions for accounts marked as logged_in in database.
        Called on server startup to restore bot instances and validate sessions.
        """
        from models import WhatsAppAccount

        try:
            logger.info("Restoring WhatsApp sessions from previous session...")

            # Query all active accounts and try to restore them
            # (even if not marked as logged in - we check the actual session state)
            logged_in_accounts = WhatsAppAccount.query.filter_by(is_active=True).all()

            if not logged_in_accounts:
                logger.info("No active accounts found")
                return

            logger.info(f"Found {len(logged_in_accounts)} accounts marked as logged in")

            for account in logged_in_accounts:
                try:
                    logger.info(f"Restoring session for account {account.id} ({account.account_name})...")

                    # Create bot instance with saved profile
                    bot = self.get_or_create_bot(account.id)
                    if not bot:
                        logger.error(f"Failed to create bot for account {account.id}")
                        continue

                    # Start browser with saved profile
                    if not bot.setup_browser():
                        logger.warning(f"Browser setup failed for account {account.id}")
                        account.is_logged_in = False
                        self.db.session.commit()
                        continue

                    # Load WhatsApp Web
                    result = bot.start_whatsapp_web()

                    if result['status'] == 'logged_in':
                        # Session still valid!
                        logger.info(f"✅ Session restored for account {account.id} ({account.account_name})")
                        bot.is_logged_in = True
                    elif result['status'] == 'qr_ready':
                        # Session expired, needs re-login
                        logger.warning(f"Session expired for account {account.id}, QR code required")
                        account.is_logged_in = False
                        bot.is_logged_in = False
                        self.db.session.commit()
                    else:
                        # Error
                        logger.error(f"Failed to restore session for account {account.id}: {result.get('message')}")
                        account.is_logged_in = False
                        self.db.session.commit()

                except Exception as e:
                    logger.error(f"Error restoring account {account.id}: {e}")
                    account.is_logged_in = False
                    self.db.session.commit()

            logger.info("Session restoration complete")

        except Exception as e:
            logger.error(f"Failed to restore logged-in accounts: {e}")

    def cleanup_all_bots(self):
        """Cleanup all active bots (call on shutdown)"""
        logger.info("Cleaning up all WhatsApp bots...")
        for account_id in list(self.active_bots.keys()):
            self.remove_bot(account_id)
        logger.info("All bots cleaned up")
