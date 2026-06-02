#!/usr/bin/env python3
import os
import time
import logging
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import cost_analyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="GCP Cost Analyzer App")

CACHE_PATH = "/tmp/gcp_cost_dashboard.html"
CACHE_DURATION_SEC = 24 * 60 * 60  # 24 hours cache lifetime

def get_user_email(request: Request) -> str:
    """
    Extracts the user email from Google Identity-Aware Proxy (IAP) headers.
    If IAP is not active (e.g. local testing), returns a default mock user.
    """
    # Header injected by IAP contains: "accounts.google.com:user@example.com"
    iap_user = request.headers.get("X-Goog-Authenticated-User-Email")
    if iap_user:
        # Strip the prefix "accounts.google.com:" or similar if present
        if ":" in iap_user:
            return iap_user.split(":")[-1]
        return iap_user
    
    # Fallback for local development
    return os.getenv("MOCK_USER_EMAIL", "user@example.com")

def is_cache_valid() -> bool:
    """Checks if the cached HTML report exists and is fresh."""
    if not os.path.exists(CACHE_PATH):
        return False
    
    file_age = time.time() - os.path.getmtime(CACHE_PATH)
    return file_age < CACHE_DURATION_SEC

def regenerate_cache(user_email: str) -> str:
    """Executes cost analysis, regenerates HTML, and saves it to the cache path."""
    logger.info(f"🔄 Regenerating cost analyzer dashboard for user: {user_email}")
    try:
        html_content = cost_analyzer.generate_dashboard_html(user_email=user_email)
        with open(CACHE_PATH, "w") as f:
            f.write(html_content)
        logger.info("✅ Dashboard cache regenerated successfully.")
        return html_content
    except Exception as e:
        logger.error(f"❌ Error generating dashboard: {str(e)}", exc_info=True)
        raise e

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    user_email = get_user_email(request)
    
    # If cache is valid, serve it directly (lightning fast!)
    if is_cache_valid():
        logger.info("Serving dashboard from local cache.")
        with open(CACHE_PATH, "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    
    # Otherwise, run BigQuery query and generate cache on-the-fly
    logger.info("Cache missing or expired. Regenerating...")
    try:
        html_content = regenerate_cache(user_email)
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h3>Error generating report: {str(e)}</h3></body></html>", 
            status_code=500
        )

@app.post("/refresh")
async def force_refresh(request: Request):
    """Manual refresh endpoint triggered by the 'Refresh Data' button in UI."""
    user_email = get_user_email(request)
    try:
        # Force regeneration
        regenerate_cache(user_email)
        return JSONResponse(content={"status": "success", "message": "Dashboard refreshed successfully."})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Refresh failed: {str(e)}"}, 
            status_code=500
        )

@app.get("/cron/refresh")
async def cron_refresh(request: Request):
    """
    Endpoint triggered automatically every day by Cloud Scheduler.
    Forces cache regeneration in the background.
    """
    # Security defense-in-depth: Verify it's called from Cloud Scheduler or App Engine / trusted origin
    # Cloud Scheduler requests contain User-Agent: "Google-Cloud-Scheduler"
    user_agent = request.headers.get("User-Agent", "")
    logger.info(f"Received cron refresh trigger. User-Agent: {user_agent}")
    
    user_email = get_user_email(request)
    try:
        regenerate_cache(user_email)
        return JSONResponse(content={"status": "success", "message": "Daily cron cache refresh complete."})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Cron refresh failed: {str(e)}"}, 
            status_code=500
        )

@app.get("/health")
async def health_check():
    """Simple health check for Cloud Run load balancers."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Listen on 127.0.0.1 for local security compliance during testing
    # In Docker it will listen on 0.0.0.0 as configured in uvicorn/Dockerfile command
    uvicorn.run(app, host="127.0.0.1", port=8080)
