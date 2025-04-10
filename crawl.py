#!/usr/bin/env python
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the main module from src
from src.main import main

if __name__ == "__main__":
    main()