"""
YouTube Crawler

Searches YouTube for music tracks using web scraping.
"""

import re
from urllib.parse import quote
from .base import BaseCrawler


class YouTubeCrawler(BaseCrawler):
    """YouTube music crawler using web scraping."""
    
    def __init__(self, delay_between_searches: float = 1.5):
        """Initialize YouTube crawler with appropriate delay."""
        super().__init__("YouTube", delay_between_searches)
    
    def clean_query(self, query: str) -> str:
        """Clean up the search query for better YouTube results."""
        # Minimal cleaning to preserve original search intent
        cleaned = re.sub(r'[^\w\s\-\(\)\[\]&\.\']', ' ', query)  # Keep apostrophes
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Don't automatically add "music" - let YouTube's algorithm decide
        return cleaned
    
    def search(self, query: str) -> dict:
        """Search YouTube for a track and return the best match."""
        try:
            clean_query = self.clean_query(query)
            search_url = f"https://www.youtube.com/results?search_query={quote(clean_query)}"
            
            print(f"  🔍 YouTube: {clean_query}")
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            video_urls = self._extract_video_urls(response.text)
            
            if video_urls:
                best_match = video_urls[0]
                return {
                    'url': best_match,
                    'confidence': 0.8,  # Default confidence for first result
                    'metadata': {
                        'search_query': clean_query,
                        'total_results': len(video_urls)
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
    
    def _extract_video_urls(self, html_content: str) -> list:
        """Extract YouTube video URLs from search results HTML."""
        video_urls = []
        
        # More precise patterns that target actual search results
        # These patterns are more specific to YouTube's current structure
        patterns = [
            # Primary video result pattern - targets main search results
            r'"videoRenderer":\s*{[^}]*"videoId":"([a-zA-Z0-9_-]{11})"',
            # Compact video result pattern
            r'"compactVideoRenderer":\s*{[^}]*"videoId":"([a-zA-Z0-9_-]{11})"',
            # Watch endpoint pattern (more specific)
            r'"watchEndpoint":\s*{\s*"videoId":"([a-zA-Z0-9_-]{11})"',
            # Fallback pattern
            r'"videoId":"([a-zA-Z0-9_-]{11})"'
        ]
        
        found_ids = set()
        
        # Try patterns in order of specificity
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            
            for match in matches:
                if match not in found_ids:
                    found_ids.add(match)
                    video_urls.append(f"https://www.youtube.com/watch?v={match}")
                    
                    # Get more results for better selection
                    if len(video_urls) >= 5:
                        break
            
            # If we found results with this pattern, use them
            if video_urls:
                break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in video_urls:
            video_id = url.split('v=')[1]
            if video_id not in seen:
                seen.add(video_id)
                unique_urls.append(url)
        
        return unique_urls[:5]  # Return top 5 results
