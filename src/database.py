import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'restaurant_reviews')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    phone = Column(String(50))
    website = Column(String(255))
    cuisine_type = Column(String(100))
    price_range = Column(String(10))
    average_rating = Column(Float)
    source_url = Column(String(255), unique=True)
    source_id = Column(String(100))
    source_platform = Column(String(50))  # e.g., 'yelp', 'google', 'tripadvisor'
    last_updated = Column(DateTime)

    # Relationship with reviews
    reviews = relationship("Review", back_populates="restaurant")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    rating = Column(Float, nullable=False)
    review_text = Column(Text)
    review_date = Column(DateTime)
    reviewer_name = Column(String(255))
    reviewer_id = Column(String(100))
    helpful_count = Column(Integer, default=0)
    source_url = Column(String(255))
    source_id = Column(String(100), unique=True)
    source_platform = Column(String(50))
    crawl_date = Column(DateTime)

    # Relationship with restaurant
    restaurant = relationship("Restaurant", back_populates="reviews")


def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Get a database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
