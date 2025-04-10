import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .database import Restaurant, Review, get_db_session, init_db

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
logger = logging.getLogger('restaurant_crawler')

# Crawler settings
USER_AGENT = os.getenv('USER_AGENT')
REQUEST_DELAY = int(os.getenv('REQUEST_DELAY', 2))


class BaseCrawler(ABC):
    """Base class for restaurant review crawlers"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.db_session = get_db_session()
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            time.sleep(REQUEST_DELAY)  # Respect the site by waiting between requests
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def save_restaurant(self, restaurant_data: Dict[str, Any]) -> Restaurant:
        """Save restaurant to database"""
        try:
            # Check if restaurant already exists based on source_url
            restaurant = self.db_session.query(Restaurant).filter_by(
                source_url=restaurant_data['source_url']
            ).first()
            
            if restaurant:
                # Update existing restaurant
                for key, value in restaurant_data.items():
                    setattr(restaurant, key, value)
            else:
                # Create new restaurant
                restaurant = Restaurant(**restaurant_data)
                self.db_session.add(restaurant)
            
            self.db_session.commit()
            return restaurant
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving restaurant: {str(e)}")
            raise
    
    def save_review(self, review_data: Dict[str, Any], restaurant_id: int) -> Review:
        """Save review to database"""
        try:
            # Add restaurant_id to review data
            review_data['restaurant_id'] = restaurant_id
            
            # Check if review already exists based on source_id
            review = self.db_session.query(Review).filter_by(
                source_id=review_data['source_id']
            ).first()
            
            if review:
                # Update existing review
                for key, value in review_data.items():
                    setattr(review, key, value)
            else:
                # Create new review
                review = Review(**review_data)
                self.db_session.add(review)
            
            self.db_session.commit()
            return review
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving review: {str(e)}")
            raise
    
    def close(self):
        """Close database session"""
        self.db_session.close()
    
    @abstractmethod
    def crawl_restaurant(self, url: str) -> Dict[str, Any]:
        """Crawl a restaurant page and extract information"""
        pass
    
    @abstractmethod
    def crawl_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Crawl reviews for a restaurant"""
        pass


class YelpCrawler(BaseCrawler):
    """Crawler for Yelp restaurant reviews"""
    
    def crawl_restaurant(self, url: str) -> Dict[str, Any]:
        """Crawl a Yelp restaurant page and extract information"""
        soup = self.fetch_page(url)
        if not soup:
            logger.error(f"Failed to fetch restaurant page: {url}")
            return {}
        
        try:
            # Extract restaurant information
            name = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
            
            # Getting address components
            address_elements = soup.select('[data-testid="bizDetailsAddress"] > p')
            address = address_elements[0].text.strip() if address_elements else ""
            
            # Getting rating
            rating_element = soup.select('[data-testid="rating-stars"]')
            average_rating = float(rating_element[0].get('aria-label', '0').split()[0]) if rating_element else 0.0
            
            # Getting price range
            price_range_element = soup.select('[data-testid="price-category"] > span:first-child')
            price_range = price_range_element[0].text.strip() if price_range_element else ""
            
            # Getting cuisine type
            cuisine_elements = soup.select('[data-testid="price-category"] > span:not(:first-child) a')
            cuisine_type = cuisine_elements[0].text.strip() if cuisine_elements else ""
            
            # Parse address for city, state, postal code
            address_parts = address.split(", ")
            city = address_parts[1] if len(address_parts) > 1 else ""
            state_zip = address_parts[2].split() if len(address_parts) > 2 else []
            state = state_zip[0] if state_zip else ""
            postal_code = state_zip[1] if len(state_zip) > 1 else ""
            
            # Extract phone number
            phone_element = soup.select('[data-testid="bizPhone"]')
            phone = phone_element[0].text.strip() if phone_element else ""
            
            # Extract website if available
            website_element = soup.select('[data-testid="bizWebsite"]')
            website = website_element[0].find('a')['href'] if website_element and website_element[0].find('a') else ""
            
            # Create restaurant data dictionary
            restaurant_data = {
                'name': name,
                'address': address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'phone': phone,
                'website': website,
                'cuisine_type': cuisine_type,
                'price_range': price_range,
                'average_rating': average_rating,
                'source_url': url,
                'source_id': url.split('/')[-1],
                'source_platform': 'yelp',
                'last_updated': datetime.now()
            }
            
            return restaurant_data
        
        except Exception as e:
            logger.error(f"Error parsing restaurant data from {url}: {str(e)}")
            return {}
    
    def crawl_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Crawl Yelp reviews for a restaurant"""
        # Yelp reviews URL format
        reviews_url = f"{url}?sort_by=date_desc"
        soup = self.fetch_page(reviews_url)
        if not soup:
            logger.error(f"Failed to fetch reviews page: {reviews_url}")
            return []
        
        reviews = []
        try:
            # Find review elements
            review_elements = soup.select('[data-testid="reviews-container"] .review')
            
            for review_element in review_elements:
                try:
                    # Extract reviewer info
                    user_element = review_element.select('.user-passport-info a')
                    reviewer_name = user_element[0].text.strip() if user_element else "Anonymous"
                    reviewer_id = user_element[0]['href'].split('=')[-1] if user_element and 'href' in user_element[0].attrs else ""
                    
                    # Extract rating
                    rating_element = review_element.select('.i-stars')
                    rating_text = rating_element[0]['aria-label'] if rating_element else "0 star rating"
                    rating = float(rating_text.split()[0])
                    
                    # Extract review date
                    date_element = review_element.select('.review-date')
                    review_date_text = date_element[0].text.strip() if date_element else ""
                    # Parse date like "10/15/2023"
                    review_date = datetime.strptime(review_date_text, "%m/%d/%Y") if review_date_text else datetime.now()
                    
                    # Extract review text
                    text_element = review_element.select('.review-content p')
                    review_text = text_element[0].text.strip() if text_element else ""
                    
                    # Extract helpful count
                    helpful_element = review_element.select('.useful-count')
                    helpful_count = int(helpful_element[0].text.strip()) if helpful_element and helpful_element[0].text.strip().isdigit() else 0
                    
                    # Create review data dictionary
                    review_data = {
                        'rating': rating,
                        'review_text': review_text,
                        'review_date': review_date,
                        'reviewer_name': reviewer_name,
                        'reviewer_id': reviewer_id,
                        'helpful_count': helpful_count,
                        'source_url': reviews_url,
                        'source_id': f"yelp_{restaurant_id}_{reviewer_id}_{int(review_date.timestamp())}",
                        'source_platform': 'yelp',
                        'crawl_date': datetime.now()
                    }
                    
                    reviews.append(review_data)
                except Exception as e:
                    logger.error(f"Error parsing review: {str(e)}")
            
            return reviews
        
        except Exception as e:
            logger.error(f"Error parsing reviews from {reviews_url}: {str(e)}")
            return []


class GoogleMapsCrawler(BaseCrawler):
    """Crawler for Google Maps restaurant reviews"""
    
    def crawl_restaurant(self, url: str) -> Dict[str, Any]:
        """Crawl a Google Maps restaurant page and extract information"""
        soup = self.fetch_page(url)
        if not soup:
            logger.error(f"Failed to fetch restaurant page: {url}")
            return {}
        
        try:
            # Extract restaurant information (Google Maps structure)
            # Note: Google Maps is more complex due to dynamic loading
            # This is a simplified implementation
            
            # Extract name from h1
            name_element = soup.find('h1')
            name = name_element.text.strip() if name_element else "Unknown"
            
            # Extract address
            address_element = soup.select('button[data-item-id="address"]')
            address = address_element[0].text.strip() if address_element else ""
            
            # Extract rating
            rating_element = soup.select('div.fontDisplayLarge')
            average_rating = float(rating_element[0].text.replace(',', '.')) if rating_element else 0.0
            
            # Extract price range
            price_element = soup.select('span:contains("$")') 
            price_range = price_element[0].text.strip() if price_element else ""
            
            # Extract cuisine type
            cuisine_element = soup.select('.fontBodyMedium > span > span > span')
            cuisine_type = cuisine_element[0].text.strip() if cuisine_element else ""
            
            # Extract phone
            phone_element = soup.select('button[data-item-id="phone:tel"]')
            phone = phone_element[0].text.strip() if phone_element else ""
            
            # Extract website
            website_element = soup.select('a[data-item-id="authority"]')
            website = website_element[0]['href'] if website_element and 'href' in website_element[0].attrs else ""
            
            # Parse address components
            address_parts = address.split(", ")
            city = address_parts[1] if len(address_parts) > 1 else ""
            state_zip = address_parts[2].split() if len(address_parts) > 2 else []
            state = state_zip[0] if state_zip else ""
            postal_code = state_zip[1] if len(state_zip) > 1 else ""
            
            # Create restaurant data dictionary
            restaurant_data = {
                'name': name,
                'address': address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'phone': phone,
                'website': website,
                'cuisine_type': cuisine_type,
                'price_range': price_range,
                'average_rating': average_rating,
                'source_url': url,
                'source_id': url.split('/')[-1] if '/' in url else url,
                'source_platform': 'google',
                'last_updated': datetime.now()
            }
            
            return restaurant_data
        
        except Exception as e:
            logger.error(f"Error parsing restaurant data from {url}: {str(e)}")
            return {}
    
    def crawl_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Crawl Google Maps reviews for a restaurant"""
        # Google Maps reviews are loaded dynamically, this is a simplified implementation
        # For a real application, you might need to use Selenium to interact with the page
        
        soup = self.fetch_page(url)
        if not soup:
            logger.error(f"Failed to fetch reviews page: {url}")
            return []
        
        reviews = []
        try:
            # Find review elements
            review_elements = soup.select('.jftiEf')
            
            for review_element in review_elements:
                try:
                    # Extract reviewer info
                    user_element = review_element.select('.d4r55')
                    reviewer_name = user_element[0].text.strip() if user_element else "Anonymous"
                    
                    # Extract reviewer ID (may not be directly available)
                    reviewer_id = ""  # Would need additional processing to extract this
                    
                    # Extract rating
                    rating_element = review_element.select('.kvMYJc')
                    rating = len(rating_element[0].select('.wzN8Ac')) if rating_element else 0
                    
                    # Extract review date
                    date_element = review_element.select('.rsqaWe')
                    review_date_text = date_element[0].text.strip() if date_element else ""
                    # Convert relative date to actual date (simplified)
                    review_date = datetime.now()  # Would need more complex parsing for actual date
                    
                    # Extract review text
                    text_element = review_element.select('.wiI7pd')
                    review_text = text_element[0].text.strip() if text_element else ""
                    
                    # Create review data dictionary
                    review_data = {
                        'rating': float(rating),
                        'review_text': review_text,
                        'review_date': review_date,
                        'reviewer_name': reviewer_name,
                        'reviewer_id': reviewer_id,
                        'helpful_count': 0,  # Google doesn't show helpful count directly
                        'source_url': url,
                        'source_id': f"google_{restaurant_id}_{hash(reviewer_name + review_text)}",
                        'source_platform': 'google',
                        'crawl_date': datetime.now()
                    }
                    
                    reviews.append(review_data)
                except Exception as e:
                    logger.error(f"Error parsing review: {str(e)}")
            
            return reviews
        
        except Exception as e:
            logger.error(f"Error parsing reviews from {url}: {str(e)}")
            return []


class TripAdvisorCrawler(BaseCrawler):
    """Crawler for TripAdvisor restaurant reviews"""
    
    def crawl_restaurant(self, url: str) -> Dict[str, Any]:
        """Crawl a TripAdvisor restaurant page and extract information"""
        soup = self.fetch_page(url)
        if not soup:
            logger.error(f"Failed to fetch restaurant page: {url}")
            return {}
        
        try:
            # Extract restaurant information
            name_element = soup.select('h1.HjBfq')
            name = name_element[0].text.strip() if name_element else "Unknown"
            
            # Extract address
            address_element = soup.select('a.AYHFM')
            address = address_element[0].text.strip() if address_element else ""
            
            # Extract rating
            rating_element = soup.select('span.ZDEqb')
            rating_text = rating_element[0].text.strip() if rating_element else "0.0"
            average_rating = float(rating_text.split(' ')[0].replace(',', '.')) if rating_text else 0.0
            
            # Extract price range
            price_element = soup.select('a.dlMOJ[data-param="trating"]')
            price_range = price_element[0].text.strip() if price_element else ""
            
            # Extract cuisine type
            cuisine_element = soup.select('a.dlMOJ[data-param="cuisine"]')
            cuisine_type = cuisine_element[0].text.strip() if cuisine_element else ""
            
            # Extract phone
            phone_element = soup.select('span.AYHFM:contains("Phone")')
            phone = phone_element[0].next_sibling.text.strip() if phone_element else ""
            
            # Extract website
            website_element = soup.select('a.YnKZo')
            website = website_element[0]['href'] if website_element and 'href' in website_element[0].attrs else ""
            
            # Parse address components (simplified)
            address_parts = address.split(", ")
            city = address_parts[1] if len(address_parts) > 1 else ""
            state_zip = address_parts[2].split() if len(address_parts) > 2 else []
            state = state_zip[0] if state_zip else ""
            postal_code = state_zip[1] if len(state_zip) > 1 else ""
            
            # Create restaurant data dictionary
            restaurant_data = {
                'name': name,
                'address': address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'phone': phone,
                'website': website,
                'cuisine_type': cuisine_type,
                'price_range': price_range,
                'average_rating': average_rating,
                'source_url': url,
                'source_id': url.split('-')[-1],
                'source_platform': 'tripadvisor',
                'last_updated': datetime.now()
            }
            
            return restaurant_data
        
        except Exception as e:
            logger.error(f"Error parsing restaurant data from {url}: {str(e)}")
            return {}
    
    def crawl_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Crawl TripAdvisor reviews for a restaurant"""
        # TripAdvisor reviews URL format
        reviews_url = f"{url.split('Reviews-')[0]}Reviews-or10-{url.split('Reviews-')[1]}"
        soup = self.fetch_page(reviews_url)
        if not soup:
            logger.error(f"Failed to fetch reviews page: {reviews_url}")
            return []
        
        reviews = []
        try:
            # Find review elements
            review_elements = soup.select('.review-container')
            
            for review_element in review_elements:
                try:
                    # Extract reviewer info
                    user_element = review_element.select('.info_text div:first-child')
                    reviewer_name = user_element[0].text.strip() if user_element else "Anonymous"
                    
                    # Extract reviewer ID 
                    reviewer_profile = review_element.select('.memberOverlayLink')
                    reviewer_id = reviewer_profile[0]['id'] if reviewer_profile and 'id' in reviewer_profile[0].attrs else ""
                    
                    # Extract rating
                    rating_element = review_element.select('.ui_bubble_rating')
                    rating_class = rating_element[0]['class'][-1] if rating_element and 'class' in rating_element[0].attrs else "bubble_00"
                    rating = float(rating_class.replace('bubble_', '')) / 10 if rating_class else 0.0
                    
                    # Extract review date
                    date_element = review_element.select('.ratingDate')
                    review_date_text = date_element[0]['title'] if date_element and 'title' in date_element[0].attrs else ""
                    # Parse date like "October 15, 2023"
                    try:
                        review_date = datetime.strptime(review_date_text, "%B %d, %Y") if review_date_text else datetime.now()
                    except ValueError:
                        review_date = datetime.now()
                    
                    # Extract review text
                    text_element = review_element.select('.prw_reviews_text_summary_hsx')
                    review_text = text_element[0].get_text(strip=True) if text_element else ""
                    
                    # Extract helpful count
                    helpful_element = review_element.select('.numHelp')
                    helpful_text = helpful_element[0].text.strip() if helpful_element else "0"
                    helpful_count = int(helpful_text.split()[0]) if helpful_text and helpful_text.split()[0].isdigit() else 0
                    
                    # Create review data dictionary
                    review_data = {
                        'rating': rating,
                        'review_text': review_text,
                        'review_date': review_date,
                        'reviewer_name': reviewer_name,
                        'reviewer_id': reviewer_id,
                        'helpful_count': helpful_count,
                        'source_url': reviews_url,
                        'source_id': f"tripadvisor_{restaurant_id}_{reviewer_id}_{int(review_date.timestamp())}",
                        'source_platform': 'tripadvisor',
                        'crawl_date': datetime.now()
                    }
                    
                    reviews.append(review_data)
                except Exception as e:
                    logger.error(f"Error parsing review: {str(e)}")
            
            return reviews
        
        except Exception as e:
            logger.error(f"Error parsing reviews from {reviews_url}: {str(e)}")
            return []
