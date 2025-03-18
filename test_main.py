import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import MagicMock, patch, AsyncMock
import json
import asyncio
from main import (
    app, is_running, results, current_text, current_num_letters,
    get_domain, cluster_search_results, get_keyword_volume, get_search_results,
    PERSIAN_LETTERS
)

@pytest.fixture(autouse=True)
async def reset_globals():
    """Reset global state before each test"""
    global is_running, results, current_text, current_num_letters
    is_running = False
    results = []
    current_text = ""
    current_num_letters = 0
    yield

def test_home_endpoint():
    """Test that home endpoint returns 200 OK"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

def test_get_domain():
    """Test domain extraction from URL"""
    url = "https://www.example.com/path"
    assert get_domain(url) == "www.example.com"

def test_cluster_search_results():
    """Test clustering of search results"""
    test_results = [
        {"link": "https://example.com/1", "title": "Title 1"},
        {"link": "https://example.com/2", "title": "Title 2"},
        {"link": "https://other.com", "title": "Title 3"}
    ]
    clustered = cluster_search_results(test_results)
    assert len(clustered) == 2
    assert any(c["domain"] == "example.com" and len(c["results"]) == 2 for c in clustered)

@pytest.mark.asyncio
async def test_start_search_valid():
    """Test starting a search with valid parameters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

@pytest.mark.asyncio
async def test_start_search_invalid_letters():
    """Test starting a search with invalid number of letters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/start", data={"text": "سیب", "num_letters": "3"})
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_fetch_suggestions():
    """Test fetching suggestions with mocked Google API response"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search first
        response = await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        assert response.status_code == 200

        # Mock the functions that make external calls
        async def mock_get_keyword_volume(session, keyword):
            return "10K+"

        async def mock_get_search_results(session, keyword):
            return [{"title": "Test", "link": "https://example.com", "snippet": "Test snippet"}]

        with patch('main.get_keyword_volume', mock_get_keyword_volume), \
             patch('main.get_search_results', mock_get_search_results):
            response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "running"

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
        assert data["error"] == "No results to download"

@pytest.mark.asyncio
async def test_fetch_suggestions_not_running():
    """Test fetching suggestions when search is not running"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search first to set up the state
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Then pause it to set is_running to False
        await ac.post("/pause")
        
        # Now try to fetch suggestions
        response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

@pytest.mark.asyncio
async def test_fetch_suggestions_invalid_params():
    """Test fetching suggestions with invalid parameters"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start with specific parameters
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Try to fetch with different parameters
        response = await ac.get("/fetch_suggestions?text=different&num_letters=2")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Invalid request parameters"

@pytest.mark.asyncio
async def test_search_completion():
    """Test that search completion is properly indicated"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Mock the functions to simulate search completion
        async def mock_get_keyword_volume(session, keyword):
            return "10K+"

        async def mock_get_search_results(session, keyword):
            return [{"title": "Test", "link": "https://example.com", "snippet": "Test snippet"}]

        with patch('main.get_keyword_volume', mock_get_keyword_volume), \
             patch('main.get_search_results', mock_get_search_results):
            # Fetch suggestions multiple times until completion
            for _ in range(len(PERSIAN_LETTERS)):
                response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
                assert response.status_code == 200
                data = response.json()
                
                # Check if we have results
                assert len(data["suggestions"]) > 0
                
                # On the last iteration, check if the search is marked as complete
                if _ == len(PERSIAN_LETTERS) - 1:
                    assert data["status"] == "complete"
                    assert data["is_complete"] == True
                else:
                    assert data["status"] == "running"
                    assert data["is_complete"] == False

@pytest.mark.asyncio
async def test_csv_download_with_results():
    """Test that CSV download contains the correct data"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Mock the functions to return test data
        async def mock_get_keyword_volume(session, keyword):
            return "10K+"

        async def mock_get_search_results(session, keyword):
            return [{"title": "Test", "link": "https://example.com", "snippet": "Test snippet"}]

        with patch('main.get_keyword_volume', mock_get_keyword_volume), \
             patch('main.get_search_results', mock_get_search_results):
            # Fetch suggestions to generate results
            await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
            
            # Download the results
            response = await ac.get("/download")
            assert response.status_code == 200
            
            # Check that the response is a CSV file
            assert response.headers["content-type"] == "text/csv"
            
            # Check that the CSV content is not empty
            csv_content = response.text
            assert len(csv_content.strip()) > 0
            
            # Check that the CSV contains the expected columns
            assert "keyword" in csv_content
            assert "volume" in csv_content
            assert "search_results" in csv_content

@pytest.mark.asyncio
async def test_keyword_volume():
    """Test that keyword volume is properly fetched and stored"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a search
        await ac.post("/start", data={"text": "سیب", "num_letters": "1"})
        
        # Mock the keyword volume function to return a specific value
        async def mock_get_keyword_volume(session, keyword):
            return "5K"

        async def mock_get_search_results(session, keyword):
            return [{"title": "Test", "link": "https://example.com", "snippet": "Test snippet"}]

        with patch('main.get_keyword_volume', mock_get_keyword_volume), \
             patch('main.get_search_results', mock_get_search_results):
            # Fetch suggestions
            response = await ac.get("/fetch_suggestions?text=سیب&num_letters=1")
            assert response.status_code == 200
            data = response.json()
            
            # Check that suggestions contain keyword volume
            assert len(data["suggestions"]) > 0
            for suggestion in data["suggestions"]:
                assert "volume" in suggestion
                assert suggestion["volume"] == "5K"