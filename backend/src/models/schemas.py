"""
Pydantic schemas for request/response validation.
Provides type-safe API contracts and data validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum

# Base configuration for all schemas
class BaseSchema(BaseModel):
    """Base Pydantic model with common configuration"""
    
    class Config:
        from_attributes = True  # Enable ORM mode (Pydantic v2)
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# Enums
class OptionType(str, Enum):
    """Option type enum"""
    call = "call"
    put = "put"

class StrikeModeType(str, Enum):
    """Strike price matching mode"""
    exact = "exact"
    percentage_range = "percentage_range"
    nearest = "nearest"

class ContractStatus(str, Enum):
    """Contract status enum"""
    active = "active"
    expired = "expired"

class MonitoringStatus(str, Enum):
    """Watchlist monitoring status"""
    active = "active"
    paused = "paused"

class SchedulerStatus(str, Enum):
    """Scheduler status enum"""
    idle = "idle"
    running = "running"
    paused = "paused"
    error = "error"

# Placeholder schemas - will be populated with actual schemas in Phase 3+
# These are imported by endpoints but defined when implementing each user story

__all__ = [
    "BaseSchema",
    "OptionType",
    "StrikeModeType",
    "ContractStatus",
    "MonitoringStatus",
    "SchedulerStatus"
]
