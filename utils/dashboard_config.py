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
# File: dashboard_config.py
# Description: Used as a helper file to modify the app_config.yaml file 
#              specifically for the dashboard screen.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from utils.config_loader import config 
import os
import yaml
from pathlib import Path

class DashboardConfigManager:
    """
    Handles loading, saving, and managing dashboard grid layout configurations.
    """
    
    @staticmethod
    def get_all_grid_layouts():
        """
        Get all configured grid layouts from the YAML configuration file.
        
        Returns:
            list: List of grid layout configurations
        """
        from utils.app_config import AppConfig
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the config file path from AppConfig
        app_config = AppConfig()
        config_path = os.path.join(app_config.app_data_dir, "config", "app_config.yaml")

        print(f"yaml config file: {config_path}")
        
        # Check if the file exists
        if not os.path.exists(config_path):
            logger.warning(f"Config file does not exist at: {config_path}")
            return []
        
        # Load the YAML file directly
        try:
            with open(config_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
            
            # Check if dashboard section exists
            if 'dashboard' not in yaml_data:
                logger.warning("No dashboard section found in YAML file")
                return []
            
            # Check if grid_layouts section exists
            if 'grid_layouts' not in yaml_data['dashboard']:
                logger.warning("No grid_layouts section found in dashboard configuration")
                return []
            
            # Get the grid layouts from the YAML
            yaml_grid_layouts = yaml_data['dashboard']['grid_layouts']
            
            # Convert YAML grid layouts to objects
            grid_layouts = []
            for grid_data in yaml_grid_layouts:
                # Create grid object
                grid = type('', (), {})()
                
                # Set basic properties
                grid.id = grid_data.get('id', f"grid_{len(grid_layouts)}")
                grid.name = grid_data.get('name', "Unnamed Grid")
                grid.position = grid_data.get('position', len(grid_layouts))
                grid.columns = grid_data.get('columns', 3)
                grid.minimize = grid_data.get('minimize', 'false')
                
                # Create filter object
                grid.filter = type('', (), {})()
                
                # Set filter properties
                filter_data = grid_data.get('filter', {})
                
                # Extract filter values directly from YAML
                # Make sure to preserve these exact keys for your GridLayout
                grid.filter.status = filter_data.get('status', [])
                grid.filter.category = filter_data.get('category', [])
                grid.filter.due = filter_data.get('due', [])
                
                grid_layouts.append(grid)
            
            # logger.info(f"Successfully loaded {len(grid_layouts)} grid layouts from configuration")
            return grid_layouts
            
        except Exception as e:
            # logger.error(f"Error loading dashboard configuration: {e}")
            import traceback
            # logger.error(traceback.format_exc())
            return []
    
    @staticmethod
    def save_grid_layouts(grid_layouts):
        """
        Save grid layouts to the configuration file in the AppConfig directory.
        
        Args:
            grid_layouts (list): List of grid layout objects to save
        """
        from utils.app_config import AppConfig
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the config file path from AppConfig
        app_config = AppConfig()
        config_dir = os.path.join(app_config.app_data_dir, "config")
        config_path = os.path.join(config_dir, "app_config.yaml")
        
        # Ensure the config directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        # Load existing YAML file
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    yaml_data = yaml.safe_load(file) or {}
            else:
                yaml_data = {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            yaml_data = {}
        
        # Ensure dashboard section exists
        if 'dashboard' not in yaml_data:
            yaml_data['dashboard'] = {}
        
        # Convert grid layouts to YAML format
        yaml_grid_layouts = []
        for grid in grid_layouts:
            grid_data = {
                'id': grid.id,
                'name': grid.name,
                'position': grid.position,
                'columns': grid.columns,
                'filter': {},
                "minimize": grid.minimize
            }
            
            # Add filters
            if hasattr(grid, 'filter'):
                if hasattr(grid.filter, 'status'):
                    grid_data['filter']['status'] = grid.filter.status
                if hasattr(grid.filter, 'category'):
                    grid_data['filter']['category'] = grid.filter.category
                if hasattr(grid.filter, 'due'):
                    grid_data['filter']['due'] = grid.filter.due
                # Include legacy fields if present
                if hasattr(grid.filter, 'type'):
                    grid_data['filter']['type'] = grid.filter.type
                if hasattr(grid.filter, 'priority'):
                    grid_data['filter']['priority'] = grid.filter.priority
                if hasattr(grid.filter, 'tags'):
                    grid_data['filter']['tags'] = grid.filter.tags
            
            yaml_grid_layouts.append(grid_data)
        
        # Update the YAML data
        yaml_data['dashboard']['grid_layouts'] = yaml_grid_layouts
        
        # Preserve other sections if they exist in the original file
        # This prevents losing other configurations when saving grid layouts
        
        # Save the YAML file
        try:
            with open(config_path, 'w') as file:
                yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Successfully saved {len(yaml_grid_layouts)} grid layouts to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving dashboard configuration: {e}")
            return False

    # Also need a corresponding load method to read from the new location
    @staticmethod
    def load_grid_layouts():
        """
        Load grid layouts from the configuration file in the AppConfig directory.
        
        Returns:
            list: List of grid layout objects
        """
        from utils.app_config import AppConfig
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the config file path from AppConfig
        app_config = AppConfig()
        config_path = os.path.join(app_config.app_data_dir, "config", "app_config.yaml")
        
        # Check if file exists
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found at {config_path}")
            return []
        
        # Load YAML file
        try:
            with open(config_path, 'r') as file:
                yaml_data = yaml.safe_load(file) or {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return []
        
        # Extract grid layouts
        try:
            layouts_data = yaml_data.get('dashboard', {}).get('grid_layouts', [])
            
            # Convert to grid layout objects - customize this part for your application
            grid_layouts = []
            for layout_data in layouts_data:
                # Create an instance of your grid layout class
                # This is a placeholder - replace with your actual class
                grid = GridLayout(
                    id=layout_data.get('id'),
                    name=layout_data.get('name'),
                    position=layout_data.get('position'),
                    columns=layout_data.get('columns', 3)
                )
                
                # Set up filters if present
                filter_data = layout_data.get('filter', {})
                if filter_data:
                    grid.filter = GridFilter()
                    grid.filter.category = filter_data.get('category', [])
                    grid.filter.status = filter_data.get('status', [])
                    grid.filter.due = filter_data.get('due', [])
                    
                    # Handle legacy fields
                    if 'type' in filter_data:
                        grid.filter.type = filter_data['type']
                    if 'priority' in filter_data:
                        grid.filter.priority = filter_data['priority']
                    if 'tags' in filter_data:
                        grid.filter.tags = filter_data['tags']
                
                grid_layouts.append(grid)
            
            logger.info(f"Loaded {len(grid_layouts)} grid layouts from configuration")
            return grid_layouts
            
        except Exception as e:
            logger.error(f"Error parsing grid layouts: {e}")
            return []
    
    # In DashboardConfigManager.add_grid_layout
    @staticmethod
    def add_grid_layout(name=None, columns=None):
        """
        Add a new grid layout.
        Returns:
            str: ID of the newly created grid layout
        """
        import uuid

        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        is_dicts = (not grid_layouts) or isinstance(grid_layouts[0], dict)

        new_grid_id = f"grid_{uuid.uuid4().hex[:8]}"

        # canonical dict form used for YAML
        new_grid_dict = {
            "id": new_grid_id,
            "name": name or "New Grid",
            "position": len(grid_layouts),
            "columns": columns or 3,
            "minimize": False,             # <-- top-level, boolean
            "filter": {
                "status": [],
                "category": [],
                "due": []
            }
        }

        if is_dicts:
            grid_layouts.append(new_grid_dict)
        else:
            # Build an object with the same top-level attributes
            grid = type("", (), {})()
            grid.id = new_grid_dict["id"]
            grid.name = new_grid_dict["name"]
            grid.position = new_grid_dict["position"]
            grid.columns = new_grid_dict["columns"]
            grid.minimize = False         # <-- top-level, boolean

            # filter object
            grid.filter = type("", (), {})()
            grid.filter.status = []
            grid.filter.category = []
            grid.filter.due = []

            grid_layouts.append(grid)

        DashboardConfigManager.save_grid_layouts(grid_layouts)
        return new_grid_id

    
    @staticmethod
    def update_grid_filter(grid_id, filter_type, filter_values):
        """
        Update a specific filter on a grid layout.
        
        Args:
            grid_id (str): ID of the grid to update
            filter_type (str): Type of filter to update (status, category, due)
            filter_values (list): New values for the filter
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        # Get existing grid layouts
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        
        # Find the grid to update
        for grid in grid_layouts:
            if grid.id == grid_id:
                # Update the filter
                setattr(grid.filter, filter_type, filter_values)
                
                # Save the updated layouts
                return DashboardConfigManager.save_grid_layouts(grid_layouts)
        
        return False
    
    @staticmethod
    def update_grid_properties(grid_id, properties):
        """
        Update grid layout properties.
        
        Args:
            grid_id (str): ID of the grid to update
            properties (dict): Dictionary of properties to update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        # Get existing grid layouts
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        
        # Find the grid to update
        for grid in grid_layouts:
            if grid.id == grid_id:
                # Update properties
                for key, value in properties.items():
                    setattr(grid, key, value)
                
                # Save the updated layouts
                return DashboardConfigManager.save_grid_layouts(grid_layouts)
        
        return False
    
    @staticmethod
    def delete_grid_layout(grid_id):
        """
        Delete a grid layout.
        
        Args:
            grid_id (str): ID of the grid to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        # Get existing grid layouts
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        
        # Find and remove the grid
        for i, grid in enumerate(grid_layouts):
            if grid.id == grid_id:
                del grid_layouts[i]
                
                # Update positions
                for j, grid in enumerate(grid_layouts):
                    grid.position = j
                
                # Save the updated layouts
                return DashboardConfigManager.save_grid_layouts(grid_layouts)
        
        return False