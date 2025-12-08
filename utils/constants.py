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
# File: constants.py
# Description: Application-wide constants for Project Meridian
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

"""Application-wide constants for Project Meridian."""

# Window sizing constants
WINDOW_DEFAULT_WIDTH_RATIO = 0.90  # 90% of screen width
WINDOW_DEFAULT_HEIGHT_RATIO = 0.90  # 90% of screen height
WINDOW_MIN_WIDTH_RATIO = 0.5  # 50% of screen width
WINDOW_MIN_HEIGHT_RATIO = 0.5  # 50% of screen height

# Layout spacing constants
LAYOUT_NO_SPACING = 0
LAYOUT_SMALL_SPACING = 4
LAYOUT_MEDIUM_SPACING = 8
LAYOUT_LARGE_SPACING = 15
LAYOUT_XLARGE_SPACING = 20

# Layout margin constants
MARGIN_NONE = 0
MARGIN_SMALL = 5
MARGIN_MEDIUM = 8
MARGIN_LARGE = 10
MARGIN_XLARGE = 15
MARGIN_XXLARGE = 20

# Task card constants
CARD_PADDING = 8
CARD_DETAIL_SPACING = 4
CARD_MIN_SPACING = 20
CARD_MIN_READABLE_WIDTH = 200
CARD_OPTIMAL_CHARACTER_COUNT = 25
CARD_MIN_HEIGHT_FOR_CONTENT = 120
CARD_TARGET_CARDS_PER_ROW_DIVISOR = 400
CARD_MIN_CARDS_PER_ROW = 4
CARD_MARGIN_MULTIPLIER = 40
CARD_HEIGHT_ASPECT_RATIO = 1.5

# Animation constants
ANIMATION_DURATION_MS = 200  # milliseconds
ANIMATION_COLLAPSE_DURATION_MS = 150  # milliseconds (slightly faster collapse)
ANIMATION_UPDATE_INTERVAL_MS = 50  # milliseconds

# Drawer constants
DRAWER_SPACING = 20

# Due date calculation constants (days)
DUE_SOON_THRESHOLD_DAYS = 3
UPCOMING_THRESHOLD_DAYS = 14
