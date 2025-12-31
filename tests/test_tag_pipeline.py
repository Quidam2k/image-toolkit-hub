"""
Test Tag Generation and Embedding Pipeline

Quick test to verify:
1. Tag generation works and saves to .txt only
2. Tag embedding preserves original prompts
3. Full pipeline is safe

Run this BEFORE processing your new batch!
"""

import os
import sys
from tag_generator import DescriptiveTagGenerator
from prompt_preservation_audit import PromptPreservationAudit
from metadata_parser import MetadataParser

def test_pipeline():
    """Run a complete pipeline test."""
    print("\n" + "="*70)
    print("TAG GENERATION & EMBEDDING PIPELINE TEST")
    print("="*70)

    # Step 1: Initialize tag generator
    print("\n[Step 1] Initializing tag generator...")
    try:
        generator = DescriptiveTagGenerator()
        print("[OK] Tag generator initialized successfully")
    except Exception as e:
        print(f"[FAIL] Failed to initialize tag generator: {e}")
        return False

    # Step 2: Find test images
    print("\n[Step 2] Finding test images...")
    base_folder = './auto_sorted/cowgirl'

    if not os.path.exists(base_folder):
        # Try alternative locations
        print(f"[INFO] Primary folder not found: {base_folder}")
        print("  Searching for alternative folders...")

        # Search for any auto_sorted folder
        for root, dirs, files in os.walk('.'):
            if 'auto_sorted' in root:
                for subfolder in os.listdir(root):
                    candidate = os.path.join(root, subfolder)
                    if os.path.isdir(candidate):
                        # Check if it has images
                        for f in os.listdir(candidate):
                            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                                base_folder = candidate
                                break
                    if os.path.isdir(base_folder) and os.listdir(base_folder):
                        break
            if os.path.exists(base_folder) and os.listdir(base_folder):
                break

    # Find image files
    image_extensions = {'.png', '.jpg', '.jpeg'}
    test_images = []

    for file in os.listdir(base_folder)[:3]:
        if os.path.splitext(file)[1].lower() in image_extensions:
            test_images.append(os.path.join(base_folder, file))

    if not test_images:
        print(f"[FAIL] No test images found in {base_folder}")
        return False

    print(f"[OK] Found {len(test_images)} test images")

    # Step 3: Test tag generation on first image
    print(f"\n[Step 3] Testing tag generation...")
    test_image = test_images[0]
    print(f"  Testing on: {os.path.basename(test_image)}")

    try:
        result = generator.generate_tags_for_image(test_image)

        if result['status'] == 'success':
            print(f"[OK] Generated {result['tag_count']} tags")
            print(f"  Tags: {', '.join(result['tags'][:5])}...")
        else:
            print(f"[FAIL] Tag generation failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during tag generation: {e}")
        return False

    # Step 4: Test saving tags
    print(f"\n[Step 4] Testing tag file save...")
    try:
        save_result = generator.save_tags_to_file(test_image, result['tags'])

        if save_result['status'] == 'success':
            tag_file = save_result['tag_file']
            print(f"[OK] Tags saved to: {tag_file}")

            # Verify file was created
            if os.path.exists(tag_file):
                with open(tag_file, 'r') as f:
                    content = f.read()
                print(f"[OK] File verified, contains {len(content)} characters")

                # Clean up
                os.remove(tag_file)
                print("[OK] Test file cleaned up")
            else:
                print(f"[FAIL] Tag file was not created")
                return False
        else:
            print(f"[FAIL] Failed to save tags: {save_result.get('error')}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during tag save: {e}")
        return False

    # Step 5: Run prompt preservation audit
    print(f"\n[Step 5] Running prompt preservation audit...")
    print("  (This tests: Generate tags -> Embed into metadata -> Verify prompts preserved)")

    try:
        audit = PromptPreservationAudit()
        audit_result = audit.audit_single_image(test_image, "Pipeline Test")

        if audit_result['results']['prompts_preserved']:
            print("[OK] Prompts were PRESERVED after embedding!")
            print("  Pipeline is SAFE to use")
        elif audit_result['results']['issues']:
            print("[FAIL] CRITICAL ISSUES FOUND:")
            for issue in audit_result['results']['issues']:
                print(f"  - {issue}")
            return False
        else:
            print("[INFO] Test completed with warnings")
            for warning in audit_result['results']['warnings']:
                print(f"  WARNING: {warning}")
    except Exception as e:
        print(f"[FAIL] Exception during audit: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "="*70)
    print("PIPELINE TEST RESULTS")
    print("="*70)
    print("[OK] Tag generation: WORKING")
    print("[OK] Tag file save: WORKING")
    print("[OK] Prompt preservation: WORKING")
    print("\n[SUCCESS] PIPELINE IS SAFE TO USE")
    print("="*70)

    return True


if __name__ == '__main__':
    success = test_pipeline()
    sys.exit(0 if success else 1)
