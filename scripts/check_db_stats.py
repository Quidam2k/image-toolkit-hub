"""Quick script to check database statistics."""
from tag_database import TagDatabase

db = TagDatabase('tag_database.db')
stats = db.get_statistics()

print("\n" + "="*60)
print("TAG DATABASE STATISTICS")
print("="*60)

print(f"\nTotal tags: {stats['total_tags']}")
print(f"Total images: {stats['total_images']}")
print(f"Total relationships: {stats['total_relationships']}")
print(f"Favorite tags: {stats['favorite_tags']}")
print(f"Hidden tags: {stats.get('hidden_tags', 0)}")

print("\nTop 10 tags:")
for i, (tag, count) in enumerate(stats['top_tags'], 1):
    print(f"  {i}. {tag}: {count}")

db.close()

print("\n" + "="*60)
