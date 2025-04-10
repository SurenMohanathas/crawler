from setuptools import setup, find_packages

setup(
    name="restaurant-review-crawler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4",
        "requests",
        "psycopg2-binary",
        "python-dotenv",
        "scrapy",
        "sqlalchemy",
    ],
    entry_points={
        "console_scripts": [
            "restaurant-crawler=src.main:main",
        ],
    },
    python_requires=">=3.8",
)