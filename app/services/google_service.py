import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
import json
import logging
from urllib.parse import urlparse
from collections import defaultdict

logger = logging.getLogger(__name__)

def get_domain(url: str) -> str:
    """Extract domain from URL for clustering."""
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else url
    except:
        return url

def cluster_search_results(search_results: List[Dict]) -> List[Dict]:
    """Cluster search results based on domain similarity."""
    domain_groups = defaultdict(list)
    for result in search_results:
        domain = get_domain(result['link'])
        domain_groups[domain].append(result)
    
    clusters = []
    for domain, results in domain_groups.items():
        cluster = {
            'domain': domain,
            'results': results,
            'cluster_size': len(results)
        }
        clusters.append(cluster)
    
    clusters.sort(key=lambda x: x['cluster_size'], reverse=True)
    return clusters

async def get_keyword_volume(session: aiohttp.ClientSession, keyword: str) -> str:
    """Get keyword search volume (mock implementation)."""
    try:
        return "10K+"
    except Exception as e:
        logger.error(f"Error getting keyword volume: {str(e)}")
    return "N/A"

async def get_search_results(session: aiohttp.ClientSession, keyword: str) -> List[Dict]:
    """Get search results from Google."""
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

async def get_suggestions(session: aiohttp.ClientSession, query: str) -> List[str]:
    """Get suggestions from Google Suggest API."""
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={query}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.text()
                suggestions = json.loads(data)[1]
                return suggestions
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
    return [] 