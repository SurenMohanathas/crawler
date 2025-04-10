#!/usr/bin/env python
import argparse
import logging
import os
import sys
from typing import List, Tuple

from dotenv import load_dotenv

from .database import init_db
from .crawler import YelpCrawler, GoogleMapsCrawler, TripAdvisorCrawler

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('restaurant_crawler_main')


def setup_argparse() -> argparse.ArgumentParser:
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description='Restaurant Review Crawler')
    parser.add_argument(
        'source',
        type=str,
        choices=['yelp', 'google', 'tripadvisor', 'all'],
        help='Source platform to crawl (yelp, google, tripadvisor, or all)'
    )
    parser.add_argument(
        'urls',
        type=str,
        nargs='+',
        help='URLs of restaurant pages to crawl'
    )
    parser.add_argument(
        '--max-reviews',
        type=int,
        default=100,
        help='Maximum number of reviews to crawl per restaurant (default: 100)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize the database (create tables)'
    )
    return parser


def get_crawler(source: str) -> Tuple[List, str]:
    """Get the appropriate crawler class based on the source"""
    if source == 'yelp':
        return [YelpCrawler()], 'Yelp'
    elif source == 'google':
        return [GoogleMapsCrawler()], 'Google Maps'
    elif source == 'tripadvisor':
        return [TripAdvisorCrawler()], 'TripAdvisor'
    elif source == 'all':
        return [YelpCrawler(), GoogleMapsCrawler(), TripAdvisorCrawler()], 'all platforms'
    else:
        logger.error(f"Unknown source: {source}")
        sys.exit(1)


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
    
    # Initialize the database if requested
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    
    # Get the crawler class
    crawlers, source_name = get_crawler(args.source)
    logger.info(f"Starting to crawl {source_name} for {len(args.urls)} restaurants")
    
    # Crawl each restaurant
    for url in args.urls:
        for crawler in crawlers:
            crawl_restaurant(crawler, url, args.max_reviews)
    
    logger.info("Crawling completed successfully")


if __name__ == "__main__":
    main()
