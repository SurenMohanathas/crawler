# Restaurant Review Crawler

A Python-based crawler for restaurant reviews from various platforms including Yelp, Google Maps, and TripAdvisor. The crawler extracts restaurant information and reviews, storing them in a PostgreSQL database.

## Features

- Crawl restaurant information and reviews from multiple platforms
- Support for Yelp, Google Maps, and TripAdvisor
- Configurable crawler settings via environment variables
- Robust error handling and logging
- PostgreSQL database integration using SQLAlchemy
- ORM-based database models with relationships
- Unit testing with pytest

## Architecture

The project follows a modular architecture with the following components:

- **BaseCrawler**: Abstract base class defining the crawler interface
- **Platform-specific crawlers**: Implementations for Yelp, Google Maps, and TripAdvisor
- **Database Models**: SQLAlchemy ORM models for restaurants and reviews
- **CLI Interface**: Command-line interface for running the crawler

## Database Schema

```
+-------------------+       +-------------------+
|    restaurants    |       |      reviews      |
+-------------------+       +-------------------+
| id (PK)           |       | id (PK)           |
| name              |       | restaurant_id (FK)|
| address           |       | rating            |
| city              |       | review_text       |
| state             |       | review_date       |
| postal_code       |       | reviewer_name     |
| phone             |       | reviewer_id       |
| website           |       | helpful_count     |
| cuisine_type      |       | source_url        |
| price_range       |       | source_id         |
| average_rating    |       | source_platform   |
| source_url        |       | crawl_date        |
| source_id         |       +-------------------+
| source_platform   |
| last_updated      |
+-------------------+
        |
        | 1:n
        v
+-------------------+
|      reviews      |
+-------------------+
```

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/restaurant-review-crawler.git
   cd restaurant-review-crawler
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Start the PostgreSQL database using Docker Compose:
   ```
   docker-compose up -d postgres
   ```

5. Configure environment variables:
   ```
   cp config/.env.example config/.env
   # Edit config/.env with your database credentials
   ```

### Manual Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/restaurant-review-crawler.git
   cd restaurant-review-crawler
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install and configure PostgreSQL:
   - [Install PostgreSQL](https://www.postgresql.org/download/)
   - Create a new database: `createdb restaurant_reviews`

5. Configure environment variables:
   ```
   cp config/.env.example config/.env
   # Edit config/.env with your database credentials
   ```

## Usage

### Basic Usage

```bash
python crawl.py [source] [urls] [options]
```

- `source`: The platform to crawl (`yelp`, `google`, `tripadvisor`, or `all`)
- `urls`: One or more URLs of restaurant pages to crawl
- `options`: Additional command-line options (see below)

### Command-line Options

- `--max-reviews N`: Maximum number of reviews to crawl per restaurant (default: 100)
- `--init-db`: Initialize the database (create tables)

### Examples

Initialize the database and crawl a Yelp restaurant:
```bash
python crawl.py yelp https://www.yelp.com/biz/restaurant-name --init-db
```

Crawl a Google Maps restaurant with a limit of 50 reviews:
```bash
python crawl.py google https://maps.google.com/place/restaurant-name --max-reviews 50
```

Crawl multiple TripAdvisor restaurants:
```bash
python crawl.py tripadvisor https://www.tripadvisor.com/Restaurant_Review-g12345-d67890-Reviews-Restaurant_Name.html https://www.tripadvisor.com/Restaurant_Review-g12345-d67891-Reviews-Another_Restaurant.html
```

Crawl a restaurant on all supported platforms:
```bash
python crawl.py all https://www.yelp.com/biz/restaurant-name https://maps.google.com/place/restaurant-name https://www.tripadvisor.com/Restaurant_Review-g12345-d67890-Reviews-Restaurant_Name.html
```

### Running with Sample Data

For a quick start, you can use the provided sample scripts:

```bash
# Run the crawler with sample URLs
./examples/run_crawler.sh

# Export the crawled data to CSV files
./examples/export_data.py
```

## Data Export

You can export the crawled data to CSV files using the provided script:

```bash
python examples/export_data.py --restaurants restaurants.csv --reviews reviews.csv
```

## Development

### Running Tests

```bash
pytest
```

### Adding a New Crawler

To add support for a new platform:

1. Create a new crawler class that inherits from `BaseCrawler`
2. Implement the required methods: `crawl_restaurant` and `crawl_reviews`
3. Add the new crawler to the `get_crawler` function in `main.py`

## Limitations and Ethical Considerations

- Always respect the terms of service of the websites you crawl
- Use appropriate delays between requests (configurable in `.env`)
- Consider the load you're placing on the target servers
- Be aware that websites may change their HTML structure, breaking the crawler

## License

This project is licensed under the MIT License - see the LICENSE file for details.