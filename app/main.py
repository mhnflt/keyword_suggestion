from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from app.routers import main
from app.services.google_service import router as google_router  # Add this

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(main.router)
app.include_router(google_router)

__all__ = ["app"]
