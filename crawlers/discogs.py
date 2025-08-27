"""
Discogs Crawler

Searches Discogs for music releases using their official API.
"""

import re
import urllib.parse
from .base import BaseCrawler


class DiscogsCrawler(BaseCrawler):
    """Discogs music crawler using their official API."""
    
    def __init__(self, delay_between_searches: float = 1.0, user_token: str = None):
        """
        Initialize Discogs crawler.
        
        Args:
            delay_between_searches: Delay between API calls
            user_token: Optional Discogs API token for higher rate limits
        """
        super().__init__("Discogs", delay_between_searches)
        self.user_token = user_token
        self.base_url = "https://api.discogs.com"
        
        if self.user_token:
            self.session.headers.update({
                'Authorization': f'Discogs token={self.user_token}'
            })
    
    def clean_query(self, query: str) -> str:
        """Clean query for Discogs search."""
        # Simple cleaning - just remove problematic characters and normalize spaces
        clean_query = re.sub(r'[^\w\s\-\(\)\[\]&\.]', ' ', query)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        return clean_query
    
    def search(self, query: str) -> dict:
        """Search Discogs for a track."""
        try:
            clean_query = self.clean_query(query)
            
            # Simple general search parameters
            params = {
                'q': clean_query,
                'type': 'release',
                'per_page': 10,
            }
            
            search_url = f"{self.base_url}/database/search"
            
            print(f"  🔍 Discogs: {clean_query}")
            
            # Debug: print the actual URL being called
            full_url = f"{search_url}?{urllib.parse.urlencode(params)}"
            print(f"    URL: {full_url}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            # Check response status
            if response.status_code == 401:
                return {
                    'url': None,
                    'confidence': 0.0,
                    'metadata': {'search_query': clean_query, 'full_url': full_url},
                    'error': 'Unauthorized - need Discogs token'
                }
            elif response.status_code == 429:
                return {
                    'url': None,
                    'confidence': 0.0,
                    'metadata': {'search_query': clean_query, 'full_url': full_url},
                    'error': 'Rate limited - try again later'
                }
            
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            
            print(f"    Found {len(results)} results")
            
            if results:
                best_match = results[0]  # Take first result
                
                # Calculate confidence based on title match
                confidence = self._calculate_confidence(query, best_match)
                
                # Build proper URL
                discogs_url = best_match.get('uri', '')
                if discogs_url:
                    if discogs_url.startswith('/releases/'):
                        discogs_url = f"https://www.discogs.com{discogs_url}"
                    elif discogs_url.startswith('/masters/'):
                        discogs_url = f"https://www.discogs.com{discogs_url}"
                    elif not discogs_url.startswith('http'):
                        discogs_url = f"https://www.discogs.com{discogs_url}"
                
                return {
                    'url': discogs_url,
                    'confidence': confidence,
                    'metadata': {
                        'title': best_match.get('title', ''),
                        'year': best_match.get('year', ''),
                        'label': ', '.join(best_match.get('label', [])),
                        'format': ', '.join(best_match.get('format', [])),
                        'country': best_match.get('country', ''),
                        'search_query': clean_query,
                        'total_results': len(results)
                    },
                    'error': None
                }
            else:
                return {
                    'url': None,
                    'confidence': 0.0,
                    'metadata': {'search_query': clean_query},
                    'error': 'No results found'
                }
                
        except Exception as e:
            return {
                'url': None,
                'confidence': 0.0,
                'metadata': {'search_query': query},
                'error': str(e)
            }
    
    def _calculate_confidence(self, original_query: str, result: dict) -> float:
        """Calculate confidence score for a Discogs result."""
        title = result.get('title', '').lower()
        query_lower = original_query.lower()
        
        # Simple confidence calculation based on string similarity
        if query_lower in title or title in query_lower:
            return 0.9
        
        # Check if key words match
        query_words = set(re.findall(r'\w+', query_lower))
        title_words = set(re.findall(r'\w+', title))
        
        if query_words and title_words:
            overlap = len(query_words.intersection(title_words))
            total_words = len(query_words.union(title_words))
            return min(0.8, overlap / total_words)
        
        return 0.5  # Default confidence for any result
