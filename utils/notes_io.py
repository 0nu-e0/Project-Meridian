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
# File: notes_io.py
# Description: Used to load and save notes to the saved_notes.json file.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os, json
from datetime import datetime
from models.note import Note
from utils.app_config import AppConfig 

def save_note_to_json(note, logger):
    """
    Save a Note object to the JSON file in the user's app data directory.
    
    Args:
        note: The Note object to save (can be new or existing)
    """
    if note is None:
        note = Note(title="New Note", content="")

    app_config = AppConfig()
    json_file_path = app_config.notes_file

    logger.info(f"Attempting to save note to: {json_file_path}")

    try:
        # Ensure the directory exists
        data_dir = os.path.dirname(json_file_path)
        if not os.path.exists(data_dir):
            logger.info(f"Creating directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
        
        # Read existing data if available
        notes_data = {}
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                notes_data = json.load(file)
        
        # Convert the Note object to a dictionary
        note_data = {
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'creation_date': note.creation_date.strftime('%Y-%m-%d, %H:%M:%S'),
            'modified_date': datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
        }
        
        # Use note ID as the key to avoid duplicates
        notes_data[note.id] = note_data

        # Write back to file
        with open(json_file_path, 'w') as file:
            json.dump(notes_data, file, indent=2)
            
        logger.info(f"Note saved to {json_file_path}")
        return True
            
    except Exception as e:
        logger.error(f"Error saving note to JSON: {e}")
        return False

def load_notes_from_json(logger):
    """
    Load notes from the JSON file in the user's app data directory.
    
    Returns:
        dict: Dictionary of notes keyed by their id.
    """
    app_config = AppConfig()
    json_file_path = app_config.notes_file

    # logger.info(f"Loading notes from: {json_file_path}")
    
    try:
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                notes_data = json.load(file)
                return notes_data
        else:
            logger.info("Notes file does not exist, returning empty dictionary.")
            return {}
    except Exception as e:
        logger.error(f"Error loading notes from JSON: {e}")
        return {}
    
def delete_note_from_json(note_id, logger):
    """
    Delete a note by its ID from the JSON file in the user's app data directory.
    
    Args:
        note_id: The unique identifier of the note to delete.
        logger: Logger for logging messages.
        
    Returns:
        True if deletion was successful, False otherwise.
    """

    app_config = AppConfig()
    json_file_path = app_config.notes_file

    logger.info(f"Attempting to delete note from: {json_file_path}")
    
    try:
        # Read existing data if available
        notes_data = {}
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                notes_data = json.load(file)
        else:
            logger.error("Notes file does not exist.")
            return False

        if note_id not in notes_data:
            logger.error("Selected note not found in saved data.")
            return False

        # Remove the note from the dictionary.
        del notes_data[note_id]

        # Write the updated dictionary back to the file.
        with open(json_file_path, 'w') as file:
            json.dump(notes_data, file, indent=2)

        logger.info("Note deleted successfully.")
        return True
    except Exception as e:
        logger.error(f"Error deleting note from JSON: {e}")
        return False
