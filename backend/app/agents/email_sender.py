from typing import Optional
from datetime import datetime
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.models import OptOut
from sqlalchemy.orm import Session
import asyncio
from collections import deque


class EmailSender:
    """Tool to send emails with compliance features."""

    def __init__(self):
        self._rate_limiter = RateLimiter(settings.max_emails_per_minute)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        db: Session,
        dry_run: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Send email with compliance checks.

        Returns (success: bool, error_message: Optional[str])
        """
        # Check opt-out list
        if self._is_opted_out(to_email, db):
            return False, "Email is on opt-out list"

        # Dry run mode
        if dry_run:
            print(f"[DRY RUN] Would send email to {to_email}")
            print(f"Subject: {subject}")
            print(f"Body preview: {body[:100]}...")
            return True, None

        # Rate limiting
        await self._rate_limiter.acquire()

        # Send via SMTP
        try:
            await self._send_smtp(to_email, subject, body)
            print(f"Sent email to {to_email}")
            return True, None
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            print(error_msg)
            return False, error_msg

    def _is_opted_out(self, email: str, db: Session) -> bool:
        """Check if email is on opt-out list."""
        exists = db.query(OptOut).filter(OptOut.email == email.lower()).first()
        return exists is not None

    async def _send_smtp(self, to_email: str, subject: str, body: str):
        """Send email via SMTP."""
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Add body
        text_part = MIMEText(body, "plain", "utf-8")
        message.attach(text_part)

        # Send via SMTP
        if settings.smtp_host and settings.smtp_username and settings.smtp_password:
            # Zoho and other providers often require SSL on 465 or STARTTLS on 587
            use_tls = (settings.smtp_port == 465)
            start_tls = (settings.smtp_port == 587)

            try:
                await aiosmtplib.send(
                    message,
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    username=settings.smtp_username,
                    password=settings.smtp_password,
                    use_tls=use_tls,
                    start_tls=start_tls,
                    timeout=30.0
                )
            except Exception as e:
                # Catch specific auth errors to provide better feedback
                if "535" in str(e):
                    raise ValueError(f"SMTP Authentication Failed: Check your username/password. For Zoho/Gmail, ensure you use an 'App Password' if 2FA is enabled. Details: {e}")
                raise e
        else:
            raise ValueError("SMTP credentials not configured in .env")

    def add_to_optout(self, email: str, db: Session):
        """Add email to opt-out list."""
        existing = db.query(OptOut).filter(OptOut.email == email.lower()).first()
        if not existing:
            optout = OptOut(email=email.lower())
            db.add(optout)
            db.commit()
            print(f"Added {email} to opt-out list")


class RateLimiter:
    """Token bucket rate limiter for email sending."""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.timestamps = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to send (blocks if rate limit exceeded)."""
        async with self.lock:
            now = datetime.now()

            # Remove timestamps older than 1 minute
            cutoff = now.timestamp() - 60
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()

            # Check if we've hit the limit
            if len(self.timestamps) >= self.max_per_minute:
                # Calculate sleep time
                oldest = self.timestamps[0]
                sleep_time = 60 - (now.timestamp() - oldest)
                if sleep_time > 0:
                    print(f"Rate limit reached, sleeping for {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                    # Clear old timestamps after sleep
                    self.timestamps.clear()

            # Add current timestamp
            self.timestamps.append(now.timestamp())
