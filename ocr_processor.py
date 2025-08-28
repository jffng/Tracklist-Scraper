"""
OCR Processor Module

Handles image processing and track extraction using pytesseract.
This module provides the core functionality for processing tracklist images.
"""

import pytesseract
from PIL import Image
import re
import json
import requests
from typing import List, Dict, Optional
import os


class OCRProcessor:
    """Handles OCR processing of tracklist images."""
    
    def __init__(self):
        """Initialize the OCR processor."""
        self.track_pattern = r'^(.+?)\s*[-–—~|/:=\\]\s*(.+)$'
    
    def process_image(self, image_path: str) -> str:
        """
        Process an image and extract text using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            # Open and process the image
            image = Image.open(image_path)
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(image)
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Error processing image {image_path}: {str(e)}")
    
    def parse_tracks_from_text(self, text: str) -> List[str]:
        """
        Parse track information from extracted text.
        
        Args:
            text: Raw text extracted from image
            
        Returns:
            List of parsed track strings
        """
        tracks = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to match track pattern
            match = re.match(self.track_pattern, line)
            if match:
                part1, part2 = match.groups()
                
                # Clean up the parts - remove track numbers and special characters
                part1 = re.sub(r'^\d+\.?\s*', '', part1)  # Remove leading numbers
                part1 = re.sub(r'^[*#@$%^&_+=|\\<>]*|[*#@$%^&_+=|\\<>]*$', '', part1).strip()
                part2 = re.sub(r'^[*#@$%^&_+=|\\<>]*|[*#@$%^&_+=|\\<>]*$', '', part2).strip()
                
                if part1 and part2:
                    track = f"{part1} - {part2}"
                    tracks.append(track)
        
        return tracks
    
    def process_tracklist_image(self, image_path: str, title: str = None) -> Dict:
        """
        Process a complete tracklist image and return structured data.
        
        Args:
            image_path: Path to the image file
            title: Optional title for the tracklist
            
        Returns:
            Dictionary with tracklist data
        """
        try:
            # Extract text from image
            extracted_text = self.process_image(image_path)
            
            # Parse tracks from text
            tracks = self.parse_tracks_from_text(extracted_text)
            
            # Create tracklist data structure
            tracklist_data = {
                'title': title or f"Tracklist from {os.path.basename(image_path)}",
                'extracted_text': extracted_text,
                'tracks': tracks,
                'image_path': image_path,
                'track_count': len(tracks)
            }
            
            return tracklist_data
            
        except Exception as e:
            raise Exception(f"Error processing tracklist image: {str(e)}")
    
    def process_are_na_channel(self, channel_slug: str) -> List[Dict]:
        """
        Process an Are.na channel to extract tracklists from images.
        
        Args:
            channel_slug: Are.na channel slug
            
        Returns:
            List of tracklist data dictionaries
        """
        try:
            # Fetch channel data from Are.na
            url = f"https://api.are.na/v2/channels/{channel_slug}"
            response = requests.get(url)
            response.raise_for_status()
            
            channel_data = response.json()
            tracklists = []
            
            # Process each block in the channel
            for block in channel_data.get('contents', []):
                if block.get('class') == 'Image':
                    image_url = block.get('image', {}).get('display', {}).get('url')
                    if image_url:
                        # For now, we'll store the image URL and extracted text
                        # In a full implementation, you'd download and process the image
                        tracklist_data = {
                            'title': block.get('title', 'Untitled Tracklist'),
                            'url': image_url,
                            'extracted_text': '',  # Would be filled by OCR processing
                            'tracks': [],  # Would be filled by parsing
                            'are_na_id': block.get('id'),
                            'are_na_slug': block.get('slug')
                        }
                        tracklists.append(tracklist_data)
            
            return tracklists
            
        except Exception as e:
            raise Exception(f"Error processing Are.na channel {channel_slug}: {str(e)}")
    
    def save_tracklist_data(self, tracklist_data: Dict, output_file: str = "tracklist_data.json"):
        """
        Save tracklist data to a JSON file.
        
        Args:
            tracklist_data: Dictionary containing tracklist data
            output_file: Output file path
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracklist_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Tracklist data saved to {output_file}")
            
        except Exception as e:
            raise Exception(f"Error saving tracklist data: {str(e)}")
    
    def load_tracklist_data(self, input_file: str = "tracklist_data.json") -> Dict:
        """
        Load tracklist data from a JSON file.
        
        Args:
            input_file: Input file path
            
        Returns:
            Dictionary containing tracklist data
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except FileNotFoundError:
            print(f"⚠️  File {input_file} not found")
            return {}
        except Exception as e:
            raise Exception(f"Error loading tracklist data: {str(e)}")


def main():
    """Example usage of the OCR processor."""
    processor = OCRProcessor()
    
    # Example: Process a single image
    # tracklist_data = processor.process_tracklist_image("path/to/image.jpg", "My Tracklist")
    # processor.save_tracklist_data(tracklist_data)
    
    # Example: Process Are.na channel
    # tracklists = processor.process_are_na_channel("your-channel-slug")
    # for tracklist in tracklists:
    #     print(f"Found tracklist: {tracklist['title']}")
    
    print("OCR Processor module loaded successfully!")
    print("Use processor.process_tracklist_image() to process individual images")
    print("Use processor.process_are_na_channel() to process Are.na channels")


if __name__ == "__main__":
    main()
