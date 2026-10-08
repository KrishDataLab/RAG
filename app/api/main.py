from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health, documents, query, extraction, comparison, findings, reports

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Evidence-grounded AI engineering assistant for AUTOSAR HLD analysis"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base API v1 prefix
api_prefix = "/api/v1"

app.include_router(health.router, prefix=api_prefix, tags=["Health"])
app.include_router(documents.router, prefix=api_prefix, tags=["Documents"])
app.include_router(query.router, prefix=api_prefix, tags=["RAG Q&A"])
app.include_router(extraction.router, prefix=api_prefix, tags=["Architecture Intelligence"])
app.include_router(comparison.router, prefix=api_prefix, tags=["Revision Comparison"])
app.include_router(findings.router, prefix=api_prefix, tags=["Findings & Review"])
app.include_router(reports.router, prefix=api_prefix, tags=["Evaluation & Reports"])

@app.get("/")
def root():
    return {
        "message": "Welcome to AUTOSAR HLD Intelligence & Traceability Assistant (AHITA) API",
        "docs_url": "/docs",
        "health_url": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)
