"""ASGI handler for Vercel deployment."""
import sys
from pathlib import Path

# Add parent directory to path so we can import app module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

# Vercel expects a variable named 'app' or 'application'
# This file serves as the entry point
