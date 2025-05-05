import pytest
from kuru_sdk.utils import get_error_message, error_codes

def test_get_error_message_known_code_hex_prefix():
    """Test with a known error code with '0x' prefix."""
    error_code = "0xbb55fd27"
    expected_message = "Insufficient Liquidity"
    assert get_error_message(error_code) == expected_message

def test_get_error_message_known_code_no_prefix():
    """Test with a known error code without '0x' prefix."""
    error_code = "bb55fd27"
    expected_message = "Insufficient Liquidity"
    assert get_error_message(error_code) == expected_message

def test_get_error_message_known_code_tuple():
    """Test with a known error code in tuple format."""
    error_code_tuple = ("0x91f53656", "some other data")
    expected_message = "Price Error"
    assert get_error_message(error_code_tuple) == expected_message

def test_get_error_message_known_code_string_tuple_format():
    """Test with a known error code in string format resembling a tuple."""
    error_code_str = "('0x06e6da4d', 'some other data')"
    expected_message = "Post Only Error"
    assert get_error_message(error_code_str) == expected_message
    
def test_get_error_message_known_code_string_tuple_format_single():
    """Test with a known error code in string format resembling a single-element tuple."""
    error_code_str = "('0x8199f5f3',)"
    expected_message = "Slippage Exceeded"
    assert get_error_message(error_code_str) == expected_message

def test_get_error_message_unknown_code():
    """Test with an unknown error code."""
    unknown_error_code = "0x12345678"
    expected_message = "Unknown error: 12345678"
    assert get_error_message(unknown_error_code) == expected_message

def test_get_error_message_unknown_code_tuple():
    """Test with an unknown error code in tuple format."""
    unknown_error_code_tuple = ("0xabcdef01",)
    expected_message = "Unknown error: abcdef01"
    assert get_error_message(unknown_error_code_tuple) == expected_message
    
def test_get_error_message_all_known_codes():
    """Test all known error codes from the dictionary."""
    for code, message in error_codes.items():
        assert get_error_message(code) == message
        assert get_error_message(f"0x{code}") == message
        assert get_error_message((f"0x{code}",)) == message
        assert get_error_message(f"('0x{code}',)") == message

# Potential edge case: Empty string (though function expects specific formats)
# def test_get_error_message_empty_string():
#     """Test with an empty string input."""
#     # Depending on desired behavior for invalid input, this might raise an error or return unknown.
#     # Current implementation would likely return "Unknown error: "
#     assert get_error_message("") == "Unknown error: "

# Potential edge case: String without valid hex code
# def test_get_error_message_invalid_string():
#     """Test with a string that doesn't contain a recognizable hex code."""
#     assert get_error_message("not a hex code") == "Unknown error: notahexcode" 