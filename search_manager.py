"""
Search Manager

Coordinates searches across multiple music platform crawlers.
"""

from crawlers import YouTubeCrawler, DiscogsCrawler, BandcampCrawler


class SearchManager:
    """Manages searching across multiple music platform crawlers."""
    
    def __init__(self, discogs_token: str = None):
        """
        Initialize search manager with available crawlers.
        
        Args:
            discogs_token: Optional Discogs API token for better rate limits
        """
        self.crawlers = {
            'youtube': YouTubeCrawler(delay_between_searches=1.5),
            'discogs': DiscogsCrawler(delay_between_searches=1.0, user_token=discogs_token),
            'bandcamp': BandcampCrawler(delay_between_searches=2.0)
        }
        # Enable all platforms - Bandcamp now provides search URLs when blocked
        self.enabled_platforms = set(self.crawlers.keys())
    
    def enable_platform(self, platform: str):
        """Enable a specific platform for searching."""
        if platform in self.crawlers:
            self.enabled_platforms.add(platform)
    
    def disable_platform(self, platform: str):
        """Disable a specific platform for searching."""
        self.enabled_platforms.discard(platform)
    
    def enable_bandcamp(self):
        """Enable Bandcamp with a warning about potential blocking."""
        if 'bandcamp' in self.crawlers:
            self.enabled_platforms.add('bandcamp')
            print("⚠️  Bandcamp enabled - may be blocked by anti-bot protection")
            print("   If you get 403 errors, Bandcamp is blocking automated requests")
        else:
            print("Bandcamp crawler not available.")
    
    def search_track(self, track: str) -> dict:
        
        """
        Search for a track across all enabled platforms.
        
        Args:
            track: Track name (usually "Artist - Track")
            
        Returns:
            dict: {
                'track': str,
                'platforms': dict,
                'best_match': dict
            }
        """
        results = {}
        
        for platform_name in self.enabled_platforms:
            if platform_name in self.crawlers:
                crawler = self.crawlers[platform_name]
                result = crawler.search(track)
                results[platform_name] = result
                
                # Wait between different platform searches
                if platform_name != list(self.enabled_platforms)[-1]:  # Don't wait after last platform
                    crawler.wait()
        
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
