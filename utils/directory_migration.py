import os
import json
import yaml
import shutil
import logging
from utils.directory_finder import resource_path

def migrate_data_if_needed():
    """
    Check for legacy files (JSON and YAML) using resource_path, and migrate them to the new location if found.
    """
    from utils.app_config import AppConfig

    # This should be imported from wherever it's defined in your project
    # from utils.helpers import resource_path

    logger = logging.getLogger("FileMigration")
    
    # Get the AppConfig instance
    app_config = AppConfig()
    
    # Files to migrate [source_path, destination_path, file_type]
    files_to_migrate = [
        # Tasks JSON file
        ('data/saved_tasks.json', app_config.tasks_file, 'json'),
        
        # Config YAML file
        ('data/app_config.yaml', os.path.join(app_config.app_data_dir, 'config', 'app_config.yaml'), 'yaml'),
        
        # Add any other files that need to be migrated
        # ('data/other_file.ext', os.path.join(app_config.app_data_dir, 'path', 'other_file.ext'), 'ext'),
    ]
    
    for source_rel_path, dest_path, file_type in files_to_migrate:
        try:
            # Get full source path
            source_path = resource_path(source_rel_path)
            
            logger.info(f"Checking for legacy file: {source_path}")
            
            # Check if source file exists
            if not os.path.exists(source_path):
                logger.info(f"No legacy file found at {source_path}")
                continue
                
            # Ensure destination directory exists
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Check if destination file already exists
            if os.path.exists(dest_path):
                logger.info(f"Destination file already exists at {dest_path}")
                # Backup the source file and skip migration
                backup_path = source_path + ".backup"
                shutil.copy2(source_path, backup_path)
                os.remove(source_path)
                logger.info(f"Legacy file backed up to {backup_path} and removed")
                continue
            
            # Copy the file based on its type
            if file_type == 'json':
                # For JSON files, read and write to ensure proper formatting
                with open(source_path, 'r') as f:
                    data = json.load(f)
                with open(dest_path, 'w') as f:
                    json.dump(data, f, indent=2)
            elif file_type == 'yaml':
                # For YAML files, read and write to ensure proper formatting
                with open(source_path, 'r') as f:
                    data = yaml.safe_load(f)
                with open(dest_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            else:
                # For other files, just copy directly
                shutil.copy2(source_path, dest_path)
            
            logger.info(f"Successfully migrated {file_type} file to {dest_path}")
            
            # Backup and remove the source file
            backup_path = source_path + ".backup"
            shutil.copy2(source_path, backup_path)
            os.remove(source_path)
            # logger.info(f"Legacy file backed up to {backup_path} and removed")

        except Exception as e:
            logger.error(f"Error migrating file {source_rel_path}: {e}")
    
    # Make sure all required directories exist
    os.makedirs(app_config.data_dir, exist_ok=True)
    os.makedirs(os.path.join(app_config.app_data_dir, 'config'), exist_ok=True)
    os.makedirs(app_config.logs_dir, exist_ok=True)
    os.makedirs(app_config.temp_dir, exist_ok=True)
    
    return True


