#!/usr/bin/env python3
"""
Enhanced Multi-Platform Track Search

Uses the modular music searcher system to find tracks across
YouTube, Discogs, and other platforms.
"""

import json
import os
from search_manager import SearchManager
from load_env import load_env

def load_tracklists(input_file="extracted_tracklists.json"):
    """Load tracklists from JSON file."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        return None


def save_results(data, output_file="tracklists_enhanced.json"):
    """Save enhanced tracklist data to JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Results saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving results: {e}")


def process_tracklists(tracklists, discogs_token=None, enable_discogs=True):
    """Process all tracklists and enhance with multi-platform search results."""
    
    # Initialize the search manager
    manager = SearchManager(discogs_token=discogs_token)
    
    # Disable Discogs if requested
    if not enable_discogs:
        manager.disable_platform('discogs')
        print("ℹ️  Discogs disabled - using YouTube only")
    
    print(f"🎵 Processing {len(tracklists)} tracklist entries...")
    print(f"🔍 Enabled platforms: {', '.join(manager.enabled_platforms)}")
    
    total_tracks = 0
    successful_searches = {'youtube': 0, 'discogs': 0}
    
    for i, tracklist_entry in enumerate(tracklists):
        print(f"\n{'='*80}")
        print(f"📀 Tracklist {i+1}/{len(tracklists)}: {tracklist_entry.get('title', 'Unknown')}")
        print(f"{'='*80}")
        
        tracks = tracklist_entry.get('tracks', [])
        if not tracks:
            print("⚠️  No tracks found in this entry")
            continue
        
        print(f"🎵 Processing {len(tracks)} tracks...")
        
        # Process each track
        enhanced_tracks = []
        for j, track_info in enumerate(tracks):
            # Handle both old format (string) and new format (dict)
            if isinstance(track_info, str):
                track_name = track_info
            else:
                track_name = track_info.get('track', str(track_info))
            
            print(f"\n  {j+1}/{len(tracks)}. {track_name}")
            total_tracks += 1
            
            # Search across all platforms
            search_result = manager.search_track(track_name)
            
            # Count successful searches
            for platform, result in search_result['platforms'].items():
                if result['url']:
                    successful_searches[platform] = successful_searches.get(platform, 0) + 1
                    print(f"    ✅ {platform.title()}: Found")
                else:
                    print(f"    ❌ {platform.title()}: {result.get('error', 'Not found')}")
            
            # Show best match
            best = search_result['best_match']
            if best['platform']:
                print(f"    🏆 Best match: {best['platform'].title()} (confidence: {best['confidence']:.2f})")
            
            enhanced_tracks.append(search_result)
        
        # Update the tracklist entry with enhanced tracks
        tracklist_entry['tracks'] = enhanced_tracks
        
        print(f"\n✅ Completed tracklist {i+1}")
    
    # Print summary
    print(f"\n{'='*80}")
    print("🏁 SEARCH SUMMARY")
    print(f"{'='*80}")
    print(f"📊 Total tracks processed: {total_tracks}")
    
    for platform, count in successful_searches.items():
        success_rate = (count / total_tracks * 100) if total_tracks > 0 else 0
        print(f"🎯 {platform.title()} matches: {count}/{total_tracks} ({success_rate:.1f}%)")
    
    return tracklists


def main():
    """Main function."""
    print("🎵 Enhanced Multi-Platform Track Search")
    print("=" * 50)
    
    # Load environment variables from .env file
    if load_env():
        print("🔧 Loaded environment variables from .env file")
    
    # Check for Discogs token (optional)
    discogs_token = os.environ.get('DISCOGS_TOKEN')
    if discogs_token:
        print("🔑 Using Discogs API token from environment")
    else:
        print("⚠️  No Discogs token found - using public API (heavily rate limited)")
        print("   Discogs public API allows ~25 requests/minute")
        print("   For better results, get a free token at: https://www.discogs.com/settings/developers")
        print("   Then set: export DISCOGS_TOKEN='your_token_here'")
        
        # Ask user if they want to continue
        response = input("\n   Continue with limited Discogs access? (y/n): ").lower()
        if response != 'y':
            print("   Tip: You can also disable Discogs in the script and use YouTube only")
            return
    
    # Load tracklists
    tracklists = load_tracklists()
    if not tracklists:
        return
    
    # Process tracklists
    enhanced_tracklists = process_tracklists(tracklists, discogs_token)
    
    # Save results
    save_results(enhanced_tracklists)
    
    print("\n🎉 Enhanced search complete!")


if __name__ == "__main__":
    main()
