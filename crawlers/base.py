"""
Base Crawler Class

Abstract base class for all music platform crawlers.
"""

from abc import ABC, abstractmethod
import time
import requests


class BaseCrawler(ABC):
    """Abstract base class for music platform crawlers."""
    
    def __init__(self, name: str, delay_between_searches: float = 1.0):
        """
        Initialize the crawler.
        
        Args:
            name: Name of the platform (e.g., "YouTube", "Discogs")
            delay_between_searches: Delay in seconds between searches
        """
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
        
        Args:
            query: Search query (usually "Artist - Track")
        
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
        """
        Clean and optimize query for this platform.
        
        Args:
            query: Raw search query
            
        Returns:
            str: Cleaned query optimized for this platform
        """
        pass
    
    def wait(self):
        """Wait between requests to be respectful to the platform."""
        time.sleep(self.delay)
    
    def __str__(self):
        """String representation of the crawler."""
        return f"{self.name}Crawler"
    
    def __repr__(self):
        """Detailed string representation of the crawler."""
        return f"{self.name}Crawler(delay={self.delay})"
