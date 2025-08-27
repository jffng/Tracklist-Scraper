# Are.na Tracklist OCR Extractor

This application fetches images from an Are.na channel and extracts text using Tesseract OCR, specifically designed for extracting tracklist information.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR:
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

Run the application:
```bash
python app.py
```

The application will:
1. Fetch data from the are.na channel API
2. Find all images in the channel contents
3. Download each image temporarily
4. Use Tesseract OCR to extract text
5. Display results and save to `extracted_tracklists.json`

## API Endpoint

Currently configured to use: `https://api.are.na/v2/channels/tracklists-bjgvj5dpt3k/contents`

## Output

The extracted text from each image will be displayed in the console and saved to a JSON file for further processing.
