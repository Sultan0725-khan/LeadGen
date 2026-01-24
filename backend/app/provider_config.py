import yaml
from pathlib import Path
from typing import Dict, List, Optional


class ProviderConfig:
    """Manages provider configuration from YAML file."""

    def __init__(self, config_path: str = "providers_config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            print(f"Warning: {self.config_path} not found, using defaults")
            return self._get_default_config()

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> dict:
        """Return default configuration."""
        return {
            "providers": {
                "openstreetmap": {
                    "enabled": True,
                    "name": "OpenStreetMap",
                    "requires_api_key": False
                }
            },
            "default_providers": ["openstreetmap"],
            "settings": {
                "max_parallel_providers": 5,
                "retry_on_failure": True,
                "max_retries": 2
            }
        }

    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider IDs."""
        providers = self._config.get("providers", {})
        return [
            provider_id
            for provider_id, config in providers.items()
            if config.get("enabled", False)
        ]

    def get_provider_config(self, provider_id: str) -> Optional[Dict]:
        """Get configuration for a specific provider."""
        return self._config.get("providers", {}).get(provider_id)

    def is_provider_enabled(self, provider_id: str) -> bool:
        """Check if provider is enabled."""
        config = self.get_provider_config(provider_id)
        return config.get("enabled", False) if config else False

    def get_api_key(self, provider_id: str) -> Optional[str]:
        """Get API key for provider."""
        config = self.get_provider_config(provider_id)
        if not config:
            return None

        api_key = config.get("api_key", "")
        return api_key if api_key else None

    def get_all_providers_info(self, usage_data: Optional[Dict[str, int]] = None) -> List[Dict]:
        """Get info about all providers for UI display.

        Args:
            usage_data: Optional dict of provider_id -> current usage count
        """
        providers_info = []
        for provider_id, config in self._config.get("providers", {}).items():
            quota_limit = config.get("quota_limit", 0)
            quota_used = usage_data.get(provider_id, 0) if usage_data else 0
            quota_available = max(0, quota_limit - quota_used) if quota_limit > 0 else 999999

            providers_info.append({
                "id": provider_id,
                "name": config.get("name", provider_id),
                "description": config.get("description", ""),
                "enabled": config.get("enabled", False),
                "requires_api_key": config.get("requires_api_key", False),
                "free_tier": config.get("free_tier", False),
                "daily_limit": config.get("daily_limit", "Unknown"),
                "quota_limit": quota_limit,
                "quota_used": quota_used,
                "quota_period": config.get("quota_period", "daily"),
                "quota_available": quota_available,
                "query_limit": config.get("query_limit", 100),
                "statistics_url": config.get("statistics_url", None)
            })
        return providers_info

    def get_default_providers(self) -> List[str]:
        """Get default provider IDs to use."""
        return self._config.get("default_providers", ["openstreetmap"])

    def get_settings(self) -> Dict:
        """Get global settings."""
        return self._config.get("settings", {})


# Global instance
provider_config = ProviderConfig()
