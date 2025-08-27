#!/usr/bin/env python3
"""
Are.na Tracklist OCR Extractor

Fetches images from an are.na channel and extracts text using Tesseract OCR.
"""

import requests
import pytesseract
from PIL import Image
import json
import os
from urllib.parse import urlparse
import tempfile
import hashlib
from io import BytesIO
import re


class ArenaTracklistExtractor:
    def __init__(self, channel_url="https://api.are.na/v2/channels/tracklists-bjgvj5dpt3k/contents"):
        self.channel_url = channel_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Arena Tracklist Extractor 1.0'
        })

    def fetch_channel_data(self):
        """Fetch JSON data from the are.na API endpoint."""
        print(f"Fetching data from: {self.channel_url}")
        try:
            response = self.session.get(self.channel_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching channel data: {e}")
            return None

    def extract_image_urls(self, data):
        """Extract image URLs from the contents array."""
        image_urls = []
        
        if not data or 'contents' not in data:
            print("No contents found in the data")
            return image_urls

        contents = data['contents']
        print(f"Found {len(contents)} items in contents")

        for i, item in enumerate(contents):
            if 'image' in item and item['image']:
                image_obj = item['image']
                if 'large' in image_obj and 'url' in image_obj['large']:
                    url = image_obj['large']['url']
                    title = item.get('title', f'Image {i+1}')
                    image_urls.append({
                        'url': url,
                        'title': title,
                        'index': i
                    })
                    print(f"Found image: {title} -> {url}")

        print(f"Total images found: {len(image_urls)}")
        return image_urls

    def download_and_ocr_image(self, image_url, max_retries=3):
        """Download an image from URL and perform OCR directly in memory."""
        for attempt in range(max_retries):
            try:
                print(f"Downloading image from: {image_url}")
                response = self.session.get(image_url, timeout=30)
                response.raise_for_status()
                
                # Check if we actually got image content
                if len(response.content) < 100:
                    print(f"Downloaded file too small ({len(response.content)} bytes), skipping")
                    return None
                
                print(f"Downloaded {len(response.content)} bytes, processing with OCR...")
                
                # Try to open with PIL to check for corruption
                img = None
                try:
                    img = Image.open(BytesIO(response.content))
                    img.verify()  # Verify the image integrity
                    print("Image verification passed")
                    
                    # Reopen since verify() closes the image
                    img = Image.open(BytesIO(response.content))
                    
                except Exception as e:
                    print(f"Image verification failed: {e}")
                    print("Attempting to load image anyway, ignoring corruption...")
                    try:
                        # Try to load anyway, ignoring errors
                        img = Image.open(BytesIO(response.content))
                        # Force load the image data
                        img.load()
                        print("Successfully loaded potentially corrupted image")
                    except Exception as load_error:
                        print(f"Failed to load image even with error tolerance: {load_error}")
                        if attempt < max_retries - 1:
                            print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                            continue
                        return None
                
                # Handle different image formats, especially PNG
                print(f"Image mode: {img.mode}, format: {img.format}")
                
                # Special handling for PNG images
                if img.format == 'PNG':
                    print("PNG detected - applying special preprocessing...")
                    
                    # Handle transparency in PNG
                    if img.mode in ('RGBA', 'LA'):
                        print("PNG has transparency, converting to white background...")
                        # Create a white background
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                        else:  # LA mode
                            background.paste(img.convert('RGB'))
                        img = background
                    elif img.mode == 'P':
                        print("PNG in palette mode, converting...")
                        img = img.convert('RGB')
                    elif img.mode not in ('RGB', 'L'):
                        print(f"Converting PNG from {img.mode} to RGB")
                        img = img.convert('RGB')
                else:
                    # Standard conversion for non-PNG images
                    if img.mode not in ('RGB', 'L'):
                        print(f"Converting image from {img.mode} to RGB")
                        img = img.convert('RGB')
                
                # Optional: Apply image enhancements for better OCR
                try:
                    from PIL import ImageEnhance, ImageFilter
                    
                    # Convert to grayscale for better OCR if it's not already
                    if img.mode == 'RGB':
                        print("Converting to grayscale for OCR...")
                        img_gray = img.convert('L')
                        
                        # Enhance contrast
                        enhancer = ImageEnhance.Contrast(img_gray)
                        img_enhanced = enhancer.enhance(1.5)  # Increase contrast
                        
                        # Optional: Apply slight sharpening
                        img_enhanced = img_enhanced.filter(ImageFilter.SHARPEN)
                        
                        img = img_enhanced
                except ImportError:
                    print("Image enhancement modules not available, using original image")
                
                # Perform OCR with custom configuration for better text detection
                print("Performing OCR...")
                
                # Try different OCR configurations
                custom_config = r'--oem 3 --psm 6'  # Assume uniform block of text
                try:
                    text = pytesseract.image_to_string(img, config=custom_config)
                except:
                    print("Custom OCR config failed, trying default...")
                    text = pytesseract.image_to_string(img)
                
                result_text = text.strip()
                
                if result_text:
                    print(f"OCR successful! Extracted {len(result_text)} characters")
                    return result_text
                else:
                    print("OCR completed but no text was extracted")
                    return ""
                
            except requests.RequestException as e:
                print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                return None
                
            except Exception as e:
                print(f"Unexpected error processing image (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                return None
        
        print("All retry attempts failed")
        return None

    def parse_tracks_from_text(self, text):
        """Parse tracks from extracted text in the format 'Artist - Track' or 'Track - Artist'."""
        if not text:
            return []
        
        tracks = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for patterns with various separators
            # This regex looks for text, followed by various separators, followed by more text
            # Including: - – — ~ | // \\ :: = --> <-- >> << and double versions
            track_pattern = r'^(.+?)\s*(?:[-–—~|/\\:=]|(?:-->|<--|>>|<<)|(?:--)|(?://)|(?:\\\\)|(?:::))\s*(.+)$'
            match = re.match(track_pattern, line)
            
            if match:
                part1 = match.group(1).strip()
                part2 = match.group(2).strip()
                
                # Skip if either part is too short or contains mainly special characters
                if (len(part1) < 2 or len(part2) < 2 or 
                    re.match(r'^[^\w\s]*$', part1) or re.match(r'^[^\w\s]*$', part2)):
                    continue
                
                # Clean up common OCR artifacts and formatting - only remove truly problematic chars
                part1 = re.sub(r'^[*#@$%^&_+=|\\<>]*|[*#@$%^&_+=|\\<>]*$', '', part1)  # Remove specific problematic chars
                part2 = re.sub(r'^[*#@$%^&_+=|\\<>]*|[*#@$%^&_+=|\\<>]*$', '', part2)
                
                if part1 and part2:
                    # Store the original format, we can't reliably determine which is artist vs track
                    tracks.append(f"{part1} - {part2}")
        
        return tracks

    def process_channel(self):
        """Main method to process the entire channel."""
        print("Starting are.na channel processing...")
        
        # Fetch channel data
        data = self.fetch_channel_data()
        if not data:
            print("Failed to fetch channel data")
            return
        
        # Extract image URLs
        image_urls = self.extract_image_urls(data)
        if not image_urls:
            print("No images found in the channel")
            return
        
        # Process each image
        results = []
        
        for img_info in image_urls:
            print(f"\n{'='*60}")
            print(f"Processing: {img_info['title']}")
            print(f"{'='*60}")
            
            # Download and extract text in one step
            extracted_text = self.download_and_ocr_image(img_info['url'])
            
            if extracted_text:
                # Parse tracks from the extracted text
                tracks = self.parse_tracks_from_text(extracted_text)
                
                result = {
                    'title': img_info['title'],
                    'url': img_info['url'],
                    'extracted_text': extracted_text,
                    'tracks': tracks
                }
                results.append(result)
                print(f"✅ Success! Extracted text length: {len(extracted_text)} characters")
                print(f"🎵 Found {len(tracks)} tracks")
                if len(extracted_text) > 100:
                    print(f"Preview: {extracted_text[:100]}...")
                else:
                    print(f"Full text: {extracted_text}")
                    
                # Show some parsed tracks if any were found
                if tracks:
                    print("Sample tracks:")
                    for i, track in enumerate(tracks[:3]):  # Show first 3 tracks
                        print(f"  {i+1}. {track}")
                    if len(tracks) > 3:
                        print(f"  ... and {len(tracks) - 3} more")
            elif extracted_text == "":
                print("⚠️  Image processed but no text was detected")
            else:
                print("❌ Failed to process this image")
        
        return results

    def save_results(self, results, output_file="extracted_tracklists.json"):
        """Save the extraction results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")


def main():
    """Main function to run the extractor."""
    extractor = ArenaTracklistExtractor()
    
    # Process the channel and extract text from images
    results = extractor.process_channel()
    
    if results:
        print(f"\n{'='*50}")
        print("EXTRACTION RESULTS")
        print(f"{'='*50}")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Extracted Text:\n{result['extracted_text']}")
            print("-" * 50)
        
        # Save results to file
        extractor.save_results(results)
    else:
        print("No text was extracted from any images")


if __name__ == "__main__":
    main()
