"""
Test Tag Frequency Database Pipeline

Tests the complete pipeline:
1. Extract tags from existing auto-sorted images (CLIP + prompts, deduplicated)
2. Build frequency database
3. Generate analysis reports
4. Identify underrepresented tags

This shows us what tags exist in the current collection before processing new batch.
"""

import os
import sys
from tag_frequency_database import TagFrequencyDatabase


def find_auto_sorted_folders():
    """Find all auto_sorted folders in project."""
    folders = []

    for root, dirs, files in os.walk('.'):
        if 'auto_sorted' in root:
            for item in os.listdir(root):
                item_path = os.path.join(root, item)
                if os.path.isdir(item_path):
                    # Check if it has images
                    for f in os.listdir(item_path):
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                            folders.append(item_path)
                            break
    return folders


def test_frequency_database():
    """Test the complete frequency database pipeline."""
    print("\n" + "="*70)
    print("TAG FREQUENCY DATABASE TEST")
    print("="*70)

    try:
        # Step 1: Initialize database
        print("\n[Step 1] Initializing frequency database...")
        db = TagFrequencyDatabase('tag_frequency.json')
        print("[OK] Database initialized")

        # Step 2: Find images to scan
        print("\n[Step 2] Finding auto-sorted folders to scan...")
        folders = find_auto_sorted_folders()

        if not folders:
            print("[INFO] No auto_sorted folders found, creating test database")
            print("        Usage: test_frequency_database.py")
            print("        Edit this script to point to image folders")
            return False

        print(f"[OK] Found {len(folders)} folders to scan:")
        for folder in folders:
            print(f"     - {folder}")

        # Step 3: Scan folders
        print("\n[Step 3] Extracting tags from existing images...")
        total_scanned = 0
        for i, folder in enumerate(folders, 1):
            print(f"\n  [{i}/{len(folders)}] Scanning: {folder}")
            result = db.scan_folder(folder, recursive=False)

            print(f"    Scanned: {result['scanned']}")
            print(f"    Added: {result['added']}")
            print(f"    Updated: {result['updated']}")
            total_scanned += result['successful']

        print(f"\n[OK] Total images processed: {total_scanned}")

        # Step 4: Generate reports
        print("\n[Step 4] Generating frequency reports...")

        # Print text report
        db.print_frequency_report(min_images=1, limit=50)

        # Export to file
        db.export_report()

        # Step 5: Identify issues
        print("\n[Step 5] Identifying underrepresented tags...")
        under = db.identify_underrepresented_tags(threshold=5)
        print(f"[INFO] Found {len(under)} tags appearing in 5 or fewer images")

        if under:
            print("\n  Underrepresented tags (consider whether to include in auto-sort):")
            for item in under[:10]:
                print(f"    - {item['tag']}: {item['count']} images")
            if len(under) > 10:
                print(f"    ... and {len(under) - 10} more")

        # Step 6: Summary
        print("\n" + "="*70)
        print("FREQUENCY DATABASE TEST COMPLETE")
        print("="*70)
        print(f"Total unique tags: {db.database['statistics']['total_unique_tags']}")
        print(f"Total images scanned: {db.database['statistics']['total_images']}")
        print(f"Database saved to: {db.db_file}")
        print("\nNEXT STEPS:")
        print("1. Review the tag frequency report")
        print("2. Process your new batch with tag generation")
        print("3. Add new batch to frequency database")
        print("4. Analyze combined distribution")
        print("5. Improve multi-tag distribution logic")
        print("="*70)

        return True

    except Exception as e:
        print(f"\n[FAIL] Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_frequency_database()
    sys.exit(0 if success else 1)
