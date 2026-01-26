import pytest
import respx
from httpx import Response
from app.services.salesforce import SalesforceService
from app.config import settings

# Mock settings for testing
settings.sfdc_client_id = "test_id"
settings.sfdc_client_secret = "9C3C5A1E860B4C90B5D91657C44E7111082568C3065CFE66E4D28A7222CF7977"
settings.sfdc_username = "test_user"
settings.sfdc_password = "test_password"
settings.sfdc_security_token = "test_token"
settings.sfdc_instance_url = "https://test.salesforce.com"
settings.sfdc_is_sandbox = True

@pytest.mark.asyncio
@respx.mock
async def test_salesforce_auth():
    service = SalesforceService()

    # Mock auth response
    respx.post("https://test.salesforce.com/services/oauth2/token").mock(return_value=Response(200, json={
        "access_token": "mock_token",
        "instance_url": "https://mock.salesforce.com"
    }))

    token = await service._get_access_token()
    assert token == "mock_token"
    assert service.instance_url == "https://mock.salesforce.com"

@pytest.mark.asyncio
@respx.mock
async def test_upsert_lead_create():
    service = SalesforceService()
    service.access_token = "mock_token"
    service.instance_url = "https://mock.salesforce.com"

    # Mock query response (no lead found)
    respx.get("https://mock.salesforce.com/services/data/v59.0/query?q=SELECT Id FROM Lead WHERE Email = 'test@example.com' LIMIT 1").mock(return_value=Response(200, json={
        "totalSize": 0,
        "records": []
    }))

    # Mock create response
    respx.post("https://mock.salesforce.com/services/data/v59.0/sobjects/Lead").mock(return_value=Response(201, json={
        "id": "new_lead_id",
        "success": True
    }))

    lead_data = {
        "FirstName": "Test",
        "LastName": "User",
        "Company": "Test Co",
        "Email": "test@example.com"
    }

    result = await service.upsert_lead_by_email(lead_data)
    assert result["id"] == "new_lead_id"
    assert result["status"] == "created"

@pytest.mark.asyncio
@respx.mock
async def test_upsert_lead_update():
    service = SalesforceService()
    service.access_token = "mock_token"
    service.instance_url = "https://mock.salesforce.com"

    # Mock query response (lead found)
    respx.get("https://mock.salesforce.com/services/data/v59.0/query?q=SELECT Id FROM Lead WHERE Email = 'test@example.com' LIMIT 1").mock(return_value=Response(200, json={
        "totalSize": 1,
        "records": [{"Id": "existing_lead_id"}]
    }))

    # Mock update response
    respx.patch("https://mock.salesforce.com/services/data/v59.0/sobjects/Lead/existing_lead_id").mock(return_value=Response(204))

    lead_data = {
        "FirstName": "Updated",
        "LastName": "User",
        "Company": "Test Co",
        "Email": "test@example.com"
    }

    result = await service.upsert_lead_by_email(lead_data)
    assert result["id"] == "existing_lead_id"
    assert result["status"] == "updated"


