#!/usr/bin/env python3
"""
Quick test: Process 100 images with WD14 to measure speed and verify correctness.
"""

import os
import shutil
import time
from pathlib import Path
from tag_frequency_database import TagFrequencyDatabase

def test_100_images():
    """Process first 100 images and measure performance."""

    print("="*70)
    print("WD14 SPEED TEST - 100 IMAGES")
    print("="*70)

    # Create test directory
    test_dir = Path('master_images_test')
    test_dir.mkdir(exist_ok=True)

    # Collect first 100 images from auto_sorted
    source_path = Path('auto_sorted')
    image_count = 0
    max_images = 100

    print(f"\nCopying first {max_images} images from auto_sorted/...")

    for root, dirs, files in os.walk(source_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                if image_count >= max_images:
                    break

                src = Path(root) / file
                dst = test_dir / file

                try:
                    shutil.copy2(src, dst)
                    image_count += 1
                    if image_count % 10 == 0:
                        print(f"  Copied {image_count}/{max_images}")
                except Exception as e:
                    print(f"Failed to copy {src}: {e}")

        if image_count >= max_images:
            break

    print(f"\nCopied {image_count} images to {test_dir}/")

    # Now process with WD14
    print("\n" + "="*70)
    print("PROCESSING WITH WD14...")
    print("="*70)

    start_time = time.time()

    db = TagFrequencyDatabase()
    result = db.scan_folder(str(test_dir), recursive=False)

    elapsed = time.time() - start_time

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"\nImages processed: {result['successful']}")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Speed: {result['successful'] / elapsed:.2f} images/second")
    print(f"\nEstimated time for 14,123 images: {(14123 / (result['successful'] / elapsed)) / 3600:.1f} hours")

    # Show sample tags from first few images
    print("\n" + "="*70)
    print("SAMPLE TAGS (first 5 images)")
    print("="*70)

    count = 0
    for image_name, image_data in db.database['images'].items():
        if count >= 5:
            break
        tags = image_data['tags']
        print(f"\n{image_name}:")
        print(f"  Tag count: {len(tags)}")
        print(f"  First 20 tags: {', '.join(tags[:20])}")
        count += 1

    # Top tags
    print("\n" + "="*70)
    print("TOP 30 TAGS BY FREQUENCY")
    print("="*70)
    db.print_frequency_report(min_images=1, limit=30)

    # Cleanup
    print("\n" + "="*70)
    print(f"Test directory preserved at: {test_dir.absolute()}")
    print("Review results, then delete test directory if satisfied")
    print("="*70)

if __name__ == '__main__':
    test_100_images()
