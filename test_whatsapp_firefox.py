#!/usr/bin/env python3
"""
Test WhatsApp automation Firefox setup
"""

from whatsapp_simple import SimpleWhatsAppBot

def test_whatsapp_firefox_setup():
    """Test WhatsApp automation with Firefox"""
    print("Testing WhatsApp Firefox setup...")

    bot = SimpleWhatsAppBot()

    try:
        # Setup browser
        success = bot.setup_browser()
        if success:
            print("✅ WhatsApp Firefox browser setup successful!")
            bot.driver.quit()
            return True
        else:
            print("❌ WhatsApp Firefox browser setup failed!")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_whatsapp_firefox_setup()
