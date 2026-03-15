"""conftest.py -- ensure tools/ is on sys.path for test discovery."""
import sys
from pathlib import Path

# Add tools/ directory to sys.path so forge_nulls etc. can be imported
tools_dir = str(Path(__file__).parent)
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)
