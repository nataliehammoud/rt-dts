"""
Pytest Configuration
====================
يضيف مجلد المشروع للـ Python path
"""
import sys
import os

# ضيف جذر المشروع للـ sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))