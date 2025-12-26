"""
Security utilities for input validation and sanitization.
Prevents SQL injection, XSS, and validates user inputs.
"""

import re
from typing import Optional
from fastapi import HTTPException, status


def validate_ticker(ticker: str) -> str:
    """
    Validate and sanitize stock ticker symbol.
    
    Args:
        ticker: Stock ticker symbol to validate
        
    Returns:
        Sanitized uppercase ticker symbol
        
    Raises:
        HTTPException: If ticker format is invalid
    """
    if not ticker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticker symbol is required"
        )
    
    # Ticker format: 1-10 uppercase letters, may contain dots (e.g., BRK.A)
    ticker_upper = ticker.strip().upper()
    
    if not re.match(r'^[A-Z]{1,10}(\.[A-Z]{1,2})?$', ticker_upper):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ticker format: {ticker}. Must be 1-10 uppercase letters (e.g., AAPL, BRK.A)"
        )
    
    return ticker_upper


def validate_positive_number(value: float, field_name: str, max_value: Optional[float] = None) -> float:
    """
    Validate that a number is positive and within optional maximum.
    
    Args:
        value: Number to validate
        field_name: Name of field for error messages
        max_value: Optional maximum allowed value
        
    Returns:
        Validated value
        
    Raises:
        HTTPException: If validation fails
    """
    if value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be positive (got {value})"
        )
    
    if max_value is not None and value > max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must not exceed {max_value} (got {value})"
        )
    
    return value


def validate_integer_range(value: int, field_name: str, min_value: int, max_value: int) -> int:
    """
    Validate that an integer is within specified range.
    
    Args:
        value: Integer to validate
        field_name: Name of field for error messages
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        Validated value
        
    Raises:
        HTTPException: If validation fails
    """
    if not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be an integer (got {type(value).__name__})"
        )
    
    if value < min_value or value > max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be between {min_value} and {max_value} (got {value})"
        )
    
    return value


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent XSS attacks.
    Removes potentially dangerous characters and limits length.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        HTTPException: If string exceeds max length
    """
    if not value:
        return ""
    
    # Trim whitespace
    sanitized = value.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input too long (max {max_length} characters)"
        )
    
    # Remove null bytes and other control characters
    sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', sanitized)
    
    # Remove HTML/script tags for basic XSS prevention
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    
    return sanitized


def validate_option_type(option_type: str) -> str:
    """
    Validate option type is either 'call' or 'put'.
    
    Args:
        option_type: Option type to validate
        
    Returns:
        Validated lowercase option type
        
    Raises:
        HTTPException: If option type is invalid
    """
    option_type_lower = option_type.lower().strip()
    
    if option_type_lower not in ['call', 'put']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid option type: {option_type}. Must be 'call' or 'put'"
        )
    
    return option_type_lower


def validate_date_range(start_date, end_date, field_prefix: str = "Date"):
    """
    Validate that start date is before end date.
    
    Args:
        start_date: Start date
        end_date: End date
        field_prefix: Prefix for field names in error messages
        
    Raises:
        HTTPException: If date range is invalid
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_prefix} range invalid: start ({start_date}) must be before end ({end_date})"
        )
