# GUI for the RedHat Events Scraper
import sys
import re
import datetime
import logging
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QCheckBox, 
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QTextBrowser,
    QProgressBar
)

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient

from data_processor import EventDataProcessor
from batch_script import BatchRunner
from config import DEFAULT_FILTERS, GUI_TITLE, GUI_WIDTH, OUTPUT_DIR
from utils import ensure_directory

logger = logging.getLogger(__name__)

# Define colors for the application
REDHAT_RED = "#EE0000"
DARK_BLUE = "#1A2C3D"
LIGHT_BLUE = "#3AA0FE"
LIGHT_GRAY = "#F5F5F5"
DARK_GRAY = "#333333"
SUCCESS_GREEN = "#1ED17E"

class ProgressAnimation(QWidget):
    """Modern loading animation with a moving ball"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setValue(0)
        self.setMinimumWidth(200)
        
        # Animation configuration
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.setInterval(20)  # Update every 20ms for smooth animation
        
        # Animation state
        self.position = 0
        self.direction = 1  # 1 = right, -1 = left
        self.running = False
        
    def setValue(self, value):
        """Set the progress value (0-100)"""
        self.value = max(0, min(100, value))
        self.update()
        
    def start_animation(self):
        """Start the animation"""
        self.running = True
        self.timer.start()
        
    def stop_animation(self):
        """Stop the animation"""
        self.running = False
        self.timer.stop()
        self.update()  # Force a final update
    
    def update_position(self):
        """Update the position of the moving element"""
        if not self.running:
            return
            
        # Update position (oscillate between 0 and 100)
        self.position += self.direction * 2
        
        # Change direction when reaching the ends
        if self.position >= 100:
            self.position = 100
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
            
        self.update()
        
    def paintEvent(self, event):
        """Draw the animation"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw track background (rounded rectangle)
        track_height = height * 0.6
        track_rect = QRectF(0, (height - track_height) / 2, width, track_height)
        
        # Create gradient for the track
        gradient = QLinearGradient(0, 0, width, 0)
        gradient.setColorAt(0, QColor(30, 30, 40))
        gradient.setColorAt(1, QColor(40, 40, 50))
        
        # Draw track with rounded corners
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(track_rect, track_height / 2, track_height / 2)
        
        if self.running:
            # Calculate ball position
            ball_size = track_height * 0.8
            pos_x = (width - ball_size) * (self.position / 100.0)
            pos_y = height / 2 - ball_size / 2
            
            # Create a circular gradient for the ball
            ball_color = QColor(LIGHT_BLUE)
            
            # Draw glow effect
            glow_size = ball_size * 1.6
            glow_rect = QRectF(
                pos_x - (glow_size - ball_size) / 2,
                pos_y - (glow_size - ball_size) / 2,
                glow_size,
                glow_size
            )
            
            # Create radial gradient for glow
            glow_gradient = QLinearGradient(
                glow_rect.left() + glow_rect.width() / 2,
                glow_rect.top() + glow_rect.height() / 2,
                glow_rect.right(),
                glow_rect.bottom()
            )
            glow_gradient.setColorAt(0, QColor(ball_color.red(), ball_color.green(), ball_color.blue(), 80))
            glow_gradient.setColorAt(1, QColor(ball_color.red(), ball_color.green(), ball_color.blue(), 0))
            
            painter.setBrush(glow_gradient)
            painter.drawEllipse(glow_rect)
            
            # Draw the ball
            ball_rect = QRectF(pos_x, pos_y, ball_size, ball_size)
            
            # Main ball
            painter.setBrush(QBrush(ball_color))
            painter.drawEllipse(ball_rect)
            
            # Highlight on the ball (small white circle)
            highlight_size = ball_size * 0.3
            highlight_rect = QRectF(
                pos_x + ball_size * 0.2,
                pos_y + ball_size * 0.2,
                highlight_size,
                highlight_size
            )
            painter.setBrush(QColor(255, 255, 255, 160))
            painter.drawEllipse(highlight_rect)

class ScraperWorker(QThread):
    """Worker thread for scraping to avoid freezing the GUI"""
    finished = pyqtSignal(list, list, str, str, str)  # Updated for 5 parameters
    error = pyqtSignal(str)
    
    def __init__(self, filters=None, use_headless=True):
        super().__init__()
        self.filters = filters or {}
        self.use_headless = use_headless
    
    def run(self):
        try:
            # Initialize batch runner with filters
            batch_runner = BatchRunner(filters=self.filters)
            
            # Run once and get results (note the new parameters)
            all_events, new_events, excel_path, csv_path, sheets_url = batch_runner.run_once(
                save_excel=True, 
                save_csv=True, 
                export_to_sheets=False  # Google Sheets disabled by default
            )
            
            # Emit results
            self.finished.emit(all_events, new_events, excel_path, csv_path, sheets_url)
        
        except Exception as e:
            logger.error(f"Error in scraper worker: {e}")
            self.error.emit(str(e))

class RedHatScraperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(GUI_TITLE)
        # Set initial size
        self.setGeometry(100, 100, GUI_WIDTH, 800)
        # Allow window resizing
        self.setMinimumSize(600, 700)
    
        # Apply global styles 
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F8F8;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #EE0000;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3AA0FE;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
                font-family: Arial, sans-serif;
                padding: 5px;
            }
        """)
    
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
    
        # Main layout with reduced padding
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)  # Reduced to save vertical space
    
        # Header section - RedHat style
        header = QWidget()
        header.setStyleSheet("""
            background-color: #1A2C3D;
            border-radius: 6px;
            padding: 5px;
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)  # Reduced margins
    
        # Logo and title
        title_label = QLabel("RedHat Events Scraper")
        title_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 22px;
            font-weight: bold;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
    
        # Subtitle
        subtitle_label = QLabel("Powered by Selenium for interactive web scraping")
        subtitle_label.setStyleSheet("""
            color: #BBBBBB;
            font-size: 12px;
            font-style: italic;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)
    
        main_layout.addWidget(header)
    
        # Output section with improved styling 
        self.create_output_section(main_layout)
    
        # Action buttons with more modern styling 
        self.create_action_buttons(main_layout)
    
        # Progress section with custom loading animation 
        self.create_progress_section(main_layout)
    
        # Initialize data members
        self.all_events = []
        self.new_events = []
        self.excel_path = None
        self.csv_path = None
    
        # Make sure output directory exists
        ensure_directory(OUTPUT_DIR)

    def create_output_section(self, parent_layout):
        """Create the output section of the GUI with improved styling"""
        output_group = QGroupBox("Results")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(10)  # Reduced for space saving
        output_layout.setContentsMargins(10, 20, 10, 10)  # Reduced margins

        # Summary in label form
        self.summary_label = QLabel("No data available")
        self.summary_label.setStyleSheet("""
            background-color: #1A2C3D;
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-weight: bold;
        """)
        self.summary_label.setAlignment(Qt.AlignCenter)
        output_layout.addWidget(self.summary_label)

        # Use QTextBrowser instead of QTextEdit
        self.results_text = QTextBrowser()
        self.results_text.setOpenExternalLinks(True)  # Enable clickable links
        self.results_text.setMinimumHeight(160)  # Reduced height
        self.results_text.setStyleSheet("""
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: white;
            color: #333333;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 8px;
        """)
        output_layout.addWidget(self.results_text)
    
        parent_layout.addWidget(output_group)

    def create_action_buttons(self, parent_layout):
        """Create action buttons with improved styling"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # Scrape button
        self.scrape_button = QPushButton("Scrape Events")
        self.scrape_button.setMinimumHeight(40)
        self.scrape_button.setStyleSheet("""
            background-color: #3AA0FE;
            font-size: 14px;
        """)
        self.scrape_button.clicked.connect(self.start_scraping)
        self.scrape_button.setCursor(Qt.PointingHandCursor)  
        button_layout.addWidget(self.scrape_button)

        # Save As Excel button - Updated text
        self.save_button = QPushButton("Save Excel As...")
        self.save_button.setMinimumHeight(40)
        self.save_button.setStyleSheet("""
            background-color: #1ED17E;
            font-size: 14px;
        """)
        self.save_button.clicked.connect(self.save_to_excel)
        self.save_button.setEnabled(False)  # Disable until data is available
        self.save_button.setCursor(Qt.PointingHandCursor)  
        button_layout.addWidget(self.save_button)
    
        # Save As CSV button - Updated text
        self.save_csv_button = QPushButton("Save CSV As...")
        self.save_csv_button.setMinimumHeight(40)
        self.save_csv_button.setStyleSheet("""
            background-color: #FFA500;
            font-size: 14px;
        """)
        self.save_csv_button.clicked.connect(self.save_to_csv)
        self.save_csv_button.setEnabled(False)  # Disable until data is available
        self.save_csv_button.setCursor(Qt.PointingHandCursor)  
        button_layout.addWidget(self.save_csv_button)

        # Schedule button - moved to the correct position in layout
        self.schedule_button = QPushButton("Schedule")
        self.schedule_button.setMinimumHeight(40)
        self.schedule_button.setStyleSheet("""
            background-color: #9B59B6;
            font-size: 14px;
        """)
        self.schedule_button.clicked.connect(self.open_scheduler)
        self.schedule_button.setCursor(Qt.PointingHandCursor)
        button_layout.addWidget(self.schedule_button)

        parent_layout.addLayout(button_layout)
    
    def get_current_filters(self):
        """Get the fixed filters - Always use headless mode"""
        return {
            "event_type": "InPerson",
            "region": "North America",
            "date": "Upcoming Events"
        }

    def create_progress_section(self, parent_layout):
        """Create progress section with custom loading animation"""
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(10, 20, 10, 10)

        # Status label with information for user
        self.status_label = QLabel("Ready to scrape RedHat events")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-weight: bold;
            color: #1A2C3D;
            font-size: 13px;
            margin-bottom: 5px;
        """)
        progress_layout.addWidget(self.status_label)

        # Improved loading animation widget
        self.loading_animation = ProgressAnimation()
        progress_layout.addWidget(self.loading_animation)

        parent_layout.addWidget(progress_group)
    
    def start_scraping(self):
        """Start the scraping process"""
        # Update UI
        self.scrape_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.save_csv_button.setEnabled(False)
        self.status_label.setText("Scraping in progress... (takes about 1 minute)")
        self.results_text.clear()
        # Update summary as well
        self.summary_label.setText("Scraping in progress...")
    
        # Start animation
        self.loading_animation.start_animation()
    
        # Get selected filters and always use headless mode
        filters = self.get_current_filters()
        use_headless = True
    
        # Display a message mentioning the selected filters
        filter_description = [
            f"Event Type: {filters['event_type']}",
            f"Region: {filters['region']}",
            f"Date: {filters['date']}"
        ]
    
        filter_text = ", ".join(filter_description)
    
        # Set filter explanation
        self.results_text.setHtml(f"""
        <div style="color: #666; margin: 10px;">
            <h3 style="color: #1A2C3D;">Starting RedHat Events Scraper</h3>
            <p>Using <b>Selenium</b> with headless browser to interactively browse the RedHat Events website with the following filters:</p>
            <ul>
                <li><b>{filter_text}</b></li>
            </ul>
            <p>Process steps:</p>
            <ol>
                <li>Opening web browser (running in background)</li>
                <li>Navigating to RedHat Events page</li>
                <li>Selecting filters</li>
                <li>Scraping event details</li>
                <li>Exporting to Excel and CSV</li>
            </ol>
            <p><i>Please wait while the browser loads and processes the data. This process takes about 1 minute...</i></p>
        </div>
        """)
    
        # Create and start worker thread
        self.worker = ScraperWorker(filters=filters, use_headless=use_headless)
        self.worker.finished.connect(self.handle_scraping_finished)
        self.worker.error.connect(self.handle_scraping_error)
        self.worker.start()
    
    def handle_scraping_finished(self, all_events, new_events, excel_path, csv_path=None, sheets_url=None):
        """Handle completion of scraping"""
        # Store results
        self.all_events = all_events
        self.new_events = new_events
        self.excel_path = excel_path
        self.csv_path = csv_path
    
        # Debug log
        if excel_path:
            logger.info(f"Excel path received: {excel_path}")
            if os.path.exists(excel_path):
                logger.info(f"Excel file exists at path: {excel_path}")
            else:
                logger.warning(f"Excel file DOES NOT exist at path: {excel_path}")

        # Update UI
        self.scrape_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.save_csv_button.setEnabled(True)

        # Stop animation
        self.loading_animation.stop_animation()

        # Display results
        if all_events:
            # Update summary with new events count
            total = len(all_events)
            new_count = sum(1 for event in all_events if event.get('is_new', False))

            if new_count > 0:
                self.summary_label.setText(f"{total} Events Found ({new_count} new)")
                self.summary_label.setStyleSheet("""
                    background-color: #1A2C3D;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-weight: bold;
                    border-left: 5px solid #FF5252;
                """)
            else:
                self.summary_label.setText(f"{total} Events Found (No new events)")
                self.summary_label.setStyleSheet("""
                    background-color: #1A2C3D;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-weight: bold;
                """)

            # Format the results with HTML for better presentation
            html_results = self.format_results_as_html(all_events)
            self.results_text.setHtml(html_results)

            # Update status with more detailed information - IMPROVED MESSAGE
            output_dir_relative = os.path.relpath(OUTPUT_DIR)
            if excel_path and os.path.exists(excel_path):
                excel_filename = os.path.basename(excel_path)
                csv_filename = os.path.basename(csv_path) if csv_path else "redhat_events_latest.csv"
                new_events_text = f"{new_count} new events" if new_count > 0 else "no new events"
                
                # Improved status message showing both Excel and CSV files
                self.status_label.setText(
                    f"Scraping completed. {total} events found ({new_events_text}). "
                    f"Results automatically saved to {output_dir_relative}/{excel_filename} and {output_dir_relative}/{csv_filename}"
                )
            else:
                new_events_text = f"{new_count} new events" if new_count > 0 else "no new events"
                self.status_label.setText(f"Scraping completed. {total} events found ({new_events_text}). (Excel file not saved)")
        else:
            self.summary_label.setText("No events found")
            self.results_text.setHtml("""
                <div style='text-align: center; margin-top: 50px; color: #666;'>
                    <h3>No events found.</h3>
                    <p>Try changing the filters or check if the RedHat Events page structure has changed.</p>
                </div>
            """)
            self.status_label.setText("Scraping completed. No events found.")
    
    def format_results_as_html(self, events):
        """Format events as HTML for better presentation in QTextEdit"""
        # Limit the number of events to show initially
        max_display = min(10, len(events))
        display_events = events[:max_display]

        # Calculate number of events per location and get unique event types
        event_types = set()
        for event in events:
            event_types.add(event.get('type', 'N/A'))

        # Formatted numbers for the summary
        total_events = len(events)
        total_types = len(event_types)

        html = f"""
        <style>
            .locations-box {{
                padding: 8px 12px;
                margin-bottom: 10px;
                border-radius: 4px;
                background-color: #1A2C3D;
                color: white;
            }}
            .event {{
                margin-bottom: 8px;
                padding: 6px 12px;
                border-left: 3px solid #3AA0FE;
                background-color: #f9f9f9;
                border-radius: 4px;
            }}

            .event-new {{
                border-left: 3px solid #FF5252;
                background-color: #FFF8E1;
            }}
            .new-badge {{
                display: inline-block;
                padding: 2px 6px;
                background-color: #FF5252;
                color: white;
                font-size: 10px;
                border-radius: 3px;
                margin-left: 8px;
                font-weight: bold;
            }}

            .event h3 {{
                margin: 0 0 3px 0;
                color: #1A2C3D;
                font-size: 13px;
            }}
            .event-details {{
                margin-left: 8px;
                color: #333;
                font-size: 12px;
            }}
            .event-meta {{
                display: flex;
                justify-content: space-between;
                font-size: 0.85em;
                color: #666;
                margin-top: 5px;
            }}
            .event-link {{
                color: #3AA0FE;
                text-decoration: none;
                cursor: pointer;
            }}
            .more-events {{
                text-align: center;
                color: #666;
                font-style: italic;
                margin-top: 12px;
                padding: 6px;
                background-color: #eee;
                border-radius: 4px;
            }}
        </style>
        """

        # Add individual events - compact version
        for i, event in enumerate(display_events, 1):
            event_title = event.get('title', 'N/A')
            event_date = event.get('date_range', 'N/A')
            event_location = event.get('location', 'N/A')
            event_link = event.get('link', 'N/A')
            is_new = event.get('is_new', False)
    
            # Add special class for new events
            event_class = "event event-new" if is_new else "event"
            # Add "NEW!" badge if this is a new event
            new_badge = '<span class="new-badge">NEW!</span>' if is_new else ''

            html += f"""
            <div class="{event_class}">
                <h3>Event {i}: {event_title} {new_badge}</h3>
                <div class="event-details">
                    <div class="event-meta">
                        <span><strong>Date:</strong> {event_date}</span>
                        <span><strong>Location:</strong> {event_location}</span>
                    </div>
            """
        
            # Link with all necessary properties
            if event_link and event_link != "N/A":
                html += f"""<p><a href="{event_link}" target="_blank" class="event-link" style="color: #3AA0FE; text-decoration: underline;">View on RedHat.com</a></p>"""
    
            html += "</div></div>"

        # Add a note if there are more events
        if len(events) > max_display:
            html += f"""
            <div class="more-events">
                + {len(events) - max_display} more events not shown. Check the Excel file for complete results.
            </div>
            """

        return html
        
    def handle_scraping_error(self, error_message):
        """Handle scraping error"""
        # Update UI
        self.scrape_button.setEnabled(True)
        self.status_label.setText(f"Error: {error_message}")
        self.loading_animation.stop_animation()
        self.summary_label.setText("Error during scraping")
    
        # Show error message using HTML formatting for better visibility
        error_html = f"""
        <div style='text-align: center; margin-top: 20px; padding: 15px; background-color: #FFEBEE; border-left: 4px solid #D32F2F; color: #D32F2F;'>
            <h3>Error During Scraping</h3>
            <p>{error_message}</p>
            <p style='font-size: smaller; margin-top: 10px;'>Check the log file for more details.</p>
        </div>
        """
        self.results_text.setHtml(error_html)
    
        # Show error message
        QMessageBox.critical(self, "Scraping Error", f"An error occurred during scraping:\n{error_message}")
    
    def save_to_excel(self):
        """Save current results to Excel at a custom location"""
        if not self.all_events:
            QMessageBox.warning(self, "No Data", "No data available to save.")
            return

        # Ask for filename
        default_dir = os.path.expanduser("~/Desktop")  # Use desktop as default location
        default_name = f"RedHat_Events_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
        default_path = os.path.join(default_dir, default_name)
    
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel As", default_path, "Excel Files (*.xlsx)"
        )

        if file_path:
            # Ensure the file has the correct extension
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
    
            # Start loading animation
            self.status_label.setText("Saving Excel file...")
            self.loading_animation.start_animation()
    
            # Save to Excel - pass the complete path
            processor = EventDataProcessor()
        
            # Use the complete path directly (don't extract basename)
            saved_path = processor.export_to_excel(self.all_events, file_path)
    
            # Stop loading animation
            self.loading_animation.stop_animation()
    
            if saved_path:
                self.status_label.setText(f"Excel file saved to {saved_path}")
            
                # Ask if user wants to open the file
                reply = QMessageBox.question(
                    self, "File Saved", 
                    f"Excel file saved successfully to {saved_path}.\nDo you want to open it now?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
        
                if reply == QMessageBox.Yes:
                    self._open_excel_file(saved_path)
            else:
                self.status_label.setText("Error saving data to Excel")
                QMessageBox.warning(self, "Save Error", "Failed to save data to Excel.")

    def save_to_csv(self):
        """Save current results to CSV at a custom location"""
        if not self.all_events:
            QMessageBox.warning(self, "No Data", "No data available to save.")
            return

        # Ask for filename
        default_dir = os.path.expanduser("~/Desktop")  # Use desktop as default location
        default_name = f"RedHat_Events_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        default_path = os.path.join(default_dir, default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV As", default_path, "CSV Files (*.csv)"
        )

        if file_path:
            # Ensure the file has the correct extension
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            # Start loading animation
            self.status_label.setText("Saving to CSV...")
            self.loading_animation.start_animation()

            # Save to CSV - pass the complete path
            processor = EventDataProcessor()
        
            # Use the complete path directly
            saved_path = processor.export_to_csv(self.all_events, file_path)

            # Stop loading animation
            self.loading_animation.stop_animation()

            if saved_path:
                self.status_label.setText(f"CSV file saved to {saved_path}")
            
                # Ask if user wants to open the file
                reply = QMessageBox.question(
                    self, "File Saved", 
                    f"CSV file saved successfully to {saved_path}.\nDo you want to open it now?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
        
                if reply == QMessageBox.Yes:
                    self._open_csv_file(saved_path)
            else:
                self.status_label.setText("Error saving data to CSV")
                QMessageBox.warning(self, "Save Error", "Failed to save data to CSV.")

    def open_scheduler(self):
        """Open the scheduler configuration dialog"""
        try:
            # Import here to avoid circular import
            from scheduler_dialog import SchedulerDialog
        
            dialog = SchedulerDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open scheduler: {str(e)}")
                
    def _open_excel_file(self, file_path):
        """Open an Excel file with the default application"""
        try:
            import platform
            import subprocess
        
            # Use different methods based on operating system
            system = platform.system()
        
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux and others
                subprocess.call(['xdg-open', file_path])
            
            self.status_label.setText(f"Opening Excel file: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"Error opening Excel file: {str(e)}")
            QMessageBox.warning(self, "Open Error", f"Could not open the Excel file: {str(e)}")
            
    def _open_csv_file(self, file_path):
        """Open a CSV file with the default application"""
        try:
            import platform
            import subprocess
        
            # Use different methods based on operating system
            system = platform.system()
        
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux and others
                subprocess.call(['xdg-open', file_path])
            
            self.status_label.setText(f"Opening CSV file: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"Error opening CSV file: {str(e)}")
            QMessageBox.warning(self, "Open Error", f"Could not open the CSV file: {str(e)}")

def run_gui():
    """Entry point for GUI"""
    app = QApplication(sys.argv)
    window = RedHatScraperGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()