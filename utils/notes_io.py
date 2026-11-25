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

from datetime import datetime
from models.note import Note
from utils.app_config import AppConfig
from utils.safe_io import read_json, write_json

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

    notes_data = read_json(json_file_path, logger)

    # Use note ID as the key to avoid duplicates
    notes_data[note.id] = {
        'id': note.id,
        'title': note.title,
        'content': note.content,
        'creation_date': note.creation_date.strftime('%Y-%m-%d, %H:%M:%S'),
        'modified_date': datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    }

    if not write_json(json_file_path, notes_data, logger):
        return False

    logger.info(f"Note saved to {json_file_path}")
    return True

def load_notes_from_json(logger):
    """
    Load notes from the JSON file in the user's app data directory.

    Returns:
        dict: Dictionary of notes keyed by their id.
    """
    app_config = AppConfig()
    json_file_path = app_config.notes_file

    # logger.info(f"Loading notes from: {json_file_path}")

    return read_json(json_file_path, logger)

def rename_note_in_json(note_id, title, logger):
    """Give a saved note a new title, leaving its content alone. Returns True if renamed."""
    json_file_path = AppConfig().notes_file
    notes_data = read_json(json_file_path, logger)
    if note_id not in notes_data:
        logger.error("Note to rename not found in saved data.")
        return False
    notes_data[note_id]['title'] = title
    notes_data[note_id]['modified_date'] = datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    return write_json(json_file_path, notes_data, logger)

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

    notes_data = read_json(json_file_path, logger)

    if note_id not in notes_data:
        logger.error("Selected note not found in saved data.")
        return False

    del notes_data[note_id]

    if not write_json(json_file_path, notes_data, logger):
        return False

    logger.info("Note deleted successfully.")
    return True
