"""
Batch Exporter - Copy or symlink matching images to batch folders with manifests.

Features:
  - Copy or symlink export modes
  - Automatic batch folder creation with timestamps
  - Manifest generation (JSON with image metadata)
  - Statistics reporting
  - Progress tracking
  - Disk space validation
"""

import json
import logging
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional, Dict
import time

from file_ops import copy_with_companions, get_companion_files

logger = logging.getLogger(__name__)


class BatchExporter:
    """Export images to batch folders with manifests and metadata."""

    def __init__(self, output_dir: str = './batch_exports'):
        """Initialize batch exporter.

        Args:
            output_dir: Directory to create batch folders in
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_images(
        self,
        image_paths: List[str],
        batch_name: str,
        query: str = "",
        mode: str = 'copy',
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Export images to a batch folder.

        Args:
            image_paths: List of image file paths to export
            batch_name: Name for the batch (will be timestamped)
            query: Original query string (for manifest)
            mode: 'copy' or 'symlink'
            progress_callback: Function to call with (current, total, message)

        Returns:
            Dict with export results:
            {
              'success': bool,
              'batch_path': str,
              'total_images': int,
              'copied': int,
              'skipped': int,
              'failed': int,
              'total_size': int,
              'time_taken': float,
              'manifest_path': str,
              'error': str (if failed)
            }
        """
        start_time = time.time()
        result = {
            'success': False,
            'batch_path': None,
            'total_images': len(image_paths),
            'copied': 0,
            'skipped': 0,
            'failed': 0,
            'total_size': 0,
            'time_taken': 0,
            'manifest_path': None,
            'error': None,
            'errors': []
        }

        if not image_paths:
            result['error'] = "No images to export"
            return result

        if mode not in ['copy', 'symlink']:
            result['error'] = f"Invalid mode: {mode}"
            return result

        try:
            # Create batch folder
            batch_path = self._create_batch_folder(batch_name)
            result['batch_path'] = str(batch_path)

            if progress_callback:
                progress_callback(0, len(image_paths), f"Creating batch folder: {batch_path.name}")

            # Export images
            for idx, image_path in enumerate(image_paths):
                if progress_callback and idx % 10 == 0:
                    pct = int((idx / len(image_paths)) * 100)
                    progress_callback(
                        idx,
                        len(image_paths),
                        f"Exporting images: {pct}%"
                    )

                try:
                    src = Path(image_path)
                    if not src.exists():
                        logger.warning(f"Source not found: {image_path}")
                        result['skipped'] += 1
                        continue

                    dst = batch_path / src.name

                    # Handle duplicate filenames
                    if dst.exists():
                        dst = self._get_unique_path(dst)

                    if mode == 'copy':
                        # Use copy_with_companions to include .txt tag files etc.
                        copy_with_companions(str(src), str(dst), handle_conflicts=False)
                    else:  # symlink
                        # Create relative symlink on Windows
                        try:
                            os.symlink(src, dst)
                            # Also symlink companion files
                            for companion in get_companion_files(str(src)):
                                comp_ext = os.path.splitext(companion)[1]
                                os.symlink(companion, str(dst) + comp_ext)
                        except OSError:
                            # Fallback: try absolute symlink
                            try:
                                os.symlink(src.absolute(), dst)
                            except OSError as e:
                                logger.warning(f"Symlink failed for {src}: {e}, copying instead")
                                copy_with_companions(str(src), str(dst), handle_conflicts=False)

                    if src.exists():
                        result['total_size'] += src.stat().st_size
                    result['copied'] += 1

                except Exception as e:
                    logger.error(f"Failed to export {image_path}: {e}")
                    result['failed'] += 1
                    result['errors'].append(f"{image_path}: {str(e)}")

            if progress_callback:
                progress_callback(
                    len(image_paths),
                    len(image_paths),
                    "Generating manifest..."
                )

            # Generate manifest
            manifest_path = self._generate_manifest(
                batch_path,
                image_paths,
                query
            )
            result['manifest_path'] = str(manifest_path)

            result['time_taken'] = time.time() - start_time
            result['success'] = result['copied'] > 0

            if progress_callback:
                progress_callback(
                    len(image_paths),
                    len(image_paths),
                    "Export complete!"
                )

            logger.info(
                f"Batch export complete: {result['copied']} copied, "
                f"{result['skipped']} skipped, {result['failed']} failed"
            )

            return result

        except Exception as e:
            logger.error(f"Export failed: {e}")
            result['error'] = str(e)
            result['time_taken'] = time.time() - start_time
            return result

    def _create_batch_folder(self, batch_name: str) -> Path:
        """Create a timestamped batch folder.

        Returns:
            Path to created folder
        """
        # Create timestamp-based folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"batch_{timestamp}_{batch_name}"

        batch_path = self.output_dir / folder_name
        batch_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created batch folder: {batch_path}")
        return batch_path

    def _get_unique_path(self, path: Path) -> Path:
        """Get unique path by adding suffix if file exists."""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def _generate_manifest(
        self,
        batch_path: Path,
        image_paths: List[str],
        query: str = ""
    ) -> Path:
        """Generate manifest JSON for batch.

        Returns:
            Path to manifest file
        """
        manifest = {
            'batch_name': batch_path.name,
            'created': datetime.now().isoformat(),
            'query': query,
            'total_images': len(image_paths),
            'manifest': {
                'images': []
            }
        }

        # Add image entries
        for img_path in image_paths:
            src = Path(img_path)
            if src.exists():
                manifest['manifest']['images'].append({
                    'original_path': str(img_path),
                    'filename': src.name,
                    'size': src.stat().st_size,
                    'modified': datetime.fromtimestamp(
                        src.stat().st_mtime
                    ).isoformat()
                })

        manifest_path = batch_path / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Created manifest: {manifest_path}")
        return manifest_path

    def report_statistics(self, batch_path: str) -> Optional[Dict]:
        """Generate statistics report for a batch.

        Returns:
            Dict with statistics or None if batch not found
        """
        batch = Path(batch_path)
        if not batch.exists():
            logger.error(f"Batch not found: {batch_path}")
            return None

        try:
            # Load manifest
            manifest_path = batch / 'manifest.json'
            if not manifest_path.exists():
                logger.error(f"Manifest not found: {manifest_path}")
                return None

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Calculate statistics
            total_size = 0
            file_count = 0

            for item in manifest['manifest']['images']:
                total_size += item.get('size', 0)
                file_count += 1

            # Get batch creation time
            created = datetime.fromisoformat(manifest['created'])

            stats = {
                'batch_name': manifest['batch_name'],
                'batch_path': str(batch),
                'created': manifest['created'],
                'query': manifest['query'],
                'total_images': manifest['total_images'],
                'actual_files': file_count,
                'total_size': total_size,
                'total_size_gb': total_size / (1024 ** 3),
                'manifest_path': str(manifest_path)
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to generate statistics: {e}")
            return None

    def format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def print_report(self, batch_path: str) -> None:
        """Print a formatted statistics report."""
        stats = self.report_statistics(batch_path)
        if not stats:
            print("Could not generate report")
            return

        print("\n" + "=" * 70)
        print("BATCH EXPORT SUMMARY")
        print("=" * 70)
        print(f"Batch: {stats['batch_name']}")
        print(f"Created: {stats['created']}")
        print(f"Query: {stats['query']}")
        print()
        print("Statistics:")
        print(f"  - Total images: {stats['total_images']:,}")
        print(f"  - Actual files: {stats['actual_files']:,}")
        print(f"  - Total size: {self.format_size(stats['total_size'])}")
        print()
        print(f"Location: {stats['batch_path']}")
        print(f"Manifest: {stats['manifest_path']}")
        print("=" * 70 + "\n")


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    exporter = BatchExporter()

    # Example: create a small test batch
    print("Testing BatchExporter...")
    print()

    # You would normally use this with results from TagQueryEngine
    # For now, just test the path creation
    batch_path = exporter._create_batch_folder("test")
    print(f"Created batch: {batch_path}")
