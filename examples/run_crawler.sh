#!/bin/bash

# Start PostgreSQL via Docker Compose
echo "Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
sleep 5

# Initialize the database
echo "Initializing database..."
python crawl.py yelp https://www.yelp.com/biz/lazy-bear-san-francisco --init-db --max-reviews 10

# Crawl Yelp restaurants
echo "Crawling Yelp restaurants..."
python crawl.py yelp \
  https://www.yelp.com/biz/state-bird-provisions-san-francisco \
  https://www.yelp.com/biz/frances-san-francisco \
  --max-reviews 10

# Crawl Google Maps restaurants
echo "Crawling Google Maps restaurants..."
python crawl.py google \
  https://www.google.com/maps/place/Acquerello/@37.7931086,-122.4235186,17z/ \
  https://www.google.com/maps/place/Benu/@37.785394,-122.3996045,17z/ \
  --max-reviews 10

# Crawl TripAdvisor restaurants
echo "Crawling TripAdvisor restaurants..."
python crawl.py tripadvisor \
  https://www.tripadvisor.com/Restaurant_Review-g60713-d365471-Reviews-Kokkari_Estiatorio-San_Francisco_California.html \
  https://www.tripadvisor.com/Restaurant_Review-g60713-d1075128-Reviews-Brenda_s_French_Soul_Food-San_Francisco_California.html \
  --max-reviews 10

echo "Crawler run completed!"