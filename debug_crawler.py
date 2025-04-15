#!/usr/bin/env python
import os
import sys
import logging
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('debug_crawler')

# URL to test
url = "https://www.tripadvisor.ca/Restaurant_Review-g155004-d683500-Reviews-Ceylonta_Restaurant-Ottawa_Ontario.html"

# Headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Fetch the page
try:
    logger.info(f"Fetching URL: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    logger.info(f"Response status: {response.status_code}")
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check for restaurant name
    logger.info("Looking for restaurant name...")
    name_element = soup.select('h1.HjBfq')
    if name_element:
        logger.info(f"Found name element: {name_element[0].text.strip()}")
    else:
        logger.warning("Name element not found with selector 'h1.HjBfq'")
        # Try a few other selectors that might match
        alt_selectors = ['h1', '.HjBfq', '.QjLKt', '.fHibz', '.eCPON']
        for selector in alt_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found potential name elements with '{selector}': {[e.text.strip() for e in elements[:3]]}")
    
    # Check for rating
    logger.info("Looking for rating...")
    rating_element = soup.select('span.ZDEqb')
    if rating_element:
        logger.info(f"Found rating element: {rating_element[0].text.strip()}")
    else:
        logger.warning("Rating element not found with selector 'span.ZDEqb'")
        # Try other selectors
        alt_selectors = ['.ZDEqb', '.bvcwU', '.UctUV', '.cNJsk']
        for selector in alt_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found potential rating elements with '{selector}': {[e.text.strip() for e in elements[:3]]}")
    
    # Check for reviews
    logger.info("Looking for reviews...")
    review_elements = soup.select('.review-container')
    if review_elements:
        logger.info(f"Found {len(review_elements)} review elements")
        for i, review in enumerate(review_elements[:2]):
            logger.info(f"Review {i+1} sample: {review.get_text()[:100]}...")
    else:
        logger.warning("Review elements not found with selector '.review-container'")
        # Try other selectors
        alt_selectors = ['.review', '.cWwQK', '.dDKKM', '.glbfwR']
        for selector in alt_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found {len(elements)} potential review elements with '{selector}'")
    
    # Save HTML for inspection
    with open('tripadvisor_debug.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    logger.info("Saved HTML to tripadvisor_debug.html")

except Exception as e:
    logger.error(f"Error: {str(e)}")
    
logger.info("Debug completed")