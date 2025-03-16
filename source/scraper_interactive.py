# scraper_interactive.py - Uses an interactive approach with filters
import time
import logging
import os
import datetime
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
from utils import clean_text, parse_date_range, save_html_for_debugging, ensure_directory
from config import BASE_URL, HEADERS

logger = logging.getLogger(__name__)

class RedHatEventsInteractiveScraper:
    def __init__(self, filters=None, headless=True, browser_type="chrome", processor=None, output_dir="output"):
        """
        Initialize the Selenium scraper with optional filters
    
        Args:
            filters (dict): Dictionary with filters to apply (event_type, region, date)
            headless (bool): Whether to run browser in headless mode
            browser_type (str): Type of browser to use ("chrome" or "edge")
            processor (EventDataProcessor): Data processor for exporting events
            output_dir (str): Directory for output files
        """
        self.base_url = BASE_URL
        self.filters = filters or {}
        self.headless = headless
        self.browser_type = browser_type.lower()  # Convert to lowercase to avoid case issues
        self.driver = None
        self.processor = processor
        self.output_dir = output_dir
        ensure_directory(output_dir)
    
    def setup_driver(self):
        """Set up WebDriver (Chrome) with platform-specific configuration and headless option"""
        try:
            # Use headless mode by default (unless specified otherwise)
            use_headless = self.headless
        
            # Detect operating system
            import platform
            system = platform.system()
            logger.info(f"Detected operating system: {system}")
        
            # Create Chrome options (common for all platforms)
            options = ChromeOptions()
            if use_headless:
                options.add_argument("--headless=new")  # Modern headless mode
            options.add_argument("--window-size=1920,1080")
        
            # Some options are problematic on Mac, so only add them on Windows/Linux
            if system != "Darwin":  # Darwin is macOS
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
        
            # Add User-Agent from config
            if "User-Agent" in HEADERS:
                options.add_argument(f"user-agent={HEADERS['User-Agent']}")
        
            # Platform-specific setup
            if system == "Darwin":  # macOS
                try:
                    # Try direct Chrome initialization first (works on newer macOS versions)
                    logger.info("Trying direct Chrome initialization on macOS")
                    driver = webdriver.Chrome(options=options)
                    logger.info("macOS Chrome initialization successful")
                    driver.implicitly_wait(10)
                    return driver
                except Exception as mac_error:
                    logger.warning(f"Direct Chrome initialization failed on macOS: {mac_error}")
                    # Fall through to the universal fallback
            else:
                # For Windows, skip the problematic WebDriverManager and use direct initialization
                logger.info(f"Using direct Chrome initialization on {system}")
                try:
                    driver = webdriver.Chrome(options=options)
                    logger.info(f"Chrome initialization successful on {system}")
                    driver.implicitly_wait(10)
                    return driver
                except Exception as win_error:
                    logger.warning(f"Direct Chrome initialization failed on {system}: {win_error}")
                    # Fall through to the universal fallback
        
            # Universal fallback method as last resort - this works well on all platforms
            logger.info("Using universal fallback method...")
        
            options = ChromeOptions()
            if use_headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        
            # Create a new Chrome driver with minimal options
            driver = webdriver.Chrome(options=options)
            logger.info("Fallback method successful")
            driver.implicitly_wait(10)
            return driver
        
        except Exception as e:
            logger.error(f"All WebDriver initialization methods failed: {e}")
            logger.exception("WebDriver initialization error details:")
            raise Exception("Failed to initialize Chrome WebDriver on all attempts")
    
    def take_screenshot(self, filename="screenshot.png"):
        """
        Take a screenshot of the current browser window
        """
        if self.driver:
            try:
                # Add timestamp to filename if not already present
                if "_202" not in filename: # Check if filename already has timestamp
                    # Get timestamp from current time
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    base, ext = os.path.splitext(filename)
                    filename = f"{base}_{timestamp}{ext}"
                
                screenshot_path = os.path.join(self.output_dir, filename)
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved to {screenshot_path}")
                return screenshot_path
            except Exception as e:
                logger.error(f"Error taking screenshot: {e}")
        return None
    
    def wait_for_element(self, by, selector, timeout=10, take_screenshot=True):
        """
        Wait for an element to be present in the DOM
        
        Returns:
            WebElement or None: The element if found, None otherwise
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            if take_screenshot:
                self.take_screenshot(f"timeout_{selector.replace('/', '_')}.png")
            return None
        
    def safe_click(self, element, description="element"):
        """
        Attempt to click on an element safely
        """
        if not element:
            logger.warning(f"Cannot click on {description}: element is None")
            return False
            
        try:
            # Try to scroll to the element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            # Try to click with JavaScript (more reliable)
            self.driver.execute_script("arguments[0].click();", element)
            logger.info(f"Clicked on {description} with JavaScript")
            return True
        except Exception as e:
            # If JavaScript click fails, try a normal click
            try:
                element.click()
                logger.info(f"Clicked on {description} with regular click")
                return True
            except Exception as click_error:
                logger.error(f"Failed to click on {description}: {click_error}")
                self.take_screenshot(f"click_error_{description.replace(' ', '_')}.png")
                return False

    def apply_filters_interactively(self):
        """
        Apply filters by interacting directly with the RedHat Events interface
        """
        logger.info(f"Applying filters interactively: {self.filters}")
    
        try:
            # Wait for the page to load completely
            self.wait_for_element(By.CSS_SELECTOR, '.rh-navigation')
            logger.info("Page loaded, navigation found")
        
            # Take a screenshot before applying filters
            self.take_screenshot("before_filters.png")
        
            # Scroll down to see the filters
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
        
            # Select the event type
            if "event_type" in self.filters and self.filters["event_type"]:
                # Find and click on the Event type section expander if needed
                event_type_header = self.driver.find_elements(By.XPATH, "//span[text()='Event type']")
                if event_type_header:
                    logger.info("Found Event type section header")
                    if not self.safe_click(event_type_header[0], "Event type header"):
                        # If clicking on the header fails, try to continue anyway
                        logger.warning("Failed to click on Event type header, but continuing")
                    time.sleep(1)
            
                # Determine the exact text to search for based on the filter
                event_type_text = "In-person" if self.filters["event_type"] == "InPerson" else "Online"
            
                # Find and click on the appropriate checkbox
                logger.info(f"Looking for {event_type_text} checkbox")
                target_labels = self.driver.find_elements(By.XPATH, f"//label[contains(text(), '{event_type_text}')]")
            
                if target_labels:
                    logger.info(f"Found {len(target_labels)} {event_type_text} labels")
                    for label in target_labels:
                        # Get the ID of the associated checkbox
                        try:
                            checkbox_id = label.get_attribute("for")
                            if checkbox_id:
                                checkbox = self.driver.find_element(By.ID, checkbox_id)
                                if not checkbox.is_selected():
                                    logger.info(f"Clicking {event_type_text} checkbox with ID: {checkbox_id}")
                                    self.safe_click(checkbox, f"{event_type_text} checkbox")
                                else:
                                    logger.info(f"{event_type_text} checkbox is already selected")
                            else:
                                # If the for attribute doesn't exist, click on the label directly
                                logger.info(f"Clicking {event_type_text} label directly")
                                self.safe_click(label, f"{event_type_text} label")
                        except Exception as e:
                            logger.error(f"Error selecting {event_type_text} checkbox: {e}")
                            # Try to click on the label directly as fallback
                            self.safe_click(label, f"{event_type_text} label (fallback)")
                        
                    time.sleep(2)
                else:
                    # Try a different approach if labels weren't found
                    type_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                    for i, checkbox in enumerate(type_checkboxes):
                        parent_element = self.driver.execute_script("return arguments[0].parentNode;", checkbox)
                        if event_type_text.lower() in parent_element.text.lower():
                            logger.info(f"Found {event_type_text} checkbox using parent text, index: {i}")
                            self.safe_click(checkbox, f"{event_type_text} checkbox #{i}")
                            break
        
            # Select the region
            if "region" in self.filters and self.filters["region"]:
                # Find and click on the Region section expander if needed
                region_header = self.driver.find_elements(By.XPATH, "//span[text()='Region']")
                if region_header:
                    logger.info("Found Region section header")
                    if not self.safe_click(region_header[0], "Region header"):
                        logger.warning("Failed to click on Region header, but continuing")
                    time.sleep(1)
            
                # Determine the exact text to search for
                region_text = self.filters["region"]
            
                # Find and click on the region checkbox
                logger.info(f"Looking for {region_text} checkbox")
                region_labels = self.driver.find_elements(By.XPATH, f"//label[contains(text(), '{region_text}')]")
            
                if region_labels:
                    logger.info(f"Found {len(region_labels)} {region_text} labels")
                    for label in region_labels:
                        try:
                            checkbox_id = label.get_attribute("for")
                            if checkbox_id:
                                checkbox = self.driver.find_element(By.ID, checkbox_id)
                                if not checkbox.is_selected():
                                    logger.info(f"Clicking {region_text} checkbox with ID: {checkbox_id}")
                                    self.safe_click(checkbox, f"{region_text} checkbox")
                                else:
                                    logger.info(f"{region_text} checkbox is already selected")
                            else:
                                logger.info(f"Clicking {region_text} label directly")
                                self.safe_click(label, f"{region_text} label")
                        except Exception as e:
                            logger.error(f"Error selecting {region_text} checkbox: {e}")
                            self.safe_click(label, f"{region_text} label (fallback)")
                
                    time.sleep(2)
                else:
                    # Alternative approach
                    region_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                    for i, checkbox in enumerate(region_checkboxes):
                        parent_element = self.driver.execute_script("return arguments[0].parentNode;", checkbox)
                        if region_text.lower() in parent_element.text.lower():
                            logger.info(f"Found {region_text} checkbox using parent text, index: {i}")
                            self.safe_click(checkbox, f"{region_text} checkbox #{i}")
                            break
        
            # Check if a date filter is specified
            if "date" in self.filters and self.filters["date"]:
                # Find and click on the Date section expander if needed
                date_header = self.driver.find_elements(By.XPATH, "//span[text()='Date']")
                if date_header:
                    logger.info("Found Date section header")
                    if not self.safe_click(date_header[0], "Date header"):
                        logger.warning("Failed to click on Date header, but continuing")
                    time.sleep(1)
            
                # Determine the exact text to search for
                date_text = "Upcoming events" if self.filters["date"] == "Upcoming Events" else "Previous events"
            
                # Find and check if the correct date filter is selected
                logger.info(f"Looking for {date_text} radio button")
                date_labels = self.driver.find_elements(By.XPATH, f"//label[contains(text(), '{date_text}')]")
            
                if date_labels:
                    logger.info(f"Found {len(date_labels)} {date_text} labels")
                    for label in date_labels:
                        try:
                            radio_id = label.get_attribute("for")
                            if radio_id:
                                radio = self.driver.find_element(By.ID, radio_id)
                                if not radio.is_selected():
                                    logger.info(f"Clicking {date_text} radio with ID: {radio_id}")
                                    self.safe_click(radio, f"{date_text} radio")
                                else:
                                    logger.info(f"{date_text} radio is already selected")
                            else:
                                logger.info(f"Clicking {date_text} label directly")
                                self.safe_click(label, f"{date_text} label")
                        except Exception as e:
                            logger.error(f"Error selecting {date_text} radio: {e}")
                            self.safe_click(label, f"{date_text} label (fallback)")
                
                    time.sleep(2)
                else:
                    # Alternative approach
                    date_radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    for i, radio in enumerate(date_radios):
                        parent_element = self.driver.execute_script("return arguments[0].parentNode;", radio)
                        if date_text.lower() in parent_element.text.lower():
                            logger.info(f"Found {date_text} radio using parent text, index: {i}")
                            self.safe_click(radio, f"{date_text} radio #{i}")
                            break
        
            # Take a screenshot after selecting filters
            self.take_screenshot("after_selecting_filters.png")
        
            # Removal of all search section and click on "Search" button
            # since results are filtered automatically
        
            # Wait for filtered results to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.rhdc-search-listing, .rh-card--layout'))
                )
                logger.info("Filtered results loaded successfully")
            except TimeoutException:
                logger.warning("Timeout waiting for filtered results")
                self.take_screenshot("timeout_waiting_for_results.png")
        
        except Exception as e:
            logger.error(f"Error applying filters interactively: {e}")
            self.take_screenshot("error_applying_filters.png")
    
    def extract_events(self, html_content):
        """
        Extract event information from HTML content
        
        Args:
            html_content (str): HTML content to parse
            
        Returns:
            list: List of event dictionaries
        """
        if not html_content:
            logger.error("No HTML content to parse")
            return []
        
        events = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Save HTML for debugging
        save_html_for_debugging(html_content, "debug_redhat_page_interactive.html")
        
        # Search for events on the page
        all_selectors = [
            # Selectors for filtered event cards
            'div.rh-card--layout',
            # Selectors for events on the home page
            '.pf-v5-c-card',
            '.pf-c-card',
            '.card',
            'div[class*="card"]',
            'div[class*="event"]',
            # Other possible selectors
            '.eventcard',
            'article.event',
            '.node--type-event'
        ]
        
        for selector in all_selectors:
            event_cards = soup.select(selector)
            if event_cards:
                logger.info(f"Found {len(event_cards)} event cards with selector '{selector}'")
                break
        else:
            event_cards = []
            logger.info("No event cards found with any selector")
        
        for card in event_cards:
            try:
                # Initialize event data
                event = {}
                
                # Use different selectors to extract the event type
                type_selectors = [
                    '.rh-card-header-title-small', 
                    '.card-header', 
                    'h4',
                    '.rh-card-header--component h3',
                    # Selectors based on the screenshot
                    '.rh-card-header',
                    'div[class*="card-header"]',
                    'div[class*="header"]'
                ]
                
                for selector in type_selectors:
                    type_elem = card.select_one(selector)
                    if type_elem:
                        event['type'] = clean_text(type_elem.text)
                        break
                else:
                    # Check for direct "ONLINE" or "IN-PERSON" header in the card
                    online_headers = card.find_all(string=re.compile(r'ONLINE|IN-PERSON|IN PERSON', re.IGNORECASE))
                    if online_headers:
                        event['type'] = clean_text(online_headers[0])
                    else:
                        event['type'] = "N/A"
                
                # Use different selectors to extract the title
                title_selectors = [
                    '.rh-featured-event-teaser-headline-secondary a',
                    'h2 a', 
                    'h3 a', 
                    '.card-title a', 
                    'a[href*="events"]',
                    # Additional title selectors
                    'h2', 'h3', '.card-title', '.event-title',
                    '[class*="title"]'
                ]
                
                for selector in title_selectors:
                    title_elems = card.select(selector)
                    if title_elems:
                        for title_elem in title_elems:
                            # Only get titles that are not "ONLINE" or "IN-PERSON"
                            if not re.match(r'^\s*(ONLINE|IN-PERSON|IN PERSON)\s*$', title_elem.text, re.IGNORECASE):
                                event['title'] = clean_text(title_elem.text)
                                
                                # Extract the link to the event
                                if title_elem.name == 'a':
                                    event['link'] = title_elem.get('href', 'N/A')
                                else:
                                    # If the element isn't an <a>, look for a link inside it or its parent
                                    link = title_elem.find('a') or title_elem.parent.find('a')
                                    if link:
                                        event['link'] = link.get('href', 'N/A')
                                    else:
                                        # Look for any link in the card
                                        any_link = card.find('a')
                                        if any_link:
                                            event['link'] = any_link.get('href', 'N/A')
                                        else:
                                            event['link'] = "N/A"
                                            
                                if event['link'] and event['link'].startswith('/'):
                                    event['link'] = f"https://www.redhat.com{event['link']}"
                                
                                break
                        
                        if 'title' in event:
                            break
                
                if 'title' not in event:
                    # If no title was found, use any text that might be a title
                    potential_titles = [e for e in card.find_all(text=True) if len(e.strip()) > 5 
                                        and not re.match(r'^\s*(ONLINE|IN-PERSON|IN PERSON|WATCH|REGISTER)\s*$', e, re.IGNORECASE)]
                    if potential_titles:
                        event['title'] = clean_text(potential_titles[0])
                    else:
                        event['title'] = "N/A"
                    
                    # Look for any link
                    any_link = card.find('a')
                    if any_link:
                        event['link'] = any_link.get('href', 'N/A')
                        if event['link'].startswith('/'):
                            event['link'] = f"https://www.redhat.com{event['link']}"
                    else:
                        event['link'] = "N/A"
                
                # Use different selectors to extract the date
                date_selectors = [
                    '.rh-featured-event-teaser-date-secondary',
                    'time', 
                    '.date', 
                    '.card-date',
                    # Additional date selectors
                    '[class*="date"]',
                    '[datetime]'
                ]
                
                for selector in date_selectors:
                    date_elem = card.select_one(selector)
                    if date_elem:
                        event['date_range'] = clean_text(date_elem.text)
                        break
                else:
                    # Look for text that resembles a date
                    date_patterns = [
                        r'\w+ \d+, \d{4}',  # January 1, 2025
                        r'\d{1,2}/\d{1,2}/\d{2,4}',  # 1/1/2025
                        r'\d{4}-\d{2}-\d{2}'  # 2025-01-01
                    ]
                    
                    for text in card.stripped_strings:
                        for pattern in date_patterns:
                            if re.search(pattern, text):
                                event['date_range'] = clean_text(text)
                                break
                        if 'date_range' in event:
                            break
                    
                    if 'date_range' not in event:
                        event['date_range'] = "N/A"
                
                # Parse the date range
                date_info = parse_date_range(event['date_range'])
                event.update(date_info)
                
                # For location, use the event type (which often contains location info)
                event['location'] = event['type']
                
                # Use different selectors to extract the action (Watch, Learn more, etc.)
                action_selectors = [
                    '.rh-cta-link',
                    'a.button',
                    '.button',
                    'a.cta',
                    '.cta-link',
                    '[class*="button"]',
                    '[class*="cta"]'
                ]
                
                for selector in action_selectors:
                    action_elem = card.select_one(selector)
                    if action_elem:
                        event['action'] = clean_text(action_elem.text)
                        break
                else:
                    # Try to find any button-like text
                    button_texts = card.find_all(string=re.compile(r'WATCH|LEARN|REGISTER', re.IGNORECASE))
                    if button_texts:
                        event['action'] = clean_text(button_texts[0])
                    else:
                        event['action'] = "N/A"
                
                # Description (not available in cards, leave empty)
                event['description'] = ""
                
                # Only add events with valid titles and filter out "Event Type" items
                if event['title'] != "N/A" and event['title'].lower() != "event type":
                    events.append(event)
                    logger.info(f"Extracted event: {event['title']} - Type: {event['type']} - Date: {event['date_range']} - Location: {event['location']} - Link: {event.get('link', 'N/A')}")
            
            except Exception as e:
                logger.error(f"Error extracting event data: {e}")
                continue
        
        return events
    
    def get_next_page_url(self):
        """
        Check if there's a next page button and return its URL
    
        Returns:
            str: URL of next page, or None if there's no next page
        """
        try:
            # Reduce the number of selectors and optimize the search
            # Use only the most likely selectors
            for selector in [
                'a[data-testid="pager-next"]', 
                'a[aria-label="Next"]',
                'a.next'
            ]:
                next_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in next_buttons:
                    # Skip disabled buttons
                    if btn.get_attribute('aria-disabled') == 'true':
                        continue
                    return btn.get_attribute('href')
        
            # Simplified text search to be faster
            next_buttons = self.driver.find_elements(By.XPATH, "//a[contains(., 'Next')]")
            for btn in next_buttons:
                if btn.get_attribute('aria-disabled') != 'true':
                    return btn.get_attribute('href')
        
            # No next page found
            return None
        except Exception as e:
            # Add error log for potential issues
            logger.debug(f"Error checking for next page: {e}")
            return None
    
    def scrape(self):
        """
        Main scraping function using interactive filtering
        """
        all_events = []
    
        try:
            # Initialize the WebDriver
            self.driver = self.setup_driver()
        
            # Navigate to base URL
            logger.info(f"Navigating to base URL: {self.base_url}")
            self.driver.get(self.base_url)
        
            # Wait for page to load - reduced to 3 seconds
            time.sleep(3)
        
            # Apply filters interactively
            self.apply_filters_interactively()
        
            # Take a screenshot after applying filters
            self.take_screenshot("after_filters_applied.png")
        
            page = 0
            max_pages = 10  # Safety limit
        
            while page < max_pages:
                page += 1
                logger.info(f"Processing page {page}")
            
                # Wait for content to load - reduced wait time
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.rh-divider-content, .rhdc-search-listing, .rh-card--layout'))
                    )
                    # Reduced wait after page load
                    time.sleep(1)
                except TimeoutException:
                    logger.warning(f"Timeout waiting for page content to load on page {page}")
                    self.take_screenshot(f"timeout_page{page}.png")
            
                # Get page HTML
                html_content = self.driver.page_source
            
                # Extract events
                events = self.extract_events(html_content)
            
                if not events:
                    logger.info(f"No events found on page {page}, stopping pagination")
                    break
            
                # Add events from this page
                all_events.extend(events)
                logger.info(f"Found {len(events)} events on page {page}")
            
                # Check for next page - optimized and faster verification
                logger.info("Checking for next page...")
                next_url = self.get_next_page_url()
            
                if not next_url:
                    logger.info("No next page found, stopping pagination")
                    # Message indicating the end of pagination and start of cleanup
                    logger.info("Finalizing scraping process...")
                    break
            
                # Move to next page
                logger.info(f"Moving to next page: {next_url}")
                self.driver.get(next_url)
                # Reduced wait after navigation
                time.sleep(1.5)
    
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            logger.exception("Detailed stack trace:")
            self.take_screenshot("error_during_scraping.png")
        
            # Export what we have if an error occurs
            if all_events and self.processor:
                # Export what we have collected to Excel
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"redhat_events_all_{timestamp}.xlsx"
                excel_path = self.processor.export_to_excel(all_events, filename)
                logger.info(f"Exported {len(all_events)} events to Excel: {excel_path}")
    
        finally:
            # Clean up - add logs to know what's happening during closure
            logger.info("Cleaning up resources...")
            if self.driver:
                logger.info("Closing browser...")
                try:
                    # Close with timeout to avoid blocking
                    self.driver.set_page_load_timeout(10)
                    self.driver.set_script_timeout(10)
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error while closing browser: {e}")
                finally:
                    self.driver = None
                    logger.info("Browser closed")
    
        logger.info(f"Total scraped events: {len(all_events)}")
        return all_events

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("redhat_scraper.log"),
            logging.StreamHandler()
        ]
    )
    
    # Initialize scraper with InPerson filter
    scraper = RedHatEventsInteractiveScraper(
        filters={"event_type": "InPerson", "region": "North America", "date": "Upcoming Events"},
        headless=False  # Set to False to see the browser
    )
    
    # Run the scraper
    events = scraper.scrape()
    
    # Print events
    print(f"\nFound {len(events)} events:")
    for i, event in enumerate(events, 1):
        print(f"Event {i}: {event['title']} ({event['date_range']})")
        print(f"  Type: {event['type']}")
        print(f"  Link: {event['link']}")
        print("-" * 50)