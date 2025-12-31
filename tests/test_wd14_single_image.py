"""
Test WD14 tag generation on a single image to verify model and integration are working.
"""

import os
from pathlib import Path
from wd14_tagger import WD14Tagger

def test_single_image():
    print("="*70)
    print("TESTING WD14 TAG GENERATION ON SINGLE IMAGE")
    print("="*70)

    # Find a test image from master_images
    master_images = Path('master_images')
    if not master_images.exists():
        print("ERROR: master_images folder not found")
        return

    # Get first PNG file
    test_images = list(master_images.glob('*.png'))[:1]
    if not test_images:
        # Try JPG if no PNG
        test_images = list(master_images.glob('*.jpg'))[:1]

    if not test_images:
        print("ERROR: No image files found in master_images/")
        return

    test_image = test_images[0]
    print(f"\nTest image: {test_image.name}")
    print(f"Path: {test_image}")

    # Initialize WD14 tagger
    print("\n" + "-"*70)
    print("Initializing WD14 tagger...")
    print("-"*70)
    try:
        tagger = WD14Tagger(
            model_path='models/wd14/model.onnx',
            tags_path='models/wd14/selected_tags.csv',
            threshold=0.35
        )
    except Exception as e:
        print(f"ERROR initializing tagger: {e}")
        import traceback
        traceback.print_exc()
        return

    if not tagger.loaded:
        print("ERROR: WD14 model not loaded properly")
        print("Check that model files exist:")
        print(f"  Model: {tagger.model_path}")
        print(f"  Tags:  {tagger.tags_path}")
        return

    # Generate tags
    print("\n" + "-"*70)
    print("Generating tags for image...")
    print("-"*70)
    try:
        result = tagger.generate_tags_for_image(str(test_image), threshold=0.35)
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
    confidences = result.get('confidences', {})
    ratings = result.get('ratings', {})

    print(f"\nTotal tags generated: {len(tags)}")
    print(f"Threshold: {result.get('threshold', 0.35)}")

    # Display ratings
    if ratings:
        print("\n" + "-"*70)
        print("RATINGS:")
        print("-"*70)
        for rating, conf in sorted(ratings.items(), key=lambda x: x[1], reverse=True):
            print(f"  {rating:20s} {conf:.4f} ({conf*100:.1f}%)")

    # Display top tags
    if tags:
        print("\n" + "-"*70)
        print("TOP 50 TAGS (by confidence):")
        print("-"*70)

        # Sort tags by confidence
        sorted_tags = sorted(
            [(tag, confidences.get(tag, 0.0)) for tag in tags],
            key=lambda x: x[1],
            reverse=True
        )

        for i, (tag, conf) in enumerate(sorted_tags[:50], 1):
            print(f"  {i:2d}. {tag:40s} {conf:.4f} ({conf*100:.1f}%)")

        # Show all tags as comma-separated (what would be written to .txt)
        print("\n" + "-"*70)
        print("ALL TAGS (as they would appear in .txt file):")
        print("-"*70)
        print(", ".join(tags))

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

    # Success criteria
    if len(tags) >= 30:
        print(f"\n[SUCCESS] Generated {len(tags)} tags - WD14 is working correctly!")
    elif len(tags) >= 10:
        print(f"\n[WARNING] Only generated {len(tags)} tags - May need lower threshold")
    else:
        print(f"\n[FAIL] Only {len(tags)} tags generated - Check model and threshold")

    # Test saving to file
    print("\n" + "-"*70)
    print("Testing tag file save...")
    print("-"*70)
    try:
        save_result = tagger.save_tags_to_file(str(test_image), tags)
        if save_result['status'] == 'success':
            print(f"[SUCCESS] Tags saved to: {save_result['tag_file']}")
            print(f"           Tag count: {save_result['tag_count']}")
        else:
            print(f"[FAIL] Failed to save tags: {save_result.get('error')}")
    except Exception as e:
        print(f"[FAIL] Exception saving tags: {e}")

if __name__ == '__main__':
    test_single_image()
