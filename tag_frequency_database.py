"""
Tag Frequency Database Builder

Scans images, extracts deduplicated tags, builds comprehensive frequency database.
Tracks:
- Tag frequency (how many images have each tag)
- Source distribution (CLIP vs prompt)
- Image-to-tags mapping
- Temporal data (when tags were added)

Output: tag_frequency.json database

Author: Claude Code Implementation
Version: 1.0
"""

import os
import json
import logging
from datetime import datetime
from tag_extractor_v2 import TagExtractorV2 as TagExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TagFrequencyDatabase:
    """Build and manage tag frequency database."""

    def __init__(self, db_file='tag_frequency.json'):
        """
        Initialize database manager.

        Args:
            db_file: Path to store the frequency database JSON
        """
        self.logger = logging.getLogger(__name__)
        self.db_file = db_file
        self.extractor = TagExtractor()
        self.database = self._load_or_create_database()

    def _load_or_create_database(self):
        """Load existing database or create new one."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                self.logger.info(f"Loaded existing database from {self.db_file}")
                return db
            except Exception as e:
                self.logger.warning(f"Failed to load database: {e}, creating new")

        # Create new database structure
        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'tags': {},  # tag_name -> {count, images, sources}
            'images': {},  # image_path -> {tags, sources}
            'statistics': {
                'total_images': 0,
                'total_unique_tags': 0,
                'images_scanned': 0,
                'last_scan': None
            }
        }

    def scan_folder(self, folder_path, recursive=True, progress_callback=None):
        """
        Scan a folder and add/update tags in database.

        Args:
            folder_path: Path to folder with images
            recursive: If True, process subfolders
            progress_callback: Optional progress callback

        Returns:
            dict with scan results
        """
        print(f"\n{'='*70}")
        print(f"Scanning folder for tags: {folder_path}")
        print(f"{'='*70}")

        # Extract tags from all images
        extraction_results = self.extractor.extract_tags_from_folder(
            folder_path,
            recursive=recursive,
            progress_callback=progress_callback
        )

        # Process extraction results into database
        added_count = 0
        updated_count = 0

        for image_result in extraction_results['images']:
            image_name = image_result['image']
            tags = image_result['tags']
            sources = image_result['sources']

            # Check if image is new or update
            if image_name not in self.database['images']:
                added_count += 1
            else:
                updated_count += 1

            # Store image record
            self.database['images'][image_name] = {
                'tags': tags,
                'sources': sources,
                'extracted': datetime.now().isoformat()
            }

            # Update tag frequencies
            for tag in tags:
                if tag not in self.database['tags']:
                    self.database['tags'][tag] = {
                        'count': 0,
                        'images': [],
                        'sources': {'clip': 0, 'prompt': 0, 'both': 0}
                    }

                tag_record = self.database['tags'][tag]
                tag_record['count'] += 1

                # Track which images have this tag
                if image_name not in tag_record['images']:
                    tag_record['images'].append(image_name)

                # Track source distribution for this tag
                if tag in sources['clip']:
                    tag_record['sources']['clip'] += 1
                if tag in sources['prompt']:
                    tag_record['sources']['prompt'] += 1
                if tag in sources['both']:
                    tag_record['sources']['both'] += 1

        # Update statistics
        self.database['statistics']['total_images'] = len(self.database['images'])
        self.database['statistics']['total_unique_tags'] = len(self.database['tags'])
        self.database['statistics']['images_scanned'] = extraction_results['successful']
        self.database['statistics']['last_scan'] = datetime.now().isoformat()

        # Save database
        self.save_database()

        return {
            'scanned': extraction_results['total_images'],
            'successful': extraction_results['successful'],
            'failed': extraction_results['failed'],
            'added': added_count,
            'updated': updated_count,
            'total_tags': len(self.database['tags']),
            'source_stats': extraction_results['source_stats']
        }

    def get_tag_frequency_report(self, min_images=1, limit=100):
        """
        Generate a frequency report.

        Args:
            min_images: Only include tags in at least this many images
            limit: Max tags to return

        Returns:
            list of (tag, frequency, percentage) tuples
        """
        total_images = self.database['statistics']['total_images']

        # Filter and sort
        tags_list = [
            {
                'tag': tag,
                'count': data['count'],
                'percentage': round(100 * data['count'] / max(total_images, 1), 1),
                'sources': data['sources'],
                'images': len(data['images'])
            }
            for tag, data in self.database['tags'].items()
            if data['count'] >= min_images
        ]

        # Sort by frequency descending
        tags_list.sort(key=lambda x: x['count'], reverse=True)

        return tags_list[:limit]

    def print_frequency_report(self, min_images=1, limit=50):
        """
        Print a human-readable frequency report.

        Args:
            min_images: Only include tags in at least this many images
            limit: Max tags to print
        """
        report = self.get_tag_frequency_report(min_images, limit)
        total_images = self.database['statistics']['total_images']

        print(f"\n{'='*70}")
        print(f"TAG FREQUENCY REPORT")
        print(f"{'='*70}")
        print(f"Total images: {total_images}")
        print(f"Total unique tags: {self.database['statistics']['total_unique_tags']}")
        print(f"Report limit: {limit} tags (min {min_images} images)")
        print(f"{'='*70}")
        print(f"{'Rank':<6} {'Tag':<25} {'Count':<8} {'Percent':<10} {'Sources':<30}")
        print(f"{'-'*70}")

        for i, item in enumerate(report, 1):
            tag = item['tag'][:24]
            count = item['count']
            percent = item['percentage']
            sources = (f"CLIP:{item['sources']['clip']}, "
                      f"Prompt:{item['sources']['prompt']}, "
                      f"Both:{item['sources']['both']}")[:29]

            print(f"{i:<6} {tag:<25} {count:<8} {percent:>7.1f}% {sources:<30}")

        print(f"{'='*70}")

    def identify_underrepresented_tags(self, threshold=5):
        """
        Find tags that appear in very few images (potential issues).

        Args:
            threshold: Tags appearing in <= this many images

        Returns:
            list of underrepresented tags
        """
        return [
            {'tag': tag, 'count': data['count']}
            for tag, data in self.database['tags'].items()
            if data['count'] <= threshold
        ]

    def save_database(self):
        """Save database to JSON file."""
        try:
            self.database['last_updated'] = datetime.now().isoformat()

            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.database, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Database saved to {self.db_file}")
        except Exception as e:
            self.logger.error(f"Failed to save database: {e}")

    def export_report(self, output_file=None):
        """
        Export frequency report to a readable file.

        Args:
            output_file: Optional output file path
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"tag_frequency_report_{timestamp}.txt"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write("TAG FREQUENCY REPORT\n")
                f.write("="*70 + "\n\n")

                # Summary
                f.write(f"Report Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Images Scanned: {self.database['statistics']['total_images']}\n")
                f.write(f"Total Unique Tags: {self.database['statistics']['total_unique_tags']}\n")
                f.write(f"Last Scan: {self.database['statistics']['last_scan']}\n\n")

                # Tag list
                f.write("="*70 + "\n")
                f.write("TOP TAGS BY FREQUENCY\n")
                f.write("="*70 + "\n\n")

                report = self.get_tag_frequency_report(min_images=1, limit=200)
                f.write(f"{'Rank':<6} {'Tag':<25} {'Count':<8} {'Percent':<10}\n")
                f.write(f"{'-'*70}\n")

                for i, item in enumerate(report, 1):
                    tag = item['tag'][:24]
                    count = item['count']
                    percent = item['percentage']
                    f.write(f"{i:<6} {tag:<25} {count:<8} {percent:>7.1f}%\n")

                # Underrepresented tags
                f.write(f"\n{'='*70}\n")
                f.write("UNDERREPRESENTED TAGS (5 or fewer images)\n")
                f.write(f"{'='*70}\n\n")

                under = self.identify_underrepresented_tags(5)
                if under:
                    f.write(f"{'Tag':<30} {'Count':<8}\n")
                    f.write(f"{'-'*40}\n")
                    for item in under:
                        f.write(f"{item['tag']:<30} {item['count']:<8}\n")
                else:
                    f.write("None - all tags appear in 6+ images\n")

            self.logger.info(f"Report exported to {output_file}")
            print(f"Report saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to export report: {e}")


def main():
    """Test frequency database."""
    print("="*70)
    print("Tag Frequency Database Builder")
    print("="*70)

    try:
        db = TagFrequencyDatabase()

        # Scan existing auto-sorted folder
        # result = db.scan_folder('./auto_sorted', recursive=True)
        # print(f"Scanned: {result['scanned']}, Added: {result['added']}")

        # Print report
        # db.print_frequency_report(min_images=1, limit=50)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
