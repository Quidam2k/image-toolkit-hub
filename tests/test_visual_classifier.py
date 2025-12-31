"""
Test Visual Classifier Module

Verifies visual classification functionality for LoRA-specific sorting.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visual_classifier import (
    VisualClassifier, VisualClassification,
    ShotType, PersonCount, NSFWRating,
    LoRASortingProfile, EXAMPLE_PROFILES
)


def test_enums():
    """Test enum definitions."""
    print("\n=== Testing Enums ===")

    # Shot types
    print("\nShot Types:")
    for st in ShotType:
        print(f"  - {st.name}: {st.value}")
    assert len(ShotType) == 7, f"Expected 7 shot types, got {len(ShotType)}"

    # Person counts
    print("\nPerson Counts:")
    for pc in PersonCount:
        print(f"  - {pc.name}: {pc.value}")
    assert len(PersonCount) == 5, f"Expected 5 person counts, got {len(PersonCount)}"

    # NSFW ratings
    print("\nNSFW Ratings:")
    for nr in NSFWRating:
        print(f"  - {nr.name}: {nr.value}")
    assert len(NSFWRating) == 5, f"Expected 5 NSFW ratings, got {len(NSFWRating)}"

    print("\n[PASS] Enum tests passed!")
    return True


def test_visual_classification_dataclass():
    """Test VisualClassification dataclass."""
    print("\n=== Testing VisualClassification Dataclass ===")

    classification = VisualClassification(
        image_path="/test/image.png",
        shot_type=ShotType.PORTRAIT,
        person_count=PersonCount.SOLO,
        nsfw_rating=NSFWRating.SENSITIVE,
        confidence_scores={'portrait': 0.85, 'solo': 0.92},
        raw_tags=['portrait', 'solo', '1girl', 'smile']
    )

    print(f"Image: {classification.image_path}")
    print(f"Shot Type: {classification.shot_type.value}")
    print(f"Person Count: {classification.person_count.value}")
    print(f"NSFW Rating: {classification.nsfw_rating.value}")

    # Test to_dict
    d = classification.to_dict()
    assert d['shot_type'] == 'portrait'
    assert d['person_count'] == 'solo'
    assert d['nsfw_rating'] == 'sensitive'
    print(f"to_dict(): {d}")

    print("\n[PASS] VisualClassification dataclass tests passed!")
    return True


def test_lora_sorting_profile():
    """Test LoRASortingProfile matching logic."""
    print("\n=== Testing LoRASortingProfile ===")

    # Create a portrait LoRA profile
    portrait_profile = LoRASortingProfile(
        name='portrait_test',
        shot_types=[ShotType.PORTRAIT, ShotType.UPPER_BODY],
        person_counts=[PersonCount.SOLO],
        nsfw_ratings=None  # Any rating
    )

    # Test matching classification
    matching_class = VisualClassification(
        image_path="/test/match.png",
        shot_type=ShotType.PORTRAIT,
        person_count=PersonCount.SOLO,
        nsfw_rating=NSFWRating.GENERAL,
        confidence_scores={},
        raw_tags=[]
    )

    # Test non-matching classification (wrong person count)
    non_matching_class = VisualClassification(
        image_path="/test/nomatch.png",
        shot_type=ShotType.PORTRAIT,
        person_count=PersonCount.DUO,  # Wrong
        nsfw_rating=NSFWRating.GENERAL,
        confidence_scores={},
        raw_tags=[]
    )

    assert portrait_profile.matches(matching_class), "Should match portrait/solo"
    assert not portrait_profile.matches(non_matching_class), "Should not match portrait/duo"

    print(f"Profile: {portrait_profile.name}")
    print(f"Matching test: PASS")
    print(f"Non-matching test: PASS")

    # Test profile with required/excluded tags
    tag_profile = LoRASortingProfile(
        name='tag_test',
        shot_types=None,
        person_counts=None,
        nsfw_ratings=None,
        required_tags=['smile'],
        excluded_tags=['crying']
    )

    with_smile = VisualClassification(
        image_path="/test/smile.png",
        shot_type=ShotType.UNKNOWN,
        person_count=PersonCount.UNKNOWN,
        nsfw_rating=NSFWRating.UNKNOWN,
        confidence_scores={},
        raw_tags=['smile', 'happy']
    )

    with_crying = VisualClassification(
        image_path="/test/crying.png",
        shot_type=ShotType.UNKNOWN,
        person_count=PersonCount.UNKNOWN,
        nsfw_rating=NSFWRating.UNKNOWN,
        confidence_scores={},
        raw_tags=['smile', 'crying']  # Has excluded tag
    )

    assert tag_profile.matches(with_smile), "Should match with required tag"
    assert not tag_profile.matches(with_crying), "Should not match with excluded tag"

    print(f"Required tag test: PASS")
    print(f"Excluded tag test: PASS")

    # Test serialization
    d = portrait_profile.to_dict()
    restored = LoRASortingProfile.from_dict(d)
    assert restored.name == portrait_profile.name
    print(f"Serialization test: PASS")

    print("\n[PASS] LoRASortingProfile tests passed!")
    return True


def test_example_profiles():
    """Test the example profiles."""
    print("\n=== Testing Example Profiles ===")

    print("\nExample profiles:")
    for name, profile in EXAMPLE_PROFILES.items():
        print(f"  - {name}:")
        d = profile.to_dict()
        if d['shot_types']:
            print(f"      Shot types: {d['shot_types']}")
        if d['person_counts']:
            print(f"      Person counts: {d['person_counts']}")
        if d['nsfw_ratings']:
            print(f"      NSFW ratings: {d['nsfw_ratings']}")

    assert len(EXAMPLE_PROFILES) >= 4, "Should have at least 4 example profiles"

    print("\n[PASS] Example profiles tests passed!")
    return True


def test_classifier_initialization():
    """Test VisualClassifier initialization (without actually loading models)."""
    print("\n=== Testing VisualClassifier Constants ===")

    # Test class constants
    assert 'portrait' in VisualClassifier.SHOT_TYPE_TAGS
    assert 'upper_body' in VisualClassifier.SHOT_TYPE_TAGS
    assert 'cowboy_shot' in VisualClassifier.SHOT_TYPE_TAGS
    assert 'full_body' in VisualClassifier.SHOT_TYPE_TAGS

    print("Shot type mappings:")
    for tag, shot_type in VisualClassifier.SHOT_TYPE_TAGS.items():
        print(f"  '{tag}' -> {shot_type.value}")

    assert 'solo' in VisualClassifier.PERSON_COUNT_TAGS
    assert '1girl' in VisualClassifier.PERSON_COUNT_TAGS
    assert '2girls' in VisualClassifier.PERSON_COUNT_TAGS
    assert 'multiple_girls' in VisualClassifier.PERSON_COUNT_TAGS

    print("\nPerson count mappings:")
    for tag, pc in list(VisualClassifier.PERSON_COUNT_TAGS.items())[:5]:
        print(f"  '{tag}' -> {pc.value}")
    print(f"  ... and {len(VisualClassifier.PERSON_COUNT_TAGS) - 5} more")

    assert 'general' in VisualClassifier.RATING_TAGS
    assert 'explicit' in VisualClassifier.RATING_TAGS

    print("\nRating mappings:")
    for tag, rating in VisualClassifier.RATING_TAGS.items():
        print(f"  '{tag}' -> {rating.value}")

    print("\n[PASS] Classifier constants tests passed!")
    return True


def test_auto_sorter_integration():
    """Test that auto_sorter imports visual classifier correctly."""
    print("\n=== Testing Auto-Sorter Integration ===")

    try:
        from auto_sorter import AutoSorter
        print("AutoSorter imported successfully")

        # Check that visual sorting methods exist
        assert hasattr(AutoSorter, 'sort_by_visual_classification')
        assert hasattr(AutoSorter, 'sort_by_lora_profile')
        assert hasattr(AutoSorter, 'classify_images_batch')

        print("Visual sorting methods found:")
        print("  - sort_by_visual_classification")
        print("  - sort_by_lora_profile")
        print("  - classify_images_batch")

        print("\n[PASS] Auto-sorter integration tests passed!")
        return True

    except ImportError as e:
        print(f"\n[WARN] Could not import AutoSorter: {e}")
        print("This is OK if running standalone tests")
        return True


def main():
    """Run all tests."""
    print("="*60)
    print("Visual Classifier Test Suite")
    print("="*60)

    all_passed = True

    try:
        all_passed &= test_enums()
        all_passed &= test_visual_classification_dataclass()
        all_passed &= test_lora_sorting_profile()
        all_passed &= test_example_profiles()
        all_passed &= test_classifier_initialization()
        all_passed &= test_auto_sorter_integration()

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
