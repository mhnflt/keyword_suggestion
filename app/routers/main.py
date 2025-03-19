from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
import aiohttp
import asyncio
import json
import pandas as pd
from datetime import datetime
import logging
from typing import List

from app.services.google_service import (
    get_suggestions, get_keyword_volume, get_search_results,
    cluster_search_results
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Templates
templates = Jinja2Templates(directory="app/templates")

# Store results globally
results = []
is_running = False
current_text = ""
current_num_letters = 1

PERSIAN_LETTERS = 'ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی'

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/start")
async def start_search(text: str = Form(...), num_letters: int = Form(...)):
    global is_running, results, current_text, current_num_letters
    logger.info(f"Starting search with text: {text}, num_letters: {num_letters}")
    
    is_running = True
    results = []
    current_text = text
    current_num_letters = num_letters
    
    if num_letters not in [1, 2]:
        return JSONResponse({"error": "Number of letters must be 1 or 2"}, status_code=400)
    
    combinations = []
    if num_letters == 1:
        combinations = [text + " " + letter for letter in PERSIAN_LETTERS]
    else:
        combinations = [text + " " + l1 + l2 for l1 in PERSIAN_LETTERS for l2 in PERSIAN_LETTERS]
    
    logger.info(f"Total combinations to check: {len(combinations)}")
    return JSONResponse({"status": "started", "total": len(combinations)})

@router.post("/cancel")
async def cancel_search():
    global is_running, results, current_text, current_num_letters
    is_running = False
    results = []
    current_text = ""
    current_num_letters = 1
    logger.info("Search cancelled")
    return JSONResponse({"status": "cancelled"})

@router.get("/fetch_suggestions")
async def fetch_suggestions(text: str, num_letters: int):
    global results, is_running, current_text, current_num_letters
    logger.info(f"Fetching suggestions for text: {text}, num_letters: {num_letters}")
    
    if not is_running:
        logger.info("Search is not running")
        return JSONResponse({"status": "stopped", "suggestions": [], "is_complete": True})
    
    if text != current_text or num_letters != current_num_letters:
        logger.error("Text or num_letters mismatch")
        return JSONResponse({"error": "Invalid request parameters"})
    
    try:
        async with aiohttp.ClientSession() as session:
            # Calculate the current combination
            if num_letters == 1:
                current_combo = text + " " + PERSIAN_LETTERS[len(results)]
            else:
                idx = len(results)
                l1_idx = idx // len(PERSIAN_LETTERS)
                l2_idx = idx % len(PERSIAN_LETTERS)
                current_combo = text + " " + PERSIAN_LETTERS[l1_idx] + PERSIAN_LETTERS[l2_idx]
            
            logger.info(f"Fetching suggestions for: {current_combo}")
            suggestions = await get_suggestions(session, current_combo)
            
            # Store the results with the current query, even if no suggestions
            suggestion_data = []
            if suggestions:
                # Process suggestions in parallel
                async def process_suggestion(suggestion):
                    volume = await get_keyword_volume(session, suggestion)
                    search_results = await get_search_results(session, suggestion)
                    clusters = cluster_search_results(search_results)
                    return {
                        "suggestion": suggestion,
                        "volume": volume,
                        "clusters": clusters
                    }
                
                # Process all suggestions concurrently
                tasks = [process_suggestion(s) for s in suggestions]
                suggestion_data = await asyncio.gather(*tasks)
            
            # Always store the result and increment progress
            results.append({
                "query": current_combo,
                "suggestions_data": suggestion_data
            })
            
            # Check if search is complete
            total = len(PERSIAN_LETTERS) if num_letters == 1 else len(PERSIAN_LETTERS) ** 2
            is_complete = len(results) >= total
            
            if is_complete:
                is_running = False
                logger.info("Search completed")
            
            return JSONResponse({
                "status": "complete" if is_complete else "running",
                "suggestions": suggestion_data,
                "is_complete": is_complete,
                "progress": len(results),
                "total": total
            })
    except Exception as e:
        logger.error(f"Error in fetch_suggestions: {e}")
        return JSONResponse({"error": str(e)})

@router.post("/pause")
async def pause_search():
    global is_running
    is_running = False
    logger.info("Search paused")
    return JSONResponse({"status": "paused"})

@router.post("/resume")
async def resume_search():
    global is_running
    is_running = True
    logger.info("Search resumed")
    return JSONResponse({"status": "resumed"})

@router.get("/download")
async def download_results():
    global results
    
    if not results:
        return JSONResponse({"error": "No results to download"})
    
    # Create a flattened list for CSV
    flat_data = []
    for result in results:
        for suggestion_data in result["suggestions_data"]:
            flat_data.append({
                "keyword": suggestion_data["suggestion"],
                "volume": suggestion_data["volume"],
                "search_results": json.dumps(suggestion_data["clusters"])
            })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(flat_data)
    filename = f"google_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'text/csv'
    }
    
    return FileResponse(
        filename,
        headers=headers,
        filename=filename
    ) 