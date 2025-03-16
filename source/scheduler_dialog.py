# scheduler_dialog.py - Updated to use only system schedulers (Windows Task Scheduler or macOS/Linux crontab)
import sys
import platform
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QComboBox, QTimeEdit, QCheckBox,
    QMessageBox, QWidget, QFrame
)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont

from scheduler import SchedulerManager

class SchedulerDialog(QDialog):
    """Dialog for configuring scheduled scraping jobs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scheduler = SchedulerManager()
        self.init_ui()
        self.load_jobs()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Schedule Automatic Scraping")
        self.setMinimumWidth(600)
        self.setMinimumHeight(550)  # Increased minimum height
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)  # Add space between sections
        
        # Schedule configuration group
        config_group = QGroupBox("Scraping Schedule Configuration")
        config_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #EE0000;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QFormLayout(config_group)
        config_layout.setVerticalSpacing(12)  # Add more vertical spacing
        
        # Schedule type (weekly or interval)
        self.schedule_type = QComboBox()
        self.schedule_type.addItem("Run every X days", "interval")
        self.schedule_type.addItem("Run on specific days of week", "weekly")
        self.schedule_type.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #BBBBBB;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
        """)
        config_layout.addRow("Schedule Type:", self.schedule_type)
        
        # Interval days (for interval schedule)
        self.interval_days = QSpinBox()
        self.interval_days.setMinimum(1)
        self.interval_days.setMaximum(30)
        self.interval_days.setValue(7)  # Default: 1 week
        self.interval_days.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #BBBBBB;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
        """)
        config_layout.addRow("Run every X days:", self.interval_days)
        
        # Days of week (for weekly schedule)
        self.days_group = QGroupBox()
        self.days_group.setTitle("Days of week:")
        self.days_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #EE0000;
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                background-color: #F8F8F8;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                margin-left: 8px;
                padding: 0 5px;
            }
        """)
        days_layout = QHBoxLayout(self.days_group)
        days_layout.setContentsMargins(10, 15, 10, 10)
        
        self.day_checkboxes = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            checkbox = QCheckBox(day)
            # Default to Monday
            if day == "Mon":
                checkbox.setChecked(True)
            checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 5px;
                }
            """)
            self.day_checkboxes[day.lower()] = checkbox
            days_layout.addWidget(checkbox)
        
        config_layout.addRow("", self.days_group)
        
        # Time to run
        self.run_time = QTimeEdit()
        self.run_time.setTime(QTime(9, 0))  # Default: 9:00 AM
        self.run_time.setDisplayFormat("HH:mm")
        self.run_time.setStyleSheet("""
            QTimeEdit {
                padding: 5px;
                border: 1px solid #BBBBBB;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
        """)
        config_layout.addRow("Time to run:", self.run_time)
        
        # Control buttons - CENTERED
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Add stretch on both sides to center
        
        self.schedule_button = QPushButton("Schedule Job")
        self.schedule_button.clicked.connect(self.schedule_job)
        self.schedule_button.setStyleSheet("""
            QPushButton {
                background-color: #3AA0FE;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 150px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        # Add pointing hand cursor
        self.schedule_button.setCursor(Qt.PointingHandCursor)
        
        button_layout.addWidget(self.schedule_button)
        button_layout.addStretch()  # Add stretch to center the button
        
        # Add configuration to main layout
        main_layout.addWidget(config_group)
        main_layout.addLayout(button_layout)
        
        # Add info about system scheduling
        system_name = platform.system()
        
        # Check if system scheduler is available
        system_scheduler_available = self.scheduler.system_scheduler_available
        
        # System scheduler info section
        if system_name == 'Darwin':  # macOS
            title = "System Scheduling (macOS)"
            if system_scheduler_available:
                info_text = (
                    "The scheduler will use macOS crontab for persistent scheduling. "
                    "This means the scraper will run at the scheduled time even if "
                    "the application is closed. Note that your computer must be powered on "
                    "for scheduled tasks to run. The scheduled runs will save results to "
                    "the output directory specified in the configuration."
                )
            else:
                info_text = (
                    "System scheduling requires crontab, which was not found on your "
                    "system. Please ensure crontab is installed and accessible to schedule jobs. "
                    "Contact your system administrator if you need assistance installing crontab."
                )
        elif system_name == 'Windows':  # Windows
            title = "System Scheduling (Windows)"
            if system_scheduler_available:
                info_text = (
                    "The scheduler will use Windows Task Scheduler for persistent scheduling. "
                    "This means the scraper will run at the scheduled time even if "
                    "the application is closed. Note that your computer must be powered on "
                    "for scheduled tasks to run. The scheduled runs will save results to "
                    "the output directory specified in the configuration."
                )
            else:
                info_text = (
                    "System scheduling requires Windows Task Scheduler, which was not found "
                    "or is not accessible. Please ensure you have sufficient permissions to "
                    "create scheduled tasks. Contact your system administrator if you need assistance."
                )
        else:  # Linux or other
            title = "System Scheduling (Linux)"
            if system_scheduler_available:
                info_text = (
                    "The scheduler will use crontab for persistent scheduling. "
                    "This means the scraper will run at the scheduled time even if "
                    "the application is closed. The scheduled runs will save results to "
                    "the output directory specified in the configuration."
                )
            else:
                info_text = (
                    "System scheduling requires crontab, which was not found on your "
                    "system. Please ensure crontab is installed and accessible to schedule jobs. "
                    "Contact your system administrator if you need assistance installing crontab."
                )
        
        # Create and add the info box
        system_info = QGroupBox(title)
        system_info.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #EE0000;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        system_layout = QVBoxLayout(system_info)
        
        # Add info text
        system_text = QLabel(info_text)
        system_text.setWordWrap(True)
        system_text.setStyleSheet("""
            padding: 10px;
            background-color: #F5F5F5;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
            color: #555555;
        """)
        
        system_layout.addWidget(system_text)
        
        # Add to main layout
        main_layout.addWidget(system_info)
        
        # Current Schedule - improved status display
        self.status_group = QGroupBox("Current Schedule Status")
        self.status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #EE0000;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        status_layout = QVBoxLayout(self.status_group)
        status_layout.setSpacing(10)
        
        # Status container
        self.status_container = QWidget()
        status_container_layout = QVBoxLayout(self.status_container)
        status_container_layout.setContentsMargins(0, 0, 0, 0)
        status_container_layout.setSpacing(8)
        
        # Status header - always visible
        self.status_header = QLabel("No job currently scheduled")
        self.status_header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.status_header.setStyleSheet("""
            padding: 10px;
            background-color: #F5F5F5;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
            color: #555555;
        """)
        self.status_header.setAlignment(Qt.AlignCenter)
        self.status_header.setMinimumHeight(40)  # Ensure sufficient height
        self.status_header.setWordWrap(True)  # Allow text wrapping
        status_container_layout.addWidget(self.status_header)
        
        # Schedule details - hidden when no job
        self.schedule_details = QLabel("")
        self.schedule_details.setStyleSheet("""
            padding: 10px;
            background-color: #F5F5F5;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
            color: #555555;
        """)
        self.schedule_details.setAlignment(Qt.AlignCenter)
        self.schedule_details.setMinimumHeight(40)  # Ensure sufficient height
        self.schedule_details.setWordWrap(True)  # Allow text wrapping
        self.schedule_details.setVisible(False)
        status_container_layout.addWidget(self.schedule_details)
        
        # Next run info - hidden when no job
        self.next_run_info = QLabel("")
        self.next_run_info.setStyleSheet("""
            padding: 10px;
            background-color: #F5F5F5;
            border: 1px solid #DDDDDD;
            border-radius: 4px;
            color: #555555;
        """)
        self.next_run_info.setAlignment(Qt.AlignCenter)
        self.next_run_info.setMinimumHeight(40)  # Ensure sufficient height
        self.next_run_info.setWordWrap(True)  # Allow text wrapping
        self.next_run_info.setVisible(False)
        status_container_layout.addWidget(self.next_run_info)
        
        # Add container to status layout
        status_layout.addWidget(self.status_container)
        
        # Add remove button centered
        remove_layout = QHBoxLayout()
        remove_layout.addStretch()
        
        self.remove_button = QPushButton("Remove Schedule")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 150px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.clicked.connect(self.remove_job)
        self.remove_button.setEnabled(False)  # Disabled by default
        
        remove_layout.addWidget(self.remove_button)
        remove_layout.addStretch()
        
        # Add to status layout with extra spacing
        status_layout.addLayout(remove_layout)
        status_layout.addSpacing(10)  # Extra space at bottom
        
        # Add status group to main layout
        main_layout.addWidget(self.status_group)
        
        # Connect schedule type change to update UI
        self.schedule_type.currentIndexChanged.connect(self.update_schedule_ui)
        self.update_schedule_ui()
        
        # Disable the schedule button if no system scheduler is available
        if not system_scheduler_available:
            self.schedule_button.setEnabled(False)
            self.schedule_button.setToolTip("System scheduler (crontab or Task Scheduler) is not available")
    
    def update_schedule_ui(self):
        """Update UI based on selected schedule type"""
        schedule_type = self.schedule_type.currentData()
        
        if schedule_type == "interval":
            self.interval_days.setEnabled(True)
            self.days_group.setEnabled(False)
        else:  # weekly
            self.interval_days.setEnabled(False)
            self.days_group.setEnabled(True)
    
    def get_selected_days(self):
        """Get selected days of week as string"""
        selected_days = []
        for day, checkbox in self.day_checkboxes.items():
            if checkbox.isChecked():
                selected_days.append(day)
        
        return ",".join(selected_days) if selected_days else None
    
    def schedule_job(self):
        """Schedule a new scraping job"""
        try:
            # Check if system scheduler is available
            if not self.scheduler.system_scheduler_available:
                QMessageBox.warning(self, "System Scheduler Not Available", 
                                   "No system scheduler (crontab or Task Scheduler) is available. "
                                   "Please ensure the appropriate scheduler is installed and accessible.")
                return
            
            # Get schedule type
            schedule_type = self.schedule_type.currentData()
            
            # Get schedule parameters
            if schedule_type == "interval":
                interval_days = self.interval_days.value()
                days_of_week = None
            else:  # weekly
                interval_days = 7  # Not used for weekly schedule
                days_of_week = self.get_selected_days()
                
                if not days_of_week:
                    QMessageBox.warning(self, "Invalid Schedule", 
                                       "Please select at least one day of the week.")
                    return
                
            # Get time to run
            time = self.run_time.time()
            hour = time.hour()
            minute = time.minute()
            
            # Schedule job
            job_id = "redhat_events_scraper"
            success = self.scheduler.schedule_job(
                job_id=job_id,
                interval_days=interval_days,
                days_of_week=days_of_week,
                hour=hour,
                minute=minute
            )
            
            if success:
                # Use the system-appropriate scheduling method
                system_name = platform.system()
                
                if system_name == 'Darwin' or system_name == 'Linux':
                    scheduler_type = "system crontab"
                elif system_name == 'Windows':
                    scheduler_type = "Windows Task Scheduler"
                else:
                    scheduler_type = "system scheduler"
                
                # Prepare success message
                message = (
                    f"The scraping job has been scheduled using {scheduler_type}.\n\n"
                    "The scraper will run at the scheduled time even when the application is closed. "
                    "Results will be saved to the output directory."
                )
                
                QMessageBox.information(self, "Job Scheduled", message)
                self.load_jobs()
            else:
                QMessageBox.warning(self, "Scheduling Error", 
                                   "Failed to schedule the scraping job. Please check the logs.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def load_jobs(self):
        """Load and display current scheduled job"""
        try:
            # Get all jobs
            jobs = self.scheduler.get_all_jobs()
            
            # Check if redhat_events_scraper job exists
            job_id = "redhat_events_scraper"
            if job_id in jobs:
                job_info = jobs[job_id]
                
                # Update status header
                self.status_header.setText("RedHat Events Scraper is scheduled")
                self.status_header.setStyleSheet("""
                    padding: 10px;
                    background-color: #E3F2FD;
                    border: 1px solid #90CAF9;
                    border-radius: 4px;
                    color: #1E88E5;
                    font-weight: bold;
                """)
                
                # Update and show schedule details
                schedule_text = job_info.get('trigger_description', 'Unknown schedule')
                self.schedule_details.setText(f"Schedule: {schedule_text}")
                self.schedule_details.setVisible(True)
                
                # Update and show next run
                next_run = job_info.get('next_run', 'Unknown')
                self.next_run_info.setText(f"Next run: {next_run}")
                self.next_run_info.setVisible(True)
                
                # Enable remove button
                self.remove_button.setEnabled(True)
            else:
                # No job scheduled
                self.status_header.setText("No job currently scheduled")
                self.status_header.setStyleSheet("""
                    padding: 10px;
                    background-color: #F5F5F5;
                    border: 1px solid #DDDDDD;
                    border-radius: 4px;
                    color: #555555;
                    font-weight: bold;
                """)
                
                # Hide details
                self.schedule_details.setVisible(False)
                self.next_run_info.setVisible(False)
                
                # Disable remove button
                self.remove_button.setEnabled(False)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load scheduled jobs: {str(e)}")
    
    def remove_job(self):
        """Remove the scheduled job"""
        try:
            reply = QMessageBox.question(
                self, "Confirm Removal",
                "Are you sure you want to remove the scheduled job?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                job_id = "redhat_events_scraper"
                success = self.scheduler.remove_job(job_id)
                
                if success:
                    QMessageBox.information(self, "Job Removed", 
                                           "The scheduled job has been removed successfully.")
                    self.load_jobs()
                else:
                    QMessageBox.warning(self, "Removal Error", 
                                       "Failed to remove the job. Please check the logs.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        event.accept()

# For testing
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = SchedulerDialog()
    dialog.show()
    sys.exit(app.exec_())