#!/usr/bin/env python3
"""
Tracklist.io Flask Application

A web application that serves tracklist data with YouTube and Discogs links.
"""

import json
import os
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, Response
from werkzeug.utils import secure_filename
from load_env import load_env
from ocr_processor import OCRProcessor
from models import db, Tracklist, Track
from search_manager import SearchManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracklists.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)

# Load environment variables first
if load_env():
    print("🔧 Loaded environment variables from .env file")

# Initialize processors after environment is loaded
ocr_processor = OCRProcessor()
search_manager = SearchManager(discogs_token=os.environ.get('DISCOGS_TOKEN'))

def load_tracklists():
    """Load tracklist data from JSON file."""
    # Look for enhanced data first, then fall back to basic data
    input_files = ['tracklists_enhanced.json', 'tracklists_with_youtube.json', 'extracted_tracklists.json']
    
    for filename in input_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not read {filename}: {e}")
                continue
    
    return []

def get_tracklist_stats(tracklists):
    """Calculate basic statistics for the tracklists."""
    total_tracklists = len(tracklists)
    total_tracks = 0
    
    for tracklist in tracklists:
        if isinstance(tracklist, dict):
            tracks = tracklist.get('tracks', [])
            total_tracks += len(tracks)
    
    return {
        'total_tracklists': total_tracklists,
        'total_tracks': total_tracks
    }

def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_tracklist_search(tracklist_id):
    """Background function to search for platform links for all tracks in a tracklist."""
    def run_search():
        with app.app_context():
            try:
                tracklist = Tracklist.query.get(tracklist_id)
                if not tracklist:
                    return
                
                # Update status to processing
                tracklist.search_status = 'processing'
                tracklist.search_progress = 0
                db.session.commit()
                
                tracks = Track.query.filter_by(tracklist_id=tracklist_id).all()
                total_tracks = len(tracks)
                
                for i, track in enumerate(tracks):
                    # Search for platform links
                    search_result = search_manager.search_track(track.track_name)
                    
                    # Update track with results
                    platforms = search_result.get('platforms', {})
                    
                    if platforms.get('youtube', {}).get('url'):
                        track.youtube_url = platforms['youtube']['url']
                        track.youtube_confidence = platforms['youtube']['confidence']
                    
                    if platforms.get('discogs', {}).get('url'):
                        track.discogs_url = platforms['discogs']['url']
                        track.discogs_confidence = platforms['discogs']['confidence']
                    
                    if platforms.get('bandcamp', {}).get('url'):
                        track.bandcamp_url = platforms['bandcamp']['url']
                        track.bandcamp_confidence = platforms['bandcamp']['confidence']
                    
                    # Update progress
                    tracklist.search_progress = int((i + 1) / total_tracks * 100)
                    db.session.commit()
                
                # Mark as completed
                tracklist.search_status = 'completed'
                tracklist.search_progress = 100
                db.session.commit()
                
                print(f"✅ Completed search for tracklist {tracklist_id}")
                
            except Exception as e:
                print(f"❌ Error processing tracklist {tracklist_id}: {e}")
                tracklist = Tracklist.query.get(tracklist_id)
                if tracklist:
                    tracklist.search_status = 'failed'
                    db.session.commit()
    
    # Start the search in a background thread
    thread = threading.Thread(target=run_search)
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    """Main tracklist page - shows list of all tracklists."""
    tracklists = Tracklist.query.order_by(Tracklist.created_at.desc()).all()
    stats = {
        'total_tracklists': len(tracklists),
        'total_tracks': sum(len(tl.tracks) for tl in tracklists)
    }
    return render_template('index.html', tracklists=tracklists, stats=stats)

@app.route('/tracklist/<tracklist_id>')
def view_tracklist(tracklist_id):
    """View individual tracklist with tracks and links."""
    tracklist = Tracklist.query.get_or_404(tracklist_id)
    return render_template('tracklist.html', tracklist=tracklist)

@app.route('/tracklist/<tracklist_id>/progress')
def tracklist_progress(tracklist_id):
    """Server-Sent Events endpoint for tracklist search progress."""
    def generate():
        while True:
            with app.app_context():
                tracklist = Tracklist.query.get(tracklist_id)
                if not tracklist:
                    break
                
                data = {
                    'status': tracklist.search_status,
                    'progress': tracklist.search_progress
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                
                if tracklist.search_status in ['completed', 'failed']:
                    break
            
            import time
            time.sleep(2)  # Check every 2 seconds
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/tracklist/<tracklist_id>/research', methods=['POST'])
def retrigger_search(tracklist_id):
    """Retrigger search for an existing tracklist."""
    tracklist = Tracklist.query.get_or_404(tracklist_id)
    
    # Reset search status and progress
    tracklist.search_status = 'pending'
    tracklist.search_progress = 0
    
    # Clear existing platform links
    for track in tracklist.tracks:
        track.youtube_url = None
        track.youtube_confidence = None
        track.discogs_url = None
        track.discogs_confidence = None
        track.bandcamp_url = None
        track.bandcamp_confidence = None
    
    db.session.commit()
    
    # Start background search process
    process_tracklist_search(tracklist_id)
    
    flash('Search process restarted!')
    return redirect(url_for('view_tracklist', tracklist_id=tracklist_id))

@app.route('/api/tracklists')
def api_tracklists():
    """API endpoint for tracklist data."""
    tracklists = load_tracklists()
    return jsonify(tracklists)

@app.route('/api/stats')
def api_stats():
    """API endpoint for basic statistics."""
    tracklists = load_tracklists()
    stats = get_tracklist_stats(tracklists)
    return jsonify(stats)

@app.route('/upload', methods=['GET', 'POST'])
def upload_tracklist():
    """Upload and process a tracklist image."""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        title = request.form.get('title', '')
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Secure the filename
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save the file
                file.save(filepath)
                
                # Process the image with OCR
                tracklist_data = ocr_processor.process_tracklist_image(filepath, title)
                
                # Create tracklist in database
                tracklist = Tracklist(
                    title=tracklist_data['title'],
                    extracted_text=tracklist_data['extracted_text'],
                    search_status='pending'
                )
                
                db.session.add(tracklist)
                db.session.flush()  # Get the ID
                
                # Create track records
                for track_name in tracklist_data['tracks']:
                    track = Track(
                        track_name=track_name,
                        tracklist_id=tracklist.id
                    )
                    db.session.add(track)
                
                db.session.commit()
                
                # Clean up uploaded file
                os.remove(filepath)
                
                # Start background search process
                process_tracklist_search(tracklist.id)
                
                flash(f'Successfully processed tracklist: {len(tracklist_data["tracks"])} tracks found')
                return redirect(url_for('view_tracklist', tracklist_id=tracklist.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing image: {str(e)}')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload an image file.')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🎵 Starting Tracklist.io Flask Server")
    print("=" * 50)
    
    # Initialize database
    with app.app_context():
        db.create_all()
        print("✅ Database initialized")
    
    # Check if we have data
    with app.app_context():
        tracklists = Tracklist.query.all()
        if tracklists:
            stats = {
                'total_tracklists': len(tracklists),
                'total_tracks': sum(len(tl.tracks) for tl in tracklists)
            }
            print(f"📊 Loaded {stats['total_tracklists']} tracklists with {stats['total_tracks']} tracks")
        else:
            print("⚠️  No tracklist data found!")
            print("   Upload images via /upload to get started")
    
    print("\n🌐 Server starting...")
    print("   Local: http://localhost:8000")
    print("   Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=8000)