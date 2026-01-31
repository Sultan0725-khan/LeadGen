from typing import List, Dict, Tuple
from app.providers.registry import ProviderRegistry
from app.providers.base import RawLead
from app.provider_config import provider_config
import asyncio


class LeadCollector:
    """Tool to collect leads from all available providers."""

    async def collect(
        self,
        location: str,
        category: str,
        selected_providers: List[str] = None,
        provider_limits: Dict[str, int] = None
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Collect leads from all available providers in parallel.

        Returns tuple of (list of leads, dict of provider usage).
        """
        print(f"[LeadCollector] Starting collection for location='{location}', category='{category}'")

        # Determine which providers to use
        if not selected_providers:
            selected_providers = provider_config.get_default_providers()
            print(f"[LeadCollector] No providers selected, using defaults: {selected_providers}")

        providers = ProviderRegistry.get_available_providers(selected_providers)

        print(f"[LeadCollector] ProviderRegistry returned {len(providers) if providers else 0} providers")
        if providers:
            print(f"[LeadCollector] Provider names: {[p.name for p in providers]}")

        if not providers:
            print("[LeadCollector] ERROR: No providers available!")
            return [], {}

        print(f"Collecting leads from {len(providers)} providers: {[p.name for p in providers]}")

        # Run all providers in parallel
        tasks = [
            self._collect_from_provider(
                provider,
                location,
                category,
                limit=provider_limits.get(provider.id) if provider_limits else None
            )
            for provider in providers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and add provenance
        all_leads = []
        usage_info = {}

        for provider, result in zip(providers, results):
            if isinstance(result, Exception):
                print(f"[LeadCollector] ERROR from {provider.name}: {result}")
                import traceback
                traceback.print_exc()
                continue

            # Unpack search result and credits
            leads_from_provider, provider_credits = result
            usage_info[provider.id] = provider_credits

            limit = provider_limits.get(provider.id) if provider_limits else None
            if limit and len(leads_from_provider) > limit:
                leads_from_provider = leads_from_provider[:limit]

            for raw_lead in leads_from_provider:
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
        return all_leads, usage_info

    async def _collect_from_provider(self, provider, location: str, category: str, limit: int = None) -> Tuple[List[RawLead], int]:
        """Collect from a single provider with error handling."""
        actual_limit = limit or 100
        print(f"[LeadCollector] Calling {provider.name}.search(location='{location}', category='{category}', limit={actual_limit})")
        try:
            kwargs = {}
            if limit:
                kwargs["limit"] = limit

            leads = await provider.search(location, category, **kwargs)

            # Calculate credits consumed
            # Note: We use actual_limit for calculation since API call was made with it
            # or we could use len(leads) if the provider charges per returned result.
            # Geoapify charges per limit/returned results.
            credits = provider.calculate_credits(limit=actual_limit, count=len(leads))

            print(f"[LeadCollector] {provider.name}: found {len(leads)} leads, cost {credits} credits")
            return leads, credits
        except Exception as e:
            print(f"{provider.name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            return [], 0
