#!/usr/bin/env python3
import asyncio
import argparse
import os
import json
import csv
import pandas as pd
from datetime import datetime
from scrapers import InstagramScraper, YouTubeScraper

async def run_instagram_scraper(target, limit):
    print(f"Starting Instagram scraper for '{target}' with limit {limit}")
    posts = await InstagramScraper.scrape(target, limit)
    
    if posts:
        print(f"Successfully scraped {len(posts)} Instagram posts")
    else:
        print("No Instagram posts were scraped")
    
    return posts

async def run_youtube_scraper(target, limit):
    print(f"Starting YouTube scraper for '{target}' with limit {limit}")
    # The BaseScraper.scrape method is async, so we need to await it
    posts = await YouTubeScraper.scrape(target, limit)
    
    if posts:
        print(f"Successfully scraped {len(posts)} YouTube videos")
    else:
        print("No YouTube videos were scraped")
    
    return posts

def save_to_metadata_csv(posts, filename='metadata.csv'):
    """Save or append scraped posts to the metadata.csv file"""
    if not posts:
        print("No data to save")
        return
    
    # Convert posts to DataFrame
    df_new = pd.DataFrame(posts)
    
    # Check if metadata.csv exists
    if os.path.exists(filename):
        try:
            # Read existing data
            df_existing = pd.read_csv(filename, encoding='utf-8')
            print(f"Found existing metadata.csv with {len(df_existing)} records")
            
            # Append new data
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            
            # Save combined data
            df_combined.to_csv(filename, index=False, encoding='utf-8')
            print(f"Added {len(df_new)} new posts to {filename}")
            print(f"Total posts in {filename}: {len(df_combined)}")
        except Exception as e:
            df_new.to_csv(filename, index=False, encoding='utf-8')
            print(f"Saved {len(df_new)} posts to new {filename}")
    else:
        # Create new file
        df_new.to_csv(filename, index=False, encoding='utf-8')
        print(f"Created new {filename} with {len(df_new)} posts")

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SlateMate Social Media Scraper')
    parser.add_argument('--platform', choices=['instagram', 'youtube'], required=True,
                        help='Platform to scrape (instagram or youtube)')
    parser.add_argument('--target', required=True, help='Search term or hashtag to scrape')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of posts to retrieve')
    
    args = parser.parse_args()
    
    all_posts = []
    
    # Run the selected scraper
    if args.platform == 'instagram':
        instagram_posts = await run_instagram_scraper(args.target, args.limit)
        if instagram_posts:
            all_posts.extend(instagram_posts)
    
    elif args.platform == 'youtube':
        youtube_posts = await run_youtube_scraper(args.target, args.limit)
        if youtube_posts:
            all_posts.extend(youtube_posts)
    
    # Save all collected data to metadata.csv
    if all_posts:
        save_to_metadata_csv(all_posts)
    
    # Print summary
    print("\nScraping Summary:")
    print(f"Total posts scraped: {len(all_posts)}")

if __name__ == "__main__":
    asyncio.run(main()) 