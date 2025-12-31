#!/usr/bin/env python3
"""
Simple script to install piexif for enhanced JPEG metadata support.
"""

import subprocess
import sys

def install_piexif():
    """Install piexif using pip."""
    try:
        print("Installing piexif for enhanced JPEG metadata support...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "piexif"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ piexif installed successfully!")
            print("\nNow you can embed tags in JPEG files with better reliability.")
            return True
        else:
            print("❌ Failed to install piexif:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error installing piexif: {e}")
        return False

if __name__ == "__main__":
    print("JPEG Tag Embedding Enhancement")
    print("=" * 40)
    print("\nThis will install 'piexif' to enable robust JPEG tag embedding.")
    print("Without piexif, only basic JPEG embedding is available (limited).")
    
    response = input("\nInstall piexif? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        install_piexif()
    else:
        print("Skipped installation. Basic JPEG embedding will still work.")