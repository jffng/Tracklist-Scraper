#!/usr/bin/env python3
"""
Modular Music Platform Search System

Provides a unified interface for searching multiple music platforms
(YouTube, Discogs, Bandcamp, etc.) for track information.
"""

from abc import ABC, abstractmethod
import time
import re
import requests
from urllib.parse import quote
import json


class MusicSearcher(ABC):
    """Abstract base class for music platform searchers."""
    
    def __init__(self, name: str, delay_between_searches: float = 1.0):
        self.name = name
        self.delay = delay_between_searches
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Setup the requests session with appropriate headers."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    @abstractmethod
    def search(self, query: str) -> dict:
        """
        Search for a track on this platform.
        
        Returns:
            dict: {
                'url': str or None,
                'confidence': float (0.0-1.0),
                'metadata': dict,
                'error': str or None
            }
        """
        pass
    
    @abstractmethod
    def clean_query(self, query: str) -> str:
        """Clean and optimize query for this platform."""
        pass
    
    def wait(self):
        """Wait between requests to be respectful."""
        time.sleep(self.delay)


class YouTubeSearcher(MusicSearcher):
    """YouTube music searcher using web scraping."""
    
    def __init__(self, delay_between_searches: float = 1.5):
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


class DiscogsSearcher(MusicSearcher):
    """Discogs searcher using their official API."""
    
    def __init__(self, delay_between_searches: float = 1.0, user_token: str = None):
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
            import urllib.parse
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


class TrackSearchManager:
    """Manages searching across multiple music platforms."""
    
    def __init__(self, discogs_token: str = None):
        self.searchers = {
            'youtube': YouTubeSearcher(delay_between_searches=1.5),
            'discogs': DiscogsSearcher(delay_between_searches=1.0, user_token=discogs_token)
        }
        self.enabled_platforms = set(self.searchers.keys())
    
    def enable_platform(self, platform: str):
        """Enable a specific platform for searching."""
        if platform in self.searchers:
            self.enabled_platforms.add(platform)
    
    def disable_platform(self, platform: str):
        """Disable a specific platform for searching."""
        self.enabled_platforms.discard(platform)
    
    def search_track(self, track: str) -> dict:
        """Search for a track across all enabled platforms."""
        results = {}
        
        for platform_name in self.enabled_platforms:
            if platform_name in self.searchers:
                searcher = self.searchers[platform_name]
                result = searcher.search(track)
                results[platform_name] = result
                
                # Wait between different platform searches
                if platform_name != list(self.enabled_platforms)[-1]:  # Don't wait after last platform
                    searcher.wait()
        
        return {
            'track': track,
            'platforms': results,
            'best_match': self._find_best_match(results)
        }
    
    def _find_best_match(self, platform_results: dict) -> dict:
        """Find the platform result with the highest confidence."""
        best_platform = None
        best_confidence = 0.0
        
        for platform, result in platform_results.items():
            if result['url'] and result['confidence'] > best_confidence:
                best_confidence = result['confidence']
                best_platform = platform
        
        return {
            'platform': best_platform,
            'confidence': best_confidence
        } if best_platform else {'platform': None, 'confidence': 0.0}


if __name__ == "__main__":
    # Example usage
    manager = TrackSearchManager()
    
    test_track = "Deadbeat - The Double Bong Cloud (Denial !)"
    result = manager.search_track(test_track)
    
    print(json.dumps(result, indent=2))
