"""
Security Utility Tests

Tests for input validation and sanitization functions.
These tests ensure that all security utilities properly reject
invalid inputs and protect against common attacks.
"""

import pytest
from fastapi import HTTPException

from src.utils.security import (
    validate_ticker,
    validate_positive_number,
    validate_integer_range,
    sanitize_string,
    validate_option_type,
    validate_date_range,
)
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.security
class TestTickerValidation:
    """Test ticker symbol validation"""
    
    def test_valid_simple_ticker(self):
        """Valid single-letter and multi-letter tickers should pass"""
        validate_ticker("AAPL")
        validate_ticker("MSFT")
        validate_ticker("A")
        validate_ticker("GOOGL")
    
    def test_valid_ticker_with_dot(self):
        """Tickers with dots (like BRK.A) should pass"""
        validate_ticker("BRK.A")
        validate_ticker("BRK.B")
    
    def test_lowercase_ticker(self):
        """Lowercase tickers should be converted to uppercase (validation accepts and converts)"""
        result = validate_ticker("aapl")
        assert result == "AAPL"
    
    def test_ticker_with_numbers(self):
        """Tickers with numbers should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_ticker("AAPL123")
        assert exc_info.value.status_code == 400
    
    def test_ticker_with_special_chars(self):
        """Tickers with special characters (except dot) should be rejected"""
        with pytest.raises(HTTPException):
            validate_ticker("AAPL$")
        with pytest.raises(HTTPException):
            validate_ticker("AAPL-")
        with pytest.raises(HTTPException):
            validate_ticker("AAPL_")
    
    def test_sql_injection_attempt(self):
        """SQL injection patterns should be rejected"""
        with pytest.raises(HTTPException):
            validate_ticker("AAPL'; DROP TABLE stocks; --")
        with pytest.raises(HTTPException):
            validate_ticker("AAPL OR 1=1")
    
    def test_empty_ticker(self):
        """Empty ticker should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_ticker("")
        assert exc_info.value.status_code == 400
    
    def test_too_long_ticker(self):
        """Ticker longer than 10 characters should be rejected"""
        with pytest.raises(HTTPException):
            validate_ticker("VERYLONGTICKER")


@pytest.mark.unit
@pytest.mark.security
class TestPositiveNumberValidation:
    """Test positive number validation"""
    
    def test_valid_positive_number(self):
        """Valid positive numbers should pass"""
        validate_positive_number(1.0, "test_field")
        validate_positive_number(100.5, "test_field")
        validate_positive_number(0.01, "test_field")
    
    def test_zero_rejected(self):
        """Zero should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_positive_number(0.0, "test_field")
        assert exc_info.value.status_code == 400
    
    def test_negative_number_rejected(self):
        """Negative numbers should be rejected"""
        with pytest.raises(HTTPException):
            validate_positive_number(-1.0, "test_field")
        with pytest.raises(HTTPException):
            validate_positive_number(-100.5, "test_field")
    
    def test_max_value_enforcement(self):
        """Numbers exceeding max should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_positive_number(1001.0, "test_field", max_value=1000.0)
        assert exc_info.value.status_code == 400
        assert "1000" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.security
class TestIntegerRangeValidation:
    """Test integer range validation"""
    
    def test_valid_integer_in_range(self):
        """Integers within range should pass"""
        validate_integer_range(5, "test_field", min_value=1, max_value=10)
        validate_integer_range(1, "test_field", min_value=1, max_value=10)
        validate_integer_range(10, "test_field", min_value=1, max_value=10)
    
    def test_below_min_rejected(self):
        """Integers below minimum should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_integer_range(0, "test_field", min_value=1, max_value=10)
        assert exc_info.value.status_code == 400
    
    def test_above_max_rejected(self):
        """Integers above maximum should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_integer_range(11, "test_field", min_value=1, max_value=10)
        assert exc_info.value.status_code == 400
    
    def test_float_rejected(self):
        """Float values should be rejected for integer validation"""
        with pytest.raises(HTTPException):
            validate_integer_range(5.5, "test_field", min_value=1, max_value=10)


@pytest.mark.unit
@pytest.mark.security
class TestStringSanitization:
    """Test string sanitization for XSS prevention"""
    
    def test_clean_string_unchanged(self):
        """Clean strings should pass through unchanged"""
        result = sanitize_string("Apple Inc.")
        assert result == "Apple Inc."
    
    def test_html_tags_removed(self):
        """HTML tags should be stripped"""
        result = sanitize_string("<script>alert('xss')</script>Apple")
        assert "<script>" not in result
        assert "Apple" in result
    
    def test_javascript_removed(self):
        """JavaScript should be removed (script tags stripped but content remains)"""
        result = sanitize_string("Company<script>alert('xss')</script>Name")
        assert "script" not in result.lower()
        assert "<" not in result
        assert ">" not in result
        # Content between tags is preserved, just tags removed
        assert "Company" in result
        assert "Name" in result
    
    def test_control_characters_removed(self):
        """Control characters should be removed"""
        result = sanitize_string("Apple\x00Inc\x01.")
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Apple" in result
        assert "Inc" in result
    
    def test_max_length_enforced(self):
        """Strings exceeding max length should be rejected"""
        long_string = "A" * 1000
        with pytest.raises(HTTPException) as exc_info:
            sanitize_string(long_string, max_length=100)
        assert exc_info.value.status_code == 400
    
    def test_empty_string_allowed(self):
        """Empty string should be allowed"""
        result = sanitize_string("")
        assert result == ""


@pytest.mark.unit
@pytest.mark.security
class TestOptionTypeValidation:
    """Test option type validation"""
    
    def test_valid_call_option(self):
        """'call' should be valid"""
        validate_option_type("call")
    
    def test_valid_put_option(self):
        """'put' should be valid"""
        validate_option_type("put")
    
    def test_uppercase_converted(self):
        """Uppercase should be converted to lowercase"""
        result = validate_option_type("CALL")
        assert result == "call"
        result = validate_option_type("PUT")
        assert result == "put"
    
    def test_invalid_type_rejected(self):
        """Invalid option types should be rejected"""
        with pytest.raises(HTTPException) as exc_info:
            validate_option_type("invalid")
        assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.security
class TestDateRangeValidation:
    """Test date range validation"""
    
    def test_valid_date_range(self):
        """Valid date range (start before end) should pass"""
        start = datetime.now()
        end = start + timedelta(days=7)
        validate_date_range(start, end)
    
    def test_reversed_dates_rejected(self):
        """End date before start date should be rejected"""
        end = datetime.now()
        start = end + timedelta(days=7)
        with pytest.raises(HTTPException) as exc_info:
            validate_date_range(start, end)
        assert exc_info.value.status_code == 400
