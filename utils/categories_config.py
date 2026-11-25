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

import logging
from pathlib import Path
from typing import List

from utils.safe_io import read_json, write_json


class CategoriesConfigManager:
    """Manages dynamic task categories stored in JSON configuration file"""

    @staticmethod
    def get_categories_file_path() -> Path:
        """Get the path to the categories configuration file (in the app data folder)"""
        from utils.app_config import AppConfig
        return Path(AppConfig().app_data_dir) / "categories_config.json"

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

            write_json(str(config_file), config_data, indent=4)

    @staticmethod
    def load_categories() -> List[str]:
        """Load categories from the configuration file"""
        # Initialize if needed
        CategoriesConfigManager.initialize_categories_config()

        config_file = CategoriesConfigManager.get_categories_file_path()

        config_data = read_json(str(config_file))
        categories = config_data.get("categories")
        if not isinstance(categories, list):
            return CategoriesConfigManager.get_default_categories()
        return categories

    @staticmethod
    def save_categories(categories: List[str]):
        """Save categories to the configuration file"""
        config_file = CategoriesConfigManager.get_categories_file_path()

        config_data = {
            "categories": categories,
            "version": "1.0"
        }

        return write_json(str(config_file), config_data, indent=4)

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


def category_usage():
    """{category name: number of tasks using it}"""
    from utils.tasks_io import load_tasks_from_json
    counts = {}
    for task in load_tasks_from_json(logging.getLogger(__name__)).values():
        counts[task.category_name] = counts.get(task.category_name, 0) + 1
    return counts


def rename_category_everywhere(old_name: str, new_name: str, logger) -> bool:
    """Rename a category in the list, on every task using it, and in Dashboard groups"""
    from models.task import category_from_name
    from utils.dashboard_config import DashboardConfigManager
    from utils.tasks_io import load_tasks_from_json, save_tasks_to_json

    if not CategoriesConfigManager.rename_category(old_name, new_name):
        return False

    tasks = [task for task in load_tasks_from_json(logger).values() if task.category_name == old_name]
    for task in tasks:
        task.category = category_from_name(new_name)
    if tasks and not save_tasks_to_json(tasks, logger):
        return False

    grids = DashboardConfigManager.get_all_grid_layouts()
    changed = False
    for grid in grids:
        categories = list(getattr(grid.filter, 'category', []) or [])
        if old_name in categories:
            grid.filter.category = [new_name if c == old_name else c for c in categories]
            changed = True
        if grid.name == old_name:
            grid.name = new_name
            changed = True
    if changed:
        DashboardConfigManager.save_grid_layouts(grids)
    return True
