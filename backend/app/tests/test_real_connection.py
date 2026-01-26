import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.salesforce import salesforce_service
from app.config import settings

async def test_real_connection():
    print("--- Salesforce Connection Test ---")
    load_dotenv()

    # Check if we have credentials
    if not settings.sfdc_client_id or not settings.sfdc_client_secret:
        print("Error: Missing Salesforce credentials (Client ID or Secret) in .env")
        return

    try:
        print(f"Attempting Client Credentials Login...")

        token = await salesforce_service._get_access_token()
        print("✅ Successfully authenticated!")
        print(f"Access Token retrieved (first 10 chars): {token[:10]}...")

        # Test a dummy upsert
        test_lead = {
            "FirstName": "Test",
            "LastName": "Integration",
            "Company": "Byte2Bite Test",
            "Email": "test-integration@example.com",
            "Phone": "123456789",
            "Notes": "Auto-generated test lead from LeadGen App Integration Test."
        }

        print(f"\nAttempting to upsert test lead: {test_lead['Email']}")
        result = await salesforce_service.upsert_lead_by_email(test_lead)
        print(f"✅ Lead {result['status']} successfully!")
        print(f"Salesforce ID: {result['id']}")

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_real_connection())
