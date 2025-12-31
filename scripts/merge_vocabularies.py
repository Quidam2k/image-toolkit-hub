"""
Merge tag vocabularies from multiple sources into comprehensive CLIP vocabulary.

Sources:
1. clip_tags_from_images.txt - Tags extracted from existing tagged images (1,889 tags)
2. danbooru_tagcomplete.csv - Comprehensive danbooru tag list (hundreds of thousands)

Output:
- clip_vocabulary_comprehensive.txt - Merged vocabulary for CLIP zero-shot classification
"""

import csv
from pathlib import Path

def load_image_tags(file_path):
    """Load tags from extracted images."""
    tags = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            tag = line.strip()
            if tag:
                tags.add(tag)
    return tags

def load_danbooru_tags(file_path, max_tags=None):
    """Load tags from danbooru CSV (first column only)."""
    tags = set()
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if row and row[0]:  # First column is the tag
                tag = row[0].strip()
                if tag:
                    tags.add(tag)

            if max_tags and i >= max_tags:
                break

    return tags

def merge_and_save(image_tags, danbooru_tags, output_file):
    """Merge tag sets and save to output file."""
    # Combine both sets
    all_tags = image_tags | danbooru_tags

    # Sort alphabetically
    sorted_tags = sorted(all_tags)

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        for tag in sorted_tags:
            f.write(tag + '\n')

    return len(sorted_tags)

def main():
    print("="*70)
    print("MERGING TAG VOCABULARIES")
    print("="*70)

    # Load tags from images
    print("\n1. Loading tags from existing images...")
    image_tags = load_image_tags('clip_tags_from_images.txt')
    print(f"   Loaded {len(image_tags)} tags from images")

    # Load danbooru tags (limit to reasonable amount for CLIP - maybe 50k)
    print("\n2. Loading danbooru tags...")
    danbooru_tags = load_danbooru_tags('danbooru_tagcomplete.csv', max_tags=50000)
    print(f"   Loaded {len(danbooru_tags)} danbooru tags")

    # Merge and save
    print("\n3. Merging vocabularies...")
    total_tags = merge_and_save(image_tags, danbooru_tags, 'clip_vocabulary_comprehensive.txt')

    print(f"\n{'='*70}")
    print("MERGE COMPLETE")
    print(f"{'='*70}")
    print(f"\nTotal unique tags: {total_tags}")
    print(f"  From images: {len(image_tags)}")
    print(f"  From danbooru: {len(danbooru_tags)}")
    print(f"  Overlap: {len(image_tags & danbooru_tags)}")
    print(f"\nSaved to: clip_vocabulary_comprehensive.txt")
    print(f"{'='*70}\n")

    # Show sample
    merged_tags = sorted(image_tags | danbooru_tags)
    print("Sample tags (first 30):")
    for tag in merged_tags[:30]:
        print(f"  {tag}")

if __name__ == '__main__':
    main()
