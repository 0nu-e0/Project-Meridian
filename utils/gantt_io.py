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
# File: gantt_io.py
# Description: I/O utilities for Gantt chart data
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import json
import os
from typing import Dict, Optional

from models.gantt_item import GanttChart
from utils.app_config import AppConfig


def _get_gantt_file_path():
    """Get the Gantt charts file path from AppConfig"""
    app_config = AppConfig()
    return os.path.join(app_config.data_dir, "gantt_charts.json")


def load_gantt_charts_from_json(logger) -> Dict[str, GanttChart]:
    """
    Load all Gantt charts from JSON file.

    Returns:
        Dictionary mapping project_id to GanttChart
    """
    json_file_path = _get_gantt_file_path()

    if not os.path.exists(json_file_path):
        logger.info(f"No Gantt charts file found at {json_file_path}, returning empty dict")
        return {}

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        charts = {}
        for chart_data in data.get('charts', []):
            chart = GanttChart.from_dict(chart_data)
            charts[chart.project_id] = chart

        logger.info(f"Loaded {len(charts)} Gantt charts from {json_file_path}")
        return charts

    except Exception as e:
        logger.error(f"Error loading Gantt charts from {json_file_path}: {e}")
        return {}


def save_gantt_charts_to_json(charts: Dict[str, GanttChart], logger) -> bool:
    """
    Save all Gantt charts to JSON file.

    Args:
        charts: Dictionary mapping project_id to GanttChart
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    json_file_path = _get_gantt_file_path()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

    try:
        data = {
            'charts': [chart.to_dict() for chart in charts.values()]
        }

        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(charts)} Gantt charts to {json_file_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving Gantt charts to {json_file_path}: {e}")
        return False


def load_gantt_chart_for_project(project_id: str, logger) -> Optional[GanttChart]:
    """
    Load Gantt chart for a specific project.

    Args:
        project_id: Project ID
        logger: Logger instance

    Returns:
        GanttChart if found, None otherwise
    """
    charts = load_gantt_charts_from_json(logger)
    return charts.get(project_id)


def save_gantt_chart(chart: GanttChart, logger) -> bool:
    """
    Save a single Gantt chart (updates existing or creates new).

    Args:
        chart: GanttChart to save
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    charts = load_gantt_charts_from_json(logger)
    charts[chart.project_id] = chart
    return save_gantt_charts_to_json(charts, logger)


def delete_gantt_chart(project_id: str, logger) -> bool:
    """
    Delete Gantt chart for a project.

    Args:
        project_id: Project ID
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    charts = load_gantt_charts_from_json(logger)
    if project_id in charts:
        del charts[project_id]
        return save_gantt_charts_to_json(charts, logger)
    return True
