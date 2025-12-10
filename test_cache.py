#!/usr/bin/env python3
import logging
import sys

# Setup logging to see the output
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Import after logging setup
from utils.tasks_io import load_tasks_from_json

print("=== Testing Task Caching ===\n")

# First load - should hit disk
print("First call - should load from disk:")
tasks1 = load_tasks_from_json(logger)
print(f"Loaded {len(tasks1)} tasks\n")

# Second load - should use cache
print("Second call - should use cache:")
tasks2 = load_tasks_from_json(logger)
print(f"Loaded {len(tasks2)} tasks\n")

# Third load - should use cache
print("Third call - should use cache:")
tasks3 = load_tasks_from_json(logger)
print(f"Loaded {len(tasks3)} tasks\n")

print("=== Test Complete ===")
