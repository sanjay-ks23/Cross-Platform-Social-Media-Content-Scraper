import asyncio
import os
import re
from datetime import datetime
import json
import time
from tqdm import tqdm
import requests

# For Instagram
from playwright.async_api import async_playwright, TimeoutError

# For YouTube
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Setup logging if not already configured
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

def ensure_dir_exists(directory):
    #Ensure directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def download_thumbnail(image_url, file_id, thumbnail_dir=None):
    '''Download and save thumbnail image
    Use thumbnail directory from config if not specified'''

    if thumbnail_dir is None:
        config = load_config()
        thumbnail_dir = config.get('thumbnail_directory', 'thumbnails')
        
    ensure_dir_exists(thumbnail_dir)
    
    try:
        # Extract proper file extension from URL or use jpg as default
        file_extension = 'jpg'
        if '.' in image_url.split('?')[0].split('/')[-1]:
            url_extension = image_url.split('?')[0].split('/')[-1].split('.')[-1].lower()
            # Only use valid image extensions
            if url_extension in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'heic']:
                file_extension = url_extension
        
        # Clean the file_id to avoid issues with special characters
        safe_file_id = "".join([c for c in file_id if c.isalnum() or c in '_-'])
        
        # Create the file path with proper extension
        file_path = os.path.join(thumbnail_dir, f"{safe_file_id}.{file_extension}")
        
        # Check if file already exists to avoid re-downloading
        if os.path.exists(file_path):
            logger.info(f"Thumbnail already exists: {file_path}")
            return True
            
        # Download the image with timeout and proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(image_url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Thumbnail saved to {file_path}")
            return True
        else:
            logger.warning(f"Failed to download thumbnail, status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error downloading thumbnail: {str(e)}")
        return False

def load_config(config_file='config.json'):
    #Load configuration from JSON file
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_file}")
            return config
        else:
            logger.warning(f"Config file {config_file} not found, using default settings")
            return {}
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {}

# A parent Scraper class for both InstagramScraper and YouTubeScraper classes, providing common interface and functionality.
class BaseScraper:
    """
    Base class for both scrapers.
    Provides common functionality and a unified interface.
    """
    
    @classmethod
    async def scrape(cls, query, limit=50):
        """
        Unified interface for scraping from any platform.
        Handles both synchronous and asynchronous implementations.
        
        Args:
            query: Search term or hashtag
            limit: Maximum number of items to retrieve
            
        Returns:
            List of post data dictionaries or empty list if scraping fails
        """
        logger.info(f"Starting {cls.__name__} for '{query}' with limit {limit}")
        
        try:
            # Check if the _execute_scrape method is a coroutine (async)
            import inspect
            if inspect.iscoroutinefunction(cls._execute_scrape):
                # Call async implementation
                return await cls._execute_scrape(query, limit) #this call will implement the instagram scraper
            else:
                # Call synchronous implementation
                return cls._execute_scrape(query, limit) #this call will implement the youtube scraper
        except ValueError as e:
            logger.error(str(e))
            return []
        except Exception as e:
            logger.error(f"{cls.__name__} scraping failed: {str(e)}")
            return []

#------------ INSTAGRAM SCRAPER USING PLAYWRIGHT ------------#

class InstagramScraper(BaseScraper):
    def __init__(self, credentials=None):
        #Initialize Instagram scraper with credentials from config file
        config = load_config()
        instagram_config = config.get('instagram', {})
        
        # Use credentials strictly from config file without fallbacks
        if not instagram_config.get('username') or not instagram_config.get('password'):
            raise ValueError("Instagram credentials missing in config.json")
            
        self.username = instagram_config.get('username')
        self.password = instagram_config.get('password')
        
        # Use thumbnail directory from config if available
        self.thumbnail_dir = config.get('thumbnail_directory', 'thumbnails')
        logger.info(f"Using Instagram username: {self.username}")
        logger.info(f"Using thumbnail directory: {self.thumbnail_dir}")
        
        self.browser = None
        self.context = None
        self.page = None
        self.posts_data = []
        
        # Create thumbnail directory if it doesn't exist
        ensure_dir_exists(self.thumbnail_dir)

    async def setup_browser(self):
        #Initialize Playwright browser
        playwright = await async_playwright().start()
        
        # Using fixed screen dimensions
        logger.info("Using fixed screen dimensions: 1920x1080")
        
        # Launch browser
        self.browser = await playwright.chromium.launch(
            headless=False, 
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-notifications',
                '--start-maximized',
                '--disable-extensions',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                f'--window-size={1920},{1080}',# can have a default value set to 1920 x 1080 or we can dynamicaly get the user system dimentions to open the browser
                '--enable-unsafe-swiftshader'
            ]
        )
        # Configure context to bypass automation detection
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            has_touch=False,
            locale='en-US',
            timezone_id='Asia/Kolkata',
            screen={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Create a new page
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(30000)
        
        logger.info("Browser setup complete")

    async def login(self):
        #Login to Instagram
        try:
            logger.info("Attempting to login to Instagram")
            await self.page.goto("https://www.instagram.com/", wait_until="networkidle")
            await asyncio.sleep(2)

            # Enter username
            await self.page.fill("input[name='username']", self.username)
            await asyncio.sleep(1)
            
            # Enter password
            await self.page.fill("input[name='password']", self.password)
            await asyncio.sleep(1)
            
            # Click login button
            await self.page.click("button[type='submit']")
            logger.info("Login credentials submitted")
            
            # Wait for login to complete
            await asyncio.sleep(5)
            
            # Verify login success by checking for Home icon
            try:
                await self.page.wait_for_selector("svg[aria-label='Home']", timeout=10000)
                logger.info("Successfully logged in")
                return True
            except TimeoutError:
                logger.error("Login verification failed - Home icon not found")
                return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def search_hashtag(self, hashtag):
        #Search Instagram for hashtag
        logger.info(f"Searching for hashtag: {hashtag}")
        
        try:
            # Click on search icon
            await self.page.click("svg[aria-label='Search']")
            logger.info("Clicked on search icon")
            await asyncio.sleep(2)
            
            # Find search input and type hashtag
            search_input = await self.page.wait_for_selector("input[placeholder='Search']", timeout=5000)
            await search_input.fill(f"#{hashtag}")
            logger.info(f"Entered search text: #{hashtag}")
            await asyncio.sleep(3)
            
            # Look for search results and try to click on the hashtag
            hashtag_result = self.page.locator(f"span:has-text('#{hashtag}')")
            if await hashtag_result.count() > 0:
                await hashtag_result.first.click()
                logger.info(f"Clicked on #{hashtag} in search results")
                await asyncio.sleep(5)  # Wait for page to load
            else:
                # If no results found, try pressing Enter
                await search_input.press("Enter")
                logger.info("No results found, pressed Enter")
                await asyncio.sleep(2)
                
                # Press Enter again to navigate to hashtag page
                await search_input.press("Enter")
                logger.info("Pressed Enter again")
                await asyncio.sleep(5)  # Wait for page to load
        except Exception as e:
            logger.warning(f"Search using UI failed: {str(e)}")
            
            # Direct URL navigation as fallback
            try:
                logger.info("Trying direct URL navigation to hashtag page")
                await self.page.goto(f"https://www.instagram.com/explore/tags/{hashtag}/", wait_until="networkidle")
                await asyncio.sleep(5)  # Wait for page to load
            except Exception as e2:
                logger.error(f"Direct navigation failed: {str(e2)}")
                return False
        
        # Verify posts are loaded - using different CSS selectors
        try:
            # Look for the grid of posts
            await self.page.wait_for_selector("div._aabd._aa8k._al3l", timeout=10000)
            logger.info(f"Successfully loaded posts grid for #{hashtag}")
            return True
        except TimeoutError:
            # Try a different selector if the first one fails
            try:
                await self.page.wait_for_selector("div._aagv", timeout=5000)
                logger.info(f"Successfully loaded posts using alternate selector for #{hashtag}")
                return True
            except TimeoutError:
                logger.error("No posts found for the hashtag - grid not detected")
                return False
        
        return False

    async def scroll_and_scrape(self, post_limit):
        #Scroll through posts and scrape data
        posts_scraped = 0
        last_height = await self.page.evaluate("document.body.scrollHeight")
        processed_ids = set()  # Track already processed post IDs to avoid duplicates
        
        with tqdm(total=post_limit, desc="Scraping posts") as pbar:
            while posts_scraped < post_limit:
                try:
                    # Find all post containers in the grid using different selectors
                    post_containers = await self.page.query_selector_all("div._aagv")
                    if not post_containers:
                        # Try alternative selectors if the first one fails
                        post_containers = await self.page.query_selector_all("div._aabd._aa8k._al3l")
                    
                    if not post_containers:
                        logger.warning("Could not find any post containers with known selectors")
                        # Try a very generic selector as last resort
                        post_containers = await self.page.query_selector_all("article div[role='button'] img")
                    
                    logger.info(f"Found {len(post_containers)} visible posts on the page")
                    
                    # Process visible posts
                    posts_processed_in_batch = 0
                    for i in range(min(len(post_containers), post_limit - posts_scraped)):
                        if posts_scraped >= post_limit:
                            break
                            
                        # Process each post
                        post_data = await self._process_post(post_containers[i], posts_scraped + 1)
                        
                        if post_data:
                            # Check if we've already processed this post (avoid duplicates)
                            if post_data['post_id'] not in processed_ids:
                                processed_ids.add(post_data['post_id'])
                                self.posts_data.append(post_data)
                                
                                # Download thumbnail
                                thumbnail_success = download_thumbnail(
                                    post_data['image_url'], 
                                    post_data['post_id'], 
                                    self.thumbnail_dir
                                )
                                
                                if thumbnail_success:
                                    logger.info(f"Downloaded thumbnail for post {post_data['post_id']}")
                                
                                posts_scraped += 1
                                posts_processed_in_batch += 1
                                pbar.update(1)
                                
                                # Log progress
                                logger.info(f"Successfully scraped post {posts_scraped}/{post_limit}")

                    if posts_scraped >= post_limit:
                        logger.info(f"Reached target of {post_limit} posts")
                        break
                    
                    if posts_processed_in_batch == 0:
                        logger.warning("No new posts were processed in this batch, attempting more aggressive scrolling")
                        # More aggressive scrolling if we're not finding new posts
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight + 2000)")
                        await asyncio.sleep(3)
                        
                        # Try clicking "Load more" button if it exists
                        try:
                            load_more = self.page.locator("text=Load more")
                            if await load_more.count() > 0:
                                logger.info("Found 'Load more' button, clicking it")
                                await load_more.first.click()
                                await asyncio.sleep(3)
                        except Exception as e:
                            logger.debug(f"No 'Load more' button found: {str(e)}")
                        
                    # Scroll down to load more posts
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # Check if page has new content
                    new_height = await self.page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        # Try scrolling more aggressively
                        for _ in range(3):  # Try multiple small scrolls
                            await self.page.evaluate(f"window.scrollTo(0, {last_height + 1000})")
                            await asyncio.sleep(1)
                        
                        new_height = await self.page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            logger.info("Reached end of scrollable content, no more posts to load")
                            break
                    
                    last_height = new_height
                    logger.info(f"Scrolled to new content, new height: {new_height}")
                    await asyncio.sleep(1)  # Give some time for posts to render
                    
                except Exception as e:
                    logger.error(f"Error during scrolling: {str(e)}")
                    # Try to continue despite errors
                    await asyncio.sleep(2)
                    
        logger.info(f"Completed scraping with {posts_scraped} posts")
        return self.posts_data

    async def _process_post(self, post_container, post_number):
        #Process a single post
        try:
            # Click on the post to open it
            await post_container.click()
            logger.info(f"Clicked on post {post_number}")
            await asyncio.sleep(3)  # Wait for post to open
            
            # Extract data from the opened post
            post_data = await self._extract_post_data()
            
            # Close the modal by pressing Escape
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)  # Wait for modal to close
            
            return post_data
                
        except Exception as e:
            logger.warning(f"Error processing post {post_number}: {str(e)}")
            # Try to close any open modal if there was an error
            try:
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(1)
            except:
                pass
            
            return None

    async def _extract_post_data(self):
        #Extract comprehensive metadata from an opened post"""
        try:
            # Get the image URL from the modal
            img = await self.page.query_selector("div[role='dialog'] article img")
            if not img:
                logger.warning("Could not find image in modal")
                return None
                
            image_url = await img.get_attribute('src')
            
            # Extract post ID - try multiple methods
            post_id = None
            
            # Method 1: Try to get post ID from URL in the address bar
            try:
                current_url = await self.page.evaluate("window.location.href")
                if '/p/' in current_url:
                    # Format: https://www.instagram.com/p/[POST_ID]/
                    post_id = current_url.split('/p/')[1].split('/')[0]
                    logger.info(f"Extracted post ID from URL: {post_id}")
            except Exception as e:
                logger.debug(f"Could not extract post ID from URL: {str(e)}")
            
            # Method 2: Extract from image URL if method 1 failed
            if not post_id:
                try:
                    # Extract the filename part from the URL
                    filename = image_url.split('/')[-1].split('?')[0]
                    # Most Instagram image filenames start with the post ID
                    if '_' in filename:
                        post_id = filename
                        logger.info(f"Extracted post ID from image filename: {post_id}")
                except Exception as e:
                    logger.debug(f"Could not extract post ID from image URL: {str(e)}")
            
            # Method 3: Fallback - use image URL hash if all else fails
            if not post_id:
                import hashlib
                post_id = hashlib.md5(image_url.encode()).hexdigest()[:16]
                logger.info(f"Generated fallback post ID using hash: {post_id}")
            
            # Extract author/username
            author = ""
            try:
                author_elem = await self.page.query_selector("div[role='dialog'] header a")
                if author_elem:
                    author = await author_elem.inner_text()                      
                # Clean up author text
                author = self._clean_text(author)
            except Exception as e:
                logger.warning(f"Could not extract author: {str(e)}")
            
            # Extract post caption/text
            post_text = ""
            try:
                # Try multiple selectors for post text
                caption_selectors = [
                    "div[role='dialog'] ul div > span",
                    "div[role='dialog'] h1", 
                    "div[role='dialog'] div[role='button'] > span",
                    "div[role='dialog'] span[dir='auto']"
                ]
                
                for selector in caption_selectors:
                    caption_elem = await self.page.query_selector(selector)
                    if caption_elem:
                        caption_text = await caption_elem.inner_text()
                        if caption_text and len(caption_text) > 5:  # Ensure it's not an empty or very short string
                            post_text = self._clean_text(caption_text)
                            break
            except Exception as e:
                logger.warning(f"Could not extract caption: {str(e)}")
            
            # Extract hashtags from post text
            hashtags = []
            if post_text:
                # Find all hashtags using regex
                hashtags = re.findall(r'#(\w+)', post_text)
                
                # Remove hashtags from post_text
                post_text = re.sub(r'#\w+\s*', '', post_text).strip()
                # Clean up any double spaces created by hashtag removal
                post_text = ' '.join(post_text.split())
            
            # Extract timestamp if available
            timestamp = ""
            try:
                # Try to find the post timestamp
                time_elem = await self.page.query_selector("div[role='dialog'] time")
                if time_elem:
                    datetime_attr = await time_elem.get_attribute('datetime')
                    if datetime_attr:
                        timestamp = datetime_attr
                    else:
                        # If datetime attribute not available, use the text
                        timestamp = await time_elem.inner_text()
            except Exception as e:
                logger.warning(f"Could not extract timestamp: {str(e)}")
                
            # If no timestamp found, use current time
            if not timestamp:
                timestamp = datetime.now().isoformat()
                
            # Extract likes count
            likes = ""
            try:
                #Look for specific like count text
                likes_selectors = [
                    "div[role='dialog'] section span span",
                    "div[role='dialog'] section span a span",
                    "div[role='dialog'] a span span",
                    "div[role='dialog'] div:has-text('likes')",
                    "div[role='dialog'] div:has-text('like')"
                ]
                
                for selector in likes_selectors:
                    likes_elem = await self.page.query_selector(selector)
                    if likes_elem:
                        likes_text = await likes_elem.inner_text()
                        # Extract numeric value using regex
                        likes_match = re.search(r'(\d+(?:,\d+)*)\s*(?:like|likes)', likes_text.lower())
                        if likes_match:
                            # Remove commas and convert to string
                            likes = likes_match.group(1).replace(',', '')
                            logger.info(f"Found likes count: {likes}")
                            break
                
            except Exception as e:
                logger.warning(f"Could not extract likes: {str(e)}")
            
            # Extract comments count
            comments = ""
            try:
                # Approach 1: Look for text containing "comments" or "comment"
                comments_patterns = [
                    r'(\d+(?:,\d+)*)\s*comments',
                    r'(\d+(?:,\d+)*)\s*comment',
                    r'view all\s*(\d+(?:,\d+)*)\s*comments'
                ]
                
                # Find elements that might contain comment counts
                comment_selectors = [
                    "div[role='dialog'] span:has-text('comment')",
                    "div[role='dialog'] a:has-text('comment')",
                    "div[role='dialog'] div:has-text('comment')"
                ]
                
                for selector in comment_selectors:
                    comments_elem = await self.page.query_selector(selector)
                    if comments_elem:
                        comments_text = await comments_elem.inner_text()
                        
                        # Try each pattern
                        for pattern in comments_patterns:
                            match = re.search(pattern, comments_text.lower())
                            if match:
                                comments = match.group(1).replace(',', '')
                                logger.info(f"Found comments count: {comments}")
                                break
                        
                        if comments:
                            break
            except Exception as e:
                logger.warning(f"Could not extract comments count: {str(e)}")
            
            # Compile all the data scraped
            return {
                'post_id': post_id,
                'platform': 'instagram',
                'post_text': post_text,
                'hashtags': ','.join(hashtags),  # Join hashtags for CSV storage
                'timestamp': timestamp,
                'image_url': image_url,
                'likes': likes,
                'comments': comments,
                'author': author,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting post data from modal: {str(e)}")
            return None

    def _clean_text(self, text):
        #Clean and normalize text to avoid encoding issues by trying to replace problematic characters with their closest ASCII equivalents
        if not text:
            return ""
            
        # Replace problematic characters
        text = text.replace('\u2122', '™') 
        text = text.replace('\u00a9', '©') 
        text = text.replace('\u00ae', '®') 
        
        # Replace other common special characters
        text = text.replace('\u2018', "'") 
        text = text.replace('\u2019', "'") 
        text = text.replace('\u201c', '"') 
        text = text.replace('\u201d', '"')
        text = text.replace('\u2013', '-')
        text = text.replace('\u2014', '--')
        
        # Remove zero-width spaces and other invisible characters
        text = text.replace('\u200b', '')  
        text = text.replace('\ufeff', '') 
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

    async def cleanup(self):
        #Close the browser and clean up
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
            
    @classmethod
    async def _execute_scrape(cls, hashtag, limit):
        """
        Instagram-specific implementation of the scrape method
        
        Args:
            hashtag: The hashtag to search for (without # symbol)
            limit: Maximum number of posts to scrape
            
        Returns:
            List of post data dictionaries or empty list if scraping fails
        """
        scraper = cls()  # Create instance of the class
        
        try:
            # Setup browser
            await scraper.setup_browser()
            
            # Login to Instagram
            if await scraper.login():
                # Search for hashtag
                if await scraper.search_hashtag(hashtag):
                    # Scrape posts
                    posts_data = await scraper.scroll_and_scrape(limit)
                    return posts_data
                else:
                    logger.error("Failed to search hashtag")
            else:
                logger.error("Login failed")
        except Exception as e:
            logger.error(f"Instagram scraping failed: {str(e)}")
            raise
        finally:
            # Ensure browser is closed
            await scraper.cleanup()
            
        return []

#------------ YOUTUBE SCRAPER WITH GOOGLE CLOUD YOUTUBE DATA API ------------#

class YouTubeScraper(BaseScraper):
    def __init__(self, api_key=None):
        # Load API key from config.json
        config = load_config()
        
        # Require API key to be in config file
        if not config.get('youtube_api_key'):
            raise ValueError("YouTube API key missing in config.json")
            
        self.api_key = config.get('youtube_api_key')
        logger.info("YouTube API key loaded from config.json")
        
        # Use thumbnail directory from config if available
        self.thumbnail_dir = config.get('thumbnail_directory', 'thumbnails')
        logger.info(f"Using thumbnail directory: {self.thumbnail_dir}")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.posts_data = []
        
        # Create thumbnail directory if it doesn't exist
        ensure_dir_exists(self.thumbnail_dir)

    def search_videos(self, query, max_results=50):
        #Search for videos on YouTube with the given query
        logger.info(f"Searching YouTube for: {query} (limit: {max_results} videos)")
        
        try:
            # Define parameters for search request
            videos_data = []
            next_page_token = None
            results_per_page = min(50, max_results)  # YouTube API allows max 50 per request
            total_retrieved = 0
            
            with tqdm(total=max_results, desc="Retrieving videos") as pbar:
                # Make initial request and handle pagination if needed
                while total_retrieved < max_results:
                    # Calculate remaining results to fetch
                    remaining = max_results - total_retrieved
                    current_results = min(results_per_page, remaining)
                    
                    # Make the search request
                    search_response = self._make_search_request(
                        query, 
                        max_results=current_results, 
                        page_token=next_page_token
                    )
                    
                    if not search_response:
                        break
                    
                    # Process search results
                    items = search_response.get('items', [])
                    if not items:
                        logger.info("No more results found")
                        break
                    
                    # Get additional data for each video
                    for item in items:
                        if item['id']['kind'] == 'youtube#video':
                            video_id = item['id']['videoId']
                            # Get detailed video information
                            video_data = self._get_video_details(video_id)
                            if video_data:
                                videos_data.append(video_data)
                                # Download thumbnail
                                download_thumbnail(video_data['image_url'], video_data['post_id'], self.thumbnail_dir)
                                total_retrieved += 1
                                pbar.update(1)
                    
                    # Check if there are more pages
                    next_page_token = search_response.get('nextPageToken')
                    if not next_page_token or total_retrieved >= max_results:
                        break
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)
            
            self.posts_data = videos_data
            logger.info(f"Successfully retrieved {len(videos_data)} videos")
            return videos_data
        
        except HttpError as e:
            error_content = json.loads(e.content.decode('utf-8'))
            error_message = error_content.get('error', {}).get('message', str(e))
            logger.error(f"YouTube API error: {error_message}")
            return []
        
        except Exception as e:
            logger.error(f"Error searching YouTube: {str(e)}")
            return []
    
    def _make_search_request(self, query, max_results=50, page_token=None):
        #Make a search request to the YouTube API
        try:
            search_params = {
                'q': query,
                'part': 'snippet',
                'maxResults': max_results,
                'type': 'video',
                'order': 'relevance'  
            }
            
            if page_token:
                search_params['pageToken'] = page_token
            
            search_response = self.youtube.search().list(**search_params).execute()
            return search_response
        
        except HttpError as e:
            if e.resp.status in [403, 429]:  # Quota exceeded or rate limiting
                logger.warning(f"API quota issue: {str(e)}")
            logger.error(f"YouTube API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Search request failed: {str(e)}")
            raise
    
    def _get_video_details(self, video_id):
        #Get detailed information about a video
        try:
            # Get video details from the API
            video_response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            ).execute()
            
            if not video_response['items']:
                logger.warning(f"No details found for video ID: {video_id}")
                return None
            
            # Extract the video information
            video_info = video_response['items'][0]
            snippet = video_info['snippet']
            statistics = video_info.get('statistics', {})
            
            # Get best available thumbnail
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = ''
            # Try to get the highest quality thumbnail
            for quality in ['maxres', 'high', 'medium', 'standard', 'default']:
                if quality in thumbnails:
                    thumbnail_url = thumbnails[quality]['url']
                    break
            
            # Clean text fields to avoid encoding issues
            title = self._clean_text(snippet.get('title', ''))
            description = self._clean_text(snippet.get('description', ''))
            channel_title = self._clean_text(snippet.get('channelTitle', ''))
            
            # Extract hashtags from description
            hashtags = re.findall(r'#(\w+)', description)
            
            # Remove hashtags from description
            description = re.sub(r'#\w+\s*', '', description).strip()
            # Clean up any double spaces created by hashtag removal
            description = ' '.join(description.split())
            
            # Format the data similar to Instagram scraper format to make the appending process easier
            video_data = {
                'post_id': video_id,
                'platform': 'youtube',
                'post_text': f"{title}\n\n{description}",
                'hashtags': ','.join(hashtags),
                'timestamp': snippet.get('publishedAt', ''),
                'image_url': thumbnail_url,
                'likes': statistics.get('likeCount', ''),
                'comments': statistics.get('commentCount', ''),
                'author': channel_title,
                'view_count': statistics.get('viewCount', ''),
                'duration': video_info.get('contentDetails', {}).get('duration', ''),
                'channel_id': snippet.get('channelId', ''),
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'scraped_at': datetime.now().isoformat()
            }
            
            return video_data
            
        except HttpError as e:
            logger.warning(f"API error getting video details for {video_id}: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Error getting video details for {video_id}: {str(e)}")
            return None

    def _clean_text(self, text):
        #Clean and normalize text to avoid encoding issues
        if not text:
            return ""
            
        # Replace problematic characters
        text = text.replace('\u2122', '™')  
        text = text.replace('\u00a9', '©') 
        text = text.replace('\u00ae', '®') 
        
        # Replace other common special characters
        text = text.replace('\u2018', "'")  
        text = text.replace('\u2019', "'")  
        text = text.replace('\u201c', '"') 
        text = text.replace('\u201d', '"') 
        text = text.replace('\u2013', '-') 
        text = text.replace('\u2014', '--')  
        
        # Remove zero-width spaces and other invisible characters
        text = text.replace('\u200b', '')  
        text = text.replace('\ufeff', '') 
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

    @classmethod
    def _execute_scrape(cls, query, limit):
        """
        YouTube-specific implementation of the scrape method
        
        Args:
            query: Search terms to find videos
            limit: Maximum number of videos to retrieve
            
        Returns:
            List of video data dictionaries or empty list if scraping fails
        """
        # Initialize the scraper with API key from config
        scraper = cls()
        
        # Search for videos and collect data
        videos_data = scraper.search_videos(query, limit)
        return videos_data 