# LeadGen Pipeline

A complete agentic lead generation and enrichment system with AI-powered outreach.

## Project Overview

This system automates the entire lead generation workflow:

1. **Collection**: Queries multiple data sources (OSM, Google Places) for businesses
2. **Normalization**: Deduplicates and merges data from different providers
3. **Enrichment**: Crawls websites to extract emails, phones, and social profiles
4. **Scoring**: Calculates confidence scores based on data completeness
5. **Personalization**: Generates custom outreach emails using AI
6. **Sending**: Delivers emails with full compliance features
7. **Dashboard**: Provides web UI for monitoring and management

## Technology Stack

**Backend**:

- Python 3.11+ with FastAPI
- SQLAlchemy ORM with SQLite
- OpenAI API for email generation
- Beautiful Soup for web scraping
- Async job queue for background processing

**Frontend**:

- React 18 with TypeScript
- Vite for fast development
- Modern CSS with glassmorphism
- Responsive design

## Key Features

✅ **Multi-source lead collection** (OpenStreetMap, Google Places, extensible)
✅ **Intelligent fuzzy deduplication** (name + address + coordinates)
✅ **Website enrichment** with robots.txt compliance
✅ **AI-powered personalization** (German & English support)
✅ **Email compliance** (opt-out, rate limiting, dry-run)
✅ **Data provenance tracking** (know where each field came from)
✅ **Premium dark-themed dashboard** with real-time updates
✅ **CSV export** for easy integration

## Quick Start

See [README.md](./README.md) for detailed setup instructions.

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your API keys
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to access the dashboard.

## Architecture

The system follows an agentic architecture with specialized tools:

- **LeadCollector**: Aggregates results from all providers
- **Normalizer**: Deduplicates using fuzzy matching
- **Enricher**: Extracts contact data from websites
- **Scorer**: Calculates lead quality metrics
- **EmailWriter**: Generates personalized emails with AI
- **EmailSender**: Handles delivery with compliance

All tools are orchestrated by the `AgentOrchestrator` which manages the end-to-end workflow.

## Project Structure

```
LeadGen/
├── backend/
│   ├── app/
│   │   ├── agents/          # Agentic tools
│   │   ├── providers/       # Data source connectors
│   │   ├── enrichment/      # Website crawling
│   │   ├── models/          # Database models
│   │   ├── api/             # API endpoints
│   │   └── main.py          # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── api/             # API client
│   │   └── App.tsx          # Main app
│   └── package.json
└── README.md
```

## Contributing

To add a new provider:

1. Create `backend/app/providers/your_provider.py` implementing `BaseProvider`
2. Register in `backend/app/providers/registry.py`
3. Add API key to `.env.example` if needed

## License

MIT - See LICENSE file for details
