import httpx
import logging
from typing import Dict, Any, Optional
from app.config import settings
from app.utils.pretty_logger import PrettyLogger

logger = logging.getLogger(__name__)

class SalesforceService:
    def __init__(self):
        self.client_id = settings.sfdc_client_id
        self.client_secret = settings.sfdc_client_secret
        self.username = settings.sfdc_username
        self.password = settings.sfdc_password
        self.security_token = settings.sfdc_security_token
        self.instance_url = settings.sfdc_instance_url
        self.is_sandbox = settings.sfdc_is_sandbox

        self.access_token = None
        self.api_version = "v59.0"

    async def _get_access_token(self) -> str:
        """Authenticate and get an access token using Client Credentials flow (modern)."""
        if self.access_token:
            return self.access_token

        # Use My Domain or login/test URLs for authentication
        base_urls = ["https://login.salesforce.com", "https://test.salesforce.com"]
        if self.instance_url:
            base_urls.insert(0, self.instance_url.rstrip('/'))

        last_error = "Unknown error"
        for base_url in base_urls:
            target_url = f"{base_url}/services/oauth2/token"
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(target_url, data=payload)
                    if response.status_code == 200:
                        data = response.json()
                        self.access_token = data["access_token"]
                        if "instance_url" in data:
                            self.instance_url = data["instance_url"]
                        logger.info(f"Successfully authenticated via {target_url}")
                        return self.access_token
                    else:
                        last_error = response.json().get('error_description', response.text)
                        logger.warning(f"Auth failed for {target_url}: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Request error for {target_url}: {last_error}")

        raise Exception(f"Salesforce Auth Failed (Client Credentials): {last_error}")

    async def _request(self, method: str, path: str, data: Optional[Dict] = None, is_retry: bool = False) -> Dict:
        """Make an authenticated request to Salesforce API."""
        token = await self._get_access_token()

        # Ensure instance_url doesn't have trailing slash for consistency
        base_url = self.instance_url.rstrip('/')
        url = f"{base_url}/services/data/{self.api_version}/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Detailed debug logging for the request
        PrettyLogger.log_request("Salesforce", method, url, data)

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, json=data)

            try:
                res_body = response.json() if response.content else {}
            except:
                res_body = response.text

            PrettyLogger.log_response("Salesforce", response.status_code, res_body)

            # Handle token expiration
            if response.status_code == 401 and not is_retry:
                logger.warning("Salesforce access token expired. Refreshing...")
                self.access_token = None
                return await self._request(method, path, data, is_retry=True)

            if response.status_code >= 400:
                logger.error(f"Salesforce request failed ({method} {path}): {response.text}")
                # Try to extract a meaningful error
                try:
                    err_data = response.json()
                    if isinstance(err_data, list) and len(err_data) > 0:
                        detail = err_data[0].get('message', response.text)
                    else:
                        detail = err_data.get('message', response.text)
                except:
                    detail = response.text
                raise Exception(f"Salesforce Error: {detail}")

            return response.json() if response.content else {}

    async def attach_email_as_file(self, lead_id: str, subject: str, body: str) -> str:
        """
        Attach an email body to a Lead as a ContentVersion (File).
        """
        import base64

        # 1. Create ContentVersion
        # FirstPublishLocationId links it directly to the Lead
        content_version_payload = {
            "Title": subject,
            "PathOnClient": f"Drafted_Email_{lead_id}.txt",
            "VersionData": base64.b64encode(body.encode('utf-8')).decode('utf-8'),
            "FirstPublishLocationId": lead_id
        }

        try:
            res = await self._request("POST", "sobjects/ContentVersion", content_version_payload)
            return res.get("id")
        except Exception as e:
            logger.error(f"Failed to attach email to Lead {lead_id}: {str(e)}")
            return None

    async def upsert_lead_by_email(self, lead_data: Dict[str, Any], email_content: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Upsert a lead by looking up the email first.
        If lead exists, update it. Otherwise create it.
        If email_content is provided, attach it as a file.
        """
        email = lead_data.get("Email")
        if not email:
            raise ValueError("Email is required for Salesforce lead upsert")

        # Query for existing lead
        q = f"SELECT Id FROM Lead WHERE Email = '{email}' LIMIT 1"
        query_path = f"query?q={q}"
        query_res = await self._request("GET", query_path)

        records = query_res.get("records", [])

        payload = {
            "FirstName": lead_data.get("FirstName"),
            "LastName": lead_data.get("LastName") or "LeadGen",
            "Company": lead_data.get("Company") or "Individual",
            "Email": lead_data.get("Email"),
            "Website": lead_data.get("Website"),
            "Phone": lead_data.get("Phone"),
            "LeadSource": lead_data.get("LeadSource", "Byte2Bite"),
            "Description": lead_data.get("Notes")
        }

        if records:
            lead_id = records[0]["Id"]
            await self._request("PATCH", f"sobjects/Lead/{lead_id}", payload)
            result = {"id": lead_id, "status": "updated"}
        else:
            res = await self._request("POST", "sobjects/Lead", payload)
            lead_id = res.get("id")
            result = {"id": lead_id, "status": "created"}

        # If email content is provided, attach it to the (new or existing) lead
        if lead_id and email_content:
            await self.attach_email_as_file(
                lead_id,
                email_content.get("subject", "Drafted Email"),
                email_content.get("body", "")
            )
            result["attachment"] = "success"

        return result

salesforce_service = SalesforceService()
