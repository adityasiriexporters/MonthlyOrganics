"""
Timezone utilities for Indian Standard Time (IST) handling
Provides consistent timezone conversion and formatting across the application
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

logger = logging.getLogger(__name__)

# IST is UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

class TimezoneHelper:
    """Helper class for IST timezone operations"""
    
    @staticmethod
    def utc_to_ist(utc_datetime: Optional[datetime]) -> Optional[datetime]:
        """Convert UTC datetime to IST"""
        if not utc_datetime:
            return None
            
        try:
            # If datetime is naive (no timezone), assume it's UTC
            if utc_datetime.tzinfo is None:
                utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
            
            # Convert to IST
            ist_datetime = utc_datetime.astimezone(IST)
            return ist_datetime
            
        except Exception as e:
            logger.error(f"Error converting UTC to IST: {e}")
            return utc_datetime
    
    @staticmethod
    def format_ist_datetime(dt: Optional[datetime], format_type: str = "full") -> str:
        """
        Format datetime in IST with specified format
        
        Args:
            dt: datetime object (can be UTC or IST)
            format_type: "full" for "07 Jan 2025, 06:24 PM", "date" for "07 Jan 2025", "time" for "06:24 PM"
        """
        if not dt:
            return "Not available"
            
        try:
            # Convert to IST if needed
            ist_dt = TimezoneHelper.utc_to_ist(dt)
            if not ist_dt:
                return "Not available"
            
            if format_type == "full":
                # Format: "07 Jan 2025, 06:24 PM"
                return ist_dt.strftime("%d %b %Y, %I:%M %p")
            elif format_type == "date":
                # Format: "07 Jan 2025"
                return ist_dt.strftime("%d %b %Y")
            elif format_type == "time":
                # Format: "06:24 PM"
                return ist_dt.strftime("%I:%M %p")
            else:
                # Default to full format
                return ist_dt.strftime("%d %b %Y, %I:%M %p")
                
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return "Invalid date"
    
    @staticmethod
    def now_ist() -> datetime:
        """Get current datetime in IST"""
        return datetime.now(IST)
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current datetime in UTC (for database storage)"""
        return datetime.now(timezone.utc)

# Convenience functions for template use
def format_datetime_ist(dt: Optional[datetime]) -> str:
    """Template helper: Format datetime as '07 Jan 2025, 06:24 PM' in IST"""
    return TimezoneHelper.format_ist_datetime(dt, "full")

def format_date_ist(dt: Optional[datetime]) -> str:
    """Template helper: Format date as '07 Jan 2025' in IST"""
    return TimezoneHelper.format_ist_datetime(dt, "date")

def format_time_ist(dt: Optional[datetime]) -> str:
    """Template helper: Format time as '06:24 PM' in IST"""
    return TimezoneHelper.format_ist_datetime(dt, "time")