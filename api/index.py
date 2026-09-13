import sys
import os

# Add root directory to sys.path so 'app' imports resolve correctly on Vercel
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
