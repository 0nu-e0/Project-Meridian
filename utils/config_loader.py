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
# File: config_loader.py
# Description: Used to modify the app_config.yaml file.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import yaml
import os
from pathlib import Path
from collections import defaultdict

class ConfigSection:
    """Helper class to allow dot notation access to nested dictionaries"""
    def __init__(self, data=None):
        if data is None:
            data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert back to dictionary for saving"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ConfigSection):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result
    
    def update(self, data):
        """Update with new dictionary data"""
        for key, value in data.items():
            if isinstance(value, dict) and hasattr(self, key) and isinstance(getattr(self, key), ConfigSection):
                getattr(self, key).update(value)
            else:
                if isinstance(value, dict):
                    setattr(self, key, ConfigSection(value))
                else:
                    setattr(self, key, value)

class AppConfig:
    """
    Configuration manager for application settings.
    Loads settings from YAML file and provides access to configuration values.
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one config instance exists"""
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._loaded = False
        return cls._instance
    
    def __init__(self):
        """Initialize config only once"""
        if not self._loaded:
            # Root sections
            self.app = ConfigSection()
            self.ui = ConfigSection()
            self.data = ConfigSection()
            self.network = ConfigSection()
            self.user_preferences = ConfigSection()
            
            # Define paths
            self._config_path = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'Project_Manager', 'data', 'app_config.yaml'))
            self._user_config_path = Path(os.path.expanduser("~/.myapp/user_config.yaml"))
            
            # print(f"Looking for config at: {self._config_path}")
            # if os.path.exists(self._config_path):
            #     print(f"File exists!")
            # else:
            #     pass
                # print(f"File does not exist")
                
            self.load_config()
            self._loaded = True
    
    def load_config(self):
        """Load the default and user configurations"""
        # Load default config first
        if self._config_path.exists():
            self._load_file(self._config_path)
        
        # Override with user config if it exists
        if self._user_config_path.exists():
            self._load_file(self._user_config_path)
    
    def _load_file(self, file_path):
        """Load a configuration file and update settings"""
        try:
            with open(file_path, 'r') as file:
                config_data = yaml.safe_load(file)
                if config_data:
                    self._update_from_dict(config_data)
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")
    
    def _update_from_dict(self, config_dict):
        """Update configuration from dictionary"""
        for section in ['app', 'ui', 'data', 'network', 'user_preferences']:
            if section in config_dict:
                getattr(self, section).update(config_dict[section])
    
    def save_user_config(self):
        """Save current configuration to user config file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self._user_config_path), exist_ok=True)
        
        # Create config dictionary
        config_dict = {
            'app': self.app.to_dict(),
            'ui': self.ui.to_dict(),
            'data': self.data.to_dict(),
            'network': self.network.to_dict(),
            'user_preferences': self.user_preferences.to_dict()
        }
        
        # Write to file
        with open(self._user_config_path, 'w') as file:
            yaml.dump(config_dict, file, default_flow_style=False)
    
    def get_section(self, path):
        """Get a specific section using dot notation path"""
        parts = path.split('.')
        
        # Navigate to the correct section
        section = self
        for part in parts:
            if hasattr(section, part):
                section = getattr(section, part)
            else:
                return None
                
        return section
    
    def set_section(self, path, value):
        """Set a specific section using dot notation path"""
        parts = path.split('.')
        
        # Navigate to the parent section
        section = self
        for part in parts[:-1]:
            if hasattr(section, part):
                section = getattr(section, part)
            else:
                # Create missing sections
                setattr(section, part, ConfigSection())
                section = getattr(section, part)
        
        # Set the value
        last_part = parts[-1]
        if isinstance(value, dict):
            setattr(section, last_part, ConfigSection(value))
        else:
            setattr(section, last_part, value)

# Singleton instance
config = AppConfig()