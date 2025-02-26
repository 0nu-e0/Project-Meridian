# -----------------------------------------------------------------------------
# Project Manager
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
        # Define the config file path
        config_path = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    'data', 'app_config.yaml'))
        
        # print(f"Looking for dashboard config at: {config_path}")
        
        # Check if the file exists
        if not config_path.exists():
            print(f"Config file does not exist at: {config_path}")
            return []
        
        # Load the YAML file directly
        try:
            with open(config_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                # print(f"YAML loaded successfully. Keys: {list(yaml_data.keys())}")
                
                # Check if dashboard section exists
                if 'dashboard' not in yaml_data:
                    print("No dashboard section found in YAML file")
                    return []
                    
                # Check if grid_layouts section exists
                if 'grid_layouts' not in yaml_data['dashboard']:
                    print("No grid_layouts section found in dashboard configuration")
                    return []
                
                # Get the grid layouts from the YAML
                yaml_grid_layouts = yaml_data['dashboard']['grid_layouts']
                # print(f"Found {len(yaml_grid_layouts)} grid layouts in configuration")
                
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
                    
                    # Create filter object
                    grid.filter = type('', (), {})()
                    
                    # Set filter properties
                    filter_data = grid_data.get('filter', {})
                    
                    # Extract filter values directly from YAML
                    # Make sure to preserve these exact keys for your GridLayout
                    grid.filter.status = filter_data.get('status', [])
                    grid.filter.category = filter_data.get('category', [])
                    grid.filter.due = filter_data.get('due', [])
                    
                    # Debug output
                    # print(f"Grid {grid.name} filter values: status={grid.filter.status}, category={grid.filter.category}, due={grid.filter.due}")
                    
                    grid_layouts.append(grid)
                
                # print(f"Successfully processed {len(grid_layouts)} grid layouts")
                return grid_layouts
                
        except Exception as e:
            print(f"Error loading dashboard configuration: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def save_grid_layouts(grid_layouts):
        """
        Save grid layouts to the configuration file.
        
        Args:
            grid_layouts (list): List of grid layout objects to save
        """
        # Define the config file path
        config_path = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      'data', 'app_config.yaml'))
        
        # Load existing YAML file
        try:
            with open(config_path, 'r') as file:
                yaml_data = yaml.safe_load(file) or {}
        except Exception:
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
                'filter': {}
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
        
        # Save the YAML file
        try:
            with open(config_path, 'w') as file:
                yaml.dump(yaml_data, file, default_flow_style=False)
            print(f"Successfully saved {len(yaml_grid_layouts)} grid layouts to configuration")
            return True
        except Exception as e:
            print(f"Error saving dashboard configuration: {e}")
            return False
    
    @staticmethod
    def add_grid_layout(name=None, columns=None):
        """
        Add a new grid layout.
        Args:
            name (str, optional): Name for the new grid.
            columns (int, optional): Number of columns.
        Returns:
            str: ID of the newly created grid layout
        """
        import uuid
        
        # Get existing grid layouts
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        
        # Create new grid as a dictionary (better for YAML serialization)
        new_grid = {
            'id': f"grid_{uuid.uuid4().hex[:8]}",
            'name': name or "New Grid",
            'position': len(grid_layouts),
            'columns': columns or 3,
            'filter': {
                'status': [],
                'category': [],
                'due': []
            }
        }
        
        # Add to list (convert to object if your system requires objects)
        if isinstance(grid_layouts[0], dict):
            # If existing grids are dictionaries
            grid_layouts.append(new_grid)
        else:
            # If existing grids are objects
            grid = type('', (), {})()
            grid.id = new_grid['id']
            grid.name = new_grid['name']
            grid.position = new_grid['position']
            grid.columns = new_grid['columns']
            
            grid.filter = type('', (), {})()
            grid.filter.status = []
            grid.filter.category = []
            grid.filter.due = []
            
            grid_layouts.append(grid)
        
        # Save updated list
        DashboardConfigManager.save_grid_layouts(grid_layouts)
        
        return new_grid['id']
    
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