from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import aiohttp
import asyncio
import json
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict
import string
import os
from datetime import datetime
import logging
from collections import defaultdict
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Store results globally
results = []
is_running = False
current_text = ""
current_num_letters = 1

PERSIAN_LETTERS = 'ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی'

def get_domain(url: str) -> str:
    """Extract domain from URL for clustering."""
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else url
    except:
        return url

def cluster_search_results(search_results: List[Dict]) -> List[Dict]:
    """Cluster search results based on domain similarity."""
    # Group results by domain
    domain_groups = defaultdict(list)
    for result in search_results:
        domain = get_domain(result['link'])
        domain_groups[domain].append(result)
    
    # Create clusters
    clusters = []
    for domain, results in domain_groups.items():
        cluster = {
            'domain': domain,
            'results': results,
            'cluster_size': len(results)
        }
        clusters.append(cluster)
    
    # Sort clusters by size (descending)
    clusters.sort(key=lambda x: x['cluster_size'], reverse=True)
    return clusters

async def get_keyword_volume(session, keyword):
    try:
        # For testing purposes, return a mock volume
        return "10K+"
    except Exception as e:
        logger.error(f"Error getting keyword volume: {str(e)}")
    return "N/A"

async def get_search_results(session, keyword):
    try:
        url = f"https://www.google.com/search?q={keyword}&hl=fa"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                search_results = []
                
                # Find all search result divs
                for div in soup.find_all('div', class_='g'):
                    if len(search_results) >= 5:
                        break
                        
                    title_elem = div.find('h3')
                    link_elem = div.find('a')
                    snippet_elem = div.find('div', class_='VwiC3b')
                    
                    if title_elem and link_elem:
                        result = {
                            'title': title_elem.get_text(),
                            'link': link_elem.get('href', ''),
                            'snippet': snippet_elem.get_text() if snippet_elem else 'No description available'
                        }
                        search_results.append(result)
                
                return search_results
    except Exception as e:
        logger.error(f"Error getting search results: {str(e)}")
    return []

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start")
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

@app.get("/fetch_suggestions")
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
            
            # Get suggestions from Google
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={current_combo}"
            logger.info(f"Fetching suggestions for: {current_combo}")
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error response from Google: {response.status}")
                    return JSONResponse({"error": f"Google API returned status {response.status}"})
                
                data = await response.text()
                try:
                    suggestions = json.loads(data)[1]
                    logger.info(f"Received {len(suggestions)} suggestions for {current_combo}")
                except (json.JSONDecodeError, IndexError) as e:
                    logger.error(f"Error parsing response: {e}")
                    return JSONResponse({"error": "Failed to parse Google response"})
                
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
                    
                    # Store the results with the current query
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
                else:
                    return JSONResponse({
                        "status": "running",
                        "suggestions": [],
                        "is_complete": False,
                        "progress": len(results),
                        "total": len(PERSIAN_LETTERS) if num_letters == 1 else len(PERSIAN_LETTERS) ** 2
                    })
    except Exception as e:
        logger.error(f"Error in fetch_suggestions: {e}")
        return JSONResponse({"error": str(e)})

@app.post("/pause")
async def pause_search():
    global is_running
    is_running = False
    logger.info("Search paused")
    return JSONResponse({"status": "paused"})

@app.post("/resume")
async def resume_search():
    global is_running
    is_running = True
    logger.info("Search resumed")
    return JSONResponse({"status": "resumed"})

@app.get("/download")
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