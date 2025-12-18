"""
Watchlist model - Tracks which stocks are actively monitored
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, String, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from src.database.connection import Base


class MonitoringStatus(str, enum.Enum):
    """Monitoring status enumeration"""
    active = "active"
    paused = "paused"


class Watchlist(Base):
    """
    Watchlist entity - Tracks which stocks are actively monitored for scraping
    
    Corresponds to spec.md Key Entities: Watchlist
    """
    __tablename__ = "watchlist"

    # Primary Key
    watchlist_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    stock_id = Column(
        Integer,
        ForeignKey('stock.stock_id', ondelete='CASCADE'),
        nullable=False,
        unique=True  # Each stock can only appear once in watchlist
    )
    
    # Timestamp
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Monitoring Configuration
    monitoring_status = Column(
        Enum(MonitoringStatus, name="monitoring_status"),
        default=MonitoringStatus.active,
        nullable=False
    )
    
    # Additional fields
    notes = Column(String)
    
    # Relationship
    stock = relationship("Stock", backref="watchlist_entry")
    
    # Indexes
    __table_args__ = (
        Index('idx_watchlist_stock', 'stock_id'),
        Index('idx_watchlist_monitoring', 'monitoring_status'),
        UniqueConstraint('stock_id', name='uq_watchlist_stock'),
    )
    
    def __repr__(self):
        return (
            f"<Watchlist("
            f"stock_id={self.stock_id}, "
            f"monitoring_status='{self.monitoring_status.value}', "
            f"added_at='{self.added_at}'"
            f")>"
        )
