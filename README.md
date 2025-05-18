#Cross-media Social Media Content Scraper for SlateMate

A powerful and efficient social media content scraper that collects data from Instagram and YouTube while respecting platform terms of service.

## Overview

SlateMate is a Python-based tool designed to scrape content from Instagram hashtags and YouTube search results. It extracts comprehensive metadata and automatically downloads thumbnail images. The tool is built with a focus on reliability, efficiency, and maintainability.


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
  - Image URL
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

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/y/SlateMate.git
   cd SlateMate
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `config.json` file with your credentials:
   ```json
   {
     "instagram": {
       "username": "your_instagram_username",
       "password": "your_instagram_password"
     },
     "youtube_api_key": "your_youtube_api_key",
     "thumbnail_directory": "thumbnails"
   }
   ```

5. Install Playwright browsers:
   ```
   playwright install chromium
   ```

## Usage

Run the scraper using the command-line interface:

### Instagram Scraping

```bash
python scrape_posts.py --platform instagram --target foodie --limit 25
```

### YouTube Scraping

```bash
python scrape_posts.py --platform youtube --target "cooking recipes" --limit 30
```

### Command-line Arguments

- `--platform`: The platform to scrape (Required, choices: 'instagram', 'youtube')
- `--target`: Search term or hashtag to scrape (Required)
- `--limit`: Maximum number of posts to retrieve (Optional, default: 50)

## Data Storage

All scraped data is stored in a single `metadata.csv` file in the main directory. When running the scraper multiple times, new data is appended to the existing file.

The CSV file contains all metadata from both platforms, with platform-specific fields where appropriate.

## Recent Improvements

1. **Enhanced Error Handling**:
   - Added robust error handling for network issues
   - Implemented retry mechanisms for failed requests
   - Improved logging of errors and warnings

2. **Better Post Processing**:
   - Improved detection and extraction of hashtags
   - Enhanced text cleaning for better UTF-8 compatibility
   - Added duplicate post detection

3. **Optimized Scrolling and Loading**:
   - Implemented more efficient scrolling for Instagram
   - Added detection for "Load more" buttons
   - Improved handling of end-of-content detection

4. **Unified Data Storage**:
   - Consolidated output to a single metadata.csv file
   - Added append functionality to preserve existing data
   - Improved CSV handling with pandas for better reliability

5. **Command-line Interface**:
   - Simplified command-line arguments
   - Added better error messages for missing arguments
   - Improved progress reporting during scraping

## Notes

- The scraper respects platform terms of service by only accessing publicly available content.
- When the script completes, you may see asyncio pipe errors on Windows systems. These are harmless and don't affect the scraped data.
- For large scrapes, be mindful of API rate limits (especially for YouTube).

## License

MIT License

## Disclaimer

This tool is intended for educational purposes only. Users are responsible for ensuring their use of this tool complies with the terms of service of the platforms being scraped.
