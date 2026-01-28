# LeadGen Pipeline

An intelligent, agentic lead generation and enrichment system with automated outreach capabilities.

## 🎯 Features

- **Multi-source lead collection** from OpenStreetMap and Google Places
- **Intelligent deduplication** with fuzzy matching
- **Website enrichment** (emails, phones, social profiles)
- **AI-powered email personalization** using OpenAI
- **Compliance-first** with opt-out lists, rate limiting, and dry-run mode
- **Modern web dashboard** for monitoring and management
- **CSV export** for easy data analysis

## 🏗️ Architecture

### Backend (Python + FastAPI)

- **Agentic Tools**: LeadCollector, Normalizer, Enricher, Scorer, EmailWriter, EmailSender
- **Provider System**: Pluggable connectors for lead sources (OSM, Google Places, Yelp)
- **Job Queue**: Async background processing
- **Database**: SQLite with SQLAlchemy ORM
- **API**: RESTful endpoints with automatic documentation

### Frontend (React + TypeScript)

- **Modern UI**: Dark theme with glassmorphism and gradients
- **Components**: Run creation form, runs list, leads table
- **Real-time updates**: Polling for run status
- **Export**: One-click CSV download

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (required)
- Google Places API key (optional)

## 🚀 Quick Start

### 1. Backend Setup

````bash
cd LeadGen/backend

# Create virtual environment
python -m venv venv

#################### Activate the virtual environment ####################
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

#################### Start the server ####################
uvicorn app.main:app --reload
```## Salesforce Integration

The LeadGen app can send drafted leads to a Salesforce instance.

### Configuration
Update `backend/.env` with your Salesforce credentials:
- `SFDC_CLIENT_ID`: Consumer Key
- `SFDC_CLIENT_SECRET`: Consumer Secret
- `SFDC_INSTANCE_URL`: Salesforce Instance URL
- `SFDC_IS_SANDBOX`: `true` for Playground/Sandbox, `false` for Production

> [!TIP]
> This integration uses the **OAuth 2.0 Client Credentials Flow**. You do **not** need to provide a username or password in the `.env` file. Ensure that the "Client Credentials Flow" is enabled in your External Client App policies and an execution user is assigned.

### Usage
1. Go to the **Drafted Emails** tab.
2. Click **Mark for Mail** to enter selection mode.
3. Select the leads you want to send.
4. Click **Send to Salesforce**.

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd LeadGen/frontend

# Install dependencies
npm install

#################### Start development server ####################
npm run dev
````

The dashboard will be available at `http://localhost:5173`

## 🔑 Configuration

Edit `backend/.env` with your credentials:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (for Google Places provider)
GOOGLE_PLACES_API_KEY=AIza...

# Email sending (configure SMTP OR SendGrid)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Application settings
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Your Company
MAX_EMAILS_PER_MINUTE=10
DEFAULT_LANGUAGE=DE
```

## 📖 Usage

1. **Start a Run**: Enter location (e.g., "Berlin, Mitte") and category (e.g., "restaurant")
2. **Monitor Progress**: Watch the run status change from queued → running → completed
3. **Review Leads**: Click "View Leads" to see collected businesses with enrichment data
4. **Export Data**: Download leads as CSV for further analysis

### Run Options

- **Require Approval**: Emails need manual approval before sending
- **Dry Run**: Generate emails but don't actually send them (for testing)

## 🛠️ Development

### Backend Structure

```
backend/app/
├── agents/          # Agentic tools (collector, enricher, etc.)
├── providers/       # Lead source connectors
├── enrichment/      # Website crawling and extraction
├── models/          # Database models
├── api/             # API endpoints
└── main.py          # FastAPI app
```

### Frontend Structure

```
frontend/src/
├── components/      # React components
├── api/             # API client
└── App.tsx          # Main application
```

## 🔒 Compliance Features

- **Opt-out List**: Persistent blacklist for unsubscribe requests
- **Rate Limiting**: Configurable email throttling (default: 10/minute)
- **Dry Run Mode**: Test email generation without sending
- **robots.txt Respect**: Website crawler checks permissions
- **Data Provenance**: Track which provider each field came from

## 📊 API Endpoints

- `POST /api/runs/` - Create new run
- `GET /api/runs/` - List all runs
- `GET /api/leads/run/{run_id}` - Get leads for run
- `POST /api/emails/{email_id}/approve` - Approve email
- `GET /api/export/run/{run_id}/csv` - Export to CSV
- `GET /api/export/run/{run_id}/logs` - Get run logs

Full API documentation: `http://localhost:8000/docs`

## 🎨 UI Features

- **Premium Design**: Dark theme with vibrant gradients
- **Glassmorphism**: Modern card designs with backdrop blur
- **Confidence Scoring**: Color-coded lead quality indicators
- **Source Tracking**: See which providers found each lead
- **Social Profiles**: Display Instagram, Facebook, LinkedIn links

## ⚠️ Important Notes

- **OpenStreetMap**: Free, no API key required, ~2 requests/second
- **Google Places**: Requires API key, costs apply after free tier
- **Email Sending**: Configure SMTP (Gmail, etc.) or use SendGrid
- **Personal Emails**: System warns about @gmail.com, @yahoo.com domains

## 🔄 Adding New Providers

Create a new provider in `backend/app/providers/`:

```python
from app.providers.base import BaseProvider, RawLead

class MyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "MyProvider"

    async def search(self, location: str, category: str) -> List[RawLead]:
        # Implement search logic
        pass

    def get_rate_limit(self) -> Tuple[int, int]:
        return (10, 1)  # 10 requests per second
```

Register in `backend/app/providers/registry.py`

## 🐛 Troubleshooting

- **Database locked**: Only one backend instance can run at a time with SQLite
- **CORS errors**: Ensure frontend runs on `localhost:5173` or update CORS in `main.py`
- **Import errors**: Activate virtual environment: `source venv/bin/activate`
- **API key errors**: Check `.env` file exists and has valid keys

## 📝 License

MIT License - feel free to use for your projects!

## 🙏 Credits

Built with:

- FastAPI, SQLAlchemy, OpenAI, BeautifulSoup
- React, TypeScript, Vite
- Love and lots of coffee ☕

---

**Happy Lead Generating! 🚀**
