"""
Test Distribution Optimizer

Tests the balanced distribution algorithm.
"""

import os
import json
from distribution_optimizer import DistributionOptimizer


def test_distribution_optimizer():
    """Test the distribution optimizer."""
    print("\n" + "=" * 80)
    print("TEST: Distribution Optimizer")
    print("=" * 80)

    # Create test terms from the actual auto_sorted folders
    print("\n[Step 1] Finding auto-sorted folders...")

    test_terms = []
    auto_sorted_base = './auto_sorted'

    if os.path.isdir(auto_sorted_base):
        for folder_name in sorted(os.listdir(auto_sorted_base)):
            folder_path = os.path.join(auto_sorted_base, folder_name)
            if os.path.isdir(folder_path):
                test_terms.append({
                    'term': folder_name,
                    'folder_name': folder_name,
                    'folder_path': folder_path,
                })
        print(f"[OK] Found {len(test_terms)} folders")
    else:
        print(f"[SKIP] auto_sorted folder not found at {auto_sorted_base}")
        print("[INFO] Creating mock data for testing...")

        # Mock data for testing
        test_terms = [
            {'term': 'blowjob', 'folder_name': 'blowjob', 'folder_path': './mock_blowjob'},
            {'term': 'succubus', 'folder_name': 'succubus', 'folder_path': './mock_succubus'},
            {'term': 'elf', 'folder_name': 'elf', 'folder_path': './mock_elf'},
        ]

    try:
        # Initialize optimizer
        print("\n[Step 2] Initializing optimizer...")
        optimizer = DistributionOptimizer()
        print("[OK] Optimizer initialized")

        # Load folder sizes
        print("\n[Step 3] Loading current folder sizes...")
        folder_sizes = optimizer.load_folder_sizes(test_terms)
        print("[OK] Folder sizes loaded:")
        for term_name, size in sorted(folder_sizes.items(), key=lambda x: x[1], reverse=True):
            print(f"      {term_name}: {size} images")

        # Calculate target size
        print("\n[Step 4] Calculating target distribution...")
        target_size = optimizer.calculate_target_size(test_terms)
        total_images = sum(folder_sizes.values())
        print(f"[OK] Target size: {target_size:.0f} images per folder")
        print(f"     Total images: {total_images}")
        print(f"     Number of folders: {len(test_terms)}")

        # Test balance scoring
        print("\n[Step 5] Testing balance scoring...")
        print("[INFO] Scores for each term:")
        for term in test_terms:
            term_name = term['term']
            size = folder_sizes.get(term_name, 0)
            score = optimizer.calculate_balance_score(term_name, size, target_size)
            ratio = size / target_size if target_size > 0 else 0
            print(f"      {term_name:20s}: score={score:6.1f}, size={size:4d}, ratio={ratio:.2f}x")

        # Test term selection (mock matching)
        print("\n[Step 6] Testing term selection for image with multiple matches...")

        # Simulate an image that matches multiple tags
        matching_terms = test_terms[:3]  # Assume it matches first 3 terms
        print(f"[INFO] Image matches {len(matching_terms)} terms")

        scored = optimizer.score_matching_terms(matching_terms, folder_sizes, target_size)
        print("[INFO] Scored terms (by priority and balance):")
        for i, scored_term in enumerate(scored, 1):
            print(
                f"      {i}. {scored_term['term_name']:20s}: "
                f"score={scored_term['total_score']:6.1f} "
                f"(base={scored_term['base_score']:3.0f}, "
                f"balance={scored_term['balance_bonus']:+6.1f})"
            )

        # Test destination selection
        print("\n[Step 7] Testing destination selection (balanced)...")
        selected_destinations = optimizer.select_balanced_destinations(
            matching_terms, folder_sizes, target_size, max_folders=2
        )
        print(f"[OK] Selected {len(selected_destinations)} destinations:")
        for dest in selected_destinations:
            term_name = dest.get('term', dest.get('folder_name', 'unknown'))
            print(f"      - {term_name}")

        # Generate balance report
        print("\n[Step 8] Generating balance report...")
        report = optimizer.generate_balance_report(test_terms, output_file='balance_report_test.json')
        print("[OK] Report generated")

        # Print report
        optimizer.print_balance_report(report)

        print("\n[SUCCESS] All tests passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_distribution_optimizer()
    exit(0 if success else 1)
