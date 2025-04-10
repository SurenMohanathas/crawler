import unittest
from unittest.mock import patch, MagicMock

import requests
from bs4 import BeautifulSoup

from src.crawler import BaseCrawler, YelpCrawler


class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")


class TestBaseCrawler(unittest.TestCase):
    """Test the BaseCrawler class functionality"""

    @patch('src.crawler.get_db_session')
    def setUp(self, mock_get_db_session):
        self.mock_db_session = MagicMock()
        mock_get_db_session.return_value = self.mock_db_session
        
        # Create a concrete implementation of BaseCrawler for testing
        class ConcreteCrawler(BaseCrawler):
            def crawl_restaurant(self, url):
                return {"name": "Test Restaurant", "source_url": url}
            
            def crawl_reviews(self, url, restaurant_id):
                return [{"rating": 5.0, "review_text": "Great place!", "source_id": "test123"}]
        
        self.crawler = ConcreteCrawler()

    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_fetch_page(self, mock_sleep, mock_get):
        # Test successful fetch
        html_content = "<html><body><h1>Test Page</h1></body></html>"
        mock_get.return_value = MockResponse(html_content)
        
        result = self.crawler.fetch_page("https://example.com")
        
        self.assertIsInstance(result, BeautifulSoup)
        self.assertEqual(result.h1.text, "Test Page")
        mock_get.assert_called_once_with("https://example.com", timeout=30)
        mock_sleep.assert_called_once()
        
        # Test failed fetch
        mock_get.reset_mock()
        mock_sleep.reset_mock()
        mock_get.return_value = MockResponse("", status_code=404)
        mock_get.return_value.raise_for_status = lambda: exec('raise requests.exceptions.HTTPError("404")')
        
        result = self.crawler.fetch_page("https://example.com/not-found")
        
        self.assertIsNone(result)
        mock_get.assert_called_once_with("https://example.com/not-found", timeout=30)
        mock_sleep.assert_not_called()

    def test_save_restaurant(self):
        # Test saving a new restaurant
        restaurant_data = {
            "name": "Test Restaurant",
            "address": "123 Test St",
            "source_url": "https://example.com/restaurant/123",
            "source_id": "123"
        }
        
        # Configure mock to return None for query.first() (no existing restaurant)
        self.mock_db_session.query().filter_by().first.return_value = None
        
        self.crawler.save_restaurant(restaurant_data)
        
        # Check that add was called
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
        
        # Test updating an existing restaurant
        self.mock_db_session.reset_mock()
        mock_restaurant = MagicMock()
        self.mock_db_session.query().filter_by().first.return_value = mock_restaurant
        
        self.crawler.save_restaurant(restaurant_data)
        
        # Check that add was not called (updating existing)
        self.mock_db_session.add.assert_not_called()
        self.mock_db_session.commit.assert_called_once()


class TestYelpCrawler(unittest.TestCase):
    """Test the YelpCrawler class functionality"""
    
    @patch('src.crawler.get_db_session')
    def setUp(self, mock_get_db_session):
        self.mock_db_session = MagicMock()
        mock_get_db_session.return_value = self.mock_db_session
        self.crawler = YelpCrawler()
    
    @patch.object(YelpCrawler, 'fetch_page')
    def test_crawl_restaurant(self, mock_fetch_page):
        # Create a mock BeautifulSoup object with restaurant data
        with open('tests/fixtures/yelp_restaurant.html', 'r', encoding='utf-8') as f:
            mock_soup = BeautifulSoup(f.read(), 'html.parser')
        
        mock_fetch_page.return_value = mock_soup
        
        result = self.crawler.crawl_restaurant("https://www.yelp.com/biz/test-restaurant")
        
        # Validate result
        self.assertEqual(result.get('name'), "Test Restaurant")
        self.assertEqual(result.get('source_platform'), "yelp")
    
    @patch.object(YelpCrawler, 'fetch_page')
    def test_crawl_reviews(self, mock_fetch_page):
        # Create a mock BeautifulSoup object with review data
        with open('tests/fixtures/yelp_reviews.html', 'r', encoding='utf-8') as f:
            mock_soup = BeautifulSoup(f.read(), 'html.parser')
        
        mock_fetch_page.return_value = mock_soup
        
        result = self.crawler.crawl_reviews("https://www.yelp.com/biz/test-restaurant", 123)
        
        # Validate result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 10)  # Assuming fixture has 10 reviews


if __name__ == '__main__':
    unittest.main()