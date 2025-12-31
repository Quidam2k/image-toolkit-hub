#!/usr/bin/env python3
"""Test script to check if all imports work correctly."""

try:
    print("Testing imports...")
    
    # Test basic imports
    import os
    import sys
    print("✓ os, sys")
    
    import shutil
    import random
    import time
    print("✓ shutil, random, time")
    
    import gc
    import threading
    import logging
    print("✓ gc, threading, logging")
    
    # Test PIL
    from PIL import Image, ImageTk
    print("✓ PIL")
    
    # Test tkinter
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    print("✓ tkinter")
    
    # Test our modules
    from config_manager import ConfigManager
    print("✓ config_manager")
    
    from metadata_parser import MetadataParser
    print("✓ metadata_parser")
    
    from auto_sorter import AutoSorter
    print("✓ auto_sorter")
    
    from auto_sort_progress import AutoSortProgressDialog
    print("✓ auto_sort_progress")
    
    from term_manager import TermManagerDialog
    print("✓ term_manager")
    
    from setup_dialog import show_setup_dialog
    print("✓ setup_dialog")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()