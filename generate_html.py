#!/usr/bin/env python3
"""
Static HTML Generator for Tracklists

Generates a beautiful static HTML page from the enhanced tracklist data
with YouTube embeds and Discogs links.
"""

import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def extract_youtube_id(url):
    """Extract YouTube video ID from URL."""
    if not url:
        return None
    
    parsed = urlparse(url)
    if parsed.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed.query).get('v', [None])[0]
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    return None


def generate_tracklist_html(tracklists, output_file="tracklists.html"):
    """Generate a complete HTML page from tracklist data."""
    
    # Count totals for stats
    total_tracklists = len(tracklists)
    total_tracks = sum(len(tl.get('tracks', [])) for tl in tracklists)
    youtube_matches = 0
    discogs_matches = 0
    
    for tracklist in tracklists:
        for track in tracklist.get('tracks', []):
            platforms = track.get('platforms', {})
            if platforms.get('youtube', {}).get('url'):
                youtube_matches += 1
            if platforms.get('discogs', {}).get('url'):
                discogs_matches += 1
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tracklist Collection</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Public Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #ffffff;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: #000000;
            color: white;
            padding: 40px 0;
            text-align: center;
            margin-bottom: 40px;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
            letter-spacing: -0.02em;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 30px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: 600;
            display: block;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.8;
            font-weight: 400;
        }}
        
        .tracklist {{
            background: white;
            margin-bottom: 2px;
            border: 1px solid #e0e0e0;
            overflow: hidden;
        }}
        
        .tracklist-header {{
            background: #f8f8f8;
            color: #333;
            padding: 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e0e0e0;
            gap: 20px;
        }}
        
        .tracklist-header:hover {{
            background: #f0f0f0;
        }}
        
        .tracklist-info {{
            flex: 1;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        
        .tracklist-image {{
            width: 60px;
            height: 60px;
            object-fit: cover;
            border: 1px solid #ddd;
            flex-shrink: 0;
        }}
        
        .tracklist-text {{
            flex: 1;
        }}
        
        .tracklist-title {{
            font-size: 1.2em;
            font-weight: 500;
            margin-bottom: 4px;
        }}
        
        .tracklist-subtitle {{
            font-size: 0.9em;
            color: #666;
            font-weight: 400;
        }}
        
        .tracklist-controls {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .track-count {{
            background: #333;
            color: white;
            padding: 4px 8px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        
        .tracks {{
            padding: 0;
        }}
        
        .track {{
            border-bottom: 1px solid #f0f0f0;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        
        .track:last-child {{
            border-bottom: none;
        }}
        
        .track:hover {{
            background: #fafafa;
        }}
        
        .track-number {{
            background: #333;
            color: white;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            font-weight: 500;
            flex-shrink: 0;
        }}
        
        .track-info {{
            flex: 1;
        }}
        
        .track-name {{
            font-weight: 500;
            margin-bottom: 6px;
            color: #333;
        }}
        
        .track-links {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .platform-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            text-decoration: none;
            font-size: 0.85em;
            font-weight: 500;
            border: 1px solid;
            transition: all 0.2s ease;
        }}
        
        .youtube-link {{
            background: #fff;
            color: #ff0000;
            border-color: #ff0000;
        }}
        
        .youtube-link:hover {{
            background: #ff0000;
            color: white;
        }}
        
        .discogs-link {{
            background: #fff;
            color: #333;
            border-color: #333;
        }}
        
        .discogs-link:hover {{
            background: #333;
            color: white;
        }}
        
        .no-results {{
            color: #999;
            font-style: italic;
            font-size: 0.9em;
        }}
        
        .confidence {{
            font-size: 0.8em;
            color: #666;
            margin-left: 4px;
        }}
        
        .toggle-btn {{
            background: none;
            border: none;
            color: #333;
            font-size: 1.2em;
            cursor: pointer;
            font-family: monospace;
        }}
        
        .tracks.collapsed {{
            display: none;
        }}
        
        footer {{
            text-align: center;
            padding: 40px 0;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
            margin-top: 40px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            header h1 {{
                font-size: 2em;
            }}
            
            .stats {{
                gap: 20px;
            }}
            
            .tracklist-info {{
                gap: 15px;
            }}
            
            .tracklist-image {{
                width: 50px;
                height: 50px;
            }}
            
            .tracklist-title {{
                font-size: 1.1em;
            }}
            
            .tracklist-subtitle {{
                font-size: 0.8em;
            }}
            
            .track {{
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }}
            
            .track-links {{
                width: 100%;
            }}
        }}
        
        .search-box {{
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .search-input {{
            padding: 12px 16px;
            font-size: 1em;
            font-family: 'Public Sans', sans-serif;
            border: 1px solid #ccc;
            width: 100%;
            max-width: 400px;
            outline: none;
            transition: border-color 0.2s ease;
        }}
        
        .search-input:focus {{
            border-color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎵 Tracklist Collection</h1>
            <p>Curated music tracklists with YouTube and Discogs links</p>
            <div class="stats">
                <div class="stat">
                    <span class="stat-number">{total_tracklists}</span>
                    <span class="stat-label">Tracklists</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{total_tracks}</span>
                    <span class="stat-label">Total Tracks</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{youtube_matches}</span>
                    <span class="stat-label">YouTube Links</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{discogs_matches}</span>
                    <span class="stat-label">Discogs Links</span>
                </div>
            </div>
        </header>
        
        <div class="search-box">
            <input type="text" class="search-input" placeholder="Search tracks, artists, or tracklists..." id="searchInput">
        </div>
        
        <div id="tracklists">
"""

    # Generate each tracklist
    for i, tracklist in enumerate(tracklists):
        title = tracklist.get('title', f'Tracklist {i+1}')
        tracks = tracklist.get('tracks', [])
        image_url = tracklist.get('url', '')
        
        # Create a subtitle with track count and platform info
        youtube_count = sum(1 for track in tracks if track.get('platforms', {}).get('youtube', {}).get('url'))
        discogs_count = sum(1 for track in tracks if track.get('platforms', {}).get('discogs', {}).get('url'))
        subtitle = f"{len(tracks)} tracks • {youtube_count} YouTube • {discogs_count} Discogs"
        
        html_content += f"""
            <div class="tracklist" data-title="{title.lower()}">
                <div class="tracklist-header" onclick="toggleTracklist({i})">
                    <div class="tracklist-info">"""
        
        # Add image if available
        if image_url:
            html_content += f"""
                        <img src="{image_url}" alt="{title}" class="tracklist-image" loading="lazy">"""
        
        html_content += f"""
                        <div class="tracklist-text">
                            <div class="tracklist-title">{title}</div>
                            <div class="tracklist-subtitle">{subtitle}</div>
                        </div>
                    </div>
                    <div class="tracklist-controls">
                        <div class="track-count">{len(tracks)} tracks</div>
                        <button class="toggle-btn" id="toggle-{i}">▼</button>
                    </div>
                </div>
                <div class="tracks" id="tracks-{i}">
"""
        
        # Generate each track
        for j, track_data in enumerate(tracks):
            track_name = track_data.get('track', str(track_data))
            platforms = track_data.get('platforms', {})
            
            youtube_data = platforms.get('youtube', {})
            discogs_data = platforms.get('discogs', {})
            
            youtube_url = youtube_data.get('url')
            discogs_url = discogs_data.get('url')
            
            youtube_confidence = youtube_data.get('confidence', 0)
            discogs_confidence = discogs_data.get('confidence', 0)
            
            html_content += f"""
                    <div class="track" data-track="{track_name.lower()}">
                        <div class="track-number">{j+1}</div>
                        <div class="track-info">
                            <div class="track-name">{track_name}</div>
                            <div class="track-links">
"""
            
            if youtube_url:
                html_content += f"""
                                <a href="{youtube_url}" target="_blank" class="platform-link youtube-link">
                                    ▶️ YouTube
                                    <span class="confidence">({youtube_confidence:.0%})</span>
                                </a>
"""
            
            if discogs_url:
                html_content += f"""
                                <a href="{discogs_url}" target="_blank" class="platform-link discogs-link">
                                    💿 Discogs
                                    <span class="confidence">({discogs_confidence:.0%})</span>
                                </a>
"""
            
            if not youtube_url and not discogs_url:
                html_content += """
                                <span class="no-results">No links found</span>
"""
            
            html_content += """
                            </div>
                        </div>
                    </div>
"""
        
        html_content += """
                </div>
            </div>
"""
    
    # Close HTML and add JavaScript
    html_content += f"""
        </div>
        
        <footer>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}</p>
            <p>🎵 Built with love for music discovery</p>
        </footer>
    </div>
    
    <script>
        function toggleTracklist(index) {{
            const tracks = document.getElementById('tracks-' + index);
            const button = document.getElementById('toggle-' + index);
            
            if (tracks.classList.contains('collapsed')) {{
                tracks.classList.remove('collapsed');
                button.textContent = '▼';
            }} else {{
                tracks.classList.add('collapsed');
                button.textContent = '▶';
            }}
        }}
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        
        searchInput.addEventListener('input', function() {{
            const query = this.value.toLowerCase();
            const tracklists = document.querySelectorAll('.tracklist');
            
            tracklists.forEach(tracklist => {{
                const title = tracklist.dataset.title;
                const tracks = tracklist.querySelectorAll('.track');
                let hasMatch = title.includes(query);
                
                tracks.forEach(track => {{
                    const trackName = track.dataset.track;
                    const trackMatch = trackName.includes(query);
                    
                    if (trackMatch) {{
                        hasMatch = true;
                        track.style.display = 'flex';
                    }} else {{
                        track.style.display = query ? 'none' : 'flex';
                    }}
                }});
                
                tracklist.style.display = hasMatch || !query ? 'block' : 'none';
            }});
        }});
        
        // Auto-expand first tracklist
        if (document.getElementById('tracks-0')) {{
            // Keep first one open by default
        }}
    </script>
</body>
</html>"""
    
    # Write to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML page generated: {output_file}")
        print(f"📊 Statistics:")
        print(f"   • {total_tracklists} tracklists")
        print(f"   • {total_tracks} total tracks")
        print(f"   • {youtube_matches} YouTube links ({youtube_matches/total_tracks*100:.1f}%)")
        print(f"   • {discogs_matches} Discogs links ({discogs_matches/total_tracks*100:.1f}%)")
        print(f"\n🌐 Open {output_file} in your browser to view!")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error generating HTML: {e}")
        return None


def main():
    """Main function."""
    print("🎨 Generating static HTML page from tracklist data...")
    
    # Look for enhanced data first, then fall back to basic data
    input_files = ['tracklists_enhanced.json', 'tracklists_with_youtube.json', 'extracted_tracklists.json']
    
    data = None
    used_file = None
    
    for filename in input_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                used_file = filename
                break
            except Exception as e:
                print(f"⚠️  Could not read {filename}: {e}")
                continue
    
    if not data:
        print("❌ No tracklist data found! Please run the search scripts first.")
        return
    
    print(f"📂 Using data from: {used_file}")
    
    # Generate HTML
    output_file = generate_tracklist_html(data)
    
    if output_file:
        # Get absolute path for easier opening
        abs_path = os.path.abspath(output_file)
        print(f"📁 Full path: {abs_path}")


if __name__ == "__main__":
    main()
