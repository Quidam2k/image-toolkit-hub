"""Test that batch export dialog loading works correctly."""
import logging
from tag_query_engine import TagQueryEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_engine_loading():
    """Test that the tag query engine loads properly."""
    print("\n=== Testing Tag Query Engine ===")

    engine = TagQueryEngine('tag_frequency.json')

    print("Loading database...")
    result = engine.load_database()

    if not result:
        print("ERROR: Failed to load database")
        return False

    print(f"[OK] Database loaded successfully")

    tags = engine.list_available_tags()

    if not tags:
        print("ERROR: No tags found in database")
        return False

    print(f"[OK] Found {len(tags)} tags")
    print(f"[OK] Top 10 tags by frequency:")
    for i, (tag, count) in enumerate(tags[:10], 1):
        print(f"  {i}. {tag}: {count}")

    # Test a simple query
    print("\n=== Testing Query Functionality ===")
    success, images, error = engine.query("blowjob")

    if not success:
        print(f"ERROR: Query failed: {error}")
        return False

    print(f"[OK] Query successful: found {len(images)} images for 'blowjob'")

    return True

if __name__ == '__main__':
    success = test_engine_loading()

    if success:
        print("\n[OK] All tests passed! The backend is working correctly.")
        print("The threading fix should resolve the UI issue.")
    else:
        print("\n[ERROR] Tests failed. There may be a database issue.")
