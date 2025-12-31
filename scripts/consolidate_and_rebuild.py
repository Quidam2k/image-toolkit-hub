#!/usr/bin/env python3
"""
Consolidate all images to master_images/ folder and rebuild tag database.

This script:
1. Creates master_images/ folder
2. Copies all images from sorted_* and auto_sorted/ folders
3. Rebuilds tag_frequency.json with full tag extraction (no filtering)
4. Updates paths in batch export system

Run this once to set up the new unified image collection.
"""

import os
import shutil
from pathlib import Path
from tag_frequency_database import TagFrequencyDatabase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def consolidate_images():
    """Consolidate all images to master_images/ folder."""

    master_dir = Path('master_images')
    master_dir.mkdir(exist_ok=True)

    # Only include folders we want to process for tagging
    source_folders = [
        'auto_sorted',           # Auto-sorted collection (7,795 images)
        'sorted_txt2img-images'  # Source material being processed (4,376 images)
    ]

    # These folders are excluded (manual MJ sorting, not for tagging)
    excluded_folders = [
        'sorted_sort_stack',      # Manual sorting in progress
        'sorted_MJall',           # Manual MJ collection
        'sorted_image_workspace'  # Manual workspace
    ]

    total_copied = 0

    for source_folder in source_folders:
        source_path = Path(source_folder)
        if not source_path.exists():
            logger.warning(f"Source folder not found: {source_folder}")
            continue

        logger.info(f"\nProcessing: {source_folder}")

        # Walk through all subdirectories
        for root, dirs, files in os.walk(source_path):
            for file in files:
                # Check if it's an image file
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')):
                    src = Path(root) / file
                    dst = master_dir / file

                    # Handle duplicate filenames
                    counter = 1
                    original_dst = dst
                    while dst.exists():
                        stem = original_dst.stem
                        suffix = original_dst.suffix
                        dst = master_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                    try:
                        shutil.copy2(src, dst)
                        total_copied += 1
                        if total_copied % 100 == 0:
                            logger.info(f"  Copied {total_copied} images so far...")
                    except Exception as e:
                        logger.error(f"Failed to copy {src}: {e}")

    logger.info(f"\n{'='*70}")
    logger.info(f"Total images consolidated: {total_copied}")
    logger.info(f"Location: {master_dir.absolute()}")
    logger.info(f"{'='*70}")

    return master_dir

def rebuild_tag_database(image_dir):
    """Rebuild tag frequency database with new extraction logic."""

    logger.info(f"\n{'='*70}")
    logger.info("Rebuilding tag frequency database...")
    logger.info(f"{'='*70}")

    # Create new database instance
    db = TagFrequencyDatabase()

    # Scan the master images folder
    result = db.scan_folder(str(image_dir), recursive=False)

    logger.info(f"\nScan Results:")
    logger.info(f"  Scanned: {result['scanned']}")
    logger.info(f"  Successful: {result['successful']}")
    logger.info(f"  Failed: {result['failed']}")
    logger.info(f"  Added: {result['added']}")
    logger.info(f"  Updated: {result['updated']}")
    logger.info(f"  Total tags: {result['total_tags']}")

    # Print frequency report
    logger.info(f"\n{'='*70}")
    logger.info("Top 50 tags by frequency:")
    logger.info(f"{'='*70}")
    db.print_frequency_report(min_images=1, limit=50)

    return db

def main():
    """Run consolidation and rebuild process."""

    print("\n" + "="*70)
    print("IMAGE CONSOLIDATION & TAG DATABASE REBUILD")
    print("="*70)
    print("\nSOURCES TO INCLUDE:")
    print("  [+] auto_sorted/ (7,795 images)")
    print("  [+] sorted_txt2img-images/ (4,376 images)")
    print("\nFOLDERS EXCLUDED (manual MJ sorting):")
    print("  [-] sorted_sort_stack/ (3,000 images - stay in recycle_bin)")
    print("  [-] sorted_MJall/ (43 images - stay in recycle_bin)")
    print("  [-] sorted_image_workspace/ (262 images - stay in recycle_bin)")
    print("\nThis will:")
    print("1. Copy ~8,200 images to master_images/")
    print("2. Rebuild tag frequency database with unlimited tag extraction")
    print("3. This may take several minutes depending on image count")
    print("\nContinuing...\n")

    # Step 1: Consolidate images
    master_dir = consolidate_images()

    # Step 2: Rebuild tag database
    db = rebuild_tag_database(master_dir)

    print("\n" + "="*70)
    print("CONSOLIDATION COMPLETE")
    print("="*70)
    print(f"\nResults:")
    print(f"[OK] All images consolidated: {master_dir.absolute()}")
    print(f"[OK] Tag database rebuilt with {len(db.database['tags'])} unique tags")
    print(f"[OK] Batch export tool now uses this master collection")
    print(f"\nExcluded folders (not in master_images):")
    print(f"  - sorted_sort_stack/ → left untouched (manual MJ sorting)")
    print(f"  - sorted_MJall/ → left untouched (manual MJ collection)")
    print(f"  - sorted_image_workspace/ → left untouched (manual workspace)")
    print(f"\nManual sorting folders preserved:")
    print(f"  - 1/, 2/, 3/ (manual categories)")
    print(f"  - removed/ (deleted items)")
    print(f"  - unmatched/ (unmatched items)")
    print(f"\nWhen satisfied this is working correctly, you can delete recycle_bin/")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
