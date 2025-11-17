"""
Test package for Minin app.

This package contains all test modules.
The conftest setup adds the parent directory to sys.path to enable imports.
"""

import sys
import os

# Add parent directory to path to enable imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)