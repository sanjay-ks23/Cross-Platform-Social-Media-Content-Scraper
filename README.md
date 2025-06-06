# Cross-media Social Media Content Scraper

A powerful and efficient social media content scraper that collects data from Instagram and YouTube.

## Overview

This is a Python-based tool designed to scrape content from Instagram hashtags and YouTube search results. It extracts comprehensive metadata and automatically downloads thumbnail images. The tool is built with a focus on reliability, efficiency, and maintainability.


## Platforms Scraped

### Instagram
- Uses Playwright for browser automation
- Scrapes hashtag search results
- Extracts post metadata including:
  - Post text/caption
  - Hashtags
  - Author/username
  - Timestamp
  - Like count
  - Image URL(Also tried to scrape comments but comments count couldn't be scraped)
  - Thumbnail image

### YouTube
- Uses the official YouTube Data API
- Searches for videos by query terms
- Extracts video metadata including:
  - Title and description
  - Channel name
  - Publish date
  - View count
  - Like count
  - Comment count
  - Video URL
  - Thumbnail image

## Technical Implementation

### Architecture

SlateMate uses a class hierarchy with a `BaseScraper` parent class that provides a common interface for all scrapers. Platform-specific implementations (`InstagramScraper` and `YouTubeScraper`) inherit from this base class and implement their own scraping logic.

The system uses asynchronous programming (asyncio) for efficient network operations, particularly for the Instagram scraper which requires browser automation.

### Key Components

- **scrapers.py**: Contains the core scraping logic with the `BaseScraper`, `InstagramScraper`, and `YouTubeScraper` classes
- **scrape_posts.py**: Command-line interface to run the scrapers
- **config.json**: Configuration file for API keys and credentials
- **thumbnails/**: Directory for downloaded thumbnail images
- **metadata.csv**: CSV file containing all scraped data


## Challenges and Solutions

### Instagram Scraping Challenges

1. **Browser Automation Migration**
   - Initially used Selenium but switched to Playwright due to better performance and reliability
   - Required significant code restructuring and adaptation to Playwright
   - Solution: Implemented a modular design that made the transition smoother

2. **Text Processing Issues**
   - Special characters in Instagram posts caused encoding problems
   - Some characters couldn't be properly handled even with regex
   - Solution: Implemented comprehensive regex patterns and UTF-8 encoding handling

3. **Error Handling and Logging**
   - Required extensive error handling for network issues and timeouts
   - Solution: Implemented comprehensive logging system and fallback mechanisms
   - Added retry logic for failed requests

### YouTube Scraping
- No significant challenges encountered
- YouTube Data API provided stable and reliable access to required data

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/y/SlateMate.git
   cd "YOUR_FOLDER_NAME"
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate or by navigating to the activate.ps1 file and running it manually 
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
   playwright install chromium
   ```

## Getting YouTube API Key
Go to the [Google Cloud Console](https://console.cloud.google.com/)
Create a new project or select an existing one
Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"
Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the generated API key
4. Create a `config.json` file with your credentials:
   ```json
   {
     "instagram": {
       "username": "INSTAGRAM_USERNAME",
       "password": "INSTAGRAM_PASSWORD"
     },
     "youtube_api_key": "YOUTUBE_API_KEY", #Paste your copied API key here 
     "thumbnail_directory": "thumbnails"
     "output_file": "metadata.csv"
   }
   ```

## Features Implemented

- Multi-platform support for both YouTube and Instagram
- Headless browser mode for Instagram scraping
- Intelligent page scroll detection
- CLI progress bar and detailed logging
- Comprehensive error handling and retry mechanisms
- Unified data storage in CSV format
  
## Usage

Run the scraper using the command-line interface:

### Instagram Scraping

```bash
python scrape_posts.py --platform instagram --target puppy --limit 25
```

### YouTube Scraping

```bash
python scrape_posts.py --platform youtube --target "machine Learning" --limit 25
```

### Command-line Arguments

- `--platform`: The platform to scrape (Required, choices: 'instagram', 'youtube')
- `--target`: Search term or hashtag to scrape (Required)
- `--limit`: Maximum number of posts to retrieve (Optional, default: 50)


## Data Storage

All scraped data is stored in a single `metadata.csv` file in the main directory. When running the scraper multiple times, new data is appended to the existing file.

The CSV file contains all metadata from both platforms, with platform-specific fields where appropriate.


## Notes

- The scraper respects platform terms of service by only accessing publicly available content.
- When the script completes, you may see asyncio pipe errors on Windows systems. These are harmless and don't affect the scraped data.
- For large scrapes, be mindful of API rate limits for Youtube.

## License

MIT License

## Disclaimer

This tool is intended for educational purposes only. Users are responsible for ensuring their use of this tool complies with the terms of service of the platforms being scraped.
