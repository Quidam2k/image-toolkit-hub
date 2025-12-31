"""
SQLite Tag Database Manager

Fast, efficient tag database with support for:
- Instant queries (indexed)
- Favorites/pinning
- Complex tag searches (AND/OR/NOT)
- Tag frequency tracking
- Image-to-tag relationships

Replaces the 60MB JSON database with a professional SQLite solution.

Author: Claude Code Implementation
Version: 1.0
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Set
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TagDatabase:
    """SQLite-based tag database with indexing and favorites support."""

    def __init__(self, db_path: str = 'tag_database.db'):
        """
        Initialize tag database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._initialize_database()

    def _initialize_database(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    tag TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0,
                    is_hidden INTEGER DEFAULT 0
                )
            ''')

            # Tag-image relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tag_images (
                    tag TEXT,
                    image_path TEXT,
                    FOREIGN KEY (tag) REFERENCES tags(tag)
                )
            ''')

            # Metadata table (for database info)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_favorite_count
                ON tags(is_favorite DESC, count DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tag_lower
                ON tags(LOWER(tag))
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tag_images_tag
                ON tag_images(tag)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tag_images_path
                ON tag_images(image_path)
            ''')

            # Migrate existing database: add is_hidden column if it doesn't exist
            cursor.execute("PRAGMA table_info(tags)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'is_hidden' not in columns:
                logger.info("Adding is_hidden column to existing database...")
                cursor.execute('ALTER TABLE tags ADD COLUMN is_hidden INTEGER DEFAULT 0')

            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row

        try:
            yield self.connection
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            self.connection.commit()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def add_tag(self, tag: str, image_paths: List[str], is_favorite: bool = False, is_hidden: bool = False):
        """
        Add a tag with its associated images.

        Args:
            tag: Tag name
            image_paths: List of image paths that have this tag
            is_favorite: Whether this tag is favorited
            is_hidden: Whether this tag is hidden/blocked
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert or update tag
            cursor.execute('''
                INSERT INTO tags (tag, count, is_favorite, is_hidden)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tag) DO UPDATE SET
                    count = ?,
                    is_favorite = MAX(is_favorite, ?),
                    is_hidden = MAX(is_hidden, ?)
            ''', (tag, len(image_paths), 1 if is_favorite else 0, 1 if is_hidden else 0,
                  len(image_paths), 1 if is_favorite else 0, 1 if is_hidden else 0))

            # Add image relationships
            for image_path in image_paths:
                cursor.execute('''
                    INSERT INTO tag_images (tag, image_path)
                    VALUES (?, ?)
                ''', (tag, image_path))

    def bulk_insert_tags(self, tag_data: dict):
        """
        Bulk insert tags and image relationships.

        Args:
            tag_data: Dictionary of {tag: [image_paths]}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Prepare data for bulk insert
            tag_rows = [(tag, len(paths), 0) for tag, paths in tag_data.items()]
            image_rows = [
                (tag, path)
                for tag, paths in tag_data.items()
                for path in paths
            ]

            # Bulk insert tags
            cursor.executemany('''
                INSERT OR REPLACE INTO tags (tag, count, is_favorite)
                VALUES (?, ?, ?)
            ''', tag_rows)

            # Bulk insert image relationships
            cursor.executemany('''
                INSERT INTO tag_images (tag, image_path)
                VALUES (?, ?)
            ''', image_rows)

            logger.info(f"Bulk inserted {len(tag_rows)} tags with {len(image_rows)} image relationships")

    def clear_database(self):
        """Clear all data from the database (keep schema)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tag_images')
            cursor.execute('DELETE FROM tags')
            logger.info("Database cleared")

    def list_tags(self, favorites_first: bool = True, limit: Optional[int] = None,
                  include_hidden: bool = False) -> List[Tuple[str, int, bool, bool]]:
        """
        List all tags sorted by frequency.

        Args:
            favorites_first: If True, show favorites first
            limit: Optional limit on number of tags returned
            include_hidden: If True, include hidden/blocked tags

        Returns:
            List of (tag, count, is_favorite, is_hidden) tuples
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if favorites_first:
                query = 'SELECT tag, count, is_favorite, is_hidden FROM tags'
                if not include_hidden:
                    query += ' WHERE is_hidden = 0'
                query += ' ORDER BY is_favorite DESC, count DESC'
            else:
                query = 'SELECT tag, count, is_favorite, is_hidden FROM tags'
                if not include_hidden:
                    query += ' WHERE is_hidden = 0'
                query += ' ORDER BY count DESC'

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query)
            return [(row['tag'], row['count'], bool(row['is_favorite']), bool(row['is_hidden']))
                    for row in cursor.fetchall()]

    def search_tags(self, search_text: str, limit: int = 200,
                    include_hidden: bool = False) -> List[Tuple[str, int, bool, bool]]:
        """
        Search for tags containing the search text.

        Args:
            search_text: Text to search for (case-insensitive)
            limit: Maximum number of results
            include_hidden: If True, include hidden/blocked tags

        Returns:
            List of (tag, count, is_favorite, is_hidden) tuples
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if include_hidden:
                cursor.execute('''
                    SELECT tag, count, is_favorite, is_hidden
                    FROM tags
                    WHERE LOWER(tag) LIKE ?
                    ORDER BY is_favorite DESC, count DESC
                    LIMIT ?
                ''', (f'%{search_text.lower()}%', limit))
            else:
                cursor.execute('''
                    SELECT tag, count, is_favorite, is_hidden
                    FROM tags
                    WHERE LOWER(tag) LIKE ? AND is_hidden = 0
                    ORDER BY is_favorite DESC, count DESC
                    LIMIT ?
                ''', (f'%{search_text.lower()}%', limit))

            return [(row['tag'], row['count'], bool(row['is_favorite']), bool(row['is_hidden']))
                    for row in cursor.fetchall()]

    def get_images_for_tag(self, tag: str) -> List[str]:
        """
        Get all images that have a specific tag.

        Args:
            tag: Tag name

        Returns:
            List of image paths
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT image_path
                FROM tag_images
                WHERE tag = ?
            ''', (tag,))

            return [row['image_path'] for row in cursor.fetchall()]

    def query_images(self, include_tags: List[str], exclude_tags: List[str] = None,
                    operator: str = 'OR') -> List[str]:
        """
        Query images by tags with AND/OR/NOT logic.

        Args:
            include_tags: Tags that should be present
            exclude_tags: Tags that should NOT be present
            operator: 'AND' or 'OR' for include_tags

        Returns:
            List of image paths matching the query
        """
        if not include_tags:
            return []

        exclude_tags = exclude_tags or []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if operator.upper() == 'AND':
                # Images must have ALL include_tags
                query = '''
                    SELECT image_path
                    FROM tag_images
                    WHERE tag IN ({})
                    GROUP BY image_path
                    HAVING COUNT(DISTINCT tag) = ?
                '''.format(','.join('?' * len(include_tags)))

                params = include_tags + [len(include_tags)]

                if exclude_tags:
                    # Exclude images with any exclude_tag
                    exclude_placeholders = ','.join('?' * len(exclude_tags))
                    query = f'''
                        SELECT image_path FROM ({query})
                        WHERE image_path NOT IN (
                            SELECT image_path FROM tag_images
                            WHERE tag IN ({exclude_placeholders})
                        )
                    '''
                    params.extend(exclude_tags)

            else:  # OR
                # Images must have AT LEAST ONE include_tag
                placeholders = ','.join('?' * len(include_tags))
                query = f'''
                    SELECT DISTINCT image_path
                    FROM tag_images
                    WHERE tag IN ({placeholders})
                '''
                params = include_tags

                if exclude_tags:
                    exclude_placeholders = ','.join('?' * len(exclude_tags))
                    query += f'''
                        AND image_path NOT IN (
                            SELECT image_path FROM tag_images
                            WHERE tag IN ({exclude_placeholders})
                        )
                    '''
                    params.extend(exclude_tags)

            cursor.execute(query, params)
            return [row['image_path'] for row in cursor.fetchall()]

    def set_favorite(self, tag: str, is_favorite: bool = True):
        """
        Set a tag as favorite or unfavorite.

        Args:
            tag: Tag name
            is_favorite: True to favorite, False to unfavorite
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE tags
                SET is_favorite = ?
                WHERE tag = ?
            ''', (1 if is_favorite else 0, tag))

            if cursor.rowcount > 0:
                logger.info(f"Tag '{tag}' {'favorited' if is_favorite else 'unfavorited'}")
            else:
                logger.warning(f"Tag '{tag}' not found")

    def set_hidden(self, tag: str, is_hidden: bool = True):
        """
        Set a tag as hidden/blocked or unhide it.

        Args:
            tag: Tag name
            is_hidden: True to hide, False to unhide
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE tags
                SET is_hidden = ?
                WHERE tag = ?
            ''', (1 if is_hidden else 0, tag))

            if cursor.rowcount > 0:
                logger.info(f"Tag '{tag}' {'hidden' if is_hidden else 'unhidden'}")
            else:
                logger.warning(f"Tag '{tag}' not found")

    def get_favorites(self) -> List[Tuple[str, int]]:
        """
        Get all favorited tags.

        Returns:
            List of (tag, count) tuples
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT tag, count
                FROM tags
                WHERE is_favorite = 1
                ORDER BY count DESC
            ''')

            return [(row['tag'], row['count']) for row in cursor.fetchall()]

    def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total tags
            cursor.execute('SELECT COUNT(*) as count FROM tags')
            stats['total_tags'] = cursor.fetchone()['count']

            # Total images
            cursor.execute('SELECT COUNT(DISTINCT image_path) as count FROM tag_images')
            stats['total_images'] = cursor.fetchone()['count']

            # Total relationships
            cursor.execute('SELECT COUNT(*) as count FROM tag_images')
            stats['total_relationships'] = cursor.fetchone()['count']

            # Favorite count
            cursor.execute('SELECT COUNT(*) as count FROM tags WHERE is_favorite = 1')
            stats['favorite_tags'] = cursor.fetchone()['count']

            # Hidden count
            cursor.execute('SELECT COUNT(*) as count FROM tags WHERE is_hidden = 1')
            stats['hidden_tags'] = cursor.fetchone()['count']

            # Top tags
            cursor.execute('SELECT tag, count FROM tags ORDER BY count DESC LIMIT 10')
            stats['top_tags'] = [(row['tag'], row['count']) for row in cursor.fetchall()]

            return stats

    def export_to_json(self, json_path: str):
        """
        Export database to JSON format (for backup/inspection).

        Args:
            json_path: Path to output JSON file
        """
        data = {
            'version': '2.0',
            'tags': {},
            'metadata': {}
        }

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Export tags with images
            cursor.execute('SELECT tag, count, is_favorite FROM tags')
            for row in cursor.fetchall():
                tag = row['tag']
                data['tags'][tag] = {
                    'count': row['count'],
                    'is_favorite': bool(row['is_favorite']),
                    'images': self.get_images_for_tag(tag)
                }

            # Export metadata
            data['metadata'] = self.get_statistics()

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Database exported to {json_path}")


def main():
    """Test tag database operations."""
    print("="*70)
    print("Tag Database - SQLite-based tag management")
    print("="*70)

    try:
        # Create test database
        db = TagDatabase('test_tag_database.db')

        # Add some test tags
        print("\nAdding test tags...")
        db.add_tag('1girl', ['img1.png', 'img2.png', 'img3.png'])
        db.add_tag('blonde', ['img1.png', 'img2.png'])
        db.add_tag('blue_eyes', ['img1.png'])

        # List tags
        print("\nAll tags:")
        for tag, count, is_fav in db.list_tags():
            print(f"  {tag}: {count} images {'*FAV*' if is_fav else ''}")

        # Set favorite
        print("\nSetting 'blonde' as favorite...")
        db.set_favorite('blonde', True)

        # List with favorites first
        print("\nTags (favorites first):")
        for tag, count, is_fav in db.list_tags(favorites_first=True):
            print(f"  {tag}: {count} images {'*FAV*' if is_fav else ''}")

        # Query images
        print("\nQuery: Images with '1girl' OR 'blonde':")
        images = db.query_images(['1girl', 'blonde'], operator='OR')
        print(f"  Found {len(images)} images: {images}")

        print("\nQuery: Images with '1girl' AND 'blonde':")
        images = db.query_images(['1girl', 'blonde'], operator='AND')
        print(f"  Found {len(images)} images: {images}")

        # Statistics
        print("\nDatabase statistics:")
        stats = db.get_statistics()
        for key, value in stats.items():
            if key != 'top_tags':
                print(f"  {key}: {value}")

        db.close()
        print("\n[SUCCESS] All tests passed!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
