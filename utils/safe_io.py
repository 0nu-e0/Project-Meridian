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
# File: safe_io.py
# Description: Safe reading and writing of the app's JSON and YAML data files.
#              Writes are atomic, files that can't be parsed are moved aside
#              instead of being overwritten, and records that fail to parse are
#              carried through saves unchanged.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import json
import logging
import os
import tempfile
import time
from datetime import datetime

import yaml

_module_logger = logging.getLogger(__name__)

# (original path, backup path) for every file moved aside this session
_quarantined_files = []

# Paths that could not be read for reasons other than bad content (locked, no
# permission). Writing them could replace data we never saw, so writes are refused.
_unreadable_paths = set()

# path -> {key: raw record} for records that failed to parse on the last load
_unparsed_records = {}

# Called with (original path, backup path) whenever a file is moved aside
_quarantine_handler = None


def set_quarantine_handler(handler):
    """Register a callback(original_path, backup_path) run when a file is moved aside."""
    global _quarantine_handler
    _quarantine_handler = handler


def get_quarantined_files():
    """Return (original path, backup path) for every file moved aside this session."""
    return list(_quarantined_files)


def _quarantine(path, reason, logger):
    """Move an unparseable file aside so later saves can't overwrite it."""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = f"{path}.corrupt-{timestamp}"
    try:
        os.replace(path, backup_path)
    except OSError as e:
        logger.error(f"Could not move unreadable file {path} aside: {e}. Writes to it are disabled.")
        _unreadable_paths.add(path)
        return

    logger.error(f"{path} could not be read ({reason}). It was moved to {backup_path}.")
    _quarantined_files.append((path, backup_path))
    if _quarantine_handler:
        try:
            _quarantine_handler(path, backup_path)
        except Exception as e:
            logger.error(f"Quarantine handler failed: {e}")


def _read(path, parse, default, expected_type, logger):
    logger = logger or _module_logger
    if not os.path.exists(path):
        _unreadable_paths.discard(path)
        return default()

    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = parse(file)
    except (ValueError, yaml.YAMLError) as e:
        # Bad content (ValueError covers JSONDecodeError and UnicodeDecodeError)
        _quarantine(path, e, logger)
        return default()
    except OSError as e:
        logger.error(f"Could not read {path}: {e}. Writes to it are disabled until it can be read.")
        _unreadable_paths.add(path)
        return default()

    _unreadable_paths.discard(path)

    if data is None:
        # An empty YAML file
        return default()
    if expected_type is not None and not isinstance(data, expected_type):
        _quarantine(path, f"expected {expected_type.__name__}, found {type(data).__name__}", logger)
        return default()
    return data


def read_json(path, logger=None, default=dict, expected_type=dict):
    """Read a JSON file. Returns default() if it is missing or can't be read."""
    return _read(path, json.load, default, expected_type, logger)


def read_yaml(path, logger=None, default=dict, expected_type=dict):
    """Read a YAML file. Returns default() if it is missing, empty, or can't be read."""
    return _read(path, yaml.safe_load, default, expected_type, logger)


def _write(path, dump, logger):
    logger = logger or _module_logger
    if path in _unreadable_paths:
        logger.error(f"Not saving {path}: it could not be read earlier, so saving could lose data.")
        return False

    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=os.path.basename(path) + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            dump(file)
            file.flush()
            os.fsync(file.fileno())

        # Antivirus and sync tools can briefly lock the target on Windows
        for attempt in range(5):
            try:
                os.replace(temp_path, path)
                return True
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return False


def write_json(path, data, logger=None, indent=2, **dump_kwargs):
    """Atomically write data as JSON. Returns True on success."""
    return _write(path, lambda file: json.dump(data, file, indent=indent, **dump_kwargs), logger)


def write_yaml(path, data, logger=None):
    """Atomically write data as YAML. Returns True on success."""
    return _write(path, lambda file: yaml.dump(data, file, default_flow_style=False, sort_keys=False), logger)


def parse_records(path, raw_records, parse, logger=None):
    """
    Parse each record in raw_records ({key: raw}) with parse(key, raw).

    Records that fail are logged and remembered, so with_unparsed_records() can
    write them back unchanged instead of the next save deleting them.
    """
    logger = logger or _module_logger
    parsed = {}
    failed = {}
    for key, raw in raw_records.items():
        try:
            parsed[key] = parse(key, raw)
        except Exception as e:
            logger.error(f"Skipping unreadable record {key!r} in {path}: {e!r}")
            failed[key] = raw
    _unparsed_records[path] = failed
    return parsed


def with_unparsed_records(path, records):
    """Return records ({key: serialized}) plus any records from path that failed to parse."""
    merged = dict(_unparsed_records.get(path, {}))
    merged.update(records)
    return merged
