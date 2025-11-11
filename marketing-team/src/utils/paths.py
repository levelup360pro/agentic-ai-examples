"""Paths and project structure helpers.

Defines canonical directories used throughout the marketing_team example.
These helpers keep path usage consistent and avoid string concatenation.
"""

from pathlib import Path

# Anchor from this file's location
THIS_FILE = Path(__file__)
SRC_DIR = THIS_FILE.parent.parent  # src/
PROJECT_ROOT = SRC_DIR.parent      # project root

# Config paths
CONFIG_DIR = PROJECT_ROOT / "configs"

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Notebooks 
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"