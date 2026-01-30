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

    def _parse_address(self, lead: Any) -> Dict[str, str]:
        """Extract granular address parts (Street, City, Zip) from lead data."""
        addr_data = {
            "Street": lead.address or "",
            "City": "",
            "PostalCode": "",
            "Country": "Germany", # Default for LeadGen context
            "State": ""
        }

        # 1. Check for structured OSM data in enrichment_data
        tags = lead.enrichment_data.get("tags", {}) if lead.enrichment_data else {}
        if tags:
            street = tags.get("addr:street", "")
            hnr = tags.get("addr:housenumber", "")
            if street:
                addr_data["Street"] = f"{street} {hnr}".strip()
            if "addr:city" in tags:
                addr_data["City"] = tags["addr:city"]
            if "addr:postcode" in tags:
                addr_data["PostalCode"] = tags["addr:postcode"]
            if "addr:country" in tags:
                addr_data["Country"] = tags["addr:country"]
            if "addr:state" in tags:
                addr_data["State"] = tags["addr:state"]

            # If we got city and zip from tags, we are done
            if addr_data["City"] and addr_data["PostalCode"]:
                return addr_data

        # 2. Fallback: Parse the formatted address string
        # Expected format: "Street Housenumber, Zip City" or "Street, City, Zip"
        if lead.address and (not addr_data["City"] or not addr_data["PostalCode"]):
            parts = [p.strip() for p in lead.address.split(",")]

            if len(parts) >= 3:
                # "Street Hnr, City, Zip" or "Name, Street, City Zip"
                addr_data["Street"] = parts[0]
                addr_data["City"] = parts[1]
                addr_data["PostalCode"] = parts[2]
            elif len(parts) == 2:
                # "Street Hnr, Zip City"
                addr_data["Street"] = parts[0]
                second_part = parts[1]
                # Split Zip and City (German style: 10625 Berlin)
                subparts = second_part.split(" ", 1)
                if len(subparts) == 2 and subparts[0].isdigit():
                    addr_data["PostalCode"] = subparts[0]
                    addr_data["City"] = subparts[1]
                else:
                    addr_data["City"] = second_part

        return addr_data

    async def prepare_lead_payload(self, lead: Any, email_record: Any = None) -> Dict:
        """Centralized mapping from Lead/Email models to Salesforce Lead fields."""
        social_links = lead.enrichment_data.get("social_links", {}) if lead.enrichment_data else {}
        addr_data = self._parse_address(lead)

        return {
            "FirstName": lead.first_name or "",
            "LastName": lead.last_name or lead.business_name,
            "Company": lead.business_name,
            "Street": addr_data["Street"],
            "City": addr_data["City"],
            "PostalCode": addr_data["PostalCode"],
            "Country": addr_data["Country"],
            "State": addr_data["State"],
            "Email": lead.email,
            "Website": lead.website,
            "Phone": lead.phone,
            "LeadSource": ", ".join(lead.sources) if lead.sources else "Byte2Bite",
            "B2B_TF_NotesInLeadGen__c": lead.notes,
            "B2B_URL_Instagram__c": social_links.get("instagram"),
            "B2B_URL_TikTok__c": social_links.get("tiktok"),
            "B2B_URL_Facebook__c": social_links.get("facebook"),
            "B2B_URL_LinkedIn__c": social_links.get("linkedin"),
            "B2B_URL_Twitter__c": social_links.get("twitter"),
            "B2B_NF_ConfidenceScore__c": lead.confidence_score,
            "B2B_TF_EmailStatus__c": email_record.status.value if email_record else "none",
            "B2B_TF_EmailError__c": email_record.error_message if email_record else None,
            "B2B_DT_EmailDraftedDate__c": email_record.generated_at.isoformat() if email_record and email_record.generated_at else None,
            "B2B_DT_EmailSentDate__c": email_record.sent_at.isoformat() if email_record and email_record.sent_at else None,
        }

    async def upsert_lead_by_email(self, payload: Dict, email_content: Optional[Dict] = None) -> Dict:
        """
        Upsert a lead in Salesforce by email and optionally attach an email body as a File.

        Args:
            payload: The Salesforce Lead payload (already mapped)
            email_content: Optional dict with 'subject' and 'body' to attach as a File (ContentVersion)
        """
        email = payload.get("Email")
        if not email:
            raise ValueError("Email is required for Salesforce upsert")

        # Check for existing lead
        query = f"SELECT Id FROM Lead WHERE Email = '{email}' LIMIT 1"
        res = await self._request("GET", f"query?q={query}")
        records = res.get("records", [])

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
