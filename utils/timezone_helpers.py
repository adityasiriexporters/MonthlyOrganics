
"""
Timezone utility functions for Monthly Organics
Handles conversion between UTC and Indian Standard Time (IST)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

class TimezoneHelper:
    """Helper class for timezone conversions"""
    
    @staticmethod
    def get_ist_now() -> datetime:
        """Get current time in IST"""
        return datetime.now(IST)
    
    @staticmethod
    def utc_to_ist(utc_datetime: datetime) -> datetime:
        """Convert UTC datetime to IST"""
        if utc_datetime is None:
            return None
            
        # If datetime is naive (no timezone), assume it's UTC
        if utc_datetime.tzinfo is None:
            utc_datetime = UTC.localize(utc_datetime)
        
        # Convert to IST
        return utc_datetime.astimezone(IST)
    
    @staticmethod
    def ist_to_utc(ist_datetime: datetime) -> datetime:
        """Convert IST datetime to UTC"""
        if ist_datetime is None:
            return None
            
        # If datetime is naive, assume it's IST
        if ist_datetime.tzinfo is None:
            ist_datetime = IST.localize(ist_datetime)
        
        # Convert to UTC
        return ist_datetime.astimezone(UTC)
    
    @staticmethod
    def format_ist_datetime(dt: datetime, format_string: str = "%d %b %Y, %I:%M %p") -> str:
        """Format datetime in IST with custom format"""
        if dt is None:
            return "N/A"
        
        # Convert to IST if needed
        ist_dt = TimezoneHelper.utc_to_ist(dt)
        return ist_dt.strftime(format_string)
    
    @staticmethod
    def format_ist_date(dt: datetime) -> str:
        """Format just the date part in IST"""
        return TimezoneHelper.format_ist_datetime(dt, "%d %b %Y")
    
    @staticmethod
    def format_ist_time(dt: datetime) -> str:
        """Format just the time part in IST"""
        return TimezoneHelper.format_ist_datetime(dt, "%I:%M %p")
