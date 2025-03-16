# RedHat Events Scraper - Technical Documentation

## Project Overview
The RedHat Events Scraper automatically extracts event information from the RedHat events page (https://www.redhat.com/en/events) with the following pre-set filters:
- Event Type: InPerson
- Region: North America
- Date: Upcoming Events

## Key Components

### Core Modules
- **scraper_interactive.py**: Selenium-based scraper that interacts with the RedHat website
- **data_processor.py**: Handles event data processing and exports to Excel/CSV
- **batch_script.py**: Manages automated scraping on a schedule
- **gui.py**: Provides the graphical user interface

### Output Files
- **redhat_events_latest.xlsx**: Excel file with all extracted events
- **redhat_events_latest.csv**: CSV file with the same data
- **last_run_data.json**: Stores previous run data to identify new events

## Features In Detail

### Event Extraction
The scraper collects the following information for each event:
- Title
- Date range (with parsed start/end dates)
- Location
- Event type
- Link to event page

### New Event Tracking
Events that weren't present in previous scraping runs are marked with "NEW!" in the exported files. This tracking works by:
1. Storing all events in a JSON file after each successful run
2. Comparing current events with previously stored events
3. Flagging any events that weren't in the previous data

### Scheduling
You can schedule automatic scraping using:
- System crontab (macOS)
- Frequency options: daily or weekly
- Custom time selection

## Command Line Options

Run the scraper without the GUI using these commands:

```bash
# Run once and exit
python3 main.py --once

# Run in continuous batch mode
python3 main.py --batch

# Export options
python3 main.py --once --excel --csv 

# Help
python3 main.py --help
```

## Configuration

Advanced settings can be modified in `config.py`:

```python
# Basic configuration
OUTPUT_DIR = "output"  # Change output directory
BATCH_FREQUENCY_DAYS = 7  # Default frequency for batch mode

# Filter settings
DEFAULT_FILTERS = {
    "event_type": "InPerson",
    "region": "North America",
    "date": "Upcoming Events"
}
```

## Troubleshooting Advanced Issues

### Selenium Issues
If the scraper fails to interact with the website:
1. Try running in visible mode: `python3 main.py --no-headless`
2. Check if website structure has changed (the "RedHat Events" page layout)
3. Review detailed logs in `redhat_scraper.log`

### Browser Driver Problems
If ChromeDriver issues persist:
1. Manually download ChromeDriver from https://chromedriver.chromium.org/
2. Place it in your PATH
3. Verify version compatibility with your Chrome installation

### Memory Usage
The scraper is designed to be lightweight, but if you encounter memory issues:
1. Limit the number of pages scraped (modify the `max_pages` variable in `scraper_interactive.py`)
2. Close other applications when running the scraper

## Limitations
- The scraper cannot access events behind login pages
- Performance depends on your internet connection speed
- Some dynamic content might be missed if it loads after the scraper processes the page
- Scheduled tasks require your Mac to be powered on at the scheduled time

## Files and Directory Structure
```
RedHatEventsScraper/
├── README.md                  # Quick start guide
├── documentation.md           # Technical documentation
└── source/
    ├── main.py                # Main entry point
    ├── gui.py                 # GUI implementation
    ├── gui_launcher.py        # GUI launcher script
    ├── batch_script.py        # Batch processing functionality
    ├── cron_runner.py         # Scheduler runner script
    ├── scraper_interactive.py # Core scraper implementation
    ├── data_processor.py      # Data processing and export
    ├── scheduler.py           # Scheduling functionality
    ├── scheduler_dialog.py    # Scheduler configuration dialog
    ├── config.py              # Configuration settings
    ├── utils.py               # Utility functions
    ├── output/                # Where results are saved
    └── requirements.txt       # Python dependencies
```

## Running from Source

To run the application directly from source code:

```bash
# Navigate to the source directory
cd /path/to/RedHatEventsScraper/source

# Run with GUI
python3 main.py --gui

# Run once in command-line mode
python3 main.py --once
```

## Development Notes

### Adding New Filters
To add or modify filters, edit the `DEFAULT_FILTERS` dictionary in `config.py` and update the `apply_filters_interactively` method in `scraper_interactive.py`.

### Browser Compatibility
The scraper is designed to work with Chrome as the primary browser. Supporting other browsers would require:
1. Modifying `setup_driver()` in `scraper_interactive.py` 
2. Adding browser-specific options and configurations

### Data Processing Extensions
To extend the data processing capabilities:
1. Add new methods to `EventDataProcessor` class in `data_processor.py`
2. Update the display formatting in the `format_for_display` method