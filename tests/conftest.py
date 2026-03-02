"""Configure pytest to add src to path for lettuce module imports."""

import sys
from pathlib import Path

# Add src to sys.path so `lettuce` package can be imported without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
