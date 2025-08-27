"""
Crawlers Package

Music platform crawlers for searching tracks across different platforms.
"""

from .base import BaseCrawler
from .youtube import YouTubeCrawler
from .discogs import DiscogsCrawler

__all__ = ['BaseCrawler', 'YouTubeCrawler', 'DiscogsCrawler']
