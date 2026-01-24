from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.jobs.queue import job_queue
from app.api import runs, leads, emails, export, providers, statistics

# Create FastAPI app
app = FastAPI(
    title="LeadGen API",
    description="Agentic lead generation and enrichment pipeline",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs.router)
app.include_router(leads.router)
app.include_router(emails.router)
app.include_router(export.router)
app.include_router(providers.router)
app.include_router(statistics.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and start job queue on startup."""
    print("Initializing database...")
    init_db()

    print("Starting job queue worker...")
    job_queue.start_worker()

    print("LeadGen API is ready!")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "LeadGen API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
