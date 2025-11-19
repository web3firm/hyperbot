#!/usr/bin/env python3
"""
Test token masking functionality
"""
import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from telegram_bot import mask_token, mask_sensitive_data


def test_mask_token():
    """Test token masking function"""
    print("Testing mask_token():")
    print("=" * 60)
    
    # Test Telegram token format
    test_token = "8374468872:AAGZEBeQ3Yjwb4v2xNQRuePIbnBrSVKaOGI"
    masked = mask_token(test_token)
    print(f"Original: {test_token}")
    print(f"Masked:   {masked}")
    print(f"✅ Token masked successfully")
    print()
    
    # Verify masking
    assert test_token not in masked, "Token should be masked!"
    assert len(masked) < len(test_token), "Masked version should be shorter"
    assert "..." in masked, "Should contain ellipsis"
    
    # Test short token
    short_token = "abc123"
    masked_short = mask_token(short_token)
    print(f"Short token: {short_token}")
    print(f"Masked:      {masked_short}")
    assert masked_short == "***", "Short tokens should be fully masked"
    print(f"✅ Short token masked correctly")
    print()
    
    # Test None/empty
    assert mask_token("") == "***"
    assert mask_token(None) == "***"
    print(f"✅ Empty/None tokens handled correctly")
    print()


def test_mask_sensitive_data():
    """Test sensitive data masking in text"""
    print("Testing mask_sensitive_data():")
    print("=" * 60)
    
    test_token = "8374468872:AAGZEBeQ3Yjwb4v2xNQRuePIbnBrSVKaOGI"
    
    # Test error message with token
    error_msg = f"Failed to connect with token {test_token}"
    masked_msg = mask_sensitive_data(error_msg, test_token)
    print(f"Original: {error_msg}")
    print(f"Masked:   {masked_msg}")
    assert test_token not in masked_msg, "Token should be removed from message!"
    assert "8374468872:AAG...aOGI" in masked_msg, "Masked token should be present"
    print(f"✅ Token in error message masked successfully")
    print()
    
    # Test message without token
    normal_msg = "Everything is working fine"
    masked_normal = mask_sensitive_data(normal_msg, test_token)
    assert masked_normal == normal_msg, "Normal messages should be unchanged"
    print(f"✅ Normal messages unchanged")
    print()
    
    # Test with environment variable
    os.environ['TELEGRAM_BOT_TOKEN'] = test_token
    auto_msg = f"Connection failed: Invalid token {test_token}"
    auto_masked = mask_sensitive_data(auto_msg)  # Should auto-detect from env
    assert test_token not in auto_masked, "Token should be auto-detected and masked"
    print(f"✅ Auto-detection from environment works")
    print()


def test_logging_scenario():
    """Test realistic logging scenarios"""
    print("Testing realistic logging scenarios:")
    print("=" * 60)
    
    test_token = "8374468872:AAGZEBeQ3Yjwb4v2xNQRuePIbnBrSVKaOGI"
    
    # Simulate various error scenarios
    scenarios = [
        f"Telegram API error: Unauthorized token {test_token}",
        f"Failed to start bot with config: {{'token': '{test_token}', 'chat_id': '123'}}",
        f"Exception in telegram bot: HTTPError 401 at https://api.telegram.org/bot{test_token}/getMe",
        "Normal log message without sensitive data",
    ]
    
    print("Masking various log messages:")
    for i, scenario in enumerate(scenarios, 1):
        masked = mask_sensitive_data(scenario, test_token)
        print(f"\n{i}. Original: {scenario[:80]}...")
        print(f"   Masked:   {masked[:80]}...")
        
        if test_token in scenario:
            assert test_token not in masked, f"Scenario {i} failed: token not masked!"
            print(f"   ✅ Token successfully masked")
        else:
            assert masked == scenario, f"Scenario {i} failed: message altered unnecessarily"
            print(f"   ✅ Clean message unchanged")
    
    print()


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("Testing Telegram Token Masking")
    print("=" * 60)
    print()
    
    try:
        test_mask_token()
        test_mask_sensitive_data()
        test_logging_scenario()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Token masking is working correctly:")
        print("• Tokens are masked in logs")
        print("• Error messages are sanitized")
        print("• Stack traces won't expose tokens")
        print()
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
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
