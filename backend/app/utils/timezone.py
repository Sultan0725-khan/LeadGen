from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older Python versions if necessary, though 3.11 is used here
    from datetime import timezone, timedelta
    ZoneInfo = None

def get_german_now() -> datetime:
    """Get current time in Europe/Berlin timezone as a naive datetime (for SQLite/SQLAlchemy compatibility)."""
    if ZoneInfo:
        berlin_tz = ZoneInfo('Europe/Berlin')
        # Use replace(tzinfo=None) to make it naive but keep the local time values
        return datetime.now(berlin_tz).replace(tzinfo=None)
    else:
        # Basic fallback to GMT+1 if zoneinfo is missing (not ideal for DST)
        offset = timedelta(hours=1)
        return datetime.now(timezone(offset)).replace(tzinfo=None)

def get_utc_now() -> datetime:
    """Get current time in UTC as a naive datetime."""
    return datetime.utcnow()
