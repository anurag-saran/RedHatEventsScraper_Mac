# Batch script for periodic execution of the RedHat Events Scraper
import os
import time
import logging
import datetime
from scraper_interactive import RedHatEventsInteractiveScraper
from data_processor import EventDataProcessor
from utils import load_last_run_data, save_last_run_data, compare_events, ensure_directory, clean_screenshots
from config import DEFAULT_FILTERS, BATCH_FREQUENCY_DAYS, OUTPUT_DIR

logger = logging.getLogger(__name__)

class BatchRunner:
    def __init__(self, filters=None, interval_days=BATCH_FREQUENCY_DAYS, output_dir=OUTPUT_DIR, headless=True):
        """
        Initialize batch runner
    
        Args:
            filters (dict): Filters to apply to scraper
            interval_days (int): Interval between runs in days
            output_dir (str): Directory for output files
            headless (bool): Whether to run browser in headless mode
        """
        self.filters = filters or DEFAULT_FILTERS
        self.interval_days = interval_days
        self.output_dir = output_dir
        self.headless = headless
        ensure_directory(output_dir)
    
        # Create the processor first
        self.processor = EventDataProcessor(output_dir=self.output_dir)
    
        # Use Chrome directly (no Edge fallback)
        self.scraper = RedHatEventsInteractiveScraper(
            filters=self.filters, 
            browser_type="chrome",
            processor=self.processor,
            output_dir=self.output_dir,
            headless=self.headless
        )
    
        # Store the path for last run data
        self.last_run_file = os.path.join(self.output_dir, "last_run_data.json")
    
    def run_once(self, save_excel=True, save_csv=True, export_to_sheets=False):
        """
        Run the scraper once and process results

        Args:
            save_excel (bool): Whether to save results to Excel
            save_csv (bool): Whether to save results to CSV
            export_to_sheets (bool): Whether to export results to Google Sheets (optional)
        
        Returns:
            tuple: (all_events, new_events, excel_path, csv_path, sheets_url)
        """
        try:
            logger.info(f"Starting batch run with filters: {self.filters}")
            start_time = time.time()
            
            # Generate timestamp for this session - used for screenshots only now
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Pass the timestamp to the scraper for consistent screenshot naming
            self.scraper.session_timestamp = timestamp
    
            # Scrape events
            all_events = self.scraper.scrape()
            logger.info(f"Scraped {len(all_events)} events")
    
            # Load last run data
            previous_events = load_last_run_data(self.last_run_file)
    
            # Identify new events and add 'is_new' flag to the data
            new_events, all_events_with_flag = compare_events(all_events, previous_events)
            all_events = all_events_with_flag  # Replace all_events with the flagged version
    
            # Log results
            logger.info(f"Found {len(new_events)} new events")
    
            excel_path = None
            csv_path = None
            sheets_url = None
        
            if all_events:
                if save_excel:
                    # Use a fixed filename instead of timestamp
                    filename = "redhat_events_latest.xlsx"

                    # Export to Excel with fixed filename
                    excel_path = self.processor.export_to_excel(all_events, filename)
                    logger.info(f"Exported all events to {excel_path}")
    
                # Export to CSV with fixed filename
                if save_csv:
                    csv_filename = "redhat_events_latest.csv"
                    csv_path = self.processor.export_to_csv(all_events, csv_filename)
                    logger.info(f"Exported all events to {csv_path}")
                
                # Clean up screenshots from previous runs, but keep ones from this run
                clean_screenshots(self.output_dir, timestamp)
            
                # Export to Google Sheets if enabled
                if export_to_sheets:
                    try:
                        sheets_url = self.processor.export_to_google_sheets(all_events)
                        if sheets_url:
                            logger.info(f"Exported all events to Google Sheets: {sheets_url}")
                        else:
                            logger.warning("Failed to export to Google Sheets")
                    except Exception as e:
                        logger.error(f"Error exporting to Google Sheets: {e}")
    
            # Save current data for next run
            save_last_run_data(all_events, self.last_run_file)
    
            # Calculate execution time
            execution_time = time.time() - start_time
            logger.info(f"Batch run completed in {execution_time:.2f} seconds")
    
            return all_events, new_events, excel_path, csv_path, sheets_url

        except Exception as e:
            logger.error(f"Error in batch run: {e}")
            return [], [], None, None, None
    
    def run_continuously(self):
        """
        Run the scraper periodically based on the configured interval
        """
        logger.info(f"Starting continuous batch mode (interval: {self.interval_days} days)")
        
        try:
            while True:
                # Run once
                all_events, new_events, excel_path, csv_path, sheets_url = self.run_once()
                
                # Calculate next run time
                next_run = datetime.datetime.now() + datetime.timedelta(days=self.interval_days)
                logger.info(f"Next run scheduled for: {next_run}")
                
                # Sleep until next run (convert days to seconds)
                time.sleep(self.interval_days * 24 * 60 * 60)
        
        except KeyboardInterrupt:
            logger.info("Batch mode stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous batch mode: {e}")

# For testing
if __name__ == "__main__":
    batch_runner = BatchRunner()
    all_events, new_events, excel_path, csv_path, sheets_url = batch_runner.run_once()
    
    print(f"Scraped {len(all_events)} events total")
    print(f"Found {len(new_events)} new events")
    if excel_path:
        print(f"Saved to Excel: {excel_path}")
    if csv_path:
        print(f"Saved to CSV: {csv_path}")