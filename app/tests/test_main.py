import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
import os
from datetime import datetime

from app.main import app
from app.routers.main import PERSIAN_LETTERS

@pytest.fixture
def client():
    return TestClient(app)

def test_home_endpoint(client):
    """Test that home endpoint returns 200 OK"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_start_search_valid():
    """Test starting a search with valid parameters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["total"] == len(PERSIAN_LETTERS)

@pytest.mark.asyncio
async def test_start_search_invalid_letters():
    """Test starting a search with invalid number of letters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/start", data={"text": "سیب", "num_letters": "3"})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

@pytest.mark.asyncio
async def test_cancel_search():
    """Test cancelling a search"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search first
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Then cancel it
        response = await ac.post("/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

@pytest.mark.asyncio
async def test_fetch_suggestions_not_running():
    """Test fetching suggestions when search is not running"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["is_complete"] is True

@pytest.mark.asyncio
async def test_fetch_suggestions_invalid_params():
    """Test fetching suggestions with invalid parameters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start with specific parameters
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Try to fetch with different parameters
        response = await ac.get("/fetch_suggestions?text=different&num_letters=1")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

@pytest.mark.asyncio
async def test_pause_resume():
    """Test pausing and resuming the search process"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Pause search
        response = await ac.post("/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        
        # Resume search
        response = await ac.post("/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"

@pytest.mark.asyncio
async def test_download_no_results():
    """Test downloading results when no results are available"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/download")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

@pytest.mark.asyncio
async def test_download_with_results():
    """Test downloading results with actual data"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Add some test results
        from app.routers.main import results
        results.append({
            "query": "test query",
            "suggestions_data": [{
                "suggestion": "test suggestion",
                "volume": "10K+",
                "clusters": [{"domain": "test.com", "results": [], "cluster_size": 1}]
            }]
        })
        
        # Download the results
        response = await ac.get("/download")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        
        # Clean up the downloaded file
        filename = response.headers["content-disposition"].split("filename=")[1].replace('"', '')
        if os.path.exists(filename):
            os.remove(filename)

@pytest.mark.asyncio
async def test_search_completion():
    """Test that search completion is properly indicated"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Fetch suggestions multiple times
        total_letters = len(PERSIAN_LETTERS)
        for i in range(total_letters):
            response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
            assert response.status_code == 200
            data = response.json()
            
            if i < total_letters - 1:
                assert data["status"] == "running"
                assert data["is_complete"] is False
                assert data["progress"] == i + 1
            else:
                assert data["status"] == "complete"
                assert data["is_complete"] is True
                assert data["progress"] == total_letters 