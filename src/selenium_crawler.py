"""
Selenium-based crawler for TripAdvisor.
This module provides a crawler that can handle JavaScript-rendered content
for better scraping of modern websites.
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .database import Restaurant, Review, get_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('selenium_crawler')

# Crawler settings
REQUEST_DELAY = int(os.getenv('REQUEST_DELAY', 2))


class SeleniumTripAdvisorCrawler:
    """Crawler for TripAdvisor restaurant reviews using Selenium."""
    
    def __init__(self, headless=True):
        """Initialize the Selenium crawler."""
        self.db_session = get_db_session()
        self.driver = self._setup_driver(headless)
    
    def _setup_driver(self, headless=True):
        """Set up the Chrome WebDriver."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--lang=en-US,en;q=0.9")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use ChromeDriverManager to automatically download the appropriate driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set navigator.webdriver to undefined
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def crawl_restaurant(self, url: str) -> Dict[str, Any]:
        """Crawl a TripAdvisor restaurant page and extract information."""
        logger.info(f"Crawling restaurant: {url}")
        
        # Check for demo mode
        if os.getenv('DEMO_MODE', 'false').lower() == 'true':
            logger.info(f"DEMO MODE: Using mock data instead of fetching {url}")
            return self._create_mock_restaurant(url)
        
        try:
            self.driver.get(url)
            time.sleep(REQUEST_DELAY)  # Wait for JavaScript to load
            
            # Extract restaurant information
            restaurant_data = {}
            
            # Get restaurant name (from meta tags)
            try:
                restaurant_name = self.driver.find_element(By.TAG_NAME, 'h1').text.strip()
                restaurant_data['name'] = restaurant_name
            except NoSuchElementException:
                try:
                    # Try getting from meta title
                    title = self.driver.title
                    if "," in title:
                        restaurant_data['name'] = title.split(',')[0].strip()
                    else:
                        restaurant_data['name'] = "Unknown"
                except:
                    restaurant_data['name'] = "Unknown"
            
            # Extract address
            try:
                # Get structured data from the page if available
                script_elements = self.driver.find_elements(By.XPATH, '//script[@type="application/ld+json"]')
                for script in script_elements:
                    try:
                        data = json.loads(script.get_attribute('innerHTML'))
                        if isinstance(data, dict) and 'address' in data:
                            address_data = data['address']
                            restaurant_data['address'] = address_data.get('streetAddress', '')
                            restaurant_data['city'] = address_data.get('addressLocality', '')
                            restaurant_data['state'] = address_data.get('addressRegion', '')
                            restaurant_data['postal_code'] = address_data.get('postalCode', '')
                            break
                    except json.JSONDecodeError:
                        continue
            except:
                restaurant_data['address'] = ''
                restaurant_data['city'] = ''
                restaurant_data['state'] = ''
                restaurant_data['postal_code'] = ''
            
            # Extract rating
            try:
                # Look for rating in meta description
                meta_desc = self.driver.find_element(By.XPATH, '//meta[@name="description"]')
                desc_content = meta_desc.get_attribute('content')
                
                # Parse rating from description (e.g., "rated 4.4 of 5")
                import re
                rating_match = re.search(r'rated (\d+\.\d+) of 5', desc_content)
                if rating_match:
                    restaurant_data['average_rating'] = float(rating_match.group(1))
                else:
                    restaurant_data['average_rating'] = 0.0
            except:
                restaurant_data['average_rating'] = 0.0
            
            # Extract other details
            restaurant_data['phone'] = ''
            restaurant_data['website'] = ''
            restaurant_data['cuisine_type'] = ''
            restaurant_data['price_range'] = ''
            restaurant_data['source_url'] = url
            restaurant_data['source_id'] = url.split('-')[-1]
            restaurant_data['source_platform'] = 'tripadvisor'
            restaurant_data['last_updated'] = datetime.now()
            
            return restaurant_data
            
        except Exception as e:
            logger.error(f"Error crawling restaurant {url}: {str(e)}")
            return {
                'name': "Unknown",
                'address': "",
                'city': "",
                'state': "",
                'postal_code': "",
                'phone': "",
                'website': "",
                'cuisine_type': "",
                'price_range': "",
                'average_rating': 0.0,
                'source_url': url,
                'source_id': url.split('-')[-1],
                'source_platform': 'tripadvisor',
                'last_updated': datetime.now()
            }
    
    def crawl_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Crawl TripAdvisor reviews for a restaurant."""
        # Check for demo mode
        if os.getenv('DEMO_MODE', 'false').lower() == 'true':
            logger.info(f"DEMO MODE: Using mock reviews data for {url}")
            return self._create_mock_reviews(url, restaurant_id)
        
        reviews = []
        logger.info(f"Crawling reviews for restaurant ID {restaurant_id}")
        
        try:
            # Navigate to the reviews page
            if "Reviews-" not in url:
                reviews_url = url
            else:
                reviews_url = url
            
            self.driver.get(reviews_url)
            time.sleep(REQUEST_DELAY * 2)  # Give extra time for reviews to load
            
            # First need to click "Read more" buttons if available to expand reviews
            try:
                read_more_buttons = self.driver.find_elements(By.XPATH, '//span[contains(text(), "Read more")]')
                for button in read_more_buttons[:5]:  # Limit to 5 to avoid too many clicks
                    try:
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass
                
            # Wait a bit for everything to load and stabilize
            time.sleep(3)
            
            # Try multiple approaches to find review elements
            review_elements = []
            
            # Approach 1: Modern data-automation attribute
            elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-automation="reviewCard"]')
            if elements:
                review_elements = elements
                logger.info(f"Found {len(review_elements)} reviews using data-automation attribute")
                
            # Approach 2: Classic review containers
            if not review_elements:
                elements = self.driver.find_elements(By.CSS_SELECTOR, '.review-container')
                if elements:
                    review_elements = elements
                    logger.info(f"Found {len(review_elements)} reviews using review-container class")
            
            # Approach 3: Generic review blocks using XPath
            if not review_elements:
                elements = self.driver.find_elements(By.XPATH, '//div[contains(@data-test-target, "review")]')
                if elements:
                    review_elements = elements
                    logger.info(f"Found {len(review_elements)} reviews using data-test-target XPath")
            
            # Approach 4: Look for review header and then get parent elements
            if not review_elements:
                try:
                    review_headers = self.driver.find_elements(By.XPATH, '//div[contains(@class, "review-header")]')
                    if review_headers:
                        review_elements = [header.find_element(By.XPATH, './..') for header in review_headers]
                        logger.info(f"Found {len(review_elements)} reviews using review headers")
                except:
                    pass
            
            # Approach 5: Look for any div containing review text and rating
            if not review_elements:
                try:
                    # First try to identify if there's a reviews section
                    sections = self.driver.find_elements(By.XPATH, '//div[contains(@id, "REVIEWS") or contains(@class, "reviews")]')
                    if sections:
                        # Extract all divs that might be review cards based on their depth and size
                        for section in sections[:1]:  # Just use the first reviews section
                            possible_reviews = section.find_elements(By.XPATH, './/div[.//span[contains(@class, "bubble") or contains(@class, "rating")] and .//p[string-length(text()) > 30]]')
                            if possible_reviews:
                                review_elements = possible_reviews
                                logger.info(f"Found {len(review_elements)} reviews by identifying review-like divs")
                                break
                except:
                    pass
                    
            # Approach 6: Just scrape all reviews visible in the page HTML
            if not review_elements:
                try:
                    # Save the page source for analysis with BeautifulSoup
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Look for elements that have both a rating and substantial text content
                    review_candidates = []
                    rating_elements = soup.find_all('span', class_=lambda c: c and ('bubble' in c or 'rating' in c))
                    for rating_element in rating_elements:
                        # Find parent container that might be a review card
                        parent_div = rating_element
                        for _ in range(3):  # Go up to 3 levels
                            parent_div = parent_div.parent if parent_div.parent else None
                            if parent_div and parent_div.name == 'div':
                                # Look for text of substantial length in this div
                                text_elements = parent_div.find_all('p')
                                text_content = ' '.join([t.text for t in text_elements if t.text])
                                if len(text_content) > 50:  # Assume reviews are at least 50 chars
                                    review_candidates.append({
                                        'element': parent_div,
                                        'rating_text': rating_element.text.strip(),
                                        'text': text_content
                                    })
                                    break
                    
                    # Process these candidates manually
                    if review_candidates:
                        logger.info(f"Found {len(review_candidates)} review candidates using BeautifulSoup analysis")
                        # We'll need to process these differently below
                        return self._extract_reviews_from_soup(review_candidates, url, restaurant_id)
                        
                except Exception as e:
                    logger.error(f"Error during BeautifulSoup processing: {str(e)}")
            
            logger.info(f"Found {len(review_elements)} review elements")
            
            for i, review_element in enumerate(review_elements):
                try:
                    # Extract reviewer name
                    try:
                        reviewer_name_elem = review_element.find_element(By.CSS_SELECTOR, '.info_text div:first-child')
                        reviewer_name = reviewer_name_elem.text.strip()
                    except:
                        try:
                            # Try alternate selector
                            reviewer_name_elem = review_element.find_element(By.CSS_SELECTOR, '[data-automation="reviewerName"]')
                            reviewer_name = reviewer_name_elem.text.strip()
                        except:
                            reviewer_name = f"User_{i+1}"
                    
                    # Extract rating
                    try:
                        rating_elem = review_element.find_element(By.CSS_SELECTOR, 'span.ui_bubble_rating')
                        rating_class = rating_elem.get_attribute('class')
                        rating = float(rating_class.split('_')[-1]) / 10
                    except:
                        try:
                            # Try alternate selector
                            rating_elem = review_element.find_element(By.CSS_SELECTOR, '[data-automation="reviewRating"]')
                            rating_text = rating_elem.get_attribute('aria-label')
                            if rating_text:
                                rating = float(rating_text.split('/')[0].strip())
                            else:
                                rating = 0.0
                        except:
                            rating = 3.0  # Default if not found
                    
                    # Extract review date
                    try:
                        date_elem = review_element.find_element(By.CSS_SELECTOR, '.ratingDate')
                        date_text = date_elem.get_attribute('title') or date_elem.text
                        if not date_text or 'date of' in date_text.lower():
                            review_date = datetime.now() - timedelta(days=i)
                        else:
                            try:
                                review_date = datetime.strptime(date_text, "%B %d, %Y")
                            except:
                                review_date = datetime.now() - timedelta(days=i)
                    except:
                        try:
                            # Try alternate selector
                            date_elem = review_element.find_element(By.CSS_SELECTOR, '[data-automation="reviewDate"]')
                            date_text = date_elem.text
                            if date_text:
                                try:
                                    if 'wrote a review' in date_text:
                                        date_parts = date_text.split('wrote a review')
                                        if len(date_parts) > 1:
                                            date_text = date_parts[1].strip()
                                    review_date = datetime.strptime(date_text, "%B %Y")
                                except:
                                    review_date = datetime.now() - timedelta(days=i)
                            else:
                                review_date = datetime.now() - timedelta(days=i)
                        except:
                            review_date = datetime.now() - timedelta(days=i)
                    
                    # Extract review text
                    try:
                        text_elem = review_element.find_element(By.CSS_SELECTOR, '.prw_reviews_text_summary_hsx')
                        review_text = text_elem.text.strip()
                    except:
                        try:
                            # Try alternate selector
                            text_elem = review_element.find_element(By.CSS_SELECTOR, '[data-automation="reviewText"]')
                            review_text = text_elem.text.strip()
                        except:
                            try:
                                # Just get all text as a fallback
                                review_text = review_element.text
                                # Remove reviewer name and date if they appear in the text
                                if reviewer_name in review_text:
                                    review_text = review_text.replace(reviewer_name, '')
                                if date_text in review_text:
                                    review_text = review_text.replace(date_text, '')
                                review_text = review_text.strip()
                            except:
                                review_text = f"Review {i+1}"
                    
                    # Generate a unique source_id
                    source_id = f"tripadvisor_{restaurant_id}_{i}_{int(review_date.timestamp())}"
                    
                    # Create review data dictionary
                    review_data = {
                        'rating': rating,
                        'review_text': review_text,
                        'review_date': review_date,
                        'reviewer_name': reviewer_name,
                        'reviewer_id': f"reviewer_{i}",
                        'helpful_count': 0,
                        'source_url': url,
                        'source_id': source_id,
                        'source_platform': 'tripadvisor',
                        'crawl_date': datetime.now()
                    }
                    
                    reviews.append(review_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing review {i}: {str(e)}")
            
            return reviews
            
        except Exception as e:
            logger.error(f"Error crawling reviews from {url}: {str(e)}")
            return []
    
    def save_restaurant(self, restaurant_data: Dict[str, Any]) -> Restaurant:
        """Save restaurant to database."""
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
        """Save review to database."""
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
        """Close database session and WebDriver."""
        self.db_session.close()
        if self.driver:
            self.driver.quit()
    
    def _create_mock_restaurant(self, url: str) -> Dict[str, Any]:
        """Create mock restaurant data for demo mode."""
        return {
            'name': "Ceylonta Restaurant (Mock)",
            'address': "403 Somerset St W",
            'city': "Ottawa",
            'state': "Ontario",
            'postal_code': "K2P 0K1",
            'phone': "+1 613-563-3989",
            'website': "https://www.ceylonta.com",
            'cuisine_type': "Sri Lankan, Indian, Vegetarian Friendly",
            'price_range': "$$",
            'average_rating': 4.4,
            'source_url': url,
            'source_id': url.split('-')[-1],
            'source_platform': 'tripadvisor',
            'last_updated': datetime.now()
        }
    
    def _extract_reviews_from_soup(self, review_candidates: List[Dict], url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Process BeautifulSoup review candidates into review data."""
        reviews = []
        
        for i, candidate in enumerate(review_candidates):
            try:
                # Extract review text
                review_text = candidate['text']
                
                # Extract rating from text (e.g., "5.0 of 5 bubbles" or similar)
                rating_text = candidate['rating_text']
                rating = 0.0
                try:
                    if 'of 5' in rating_text:
                        rating = float(rating_text.split('of 5')[0].strip())
                    elif any(str(num) in rating_text for num in range(1, 6)):
                        for num in range(1, 6):
                            if str(num) in rating_text:
                                rating = float(num)
                                break
                    else:
                        rating = 3.0  # Default
                except:
                    rating = 3.0  # Default
                
                # Extract reviewer name
                reviewer_name = "Unknown"
                try:
                    name_element = candidate['element'].find('span', class_=lambda c: c and 'username' in c)
                    if name_element:
                        reviewer_name = name_element.text.strip()
                    else:
                        # Try other approaches
                        name_divs = candidate['element'].find_all('div', class_=lambda c: c and ('member' in c or 'user' in c))
                        for div in name_divs:
                            if div.text and len(div.text.strip()) < 30:  # Username likely short
                                reviewer_name = div.text.strip()
                                break
                except:
                    pass
                
                # Extract date or use a mock date
                review_date = datetime.now() - timedelta(days=i*7)
                try:
                    date_element = candidate['element'].find('span', class_=lambda c: c and ('date' in c or 'when' in c))
                    if date_element and date_element.text:
                        date_text = date_element.text.strip()
                        # Try various date formats
                        try:
                            if 'wrote a review' in date_text:
                                date_parts = date_text.split('wrote a review')
                                if len(date_parts) > 1:
                                    date_text = date_parts[1].strip()
                            
                            if ',' in date_text:
                                # Format like "January 15, 2023"
                                review_date = datetime.strptime(date_text, "%B %d, %Y")
                            elif any(month in date_text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                                # Format like "Jan 2023"
                                review_date = datetime.strptime(date_text, "%b %Y")
                        except:
                            pass
                except:
                    pass
                
                # Generate a unique source_id
                source_id = f"tripadvisor_{restaurant_id}_soup_{i}_{int(review_date.timestamp())}"
                
                # Create review data dictionary
                review_data = {
                    'rating': rating,
                    'review_text': review_text,
                    'review_date': review_date,
                    'reviewer_name': reviewer_name,
                    'reviewer_id': f"reviewer_soup_{i}",
                    'helpful_count': 0,
                    'source_url': url,
                    'source_id': source_id,
                    'source_platform': 'tripadvisor',
                    'crawl_date': datetime.now()
                }
                
                reviews.append(review_data)
                
            except Exception as e:
                logger.error(f"Error processing BeautifulSoup review candidate {i}: {str(e)}")
        
        return reviews
        
    def _create_mock_reviews(self, url: str, restaurant_id: int) -> List[Dict[str, Any]]:
        """Create mock reviews for demo mode."""
        mock_reviews = []
        
        review_texts = [
            "Excellent food! The kottu roti was particularly good, and the service was top-notch. Will definitely be coming back here again.",
            "We tried this restaurant for the first time and were very impressed. The flavors were authentic and the portions generous. Highly recommend the string hoppers!",
            "The lunch buffet is an excellent value. Great selection of curry options for both meat eaters and vegetarians. The dosa was crispy and delicious.",
            "Service was a bit slow on the weekend but the food made up for it. The lamb curry was excellent - tender and perfectly spiced.",
            "Came here with my family for dinner. The ambiance is simple but the food is amazing. Try the mango lassi!",
            "Good Sri Lankan food, though I found some dishes a bit too spicy for my taste. The waiter was happy to recommend milder options though.",
            "One of the best South Asian restaurants in Ottawa. The masala dosa is huge and very tasty. Good prices too."
        ]
        
        ratings = [5.0, 4.0, 4.5, 3.5, 5.0, 3.0, 4.5]
        
        for i in range(7):
            review_date = datetime.now() - timedelta(days=i*10)
            mock_reviews.append({
                'rating': ratings[i],
                'review_text': review_texts[i],
                'review_date': review_date,
                'reviewer_name': f"MockReviewer{i+1}",
                'reviewer_id': f"reviewer_{i}",
                'helpful_count': i,
                'source_url': url,
                'source_id': f"tripadvisor_{restaurant_id}_mock_{i}_{int(review_date.timestamp())}",
                'source_platform': 'tripadvisor',
                'crawl_date': datetime.now()
            })
        
        return mock_reviews