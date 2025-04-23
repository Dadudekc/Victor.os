# tests/conftest.py
import sys
import os

# Ensure project root is on sys.path so that core and other packages are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
