from typing import List, Dict
from app.providers.registry import ProviderRegistry
from app.providers.base import RawLead
import asyncio


class LeadCollector:
    """Tool to collect leads from all available providers."""

    async def collect(self, location: str, category: str) -> List[Dict]:
        """
        Collect leads from all available providers in parallel.

        Returns list of raw leads with provider provenance.
        """
        providers = ProviderRegistry.get_available_providers()

        if not providers:
            print("No providers available")
            return []

        print(f"Collecting leads from {len(providers)} providers: {[p.name for p in providers]}")

        # Run all providers in parallel
        tasks = [
            self._collect_from_provider(provider, location, category)
            for provider in providers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and add provenance
        all_leads = []
        for provider, result in zip(providers, results):
            if isinstance(result, Exception):
                print(f"Error from {provider.name}: {result}")
                continue

            for raw_lead in result:
                lead_dict = {
                    "business_name": raw_lead.business_name,
                    "address": raw_lead.address,
                    "latitude": raw_lead.latitude,
                    "longitude": raw_lead.longitude,
                    "phone": raw_lead.phone,
                    "website": raw_lead.website,
                    "email": raw_lead.email,
                    "source": provider.name,
                    "additional_data": raw_lead.additional_data or {},
                }
                all_leads.append(lead_dict)

        print(f"Collected {len(all_leads)} total leads")
        return all_leads

    async def _collect_from_provider(self, provider, location: str, category: str) -> List[RawLead]:
        """Collect from a single provider with error handling."""
        try:
            leads = await provider.search(location, category)
            print(f"{provider.name}: found {len(leads)} leads")
            return leads
        except Exception as e:
            print(f"{provider.name}: error - {e}")
            return []
