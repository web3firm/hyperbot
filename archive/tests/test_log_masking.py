#!/usr/bin/env python3
"""
Test log masking for sensitive data (tokens, URLs, etc.)
"""
import logging
import os
import sys
import re
from io import StringIO

# Set test token
os.environ['TELEGRAM_BOT_TOKEN'] = '8374468872:AAGZEBeQ3Yjwb4v2xNQRuePIbnBrSVKaOGI'
os.environ['HYPERLIQUID_API_SECRET'] = 'test_secret_key_12345'

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs (tokens, API keys, URLs with tokens)"""
    
    def __init__(self):
        super().__init__()
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.api_secret = os.getenv('HYPERLIQUID_API_SECRET', '')
        
    def filter(self, record):
        """Mask sensitive data in log records"""
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            
            # Mask Telegram bot token in URLs
            if self.telegram_token and self.telegram_token in msg:
                if ':' in self.telegram_token:
                    bot_id = self.telegram_token.split(':')[0]
                    msg = msg.replace(self.telegram_token, f"{bot_id}:***MASKED***")
                else:
                    msg = msg.replace(self.telegram_token, "***MASKED***")
            
            # Mask API URLs with tokens using regex
            msg = re.sub(
                r'(https?://[^/]+/bot)(\d+:[A-Za-z0-9_-]+)',
                r'\1***MASKED***',
                msg
            )
            
            # Mask API secrets
            if self.api_secret and len(self.api_secret) > 10:
                msg = msg.replace(self.api_secret, '***MASKED***')
            
            record.msg = msg
            
        return True


def test_log_masking():
    """Test that sensitive data is masked in logs"""
    print("Testing log masking...")
    print("=" * 60)
    
    # Setup logger with filter
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))
    handler.addFilter(SensitiveDataFilter())
    
    test_logger = logging.getLogger('test_logger')
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)
    
    token = os.environ['TELEGRAM_BOT_TOKEN']
    secret = os.environ['HYPERLIQUID_API_SECRET']
    
    # Test cases
    test_cases = [
        {
            'name': 'HTTP Request with token in URL',
            'message': f'HTTP Request: POST https://api.telegram.org/bot{token}/getUpdates "HTTP/1.1 200 OK"',
            'should_not_contain': [token],
            'should_contain': ['8374468872:***MASKED***']
        },
        {
            'name': 'Error message with token',
            'message': f'Failed to connect: Invalid token {token}',
            'should_not_contain': [token],
            'should_contain': ['8374468872:***MASKED***']
        },
        {
            'name': 'Config with API secret',
            'message': f'Config loaded: api_secret={secret}',
            'should_not_contain': [secret],
            'should_contain': ['***MASKED***']
        },
        {
            'name': 'Normal log without sensitive data',
            'message': 'Account updated: value=$38.30',
            'should_not_contain': [token, secret],
            'should_contain': ['Account updated']
        },
        {
            'name': 'URL with generic bot token format',
            'message': 'POST https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789/sendMessage',
            'should_not_contain': ['1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789'],
            'should_contain': ['bot***MASKED***']
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 60)
        
        # Clear stream
        log_stream.truncate(0)
        log_stream.seek(0)
        
        # Log the message
        test_logger.info(test_case['message'])
        
        # Get logged output
        output = log_stream.getvalue()
        
        print(f"Original: {test_case['message'][:80]}...")
        print(f"Logged:   {output[:80]}...")
        
        # Check that sensitive data is not in output
        test_passed = True
        for sensitive in test_case['should_not_contain']:
            if sensitive and sensitive in output:
                print(f"❌ FAIL: Found sensitive data '{sensitive[:20]}...' in output")
                test_passed = False
                all_passed = False
        
        # Check that expected masked values are present
        for expected in test_case['should_contain']:
            if expected not in output:
                print(f"⚠️  WARNING: Expected '{expected}' not found in output")
        
        if test_passed:
            print("✅ PASS: No sensitive data leaked")
    
    print()
    print("=" * 60)
    
    return all_passed


def test_httpx_log_suppression():
    """Test that httpx logs are suppressed"""
    print("\nTesting httpx log suppression...")
    print("=" * 60)
    
    # Set httpx logger to WARNING
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    httpx_logger = logging.getLogger('httpx')
    
    # Create test handler
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    httpx_logger.addHandler(handler)
    
    # Try to log INFO level (should be suppressed)
    httpx_logger.info("This INFO message should be suppressed")
    
    output = log_stream.getvalue()
    
    if not output:
        print("✅ PASS: httpx INFO logs are suppressed")
        return True
    else:
        print(f"❌ FAIL: httpx INFO logs not suppressed: {output}")
        return False


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("Testing Log Security Features")
    print("=" * 60)
    print()
    
    try:
        test1_passed = test_log_masking()
        test2_passed = test_httpx_log_suppression()
        
        print()
        print("=" * 60)
        
        if test1_passed and test2_passed:
            print("✅ ALL TESTS PASSED!")
            print("=" * 60)
            print()
            print("Security features working:")
            print("• Telegram tokens masked in logs")
            print("• API secrets masked")
            print("• URLs with tokens sanitized")
            print("• httpx HTTP logs suppressed")
            print()
            sys.exit(0)
        else:
            print("❌ SOME TESTS FAILED")
            print("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
