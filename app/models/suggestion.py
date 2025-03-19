from typing import List, Dict
from pydantic import BaseModel

class Cluster(BaseModel):
    domain: str
    results: List[Dict]
    cluster_size: int

class SuggestionData(BaseModel):
    suggestion: str
    volume: str
    clusters: List[Cluster]

class SearchResult(BaseModel):
    query: str
    suggestions_data: List[SuggestionData] 