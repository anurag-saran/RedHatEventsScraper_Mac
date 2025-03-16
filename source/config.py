# Configuration file for RedHat Events Scraper
# Contains all settings and constants used throughout the application

# Base URL for RedHat events page
BASE_URL = "https://www.redhat.com/en/events"

# HTTP headers to mimic browser behavior and avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

# Output directory for saving scraped data
OUTPUT_DIR = "output"

# Default output format
DEFAULT_FORMAT = "excel"

# Batch script configuration
BATCH_FREQUENCY_DAYS = 7  # Run weekly

# Event filters
DEFAULT_FILTERS = {
    "event_type": "InPerson",
    "region": "North America",
    "date": "Upcoming Events"
}

# GUI configuration
GUI_TITLE = "RedHat Events Scraper"
GUI_WIDTH = 800
GUI_HEIGHT = 600