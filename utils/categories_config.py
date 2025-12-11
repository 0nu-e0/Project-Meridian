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
# File: categories_config.py
# Description: Manager for dynamic task categories configuration
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import json
from pathlib import Path
from typing import List, Dict


class CategoriesConfigManager:
    """Manages dynamic task categories stored in JSON configuration file"""

    @staticmethod
    def get_categories_file_path() -> Path:
        """Get the path to the categories configuration file"""
        # Always use direct path calculation to avoid AppConfig recursion
        import os
        import platform

        system = platform.system()
        app_name = "MeridianTasks"

        if system == "Windows":
            app_data_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser(r'~\AppData\Local'))
            return Path(app_data_dir) / app_name / "categories_config.json"
        elif system == "Darwin":
            app_data_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", app_name)
            return Path(app_data_dir) / "categories_config.json"
        else:
            app_data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", app_name)
            return Path(app_data_dir) / "categories_config.json"

    @staticmethod
    def get_default_categories() -> List[str]:
        """Return the default list of task categories"""
        return [
            "Feature",
            "Bug",
            "Maintenance",
            "Documentation",
            "Research",
            "Meeting",
            "ECO",
            "ERP Change",
            "Boride Shaping",
            "Drawing Update",
            "CAPA",
            "Build Fixture",
            "Work Instruction",
            "Lab Testing",
            "Projects",
            "Archived"
        ]

    @staticmethod
    def initialize_categories_config():
        """Initialize the categories config file with default categories if it doesn't exist"""
        config_file = CategoriesConfigManager.get_categories_file_path()

        if not config_file.exists():
            default_categories = CategoriesConfigManager.get_default_categories()
            config_data = {
                "categories": default_categories,
                "version": "1.0"
            }

            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4)

    @staticmethod
    def load_categories() -> List[str]:
        """Load categories from the configuration file"""
        # Initialize if needed
        CategoriesConfigManager.initialize_categories_config()

        config_file = CategoriesConfigManager.get_categories_file_path()

        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                return config_data.get("categories", CategoriesConfigManager.get_default_categories())
        except Exception as e:
            print(f"Error loading categories: {e}")
            return CategoriesConfigManager.get_default_categories()

    @staticmethod
    def save_categories(categories: List[str]):
        """Save categories to the configuration file"""
        config_file = CategoriesConfigManager.get_categories_file_path()

        config_data = {
            "categories": categories,
            "version": "1.0"
        }

        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving categories: {e}")
            return False

    @staticmethod
    def add_category(category_name: str) -> bool:
        """Add a new category to the configuration"""
        categories = CategoriesConfigManager.load_categories()

        # Check if category already exists (case-insensitive)
        if category_name.strip() in categories:
            return False

        # Add new category
        categories.append(category_name.strip())

        # Save updated list
        return CategoriesConfigManager.save_categories(categories)

    @staticmethod
    def remove_category(category_name: str) -> bool:
        """Remove a category from the configuration"""
        categories = CategoriesConfigManager.load_categories()

        # Don't allow removing "Archived" category
        if category_name == "Archived":
            return False

        if category_name in categories:
            categories.remove(category_name)
            return CategoriesConfigManager.save_categories(categories)

        return False

    @staticmethod
    def rename_category(old_name: str, new_name: str) -> bool:
        """Rename an existing category"""
        categories = CategoriesConfigManager.load_categories()

        if old_name in categories and new_name.strip() not in categories:
            index = categories.index(old_name)
            categories[index] = new_name.strip()
            return CategoriesConfigManager.save_categories(categories)

        return False

    @staticmethod
    def get_category_count() -> int:
        """Get the total number of categories"""
        return len(CategoriesConfigManager.load_categories())

    @staticmethod
    def category_exists(category_name: str) -> bool:
        """Check if a category exists"""
        categories = CategoriesConfigManager.load_categories()
        return category_name in categories
