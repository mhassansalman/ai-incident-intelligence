"""Conftest for Stage 2 tests."""

import sys
from pathlib import Path

# Ensure the project root is in sys.path so that `investigation` package is importable
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))