#!/usr/bin/env python
"""
A utility script to export restaurant review data from the database to CSV files.
"""
import argparse
import csv
import os
import sys
from datetime import datetime

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.database import Restaurant, Review, get_db_session


def export_restaurants_to_csv(output_file):
    """Export restaurants to a CSV file"""
    db = get_db_session()
    restaurants = db.query(Restaurant).all()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'name', 'address', 'city', 'state', 'postal_code',
            'phone', 'website', 'cuisine_type', 'price_range',
            'average_rating', 'source_platform', 'last_updated'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for restaurant in restaurants:
            writer.writerow({
                'id': restaurant.id,
                'name': restaurant.name,
                'address': restaurant.address,
                'city': restaurant.city,
                'state': restaurant.state,
                'postal_code': restaurant.postal_code,
                'phone': restaurant.phone,
                'website': restaurant.website,
                'cuisine_type': restaurant.cuisine_type,
                'price_range': restaurant.price_range,
                'average_rating': restaurant.average_rating,
                'source_platform': restaurant.source_platform,
                'last_updated': restaurant.last_updated.strftime('%Y-%m-%d %H:%M:%S') if restaurant.last_updated else ''
            })
    
    print(f"Exported {len(restaurants)} restaurants to {output_file}")


def export_reviews_to_csv(output_file):
    """Export reviews to a CSV file"""
    db = get_db_session()
    reviews = db.query(Review).all()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'restaurant_id', 'rating', 'review_text', 'review_date',
            'reviewer_name', 'helpful_count', 'source_platform', 'crawl_date'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for review in reviews:
            writer.writerow({
                'id': review.id,
                'restaurant_id': review.restaurant_id,
                'rating': review.rating,
                'review_text': review.review_text,
                'review_date': review.review_date.strftime('%Y-%m-%d %H:%M:%S') if review.review_date else '',
                'reviewer_name': review.reviewer_name,
                'helpful_count': review.helpful_count,
                'source_platform': review.source_platform,
                'crawl_date': review.crawl_date.strftime('%Y-%m-%d %H:%M:%S') if review.crawl_date else ''
            })
    
    print(f"Exported {len(reviews)} reviews to {output_file}")


def main():
    """Main entry point for the export script"""
    parser = argparse.ArgumentParser(description='Export restaurant review data to CSV')
    parser.add_argument(
        '--restaurants',
        type=str,
        default='restaurants.csv',
        help='Output file for restaurants data (default: restaurants.csv)'
    )
    parser.add_argument(
        '--reviews',
        type=str,
        default='reviews.csv',
        help='Output file for reviews data (default: reviews.csv)'
    )
    
    args = parser.parse_args()
    
    print("Exporting restaurant data...")
    export_restaurants_to_csv(args.restaurants)
    
    print("Exporting review data...")
    export_reviews_to_csv(args.reviews)
    
    print("Export completed successfully!")


if __name__ == "__main__":
    main()