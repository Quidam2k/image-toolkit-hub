"""
Rebuild Tag Database - Scan images and build clean SQLite tag database

Scans all images in auto_sorted folders, extracts clean tags (no technical metadata),
and builds a fast SQLite database for the batch export tool.

Features:
- Progress tracking with cancellation support
- Incremental or full rebuild
- Statistics reporting
- Background thread compatible

Author: Claude Code Implementation
Version: 1.0
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Callable
from tag_extractor_v2 import TagExtractorV2
from tag_database import TagDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TagDatabaseRebuilder:
    """Rebuild tag database from image collection."""

    def __init__(self, db_path: str = 'tag_database.db'):
        """
        Initialize rebuilder.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.extractor = TagExtractorV2()
        self.db = None
        self.cancelled = False

    def cancel(self):
        """Cancel the rebuild operation."""
        self.cancelled = True
        logger.info("Rebuild cancelled by user")

    def rebuild_from_folder(
        self,
        folder_path: str,
        recursive: bool = True,
        clear_existing: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """
        Rebuild tag database by scanning a folder.

        Args:
            folder_path: Root folder to scan (e.g., 'auto_sorted')
            recursive: If True, scan subfolders
            clear_existing: If True, clear database before rebuilding
            progress_callback: Optional callback(current, total, message)

        Returns:
            Dictionary with rebuild statistics
        """
        start_time = time.time()

        stats = {
            'success': False,
            'images_scanned': 0,
            'images_processed': 0,
            'images_failed': 0,
            'tags_discovered': 0,
            'total_tag_occurrences': 0,
            'time_taken': 0,
            'cancelled': False,
            'errors': []
        }

        try:
            # Initialize database
            self.db = TagDatabase(self.db_path)

            if clear_existing:
                logger.info("Clearing existing database...")
                self.db.clear_database()
                if progress_callback:
                    progress_callback(0, 1, "Clearing existing database...")

            # Find all image files
            logger.info(f"Scanning folder: {folder_path}")
            if progress_callback:
                progress_callback(0, 1, f"Scanning {folder_path}...")

            image_files = self._find_image_files(folder_path, recursive)
            stats['images_scanned'] = len(image_files)

            if not image_files:
                logger.warning("No images found!")
                return stats

            logger.info(f"Found {len(image_files)} images")

            # Build tag index: tag -> [image_paths]
            tag_index = {}

            # Process each image
            for i, image_path in enumerate(image_files):
                if self.cancelled:
                    stats['cancelled'] = True
                    logger.info("Rebuild cancelled")
                    break

                try:
                    # Update progress
                    if progress_callback:
                        progress_callback(
                            i + 1,
                            len(image_files),
                            f"Processing: {Path(image_path).name}"
                        )

                    # Extract tags from image
                    result = self.extractor.extract_tags_from_image(image_path)

                    if result['status'] == 'success':
                        tags = result['tags']

                        # Add to tag index
                        for tag in tags:
                            if tag not in tag_index:
                                tag_index[tag] = []
                            tag_index[tag].append(image_path)

                        stats['images_processed'] += 1
                        stats['total_tag_occurrences'] += len(tags)

                    else:
                        stats['images_failed'] += 1
                        error_msg = f"{image_path}: {result.get('error', 'Unknown error')}"
                        stats['errors'].append(error_msg)
                        logger.warning(error_msg)

                except Exception as e:
                    stats['images_failed'] += 1
                    error_msg = f"{image_path}: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)

            # Save to database
            if not self.cancelled and tag_index:
                logger.info(f"Saving {len(tag_index)} unique tags to database...")
                if progress_callback:
                    progress_callback(
                        len(image_files),
                        len(image_files),
                        f"Saving {len(tag_index)} tags to database..."
                    )

                self.db.bulk_insert_tags(tag_index)
                stats['tags_discovered'] = len(tag_index)

            # Final statistics
            stats['time_taken'] = time.time() - start_time
            stats['success'] = not self.cancelled and stats['images_processed'] > 0

            # Log summary
            logger.info("="*70)
            logger.info("Rebuild Summary:")
            logger.info(f"  Images scanned: {stats['images_scanned']}")
            logger.info(f"  Images processed: {stats['images_processed']}")
            logger.info(f"  Images failed: {stats['images_failed']}")
            logger.info(f"  Unique tags: {stats['tags_discovered']}")
            logger.info(f"  Total occurrences: {stats['total_tag_occurrences']}")
            logger.info(f"  Time taken: {stats['time_taken']:.1f}s")
            if stats['cancelled']:
                logger.info("  Status: CANCELLED")
            logger.info("="*70)

            return stats

        except Exception as e:
            logger.error(f"Rebuild failed: {e}", exc_info=True)
            stats['success'] = False
            stats['errors'].append(f"Critical error: {str(e)}")
            return stats

        finally:
            if self.db:
                self.db.close()

    def _find_image_files(self, folder_path: str, recursive: bool) -> list:
        """
        Find all image files in folder.

        Args:
            folder_path: Root folder to scan
            recursive: If True, scan subfolders

        Returns:
            List of image file paths
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
        image_files = []

        folder = Path(folder_path)

        if not folder.exists():
            logger.warning(f"Folder not found: {folder_path}")
            return []

        if recursive:
            for file_path in folder.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(str(file_path))
        else:
            for file_path in folder.glob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(str(file_path))

        return sorted(image_files)

    def get_database_stats(self) -> dict:
        """
        Get current database statistics.

        Returns:
            Dictionary with database stats
        """
        try:
            db = TagDatabase(self.db_path)
            stats = db.get_statistics()
            db.close()
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


def main():
    """Rebuild tag database from command line."""
    print("="*70)
    print("Tag Database Rebuilder")
    print("="*70)

    # Check for auto_sorted folder
    auto_sorted = Path('auto_sorted')
    if not auto_sorted.exists():
        print(f"\nError: auto_sorted folder not found!")
        print(f"Expected path: {auto_sorted.absolute()}")
        return 1

    # Check for master_images folder (alternative source)
    master_images = Path('master_images')
    if master_images.exists():
        print(f"\nFound master_images folder with organized images")
        folder_to_scan = master_images
    else:
        folder_to_scan = auto_sorted

    print(f"\nScanning: {folder_to_scan.absolute()}")
    print("This may take several minutes for large collections...")

    # Progress callback
    def progress(current, total, message):
        if total > 0:
            pct = (current / total) * 100
            print(f"\r[{current}/{total}] {pct:.1f}% - {message}", end='', flush=True)
        else:
            print(f"\r{message}", end='', flush=True)

    try:
        # Create rebuilder
        rebuilder = TagDatabaseRebuilder('tag_database.db')

        # Start rebuild
        print("\nStarting rebuild...")
        stats = rebuilder.rebuild_from_folder(
            str(folder_to_scan),
            recursive=True,
            clear_existing=True,
            progress_callback=progress
        )

        print("\n")  # New line after progress

        # Show results
        if stats['success']:
            print("\n[SUCCESS] Database rebuilt successfully!")
            print(f"\nDatabase saved to: tag_database.db")
            print(f"Total tags: {stats['tags_discovered']}")
            print(f"Total images: {stats['images_processed']}")
            print(f"Time taken: {stats['time_taken']:.1f}s")

            if stats['images_failed'] > 0:
                print(f"\nWarning: {stats['images_failed']} images failed to process")

        elif stats['cancelled']:
            print("\n[CANCELLED] Rebuild was cancelled")
            return 2

        else:
            print("\n[ERROR] Rebuild failed!")
            if stats['errors']:
                print("\nErrors:")
                for error in stats['errors'][:10]:  # Show first 10
                    print(f"  - {error}")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Interrupted by user")
        return 2

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
