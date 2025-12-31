"""
Test tag generation on a single image to verify CLIP model and vocabulary are working.
"""

import os
from pathlib import Path
from tag_generator import DescriptiveTagGenerator

def test_single_image():
    print("="*70)
    print("TESTING CLIP TAG GENERATION ON SINGLE IMAGE")
    print("="*70)

    # Find a test image from master_images
    master_images = Path('master_images')
    if not master_images.exists():
        print("ERROR: master_images folder not found")
        return

    # Get first PNG file
    test_images = list(master_images.glob('*.png'))[:1]
    if not test_images:
        print("ERROR: No PNG files found in master_images/")
        return

    test_image = test_images[0]
    print(f"\nTest image: {test_image.name}")
    print(f"Path: {test_image}")

    # Initialize tag generator
    print("\n" + "-"*70)
    print("Initializing tag generator...")
    print("-"*70)
    try:
        generator = DescriptiveTagGenerator()
    except Exception as e:
        print(f"ERROR initializing generator: {e}")
        import traceback
        traceback.print_exc()
        return

    # Generate tags
    print("\n" + "-"*70)
    print("Generating tags for image...")
    print("-"*70)
    try:
        result = generator.generate_tags_for_image(str(test_image))
    except Exception as e:
        print(f"ERROR generating tags: {e}")
        import traceback
        traceback.print_exc()
        return

    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"\nStatus: {result.get('status', 'unknown')}")
    if result.get('status') == 'error':
        print(f"Error: {result.get('error')}")
        return

    tags = result.get('tags', [])
    print(f"\nTotal tags generated: {len(tags)}")

    if tags:
        print("\nTop 30 tags (by confidence):")
        for i, tag_info in enumerate(tags[:30], 1):
            if isinstance(tag_info, dict):
                tag = tag_info.get('tag', tag_info.get('name', 'unknown'))
                confidence = tag_info.get('confidence', 'N/A')
                score = tag_info.get('score', 0)
                print(f"  {i:2d}. {tag:30s} (confidence: {confidence:6s}, score: {score:.4f})")
            else:
                print(f"  {i:2d}. {tag_info}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

    # Success criteria
    if len(tags) >= 10:
        print("\n[SUCCESS] Generated 10+ tags - CLIP is working correctly!")
    elif len(tags) >= 1:
        print(f"\n[WARNING] Only generated {len(tags)} tags - May need tuning")
    else:
        print("\n[FAIL] No tags generated - Check model and vocabulary")

if __name__ == '__main__':
    test_single_image()
