# Provider Management System

## Overview

The LeadGen system now has a centralized provider management system that allows you to:

- Control which data providers are enabled/disabled
- Manage API keys for all providers in one place
- Select which providers to use per run via the UI

## Configuration File

All provider settings are managed in:

```
backend/providers_config.yaml
```

### Structure

```yaml
providers:
  provider_id:
    enabled: true/false # Enable/disable this provider
    name: "Display Name" # Shown in UI
    description: "Description" # Provider info
    requires_api_key: true/false # Does it need an API key?
    api_key: "" # Your API key (if required)
    free_tier: true/false # Is there a free tier?
    daily_limit: "X requests/day" # Rate limit info
```

### Currently Configured Providers

| Provider      | Status      | API Key Required | Free Tier | Daily Limit              |
| ------------- | ----------- | ---------------- | --------- | ------------------------ |
| OpenStreetMap | ✅ Enabled  | No               | Yes       | Unlimited (rate limited) |
| Google Places | ❌ Disabled | Yes              | No        | Pay per use              |
| Geoapify      | ❌ Disabled | Yes              | Yes       | 3,000 requests/day       |
| TomTom        | ❌ Disabled | Yes              | Yes       | 2,500 requests/day       |
| MapQuest      | ❌ Disabled | Yes              | Yes       | 15,000 requests/month    |
| Yelp Fusion   | ❌ Disabled | Yes              | Yes       | 5,000 requests/day       |

## How to Enable a Provider

### 1. Get API Key (if required)

For providers that require an API key:

- **Geoapify**: Sign up at https://myprojects.geoapify.com/
- **TomTom**: Sign up at https://developer.tomtom.com/
- **MapQuest**: Sign up at https://developer.mapquest.com/
- **Yelp**: Sign up at https://www.yelp.com/developers
- **Google Places**: Enable in Google Cloud Console

### 2. Update Configuration

Edit `backend/providers_config.yaml`:

```yaml
providers:
  geoapify:
    enabled: true # Change to true
    api_key: "your-api-key-here" # Add your key
    # ... rest stays the same
```

### 3. Restart Backend

```bash
# The backend will automatically reload
# No additional steps needed
```

### 4. Verify in UI

Open the frontend - you should see the provider in the "Select Data Sources" section when creating a run.

## Using the UI

### Creating a Run

1. Fill in Location and Category
2. **Select Data Sources**: Check the providers you want to use
   - ✅ Green "FREE" badge = Free tier available
   - ℹ️ Blue "Disabled" badge = Provider is disabled in config
3. Configure other options (approval, dry run)
4. Click "Start Lead Generation"

### Provider Selection

- **Default**: All enabled providers are auto-selected
- **Custom**: Uncheck providers you don't want to use for this specific run
- **At least one required**: You must select at least one enabled provider

## Backend Integration

The system automatically:

- Loads configuration from `providers_config.yaml` on startup
- Exposes provider info via `/api/providers/` endpoint
- Only queries providers you selected in the UI
- Falls back to default providers if none specified

## Adding a New Provider

To add a new data provider:

1. **Create provider class** in `backend/app/providers/your_provider.py`:

```python
from app.providers.base import BaseProvider, RawLead

class YourProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Your Provider Name"

    async def search(self, location: str, category: str) -> List[RawLead]:
        # Implementation here
        pass

    def get_rate_limit(self) -> Tuple[int, int]:
        return (100, 60)  # 100 requests per 60 seconds
```

2. **Add to config** in `providers_config.yaml`:

```yaml
your_provider:
  enabled: false
  name: "Your Provider"
  description: "What it does"
  requires_api_key: true
  api_key: ""
  free_tier: true
  daily_limit: "X requests/day"
```

3. **Register** in `backend/app/providers/registry.py`:

```python
from app.providers.your_provider import YourProvider

class ProviderRegistry:
    _providers: List[Type[BaseProvider]] = [
        OSMOverpassProvider,
        GooglePlacesProvider,
        YourProvider,  # Add here
    ]
```

4. **Test**: Restart backend and verify it appears in the UI

## Benefits

✅ **Centralized Management**: All provider config in one file
✅ **Flexible**: Enable/disable providers without code changes
✅ **User Control**: Select providers per run
✅ **Safe**: API keys stored locally, not in code
✅ **Scalable**: Easy to add new providers

## Security Note

**Never commit `providers_config.yaml` with real API keys to version control!**

Add to `.gitignore`:

```
providers_config.yaml
```

Use `providers_config.yaml.example` as a template without real keys.
