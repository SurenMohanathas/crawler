#!/usr/bin/env python
"""
Selenium-based crawler runner for restaurant reviews.
"""
import os
import sys
import argparse
import logging
from typing import List

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.database import init_db
from src.selenium_crawler import SeleniumTripAdvisorCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'crawler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('selenium_crawler_runner')


def setup_argparse() -> argparse.ArgumentParser:
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description='Selenium-based Restaurant Review Crawler')
    parser.add_argument(
        'urls',
        type=str,
        nargs='+',
        help='URLs of restaurant pages to crawl'
    )
    parser.add_argument(
        '--max-reviews',
        type=int,
        default=50,
        help='Maximum number of reviews to crawl per restaurant (default: 50)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize the database (create tables)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--demo-mode',
        action='store_true',
        help='Run in demo mode with mock data'
    )
    return parser


def crawl_restaurant(crawler, url: str, max_reviews: int) -> None:
    """Crawl a restaurant and its reviews"""
    try:
        logger.info(f"Crawling restaurant: {url}")
        restaurant_data = crawler.crawl_restaurant(url)
        
        if not restaurant_data:
            logger.error(f"Failed to extract restaurant data from {url}")
            return
        
        # Save restaurant to database
        restaurant = crawler.save_restaurant(restaurant_data)
        logger.info(f"Saved restaurant: {restaurant.name} (ID: {restaurant.id})")
        
        # Crawl reviews
        logger.info(f"Crawling reviews for restaurant: {restaurant.name}")
        review_data_list = crawler.crawl_reviews(url, restaurant.id)
        
        # Limit the number of reviews to save
        review_data_list = review_data_list[:max_reviews]
        
        # Save reviews to database
        for review_data in review_data_list:
            review = crawler.save_review(review_data, restaurant.id)
            logger.debug(f"Saved review from {review.reviewer_name} (ID: {review.id})")
        
        logger.info(f"Saved {len(review_data_list)} reviews for {restaurant.name}")
    
    except Exception as e:
        logger.error(f"Error crawling restaurant {url}: {str(e)}")
    
    finally:
        # Close the crawler session
        crawler.close()


def main():
    """Main entry point for the crawler"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Set demo mode if requested
    if args.demo_mode:
        os.environ['DEMO_MODE'] = 'true'
        logger.info("Running in DEMO MODE with mock data")
    else:
        os.environ['DEMO_MODE'] = 'false'
    
    # Initialize the database if requested
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    
    # Create crawler
    crawler = SeleniumTripAdvisorCrawler(headless=args.headless)
    logger.info(f"Starting to crawl {len(args.urls)} restaurants")
    
    # Crawl each restaurant
    for url in args.urls:
        crawl_restaurant(crawler, url, args.max_reviews)
    
    logger.info("Crawling completed successfully")


if __name__ == "__main__":
    main()