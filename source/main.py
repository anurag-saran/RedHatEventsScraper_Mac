# Main entry point for RedHat Events Scraper
import sys
import argparse
import logging
from batch_script import BatchRunner
# from gui import run_gui
from config import DEFAULT_FILTERS, OUTPUT_DIR
from utils import ensure_directory
from scheduler import SchedulerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("redhat_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="RedHat Events Scraper")
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--gui", action="store_true", help="Run with graphical user interface")
    mode_group.add_argument("--batch", action="store_true", help="Run in batch mode")
    mode_group.add_argument("--once", action="store_true", help="Run once and exit")
    
    # Batch configuration
    parser.add_argument("--interval", type=int, default=7, help="Interval between batch runs (days)")
    
    # Output configuration
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory for files")
    
    # Selenium options
    parser.add_argument("--no-headless", action="store_true", help="Run Selenium in visible mode")
    
    # Export options
    parser.add_argument("--excel", action="store_true", help="Export to Excel format")
    parser.add_argument("--csv", action="store_true", help="Export to CSV format")
    parser.add_argument("--sheets", action="store_true", help="Export to Google Sheets")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Ensure output directory exists
    ensure_directory(args.output)
    
    # Use the default filters (no customization)
    filters = DEFAULT_FILTERS
    
    # Determine headless mode
    headless = not args.no_headless
    
    # Determine export formats
    save_excel = True  # Always true by default
    save_csv = True    # Always true by default
    export_sheets = args.sheets
    
    # If specific export formats are specified, only use those
    if args.excel or args.csv or args.sheets:
        save_excel = args.excel
        save_csv = args.csv
    
    # Initialize the scheduler (for all modes)
    scheduler = SchedulerManager(output_dir=args.output)
    
    # Run in appropriate mode
    if args.gui:
        # GUI mode
        logger.info("Starting in GUI mode")
        run_gui()
    elif args.batch:
        # Batch mode (continuous)
        logger.info(f"Starting in batch mode (interval: {args.interval} days)")
        batch_runner = BatchRunner(filters=filters, interval_days=args.interval, output_dir=args.output, headless=headless)
        batch_runner.run_continuously()
    else:
        # Single run mode (default)
        logger.info("Running scraper once")
        batch_runner = BatchRunner(filters=filters, output_dir=args.output, headless=headless)
        all_events, new_events, excel_path, csv_path, sheets_url = batch_runner.run_once(
            save_excel=save_excel,
            save_csv=save_csv,
            export_to_sheets=export_sheets
        )
        
        # Print summary
        print(f"\nScraping completed:")
        print(f"- Total events found: {len(all_events)}")
        print(f"- New events found: {len(new_events)}")
        if excel_path:
            print(f"- Excel results saved to: {excel_path}")
        if csv_path:
            print(f"- CSV results saved to: {csv_path}")
        if sheets_url:
            print(f"- Google Sheets URL: {sheets_url}")
        if not (excel_path or csv_path or sheets_url):
            print("- No results were saved")

if __name__ == "__main__":
    main()
