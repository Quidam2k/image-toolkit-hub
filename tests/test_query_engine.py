"""
Test suite for Tag Query Engine.

Tests:
  - Single tag queries
  - AND combinations
  - OR combinations
  - NOT exclusions
  - Complex queries
  - Error handling
  - Performance
"""

import logging
import sys
import time
from tag_query_engine import TagQueryEngine


logging.basicConfig(level=logging.WARNING)


def test_load_database():
    """Test database loading."""
    print("TEST: Load database...")
    engine = TagQueryEngine()
    assert engine.load_database(), "Failed to load database"
    assert engine.database is not None, "Database is None"
    assert len(engine.tags_db) > 0, "No tags loaded"
    assert len(engine.image_index) > 0, "No images indexed"
    print("  [OK] Database loaded successfully")


def test_list_available_tags():
    """Test listing available tags."""
    print("TEST: List available tags...")
    engine = TagQueryEngine()
    engine.load_database()

    tags = engine.list_available_tags()
    assert len(tags) == 80, f"Expected 80 tags, got {len(tags)}"
    assert tags[0][0] == 'blowjob', "First tag should be blowjob"
    assert tags[0][1] == 2921, f"Blowjob count should be 2921, got {tags[0][1]}"
    print(f"  [OK] Listed {len(tags)} tags")


def test_single_tag_query():
    """Test single tag query."""
    print("TEST: Single tag query...")
    engine = TagQueryEngine()
    engine.load_database()

    success, images, error = engine.query("blowjob")
    assert success, f"Query failed: {error}"
    assert len(images) == 2847, f"Expected 2847 images, got {len(images)}"
    assert all(isinstance(img, str) for img in images), "Not all results are strings"
    print(f"  [OK] Found {len(images)} images with 'blowjob' tag")


def test_and_query():
    """Test AND query."""
    print("TEST: AND query...")
    engine = TagQueryEngine()
    engine.load_database()

    success, images, error = engine.query("blowjob,succubus")
    assert success, f"Query failed: {error}"
    assert len(images) == 128, f"Expected 128 images, got {len(images)}"

    # Verify all results have both tags
    blowjob_only = engine.find_matching_images(
        engine.parse_query("blowjob")
    )
    succubus_only = engine.find_matching_images(
        engine.parse_query("succubus")
    )

    assert len(images) <= min(len(blowjob_only), len(succubus_only)), \
        "AND result should have fewer images than single tags"

    print(f"  [OK] AND query returned {len(images)} images")


def test_or_query():
    """Test OR query."""
    print("TEST: OR query...")
    engine = TagQueryEngine()
    engine.load_database()

    success, images, error = engine.query("blowjob|succubus")
    assert success, f"Query failed: {error}"
    assert len(images) == 4319, f"Expected 4319 images, got {len(images)}"

    # Verify OR returns more than individual
    blowjob = engine.find_matching_images(
        engine.parse_query("blowjob")
    )
    succubus = engine.find_matching_images(
        engine.parse_query("succubus")
    )

    expected_min = max(len(blowjob), len(succubus))
    assert len(images) >= expected_min, \
        f"OR result should have at least {expected_min} images"

    print(f"  [OK] OR query returned {len(images)} images")


def test_not_query():
    """Test NOT (exclusion) query."""
    print("TEST: NOT query...")
    engine = TagQueryEngine()
    engine.load_database()

    success, images, error = engine.query("blowjob,!elf")
    assert success, f"Query failed: {error}"
    assert len(images) == 2716, f"Expected 2716 images, got {len(images)}"

    # Verify no excluded tag
    elf_images = set(engine.find_matching_images(
        engine.parse_query("elf")
    ))
    assert not any(img in elf_images for img in images), \
        "Result contains excluded tag"

    print(f"  [OK] NOT query returned {len(images)} images")


def test_complex_query():
    """Test complex query."""
    print("TEST: Complex query...")
    engine = TagQueryEngine()
    engine.load_database()

    # (blowjob OR succubus) AND NOT elf
    success, images, error = engine.query("(blowjob|succubus),!elf")
    assert success, f"Query failed: {error}"

    # Verify no excluded tag
    elf_images = set(engine.find_matching_images(
        engine.parse_query("elf")
    ))
    assert not any(img in elf_images for img in images), \
        "Complex query result contains excluded tag"

    print(f"  [OK] Complex query returned {len(images)} images")


def test_parse_query_formats():
    """Test different query formats."""
    print("TEST: Parse query formats...")
    engine = TagQueryEngine()
    engine.load_database()

    formats = [
        ("blowjob", "single tag"),
        ("blowjob,succubus", "AND format"),
        ("blowjob|succubus", "OR format"),
        ("blowjob,!elf", "NOT format"),
    ]

    for query, desc in formats:
        parsed = engine.parse_query(query)
        assert parsed is not None, f"Failed to parse {desc}: {query}"
        assert 'operator' in parsed, f"Missing operator in {desc}"
        assert 'include_tags' in parsed, f"Missing include_tags in {desc}"

    print(f"  [OK] Parsed {len(formats)} query formats")


def test_validate_query():
    """Test query validation."""
    print("TEST: Validate query...")
    engine = TagQueryEngine()
    engine.load_database()

    # Valid query
    is_valid, error = engine.validate_query("blowjob")
    assert is_valid, f"Valid query rejected: {error}"

    # Invalid query - unknown tag
    is_valid, error = engine.validate_query("nonexistent_tag_xyz")
    assert not is_valid, "Invalid query accepted"
    assert error is not None, "No error message"

    print("  [OK] Query validation working")


def test_case_insensitivity():
    """Test case insensitivity."""
    print("TEST: Case insensitivity...")
    engine = TagQueryEngine()
    engine.load_database()

    # These should all return the same results
    queries = [
        "blowjob",
        "BLOWJOB",
        "BlowJob",
        "BLoWjOb",
    ]

    results = []
    for query in queries:
        success, images, error = engine.query(query)
        assert success, f"Query failed: {query}"
        results.append(set(images))

    # All should be identical
    for i, result_set in enumerate(results[1:], 1):
        assert result_set == results[0], f"Query {i} returned different results"

    print("  [OK] Case insensitivity verified")


def test_empty_query():
    """Test error handling for empty query."""
    print("TEST: Empty query error handling...")
    engine = TagQueryEngine()
    engine.load_database()

    success, images, error = engine.query("")
    assert not success, "Empty query should fail"
    assert error is not None, "No error message for empty query"

    print("  [OK] Empty query rejected with error")


def test_query_performance():
    """Test query performance."""
    print("TEST: Query performance...")
    engine = TagQueryEngine()
    engine.load_database()

    # Simple query should be very fast
    start = time.time()
    success, images, error = engine.query("blowjob")
    simple_time = time.time() - start
    assert simple_time < 0.1, f"Simple query too slow: {simple_time:.3f}s"

    # Complex query should still be reasonable
    start = time.time()
    success, images, error = engine.query("(blowjob|succubus),!elf")
    complex_time = time.time() - start
    assert complex_time < 0.5, f"Complex query too slow: {complex_time:.3f}s"

    print(f"  [OK] Simple query: {simple_time*1000:.1f}ms")
    print(f"  [OK] Complex query: {complex_time*1000:.1f}ms")


def run_all_tests():
    """Run complete test suite."""
    print("=" * 70)
    print("PHASE 4: QUERY ENGINE - TEST SUITE")
    print("=" * 70)
    print()

    tests = [
        test_load_database,
        test_list_available_tags,
        test_single_tag_query,
        test_and_query,
        test_or_query,
        test_not_query,
        test_complex_query,
        test_parse_query_formats,
        test_validate_query,
        test_case_insensitivity,
        test_empty_query,
        test_query_performance,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed += 1
        print()

    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
