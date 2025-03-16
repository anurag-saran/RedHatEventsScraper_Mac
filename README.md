# Quick Start Guide: RedHat Events Scraper for Mac

This guide will help you get the RedHat Events Scraper running on your Mac quickly.

> ⏱️ The complete installation process takes approximately 10-15 minutes, depending on your internet connection and if you need to install Homebrew.

## 📁 Directory Structure

The application has the following structure:
```
RedHatEventsScraper/
├── README.md                  <- This guide
├── documentation.md           <- Technical documentation
└── source/                    <- Source code folder
    ├── main.py                <- Main program entry point
    ├── requirements.txt       <- Python dependencies
    ├── output/                <- Where results will be saved
    └── [other Python files]   
```

## 🔧 Installation Requirements

1. **Install Python 3.8+**
  
   ```bash
   # Check if Python is installed
   python3 --version
   
   # If not installed, use Homebrew
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install python3
   ```
 
2. **Install Google Chrome**
   - Download from https://www.google.com/chrome/ if not already installed

3. **Install ChromeDriver**
   ```bash
   brew install --cask chromedriver
   xattr -d com.apple.quarantine $(which chromedriver)
   ```

## ⚙️ Setting Up the Scraper

1. **Open Terminal and navigate to the RedHatEventsScraper folder**
   ```bash
   # Replace /path/to with your actual path
   cd /path/to/RedHatEventsScraper
   
   # Verify you're in the correct directory - you should see README.md listed
   ls
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate it (you'll see (venv) at the beginning of your prompt)
   source venv/bin/activate
   ```

3. **Navigate to the source folder and install dependencies**
   ```bash
   # IMPORTANT: Make sure you're in the source directory where requirements.txt is located
   cd source
   
   # Verify requirements.txt exists in current directory
   ls
   
   # Install the dependencies
   pip3 install -r requirements.txt
   ```
   
   If you encounter errors installing dependencies, you might need Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```

## 🚀 Running the Scraper

1. **Launch the GUI application**
   ```bash
   # Make sure you're in the source directory
   # If you're in the main RedHatEventsScraper directory:
   cd source
   
   # Launch the application with the graphical interface
   python3 main.py --gui
   ```
   
2. **Using the Interface**
   - Click **"Scrape Events"** to start the scraping process
   - Results will automatically be saved to the `output` folder as:
     - `redhat_events_latest.xlsx`
     - `redhat_events_latest.csv`
   - Use **"Save Excel As..."** or **"Save CSV As..."** to save to a custom location

3. **Scheduling Automatic Scraping**
   - Click the **"Schedule"** button
   - Select frequency (daily or weekly)
   - Set time to run
   - Click **"Schedule Job"**
   - Note: Your Mac must be powered on at the scheduled time

## 📊 Understanding Output Files

- Excel/CSV files include the following columns:
  - **New**: Indicates newly discovered events with "NEW!" flag
  - **Title**: Event title 
  - **Location**: Event location
  - **Date Range**: Full date information
  - **Start/End Date**: Formatted dates for sorting
  - **Link**: URL to the event page

## ⚠️ Important Notes

- The scraper automatically saves results to the `source/output` folder
- New events are marked with "NEW!" in the Excel and CSV files
- The scraper uses macOS crontab for scheduling
- Your Mac must be powered on for scheduled tasks to run

## 🛠️ Troubleshooting

**Cannot find requirements.txt**
```bash
# Make sure you're in the source directory where requirements.txt is located
cd /path/to/RedHatEventsScraper/source
ls
# You should see requirements.txt listed
```

**"ChromeDriver" security warning**
```bash
# Check ChromeDriver installation path
which chromedriver

# Then use that exact path in the command below
xattr -d com.apple.quarantine /path/to/chromedriver
```

**Permission denied for ChromeDriver**
```bash
chmod +x $(which chromedriver)
```

**Python command not found**
```bash
# Use full path to Python
/usr/local/bin/python3 main.py --gui
# Or for Homebrew Python
/opt/homebrew/bin/python3 main.py --gui
```

For detailed logs, check `redhat_scraper.log` in the application folder.