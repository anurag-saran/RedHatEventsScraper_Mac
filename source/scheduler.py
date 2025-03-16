# scheduler.py - System schedulers only (Windows Task Scheduler and macOS/Linux crontab)
import os
import sys
import logging
import json
import subprocess
import platform
from datetime import datetime

from config import OUTPUT_DIR
from utils import ensure_directory

logger = logging.getLogger(__name__)

def crontab_command_exists():
    """Check if crontab command exists on the system"""
    try:
        result = subprocess.run(['which', 'crontab'], capture_output=True, check=False)
        return result.returncode == 0
    except Exception:
        return False

def get_current_crontab():
    """Get current user's crontab"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False)
        if result.returncode != 0 and "no crontab" not in result.stderr:
            logger.error(f"Error getting crontab: {result.stderr}")
            return ""
        return result.stdout
    except Exception as e:
        logger.error(f"Exception getting crontab: {e}")
        return ""

def set_crontab(content):
    """Set user's crontab with new content"""
    try:
        proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        proc.communicate(input=content)
        if proc.returncode != 0:
            logger.error(f"Error setting crontab, return code: {proc.returncode}")
            return False
        return True
    except Exception as e:
        logger.error(f"Exception setting crontab: {e}")
        return False

def crontab_entry_exists(job_id):
    """Check if a crontab entry with the given job_id exists"""
    current = get_current_crontab()
    return f"#{job_id}" in current

def add_crontab_job(job_id, schedule, command):
    """
    Add a job to user's crontab
    
    Args:
        job_id (str): Unique identifier for the job
        schedule (str): Crontab schedule (e.g., "0 9 * * 1" for Mondays at 9 AM)
        command (str): Command to run
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not crontab_command_exists():
        logger.error("Crontab command not found on this system")
        return False
    
    # Get current crontab
    current = get_current_crontab()
    
    # Check if job already exists
    if crontab_entry_exists(job_id):
        # Remove existing job
        remove_crontab_job(job_id)
        # Get updated crontab
        current = get_current_crontab()
    
    # Prepare job entry
    job_entry = f"{schedule} {command} #{job_id}\n"
    
    # Add to crontab
    new_crontab = current + job_entry
    return set_crontab(new_crontab)

def remove_crontab_job(job_id):
    """Remove a job from user's crontab"""
    if not crontab_command_exists():
        logger.error("Crontab command not found on this system")
        return False
    
    # Get current crontab
    current = get_current_crontab()
    
    # Remove lines containing job_id
    new_lines = []
    for line in current.splitlines():
        if f"#{job_id}" not in line:
            new_lines.append(line)
    
    new_crontab = "\n".join(new_lines)
    if new_crontab and not new_crontab.endswith("\n"):
        new_crontab += "\n"
    
    return set_crontab(new_crontab)

def get_crontab_expression(days_of_week=None, hour=9, minute=0):
    """
    Generate a crontab expression
    
    Args:
        days_of_week (str): Days of week (e.g., "mon,wed,fri")
        hour (int): Hour (0-23)
        minute (int): Minute (0-59)
        
    Returns:
        str: Crontab expression
    """
    if days_of_week:
        # Convert "mon,wed,fri" to "1,3,5"
        day_map = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}
        days = []
        for day in days_of_week.split(","):
            if day.lower() in day_map:
                days.append(str(day_map[day.lower()]))
        
        day_str = ",".join(days)
        return f"{minute} {hour} * * {day_str}"
    else:
        # Run daily at specified time
        return f"{minute} {hour} * * *"

def create_crontab_command():
    """Create the command that crontab will execute"""
    # Get the path to the Python interpreter
    python_path = sys.executable
    
    # Get the path to the cron_runner.py script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'cron_runner.py')
    
    # Return the full command
    return f"{python_path} {script_path}"

# Windows Task Scheduler Functions
def task_scheduler_available():
    """Check if Windows Task Scheduler is available"""
    if platform.system() != 'Windows':
        return False
    
    try:
        # Check if schtasks command is available
        result = subprocess.run(['where', 'schtasks'], capture_output=True, check=False)
        return result.returncode == 0
    except Exception:
        return False

def create_windows_task(task_name, command, schedule_type, interval=None, days=None, hour=None, minute=None):
    """
    Create a scheduled task in Windows Task Scheduler
    
    Args:
        task_name (str): Name of the task
        command (str): Command to run
        schedule_type (str): 'DAILY', 'WEEKLY', or 'ONCE'
        interval (int): For DAILY, run every X days
        days (str): For WEEKLY, days of the week (e.g., "MON,WED,FRI")
        hour (int): Hour to run (0-23)
        minute (int): Minute to run (0-59)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Prepare the Windows batch file that will run the command
        batch_file = create_batch_file(command)
        
        # Format time as HH:MM
        start_time = f"{hour:02d}:{minute:02d}"
        
        # Prepare base command
        cmd = ['schtasks', '/Create', '/F', '/TN', task_name, '/TR', batch_file, '/SC', schedule_type, '/ST', start_time]
        
        # Add schedule-specific parameters
        if schedule_type == 'DAILY' and interval:
            cmd.extend(['/MO', str(interval)])
        elif schedule_type == 'WEEKLY' and days:
            cmd.extend(['/D', days])
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Error creating Windows scheduled task: {result.stderr}")
            return False
        
        logger.info(f"Windows scheduled task '{task_name}' created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Exception creating Windows scheduled task: {e}")
        return False

def create_batch_file(command):
    """
    Create a batch file to run the Python script
    
    Args:
        command (str): Python command to run
        
    Returns:
        str: Path to the batch file
    """
    # Get the script directory for the batch file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    batch_dir = os.path.join(script_dir, 'batch')
    ensure_directory(batch_dir)
    
    # Create the batch file path
    batch_file = os.path.join(batch_dir, 'run_redhat_scraper.bat')
    
    # Write the batch file
    with open(batch_file, 'w') as f:
        f.write('@echo off\n')
        f.write(f'cd /d "{script_dir}"\n')
        f.write(f'{command}\n')
        f.write('if %ERRORLEVEL% NEQ 0 (\n')
        f.write(f'  echo Error running RedHat scraper >> "{os.path.join(batch_dir, "error.log")}"\n')
        f.write(')\n')
    
    return batch_file

def remove_windows_task(task_name):
    """
    Remove a scheduled task from Windows Task Scheduler
    
    Args:
        task_name (str): Name of the task
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = subprocess.run(['schtasks', '/Delete', '/F', '/TN', task_name], 
                               capture_output=True, text=True, check=False)
        
        if result.returncode != 0 and 'cannot find the file specified' not in result.stderr.lower():
            logger.error(f"Error removing Windows scheduled task: {result.stderr}")
            return False
        
        logger.info(f"Windows scheduled task '{task_name}' removed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Exception removing Windows scheduled task: {e}")
        return False

def create_windows_command():
    """Create the command that Windows Task Scheduler will execute"""
    # Get the path to the Python interpreter
    python_path = sys.executable
    
    # Get the path to the cron_runner.py script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'cron_runner.py')
    
    # Return the full command wrapped in quotes to handle spaces in paths
    return f'"{python_path}" "{script_path}"'

class SchedulerManager:
    """Manages scheduled scraping jobs using system schedulers"""
    
    def __init__(self, output_dir=OUTPUT_DIR):
        """Initialize the scheduler manager"""
        self.output_dir = output_dir
        ensure_directory(output_dir)
        
        # Configuration file to store scheduler settings
        self.config_file = os.path.join(output_dir, 'scheduler_config.json')
        
        # Determine if system schedulers are available
        self.has_crontab = platform.system() in ('Darwin', 'Linux') and crontab_command_exists()
        self.has_task_scheduler = platform.system() == 'Windows' and task_scheduler_available()
        
        self.system_scheduler_available = self.has_crontab or self.has_task_scheduler
        
        if not self.system_scheduler_available:
            logger.warning("No system scheduler available (crontab or Task Scheduler)")
            
            if platform.system() == 'Darwin' or platform.system() == 'Linux':
                logger.warning("Please make sure crontab is installed and accessible")
            elif platform.system() == 'Windows':
                logger.warning("Please ensure Task Scheduler is accessible with current permissions")
        else:
            logger.info(f"Using system scheduler: {'crontab' if self.has_crontab else 'Windows Task Scheduler'}")
    
    def schedule_crontab_job(self, job_id, interval_days=None, days_of_week=None, hour=9, minute=0):
        """
        Schedule a job using crontab for persistent scheduling
        
        Args:
            job_id (str): Unique identifier for the job
            interval_days (int): Interval in days (for logging only)
            days_of_week (str): Days of week (e.g., "mon,wed,fri")
            hour (int): Hour (0-23)
            minute (int): Minute (0-59)
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Generate crontab expression
        cron_expression = get_crontab_expression(days_of_week, hour, minute)
        
        # Create command to run
        command = create_crontab_command()
        
        # Add job to crontab
        success = add_crontab_job(job_id, cron_expression, command)
        
        if success:
            # Update job info in config
            config = self._load_config()
            
            # Format description based on schedule type
            if days_of_week:
                trigger_desc = f"Weekly on {days_of_week} at {hour:02d}:{minute:02d}"
            else:
                trigger_desc = f"Every day at {hour:02d}:{minute:02d}"
            
            config[job_id] = {
                'interval_days': interval_days,
                'days_of_week': days_of_week,
                'hour': hour,
                'minute': minute,
                'trigger_description': trigger_desc,
                'next_run': "Using system crontab",
                'status': 'Active (crontab)',
                'is_crontab': True
            }
            self._save_config(config)
            
            logger.info(f"Job '{job_id}' scheduled using crontab: {cron_expression}")
        
        return success
    
    def schedule_windows_task(self, job_id, interval_days=None, days_of_week=None, hour=9, minute=0):
        """
        Schedule a job using Windows Task Scheduler
        
        Args:
            job_id (str): Unique identifier for the job
            interval_days (int): Interval in days
            days_of_week (str): Days of week (e.g., "mon,wed,fri")
            hour (int): Hour (0-23)
            minute (int): Minute (0-59)
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Task name must be unique
        task_name = f"RedHat_Events_Scraper_{job_id}"
        
        # Create command
        command = create_windows_command()
        
        # Determine schedule type and parameters
        if days_of_week:
            schedule_type = 'WEEKLY'
            # Convert from lowercase to uppercase and remap from mon->MON to MON->MON
            win_days = days_of_week.upper()
        else:
            schedule_type = 'DAILY'
            win_days = None
            
        # Create the task
        success = create_windows_task(
            task_name=task_name,
            command=command,
            schedule_type=schedule_type,
            interval=interval_days if schedule_type == 'DAILY' else None,
            days=win_days if schedule_type == 'WEEKLY' else None,
            hour=hour,
            minute=minute
        )
        
        if success:
            # Update job info in config
            config = self._load_config()
            
            # Format description based on schedule type
            if days_of_week:
                trigger_desc = f"Weekly on {days_of_week} at {hour:02d}:{minute:02d}"
            else:
                trigger_desc = f"Every {interval_days} day(s) at {hour:02d}:{minute:02d}"
            
            config[job_id] = {
                'interval_days': interval_days,
                'days_of_week': days_of_week,
                'hour': hour,
                'minute': minute,
                'trigger_description': trigger_desc,
                'next_run': "Using Windows Task Scheduler",
                'status': 'Active (Task Scheduler)',
                'is_task_scheduler': True,
                'task_name': task_name
            }
            self._save_config(config)
            
            logger.info(f"Job '{job_id}' scheduled using Windows Task Scheduler: {trigger_desc}")
        
        return success
    
    def schedule_job(self, job_id, interval_days=7, days_of_week=None, hour=9, minute=0):
        """
        Schedule a scraping job using the system scheduler
        
        Args:
            job_id (str): Unique identifier for the job
            interval_days (int): Interval in days between runs
            days_of_week (str): Cron-style days of week (e.g., 'mon,wed,fri')
            hour (int): Hour to run (0-23)
            minute (int): Minute to run (0-59)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove existing job with the same ID
            self.remove_job(job_id)
            
            # If crontab is available on macOS/Linux, use it for scheduling
            if self.has_crontab:
                return self.schedule_crontab_job(job_id, interval_days, days_of_week, hour, minute)
            # If Windows Task Scheduler is available, use it for scheduling
            elif self.has_task_scheduler:
                return self.schedule_windows_task(job_id, interval_days, days_of_week, hour, minute)
            else:
                # No system scheduler available
                error_msg = "No system scheduler available. Please install or enable crontab (macOS/Linux) or ensure Task Scheduler is accessible (Windows)."
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            return False
    
    def remove_job(self, job_id):
        """Remove a scheduled job"""
        try:
            # Load config to check job type
            config = self._load_config()
            job_config = config.get(job_id, {})
            
            # If crontab job, remove from crontab
            if job_config.get('is_crontab', False) and self.has_crontab:
                success = remove_crontab_job(job_id)
                
                if success:
                    # Remove from config
                    if job_id in config:
                        del config[job_id]
                        self._save_config(config)
                        logger.info(f"Job '{job_id}' removed from crontab and configuration")
                    
                    return True
            
            # If Windows Task Scheduler job, remove from Task Scheduler
            elif job_config.get('is_task_scheduler', False) and self.has_task_scheduler:
                task_name = job_config.get('task_name', f"RedHat_Events_Scraper_{job_id}")
                success = remove_windows_task(task_name)
                
                if success:
                    # Remove from config
                    if job_id in config:
                        del config[job_id]
                        self._save_config(config)
                        logger.info(f"Job '{job_id}' removed from Windows Task Scheduler and configuration")
                    
                    return True
            
            # Remove from config anyway (in case of orphaned config)
            if job_id in config:
                del config[job_id]
                self._save_config(config)
                logger.info(f"Job '{job_id}' removed from configuration")
            
            return True
        except Exception as e:
            logger.error(f"Error removing job '{job_id}': {e}")
            return False
    
    def get_all_jobs(self):
        """Get information about all scheduled jobs"""
        try:
            # Get saved configuration
            config = self._load_config()
            
            # Process all jobs from config
            results = {}
            for job_id, job_info in config.items():
                results[job_id] = job_info.copy()
                
                # Add status based on job type
                if job_info.get('is_crontab'):
                    # For crontab jobs, check if crontab entry exists
                    if self.has_crontab and crontab_entry_exists(job_id):
                        results[job_id]['status'] = 'Active (crontab)'
                    else:
                        results[job_id]['status'] = 'Inactive (crontab entry not found)'
                elif job_info.get('is_task_scheduler'):
                    # For Task Scheduler jobs, we can't easily check if task exists
                    # So we just show it as active based on the config
                    results[job_id]['status'] = 'Active (Task Scheduler)'
                else:
                    results[job_id]['status'] = 'Unknown'
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return {}
    
    def _save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}