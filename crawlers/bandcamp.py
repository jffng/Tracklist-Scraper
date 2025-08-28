"""
Bandcamp Crawler

Searches Bandcamp for music tracks using web scraping.
"""

import re
from urllib.parse import quote, urljoin
from .base import BaseCrawler


class BandcampCrawler(BaseCrawler):
    """Bandcamp music crawler using web scraping."""
    
    def __init__(self, delay_between_searches: float = 2.0):
        """
        Initialize Bandcamp crawler.
        
        Args:
            delay_between_searches: Delay between searches (Bandcamp is more sensitive)
        """
        super().__init__("Bandcamp", delay_between_searches)
        self.base_url = "https://bandcamp.com"
        
        # Update headers to look more like a real browser
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def clean_query(self, query: str) -> str:
        """Clean query for Bandcamp search."""
        # Bandcamp works well with simple, clean queries
        cleaned = re.sub(r'[^\w\s\-\(\)\[\]&\.\']', ' ', query)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove common track indicators that might confuse Bandcamp
        cleaned = re.sub(r'\s*\([^)]*remix[^)]*\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*\([^)]*mix[^)]*\)', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def search(self, query: str) -> dict:
        """Search Bandcamp for a track."""
        try:
            clean_query = self.clean_query(query)
            
            # Bandcamp search URL
            search_url = f"https://bandcamp.com/search?q={quote(clean_query)}"
            
            print(f"  🔍 Bandcamp: {clean_query}")
            
            response = self.session.get(search_url, timeout=15)
            
            # Handle specific HTTP errors - return search URL instead of failing
            if response.status_code == 403:
                return {
                    'url': search_url,  # Return the search URL for manual browsing
                    'confidence': 0.6,  # Medium confidence since it's a search page
                    'metadata': {
                        'search_query': clean_query,
                        'search_url': search_url,
                        'note': 'Manual search required - Bandcamp blocked automated requests'
                    },
                    'error': None
                }
            elif response.status_code == 429:
                return {
                    'url': search_url,  # Return the search URL for manual browsing
                    'confidence': 0.6,
                    'metadata': {
                        'search_query': clean_query,
                        'search_url': search_url,
                        'note': 'Manual search required - Bandcamp rate limited'
                    },
                    'error': None
                }
            
            response.raise_for_status()
            
            # Extract results from the search page
            results = self._extract_search_results(response.text, clean_query)
            
            if results:
                best_match = results[0]  # Take first result
                
                # Calculate confidence based on title match
                confidence = self._calculate_confidence(query, best_match)
                
                return {
                    'url': best_match['url'],
                    'confidence': confidence,
                    'metadata': {
                        'title': best_match.get('title', ''),
                        'artist': best_match.get('artist', ''),
                        'album': best_match.get('album', ''),
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
    
    def _extract_search_results(self, html_content: str, query: str) -> list:
        """Extract search results from Bandcamp HTML."""
        results = []
        
        # Bandcamp search results are in a specific structure
        # Look for result items in the search page
        patterns = [
            # Pattern for track results
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>.*?<div[^>]*class="[^"]*heading[^"]*"[^>]*>([^<]*)</div>.*?<div[^>]*class="[^"]*subhead[^"]*"[^>]*>([^<]*)</div>',
            # Alternative pattern for album/artist results
            r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*result[^"]*"[^>]*>.*?<div[^>]*class="[^"]*heading[^"]*"[^>]*>([^<]*)</div>.*?<div[^>]*class="[^"]*subhead[^"]*"[^>]*>([^<]*)</div>'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if len(match) >= 3:
                    url = match[0]
                    title = match[1].strip()
                    artist = match[2].strip()
                    
                    # Clean up the URL
                    if url.startswith('/'):
                        url = f"https://bandcamp.com{url}"
                    elif not url.startswith('http'):
                        url = f"https://bandcamp.com/{url}"
                    
                    # Skip if it's not a music result
                    if any(skip in url.lower() for skip in ['/tag/', '/label/', '/fan/']):
                        continue
                    
                    results.append({
                        'url': url,
                        'title': title,
                        'artist': artist,
                        'album': ''  # Bandcamp doesn't always show album in search
                    })
                    
                    # Limit results
                    if len(results) >= 5:
                        break
            
            if results:
                break
        
        # If no structured results found, try a simpler approach
        if not results:
            results = self._extract_simple_results(html_content, query)
        
        return results[:5]  # Return top 5 results
    
    def _extract_simple_results(self, html_content: str, query: str) -> list:
        """Fallback method to extract results using simpler patterns."""
        results = []
        
        # Look for any Bandcamp links in the search results
        link_pattern = r'href="(https://[^"]*\.bandcamp\.com/[^"]*)"'
        title_pattern = r'<[^>]*class="[^"]*heading[^"]*"[^>]*>([^<]+)</[^>]*>'
        
        links = re.findall(link_pattern, html_content)
        titles = re.findall(title_pattern, html_content)
        
        # Match links with titles
        for i, link in enumerate(links[:5]):
            title = titles[i] if i < len(titles) else "Unknown Track"
            
            results.append({
                'url': link,
                'title': title.strip(),
                'artist': '',
                'album': ''
            })
        
        return results
    
    def _calculate_confidence(self, original_query: str, result: dict) -> float:
        """Calculate confidence score for a Bandcamp result."""
        title = result.get('title', '').lower()
        artist = result.get('artist', '').lower()
        query_lower = original_query.lower()
        
        # Check if query matches title or artist
        if query_lower in title or title in query_lower:
            return 0.9
        if query_lower in artist or artist in query_lower:
            return 0.8
        
        # Check word overlap
        query_words = set(re.findall(r'\w+', query_lower))
        title_words = set(re.findall(r'\w+', title))
        artist_words = set(re.findall(r'\w+', artist))
        
        all_result_words = title_words.union(artist_words)
        
        if query_words and all_result_words:
            overlap = len(query_words.intersection(all_result_words))
            total_words = len(query_words.union(all_result_words))
            return min(0.7, overlap / total_words)
        
        return 0.5  # Default confidence for any result
