# Utility functions for the RedHat Events Scraper
import os
import re
import logging
import json
from datetime import datetime
from dateutil import parser

logger = logging.getLogger(__name__)

def ensure_directory(directory):
    """
    Ensure that the specified directory exists
    
    Args:
        directory (str): Directory path to create if it doesn't exist
    """
    if not directory:
        logger.warning("Empty directory path provided")
        return
        
    try:
        # Use absolute path to avoid relative path issues
        abs_dir = os.path.abspath(directory)
        logger.info(f"Ensuring directory exists: {abs_dir}")
        
        if not os.path.exists(abs_dir):
            os.makedirs(abs_dir)
            logger.info(f"Created directory: {abs_dir}")
        else:
            logger.info(f"Directory already exists: {abs_dir}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}", exc_info=True)

def clean_text(text):
    """
    Clean text by removing extra spaces and normalizing whitespace
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    # Replace multiple spaces with a single space
    return re.sub(r'\s+', ' ', text.strip())

def parse_date_range(date_string):
    """
    Parse a date range string (e.g., "January 21, 2025 - March 19, 2025 (UTC)")
    
    Args:
        date_string (str): Date range string to parse
        
    Returns:
        dict: Dictionary with start_date and end_date
    """
    if not date_string or date_string == "N/A":
        return {"start_date": None, "end_date": None}
    
    try:
        # Remove timezone information in parentheses
        cleaned = re.sub(r'\([^)]*\)', '', date_string).strip()
        
        # Handle various formats
        if '-' in cleaned:
            parts = cleaned.split('-', 1)
            start_str = parts[0].strip()
            end_str = parts[1].strip()
            
            # Try to parse with dateutil
            try:
                start_date = parser.parse(start_str)
                end_date = parser.parse(end_str)
            except:
                # Fallback for unusual formats
                logger.warning(f"Using fallback date parsing for: {date_string}")
                # Try different format patterns here if needed
                return {
                    "date_text": clean_text(date_string),
                    "start_date": None,
                    "end_date": None
                }
            
            return {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        else:
            # Single date
            date = parser.parse(cleaned)
            return {
                "start_date": date.strftime("%Y-%m-%d"),
                "end_date": date.strftime("%Y-%m-%d")
            }
    except Exception as e:
        logger.error(f"Error parsing date: {date_string}, Error: {e}")
        return {
            "date_text": clean_text(date_string),
            "start_date": None,
            "end_date": None
        }

def compare_events(new_events, previous_events):
    """
    Compare new events with previously scraped events to identify new ones.
    Add an 'is_new' flag to events that weren't in the previous scrape.
    
    Args:
        new_events (list): List of newly scraped events
        previous_events (list): List of previously scraped events
        
    Returns:
        tuple: (List of new events only, List of all events with 'is_new' flag)
    """
    if not previous_events:
        # If no previous events, all are new
        new_only = new_events.copy()
        # Add 'is_new' flag to all events
        all_with_flag = []
        for event in new_events:
            event_copy = event.copy()
            event_copy['is_new'] = True
            all_with_flag.append(event_copy)
        return new_only, all_with_flag
    
    # Create a set of unique identifiers for previous events
    # Using title and start_date as a unique identifier
    previous_ids = {f"{event.get('title', '')}-{event.get('start_date', '')}" for event in previous_events}
    
    # Filter new events to only include those not in previous events
    new_only = []
    all_with_flag = []
    
    for event in new_events:
        event_id = f"{event.get('title', '')}-{event.get('start_date', '')}"
        event_copy = event.copy()
        
        if event_id not in previous_ids:
            event_copy['is_new'] = True
            new_only.append(event_copy)
        else:
            event_copy['is_new'] = False
        
        all_with_flag.append(event_copy)
    
    return new_only, all_with_flag

def save_last_run_data(events, filename="last_run_data.json"):
    """
    Save data from the last scraping run to compare in future runs
    
    Args:
        events (list): List of events from the current run
        filename (str): Filename to save the data to
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved last run data to {filename}")
    except Exception as e:
        logger.error(f"Error saving last run data: {e}")

def load_last_run_data(filename="last_run_data.json"):
    """
    Load data from the last scraping run
    
    Args:
        filename (str): Filename to load the data from
        
    Returns:
        list: List of events from the last run, or empty list if file doesn't exist
    """
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading last run data: {e}")
        return []

def generate_filename(prefix="redhat_events", extension="xlsx"):
    """
    Generate a filename with timestamp
    
    Args:
        prefix (str): Prefix for the filename
        extension (str): File extension
        
    Returns:
        str: Generated filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def save_html_for_debugging(html_content, filename="debug_redhat_page.html"):
    """
    Save HTML content to a file for debugging purposes
    
    Args:
        html_content (str): HTML content to save
        filename (str): Filename to save the content to
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Saved HTML content to {filename} for debugging")
    except Exception as e:
        logger.error(f"Error saving HTML content: {e}")

def clean_screenshots(directory, current_timestamp=None):
    """
    Remove screenshot files from the specified directory,
    but keep those from the current session if timestamp is provided
    
    Args:
        directory (str): Directory to clean
        current_timestamp (str): Current session timestamp to preserve (format: YYYYMMDD_HHMMSS)
    """
    try:
        # Find all screenshot files
        screenshot_files = [os.path.join(directory, f) for f in os.listdir(directory) 
                          if f.endswith('.png')]
        
        # Count before cleaning
        total_count = len(screenshot_files)
        removed_count = 0
        
        # Remove screenshots from previous sessions
        for file_path in screenshot_files:
            file_name = os.path.basename(file_path)
            
            # If current_timestamp is provided, keep screenshots from current session
            if current_timestamp and current_timestamp in file_name:
                logger.debug(f"Keeping current screenshot: {file_name}")
                continue
                
            try:
                os.remove(file_path)
                removed_count += 1
                logger.debug(f"Removed screenshot: {file_name}")
            except Exception as e:
                logger.warning(f"Could not remove screenshot {file_name}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned {removed_count}/{total_count} screenshot files")
    except Exception as e:
        logger.error(f"Error cleaning screenshots: {e}")
        
def configure_debug_mode(enable_screenshots=False):
    """
    Configure debug options globally
    
    Args:
        enable_screenshots (bool): Whether to save screenshots during scraping
    """
    global TAKE_SCREENSHOTS
    TAKE_SCREENSHOTS = enable_screenshots