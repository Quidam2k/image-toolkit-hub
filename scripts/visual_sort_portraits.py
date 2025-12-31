"""
Visual Sort Portraits Script

Sorts images from sorted_txt2img-images/1/ into portrait-like categories:
- Solo subject only
- Shot types: portrait, upper_body, extreme_closeup

Uses COPY mode to preserve originals.
Caches WD14 results alongside images for fast re-runs.

Usage:
    python scripts/visual_sort_portraits.py [--sample N] [--dry-run]

Options:
    --sample N   Only process first N images (for testing)
    --dry-run    Show what would happen without copying files
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visual_classifier import (
    VisualClassifier, ShotType, PersonCount, NSFWRating,
    LoRASortingProfile, VisualClassification
)


def get_image_files(folder: str) -> list:
    """Get all image files from a folder."""
    extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    files = []

    for f in os.listdir(folder):
        if Path(f).suffix.lower() in extensions:
            files.append(os.path.join(folder, f))

    return sorted(files)


def create_portrait_profile() -> LoRASortingProfile:
    """Create a profile for solo portraits (head to sternum)."""
    return LoRASortingProfile(
        name='solo_portrait',
        shot_types=[
            ShotType.PORTRAIT,
            ShotType.UPPER_BODY,
            ShotType.EXTREME_CLOSEUP
        ],
        person_counts=[PersonCount.SOLO],
        nsfw_ratings=None,  # Any rating
        required_tags=[],
        excluded_tags=[]
    )


def matches_strict(classification: VisualClassification, profile: LoRASortingProfile) -> str:
    """
    Strict matching - returns category or None.

    Returns:
        'match' - matches profile with confirmed shot type
        'unknown_solo' - solo but unknown shot type (for review)
        None - doesn't match at all
    """
    # Must be solo
    if classification.person_count != PersonCount.SOLO:
        # Also accept if person_count is unknown but has solo-like tags
        if classification.person_count != PersonCount.UNKNOWN:
            return None

    # Check shot type strictly
    if classification.shot_type in profile.shot_types:
        return 'match'
    elif classification.shot_type == ShotType.UNKNOWN:
        # Solo but unknown shot - put in review pile
        if classification.person_count == PersonCount.SOLO:
            return 'unknown_solo'
        return None
    else:
        # Known shot type but not what we want (full_body, cowboy, wide)
        return None


def main():
    parser = argparse.ArgumentParser(description='Visual sort for solo portraits')
    parser.add_argument('--sample', type=int, default=0,
                        help='Only process first N images (0 = all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without copying')
    parser.add_argument('--source', type=str,
                        default=r'H:\Development\image_grid_sorter\sorted_txt2img-images\1',
                        help='Source folder')
    parser.add_argument('--output-base', type=str,
                        default=r'H:\Development\image_grid_sorter\auto_sorted\visual_solo_portrait',
                        help='Base output folder')
    args = parser.parse_args()

    # Two output folders: strict matches and unknowns for review
    output_match = args.output_base
    output_unknown = args.output_base + '_unknown_review'

    print("=" * 70)
    print("Visual Sort - Solo Portraits (STRICT MODE)")
    print("=" * 70)
    print(f"Source: {args.source}")
    print(f"Output (matches):  {output_match}")
    print(f"Output (unknowns): {output_unknown}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'COPY (preserving originals)'}")
    print("=" * 70)

    # Check source exists
    if not os.path.isdir(args.source):
        print(f"ERROR: Source folder not found: {args.source}")
        return 1

    # Get image files
    print("\nScanning for images...")
    images = get_image_files(args.source)
    total_images = len(images)
    print(f"Found {total_images} images")

    if args.sample > 0:
        images = images[:args.sample]
        print(f"Processing sample of {len(images)} images")

    # Create output folders
    if not args.dry_run:
        os.makedirs(output_match, exist_ok=True)
        os.makedirs(output_unknown, exist_ok=True)

    # Initialize classifier
    print("\nInitializing visual classifier (loading WD14 model)...")
    try:
        classifier = VisualClassifier(use_yolo=False)
        if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
            print("ERROR: WD14 tagger not loaded. Check model files.")
            return 1
        print("Classifier ready!")
    except Exception as e:
        print(f"ERROR: Failed to initialize classifier: {e}")
        return 1

    # Create profile
    profile = create_portrait_profile()
    print(f"\nProfile: {profile.name}")
    print(f"  Shot types: {[st.value for st in profile.shot_types]}")
    print(f"  Person count: {[pc.value for pc in profile.person_counts]}")

    # Process images
    print(f"\nProcessing {len(images)} images...")
    print("-" * 70)

    matches = []       # Strict matches (confirmed portrait/upper_body/closeup + solo)
    unknowns = []      # Solo but unknown shot type (for review)
    rejected = {       # Track why images were rejected
        'not_solo': 0,
        'wrong_shot_type': 0
    }
    start_time = datetime.now()

    for i, image_path in enumerate(images):
        # Progress
        if (i + 1) % 100 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(images) - i - 1) / rate if rate > 0 else 0

            cache_stats = classifier.wd14_tagger.get_cache_stats()
            print(f"  [{i+1}/{len(images)}] "
                  f"{rate:.1f} img/sec, ~{remaining/60:.1f} min remaining, "
                  f"cache: {cache_stats['hit_rate_percent']}% hits, "
                  f"matches: {len(matches)}, unknowns: {len(unknowns)}")

        # Classify
        result = classifier.classify_image(image_path)

        # Check with strict matching
        match_type = matches_strict(result, profile)

        if match_type == 'match':
            matches.append({
                'path': image_path,
                'classification': result
            })
        elif match_type == 'unknown_solo':
            unknowns.append({
                'path': image_path,
                'classification': result
            })
        else:
            # Track rejection reason
            if result.person_count != PersonCount.SOLO:
                rejected['not_solo'] += 1
            else:
                rejected['wrong_shot_type'] += 1

    # Summary
    elapsed_total = (datetime.now() - start_time).total_seconds()
    cache_stats = classifier.wd14_tagger.get_cache_stats()

    print("-" * 70)
    print(f"\nProcessing complete!")
    print(f"  Time: {elapsed_total:.1f} seconds ({elapsed_total/60:.1f} minutes)")
    print(f"  Rate: {len(images)/elapsed_total:.1f} images/second")
    print(f"  Cache: {cache_stats['hits']} hits, {cache_stats['misses']} misses "
          f"({cache_stats['hit_rate_percent']}% hit rate)")

    print(f"\nResults:")
    print(f"  Total processed: {len(images)}")
    print(f"  STRICT MATCHES: {len(matches)} ({len(matches)/len(images)*100:.1f}%)")
    print(f"  Unknown (solo): {len(unknowns)} ({len(unknowns)/len(images)*100:.1f}%)")
    print(f"  Rejected:")
    print(f"    - Not solo: {rejected['not_solo']}")
    print(f"    - Wrong shot type (full_body/cowboy/wide): {rejected['wrong_shot_type']}")

    # Show breakdown by shot type for matches
    if matches:
        shot_breakdown = {}
        for m in matches:
            st = m['classification'].shot_type.value
            shot_breakdown[st] = shot_breakdown.get(st, 0) + 1

        print(f"\n  Matches by shot type:")
        for st, count in sorted(shot_breakdown.items(), key=lambda x: -x[1]):
            print(f"    {st}: {count}")

    # Copy function
    def copy_files(file_list, dest_folder, label):
        if not file_list:
            return 0, 0

        print(f"\nCopying {len(file_list)} {label} to {dest_folder}...")
        copied = 0
        errors = 0

        for m in file_list:
            src = m['path']
            dst = os.path.join(dest_folder, os.path.basename(src))

            try:
                shutil.copy2(src, dst)

                # Also copy associated files (.txt, .wd14cache.json)
                for ext in ['.txt', '.wd14cache.json']:
                    src_assoc = src + ext
                    if os.path.exists(src_assoc):
                        shutil.copy2(src_assoc, dst + ext)

                copied += 1
            except Exception as e:
                print(f"  ERROR copying {os.path.basename(src)}: {e}")
                errors += 1

        print(f"  Copied: {copied}")
        if errors:
            print(f"  Errors: {errors}")

        return copied, errors

    # Copy files
    if not args.dry_run:
        copy_files(matches, output_match, "strict matches")
        copy_files(unknowns, output_unknown, "unknown-shot-type images for review")
    else:
        print(f"\n[DRY RUN] Would copy:")
        print(f"  - {len(matches)} strict matches to {output_match}")
        print(f"  - {len(unknowns)} unknowns to {output_unknown}")

    print("\nDone!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
