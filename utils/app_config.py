# -----------------------------------------------------------------------------
# Project Meridian
# Copyright (c) 2025 Jereme Shaver
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# File: app_confg.py
# Description: Class to handle application configuration, including system detection
# and data directory management.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------


import os
import platform
import logging
from pathlib import Path

class AppConfig:
    """
    Singleton class to handle application configuration, including system detection
    and data directory management.
    """
    _instance = None
    
    path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), "MeridianTasks")
    # print(f"Expected directory: {path}")
    # print(f"Exists: {os.path.exists(path)}")
    # print(f"Real Path: {os.path.realpath(path)}")
    # print(f"Dir Contents: {os.listdir(path) if os.path.exists(path) else 'Not Found'}")

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize configuration properties"""
        # Set up logger
        self.logger = logging.getLogger("AppConfig")
        
        # Detect the system platform
        self.system = platform.system()
        self.app_name = "MeridianTasks"  # You can change this to your chosen name
        
        # Determine the appropriate data directory
        self.app_data_dir = self._get_app_data_dir()
        self.data_dir = os.path.join(self.app_data_dir, "data")
        self.logs_dir = os.path.join(self.app_data_dir, "logs")
        self.temp_dir = os.path.join(self.app_data_dir, "temp")
        
        # Create necessary directories
        self._ensure_directories_exist()
        
        # Store paths for common data files
        self.tasks_file = os.path.join(self.data_dir, "saved_tasks.json")
        print(f"Tasks directory: {self.tasks_file}")
        self.projects_file = os.path.join(self.data_dir, "projects.json")
        self.notes_file = os.path.join(self.data_dir, "notes.json")
        self.settings_file = os.path.join(self.app_data_dir, "settings.json")
        
        # self.logger.info(f"AppConfig initialized for {self.system} system")
        # self.logger.info(f"App data directory: {self.app_data_dir}")
    
    def _get_app_data_dir(self):
        """
        Get the platform-specific application data directory
        
        Returns:
            str: Path to the application data directory
        """
        if self.system == "Windows":
            # Windows: AppData\Local\{app_name}
            print(f"Path name: {os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), self.app_name)}")
            return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), self.app_name)
        elif self.system == "Darwin":
            # macOS: ~/Library/Application Support/{app_name}
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", self.app_name)
        else:
            # Linux/Unix: ~/.local/share/{app_name}
            return os.path.join(os.path.expanduser("~"), ".local", "share", self.app_name)
    
    def _ensure_directories_exist(self):
        """Create all required application directories if they don't exist"""
        for directory in [self.app_data_dir, self.data_dir, self.logs_dir, self.temp_dir]:
            try:
                os.makedirs(directory, exist_ok=True)
                # Test if the directory is writable
                test_file = os.path.join(directory, '.write_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                # self.logger.info(f"Successfully created and verified directory: {directory}")
            except Exception as e:
                self.logger.error(f"Error creating directory {directory}: {e}")
                # Try to create in an alternative location if primary fails
                if directory == self.app_data_dir:
                    fallback_dir = os.path.join(os.path.expanduser("~"), "MeridianTasks")
                    self.logger.warning(f"Trying fallback directory: {fallback_dir}")
                    try:
                        os.makedirs(fallback_dir, exist_ok=True)
                        self.app_data_dir = fallback_dir
                        self.data_dir = os.path.join(self.app_data_dir, "data") 
                        self.logs_dir = os.path.join(self.app_data_dir, "logs")
                        self.temp_dir = os.path.join(self.app_data_dir, "temp")
                        # Restart the directory creation with new paths
                        return self._ensure_directories_exist()
                    except Exception as e2:
                        self.logger.error(f"Error creating fallback directory: {e2}")
    
    def get_file_path(self, filename, directory_type="data"):
        """
        Get the full path for a file in one of the app's directories
        
        Args:
            filename: Name of the file
            directory_type: Type of directory ('data', 'logs', 'temp')
            
        Returns:
            str: Full path to the file
        """
        if directory_type == "data":
            directory = self.data_dir
        elif directory_type == "logs":
            directory = self.logs_dir
        elif directory_type == "temp":
            directory = self.temp_dir
        else:
            directory = self.app_data_dir
            
        return os.path.join(directory, filename)
    
    def get_system_info(self):
        """
        Get basic system information
        
        Returns:
            dict: System information
        """
        return {
            "system": self.system,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "app_data_dir": self.app_data_dir
        }