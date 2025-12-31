"""
Visual Sort Script - Sort images by visual classification

This script sorts images based on visual properties detected by WD14:
- Shot composition (portrait, upper_body, cowboy_shot, full_body, wide_shot)
- Person count (solo, duo, group)
- NSFW rating (general, sensitive, questionable, explicit)

Usage:
    python scripts/visual_sort.py --source <folder> --sort-by shot_type
    python scripts/visual_sort.py --source <folder> --sort-by person_count
    python scripts/visual_sort.py --source <folder> --profile portrait_lora

For LoRA workflows:
    Sorts images into folders that match your LoRA's expected input composition.
    e.g., portrait LoRAs expect close-up/upper body shots with single subjects.

Author: Claude Code Implementation
Version: 1.0
"""

import sys
import os
import argparse
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visual_classifier import (
    VisualClassifier, ShotType, PersonCount, NSFWRating,
    LoRASortingProfile, EXAMPLE_PROFILES
)
from config_manager import ConfigManager


def find_images(folder, recursive=True):
    """Find all image files in a folder."""
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
    images = []

    if recursive:
        for root, dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in image_extensions:
                    images.append(os.path.join(root, f))
    else:
        for f in os.listdir(folder):
            if os.path.splitext(f)[1].lower() in image_extensions:
                images.append(os.path.join(folder, f))

    return images


def preview_classification(source_folder, use_yolo=False, limit=50):
    """Preview how images would be classified without moving them."""
    print(f"\nScanning {source_folder}...")
    images = find_images(source_folder)
    images = images[:limit] if limit else images

    print(f"Found {len(images)} images (previewing up to {limit})")

    classifier = VisualClassifier(use_yolo=use_yolo)
    if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
        print("ERROR: WD14 tagger not loaded. Check model files in models/wd14/")
        return

    shot_counts = {}
    person_counts = {}
    rating_counts = {}

    for i, img in enumerate(images):
        result = classifier.classify_image(img)

        shot = result.shot_type.value
        person = result.person_count.value
        rating = result.nsfw_rating.value

        shot_counts[shot] = shot_counts.get(shot, 0) + 1
        person_counts[person] = person_counts.get(person, 0) + 1
        rating_counts[rating] = rating_counts.get(rating, 0) + 1

        print(f"[{i+1}/{len(images)}] {os.path.basename(img)}: "
              f"{shot} / {person} / {rating}")

    print("\n" + "="*50)
    print("CLASSIFICATION SUMMARY")
    print("="*50)

    print("\nShot Types:")
    for shot, count in sorted(shot_counts.items(), key=lambda x: -x[1]):
        pct = count / len(images) * 100
        print(f"  {shot}: {count} ({pct:.1f}%)")

    print("\nPerson Counts:")
    for person, count in sorted(person_counts.items(), key=lambda x: -x[1]):
        pct = count / len(images) * 100
        print(f"  {person}: {count} ({pct:.1f}%)")

    print("\nNSFW Ratings:")
    for rating, count in sorted(rating_counts.items(), key=lambda x: -x[1]):
        pct = count / len(images) * 100
        print(f"  {rating}: {count} ({pct:.1f}%)")


def sort_images(source_folder, sort_by='shot_type', use_yolo=False, copy_mode=True):
    """Sort images by visual classification."""
    print(f"\nSorting images by {sort_by}...")
    images = find_images(source_folder)
    print(f"Found {len(images)} images")

    # Initialize config manager for auto_sorter
    config = ConfigManager()

    # Import AutoSorter
    from auto_sorter import AutoSorter

    sorter = AutoSorter(config)

    # Set copy mode in settings
    settings = config.get_auto_sort_settings()
    settings['copy_instead_of_move'] = copy_mode
    config.set_auto_sort_settings(settings)

    def progress(current, total, filename, **kwargs):
        print(f"[{current}/{total}] {filename}")

    results = sorter.sort_by_visual_classification(
        images,
        sort_by=sort_by,
        use_yolo=use_yolo,
        progress_callback=progress
    )

    print("\n" + "="*50)
    print("SORT RESULTS")
    print("="*50)
    print(f"Processed: {results['processed']}")
    print(f"Sorted: {results['sorted']}")
    print(f"Errors: {len(results['errors'])}")

    if results['classification_counts']:
        print("\nBy category:")
        for cat, count in sorted(results['classification_counts'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")


def sort_by_profile(source_folder, profile_name, use_yolo=False, copy_mode=True):
    """Sort images matching a LoRA profile."""
    if profile_name in EXAMPLE_PROFILES:
        profile = EXAMPLE_PROFILES[profile_name]
    else:
        print(f"Unknown profile: {profile_name}")
        print(f"Available profiles: {list(EXAMPLE_PROFILES.keys())}")
        return

    print(f"\nSorting images matching profile: {profile_name}")
    print(f"Profile criteria: {profile.to_dict()}")

    images = find_images(source_folder)
    print(f"Found {len(images)} images")

    config = ConfigManager()
    from auto_sorter import AutoSorter

    sorter = AutoSorter(config)

    settings = config.get_auto_sort_settings()
    settings['copy_instead_of_move'] = copy_mode
    config.set_auto_sort_settings(settings)

    def progress(current, total, filename, **kwargs):
        matched = kwargs.get('matched', 0)
        print(f"[{current}/{total}] {filename} (matched: {matched})")

    results = sorter.sort_by_lora_profile(
        images,
        profile=profile,
        use_yolo=use_yolo,
        progress_callback=progress
    )

    print("\n" + "="*50)
    print("PROFILE SORT RESULTS")
    print("="*50)
    print(f"Processed: {results['processed']}")
    print(f"Matched profile: {results['matched']}")
    print(f"Not matched: {results['not_matched']}")
    print(f"Errors: {len(results['errors'])}")

    match_pct = results['matched'] / results['processed'] * 100 if results['processed'] else 0
    print(f"\nMatch rate: {match_pct:.1f}%")


def create_custom_profile(name, shot_types=None, person_counts=None,
                          nsfw_ratings=None, required_tags=None, excluded_tags=None):
    """Create a custom LoRA sorting profile."""
    # Convert string values to enums
    shots = None
    if shot_types:
        shots = [ShotType(s) for s in shot_types]

    persons = None
    if person_counts:
        persons = [PersonCount(p) for p in person_counts]

    ratings = None
    if nsfw_ratings:
        ratings = [NSFWRating(r) for r in nsfw_ratings]

    profile = LoRASortingProfile(
        name=name,
        shot_types=shots,
        person_counts=persons,
        nsfw_ratings=ratings,
        required_tags=required_tags or [],
        excluded_tags=excluded_tags or []
    )

    return profile


def main():
    parser = argparse.ArgumentParser(
        description='Sort images by visual classification for LoRA workflows'
    )
    parser.add_argument('--source', '-s',
                        help='Source folder containing images')
    parser.add_argument('--sort-by', choices=['shot_type', 'person_count', 'nsfw_rating'],
                        help='Classification to sort by')
    parser.add_argument('--profile', '-p',
                        help='LoRA profile name to filter by')
    parser.add_argument('--preview', action='store_true',
                        help='Preview classification without sorting')
    parser.add_argument('--limit', type=int, default=50,
                        help='Limit images for preview (default: 50)')
    parser.add_argument('--yolo', action='store_true',
                        help='Use YOLO for more accurate person detection')
    parser.add_argument('--move', action='store_true',
                        help='Move files instead of copy (default: copy)')
    parser.add_argument('--list-profiles', action='store_true',
                        help='List available LoRA profiles')

    args = parser.parse_args()

    if args.list_profiles:
        print("\nAvailable LoRA Profiles:")
        print("="*50)
        for name, profile in EXAMPLE_PROFILES.items():
            print(f"\n{name}:")
            d = profile.to_dict()
            if d['shot_types']:
                print(f"  Shot types: {', '.join(d['shot_types'])}")
            if d['person_counts']:
                print(f"  Person counts: {', '.join(d['person_counts'])}")
            if d['nsfw_ratings']:
                print(f"  NSFW ratings: {', '.join(d['nsfw_ratings'])}")
            if d['required_tags']:
                print(f"  Required tags: {', '.join(d['required_tags'])}")
            if d['excluded_tags']:
                print(f"  Excluded tags: {', '.join(d['excluded_tags'])}")
        return 0

    # Source is required for all other operations
    if not args.source:
        print("ERROR: --source is required for sorting/preview operations")
        parser.print_help()
        return 1

    if not os.path.exists(args.source):
        print(f"ERROR: Source folder not found: {args.source}")
        return 1

    if args.preview:
        preview_classification(args.source, use_yolo=args.yolo, limit=args.limit)
    elif args.profile:
        sort_by_profile(args.source, args.profile,
                        use_yolo=args.yolo, copy_mode=not args.move)
    elif args.sort_by:
        sort_images(args.source, sort_by=args.sort_by,
                    use_yolo=args.yolo, copy_mode=not args.move)
    else:
        print("Please specify --sort-by, --profile, or --preview")
        parser.print_help()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
