"""
Database Models

SQLAlchemy models for tracklist storage and management.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class Tracklist(db.Model):
    """Tracklist model - represents a collection of tracks from an uploaded image."""
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    extracted_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    search_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    search_progress = db.Column(db.Integer, default=0)  # 0-100 percentage
    
    # Relationships
    tracks = db.relationship('Track', backref='tracklist', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Tracklist {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert tracklist to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'extracted_text': self.extracted_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'search_status': self.search_status,
            'search_progress': self.search_progress,
            'tracks': [track.to_dict() for track in self.tracks]
        }


class Track(db.Model):
    """Track model - represents individual tracks within a tracklist."""
    
    id = db.Column(db.Integer, primary_key=True)
    track_name = db.Column(db.String(300), nullable=False)
    tracklist_id = db.Column(db.String(36), db.ForeignKey('tracklist.id'), nullable=False)
    
    # Platform links
    youtube_url = db.Column(db.String(500))
    youtube_confidence = db.Column(db.Float)
    discogs_url = db.Column(db.String(500))
    discogs_confidence = db.Column(db.Float)
    bandcamp_url = db.Column(db.String(500))
    bandcamp_confidence = db.Column(db.Float)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Track {self.id}: {self.track_name}>'
    
    def to_dict(self):
        """Convert track to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'track_name': self.track_name,
            'platforms': {
                'youtube': {
                    'url': self.youtube_url,
                    'confidence': self.youtube_confidence
                },
                'discogs': {
                    'url': self.discogs_url,
                    'confidence': self.discogs_confidence
                },
                'bandcamp': {
                    'url': self.bandcamp_url,
                    'confidence': self.bandcamp_confidence
                }
            }
        }
    
    def has_any_links(self):
        """Check if track has any platform links."""
        return any([
            self.youtube_url,
            self.discogs_url,
            self.bandcamp_url
        ])
