from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from app.routers import main

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(main.router)

# Export the app instance
__all__ = ['app'] 