#!/usr/bin/env python3
# cron_runner.py - Standalone script for scheduled execution of RedHat scraper

import sys
import os
import logging
import argparse
import platform
from datetime import datetime
from batch_script import BatchRunner
from config import DEFAULT_FILTERS, OUTPUT_DIR
from utils import ensure_directory

# Configure logging to file in output directory
ensure_directory(OUTPUT_DIR)
log_file = os.path.join(OUTPUT_DIR, "cron_scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_scheduled_scrape(export_sheets=False):
    """
    Run a scheduled scrape with default settings
    
    Args:
        export_sheets (bool): Whether to export to Google Sheets
        
    Returns:
        bool: Success status
    """
    logger.info(f"Starting scheduled RedHat events scrape on {platform.system()}")
    
    try:
        # Record start time
        start_time = datetime.now()
        logger.info(f"Scrape started at: {start_time}")
        
        # Create batch runner with default filters
        batch_runner = BatchRunner(
            filters=DEFAULT_FILTERS,
            headless=True,  # Always use headless mode for cron jobs
            output_dir=OUTPUT_DIR
        )
        
        # Run scraper once
        all_events, new_events, excel_path, csv_path, sheets_url = batch_runner.run_once(
            save_excel=True,
            save_csv=True,
            export_to_sheets=export_sheets
        )
        
        # Log results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Scrape completed at: {end_time}")
        logger.info(f"Total duration: {duration:.2f} seconds")
        logger.info(f"Total events found: {len(all_events)}")
        logger.info(f"New events found: {len(new_events)}")
        
        if excel_path:
            logger.info(f"Excel file saved to: {excel_path}")
        if csv_path:
            logger.info(f"CSV file saved to: {csv_path}")
        if sheets_url:
            logger.info(f"Google Sheets updated: {sheets_url}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error during scheduled scrape: {e}")
        logger.exception("Detailed error:")
        return False

if __name__ == "__main__":
    # Log system information
    logger.info(f"Running on: {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="RedHat Events Scraper - Cron Runner")
    parser.add_argument("--sheets", action="store_true", help="Export to Google Sheets")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Run the scheduled scrape
    success = run_scheduled_scrape(export_sheets=args.sheets)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)