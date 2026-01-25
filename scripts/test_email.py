import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.agents.email_sender import EmailSender
from app.database import SessionLocal, init_db

async def test_email(to_email):
    print(f"Sending test email to: {to_email}")
    init_db()
    sender = EmailSender()
    db = SessionLocal()

    subject = "LeadGen Pipeline Test Email"
    body = """
Hello,

This is a test email from your LeadGen Pipeline system.
If you receive this, it means your Zoho SMTP, SPF, DKIM, and DMARC settings are working correctly!

Domain: byte2bite.de
From: info@byte2bite.de

Best regards,
LeadGen Bot
    """

    try:
        success, error = await sender.send_email(to_email, subject, body, db)
        if success:
            print("✅ Email sent successfully!")
        else:
            print(f"❌ Failed to send email: {error}")
    finally:
        db.close()

if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else "paravanto89@gmail.com"
    asyncio.run(test_email(target_email))
