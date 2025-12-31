#!/usr/bin/env python3
"""
Export Batch - CLI tool for querying tags and exporting image batches.

Usage:
  python export_batch.py query --tags blowjob
  python export_batch.py query --tags "blowjob AND succubus" --limit 20
  python export_batch.py export --tags blowjob --mode copy
  python export_batch.py export --tags "blowjob OR succubus" --output ./my_batches
  python export_batch.py list
  python export_batch.py list --sort name

Examples:
  # Query what images match a tag (dry-run)
  python export_batch.py query --tags blowjob

  # Export all blowjob images to a batch folder
  python export_batch.py export --tags blowjob

  # Export combined images
  python export_batch.py export --tags "blowjob,succubus" --name my_batch

  # Use OR logic
  python export_batch.py export --tags "blowjob|succubus"

  # Exclude tags
  python export_batch.py export --tags "blowjob,!elf"

  # List all available tags
  python export_batch.py list --sort count
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from tag_query_engine import TagQueryEngine
from batch_exporter import BatchExporter


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExportBatchCLI:
    """Command-line interface for batch export tool."""

    def __init__(self):
        """Initialize CLI."""
        self.query_engine = TagQueryEngine()
        self.batch_exporter = BatchExporter()
        self.db_loaded = False

    def initialize(self) -> bool:
        """Load database and prepare for operations."""
        if self.db_loaded:
            return True

        if not self.query_engine.load_database():
            print("ERROR: Failed to load tag database (tag_frequency.json)")
            print("Make sure tag_frequency.json exists in the current directory")
            return False

        self.db_loaded = True
        return True

    def do_query(self, args) -> int:
        """Execute query command."""
        if not self.initialize():
            return 1

        query_string = args.tags
        limit = args.limit

        # Validate query
        is_valid, error_msg = self.query_engine.validate_query(query_string)
        if not is_valid:
            print(f"ERROR: Invalid query")
            print(f"  {error_msg}")
            print()
            self._print_query_help()
            return 1

        # Execute query
        success, images, error = self.query_engine.query(query_string)
        if not success:
            print(f"ERROR: {error}")
            return 1

        # Display results
        print()
        print("=" * 70)
        print(f'Query Results: "{query_string}"')
        print("=" * 70)
        print(f"Found: {len(images):,} matching images")
        print()

        if images:
            print("Sample images:")
            for img in images[:limit]:
                print(f"  - {img}")

            if len(images) > limit:
                print(f"  ... and {len(images) - limit:,} more images")

        print()
        print("Tip: Use 'export' command to save to batch folder")
        print()

        return 0

    def do_export(self, args) -> int:
        """Execute export command."""
        if not self.initialize():
            return 1

        query_string = args.tags
        output_dir = args.output
        mode = args.mode
        custom_name = args.name

        # Validate query
        is_valid, error_msg = self.query_engine.validate_query(query_string)
        if not is_valid:
            print(f"ERROR: Invalid query")
            print(f"  {error_msg}")
            print()
            self._print_query_help()
            return 1

        # Execute query
        success, images, error = self.query_engine.query(query_string)
        if not success:
            print(f"ERROR: {error}")
            return 1

        if not images:
            print(f"ERROR: No images match query: {query_string}")
            return 1

        # Generate batch name
        if custom_name:
            batch_name = custom_name
        else:
            # Create name from query, sanitizing special characters
            batch_name = query_string.replace(' ', '_').replace(',', '').replace('|', '_')
            batch_name = batch_name[:50]  # Limit length

        # Export
        print()
        print("=" * 70)
        print(f'Exporting: "{query_string}"')
        print("=" * 70)
        print(f"Exporting {len(images):,} images...")
        print()

        def progress(current, total, message):
            pct = int((current / total) * 100) if total > 0 else 0
            bar_length = 30
            filled = int((current / total) * bar_length) if total > 0 else 0
            bar = "#" * filled + "-" * (bar_length - filled)
            try:
                print(f"[{bar}] {pct}% - {message}", end='\r', flush=True)
            except UnicodeEncodeError:
                # Fallback for Windows console encoding issues
                print(f"[{bar}] {pct}%", end='\r', flush=True)

        result = self.batch_exporter.export_images(
            images,
            batch_name,
            query=query_string,
            mode=mode,
            progress_callback=progress
        )

        print()  # Clear progress line
        print()

        if not result['success']:
            print(f"ERROR: Export failed: {result['error']}")
            return 1

        # Print summary
        print("Export complete!")
        print()
        print(f"Batch folder: {result['batch_path']}")
        print(f"  - {result['copied']:,} images {mode}d")

        if result['skipped'] > 0:
            print(f"  - {result['skipped']:,} images skipped")
        if result['failed'] > 0:
            print(f"  - {result['failed']:,} images failed")

        print(f"  - Total size: {self.batch_exporter.format_size(result['total_size'])}")
        print(f"  - Time taken: {result['time_taken']:.1f} seconds")
        print()

        if result['manifest_path']:
            print(f"Manifest: {Path(result['manifest_path']).name}")

        print(f"Ready for WAN 2.2 i2v processing")
        print("=" * 70)
        print()

        return 0

    def do_list(self, args) -> int:
        """Execute list command."""
        if not self.initialize():
            return 1

        sort_by = args.sort
        tags = self.query_engine.list_available_tags()

        if sort_by == 'name':
            tags = sorted(tags, key=lambda x: x[0])

        print()
        print("=" * 70)
        print(f"Available Tags ({len(tags)} total)")
        print("=" * 70)

        total_images = sum(count for _, count in tags)

        for idx, (tag, count) in enumerate(tags, 1):
            pct = (count / total_images * 100) if total_images > 0 else 0
            print(f"  {idx:2d}. {tag:25s} - {count:5,d} images ({pct:5.1f}%)")

        print("=" * 70)
        print()

        return 0

    def _print_query_help(self):
        """Print query syntax help."""
        print("Query syntax examples:")
        print("  Single tag:           blowjob")
        print("  AND query:            blowjob,succubus")
        print("  OR query:             blowjob|succubus")
        print("  NOT query:            blowjob,!elf")
        print("  Complex:              (blowjob|succubus),!elf")
        print()
        print("Use 'export_batch.py list' to see all available tags")

    def run(self, argv: Optional[list] = None) -> int:
        """Run CLI application."""
        parser = argparse.ArgumentParser(
            prog='export_batch.py',
            description='Query and export images by tags for WAN 2.2 i2v processing',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__doc__
        )

        subparsers = parser.add_subparsers(
            dest='command',
            help='Command to execute'
        )

        # Query subcommand
        query_parser = subparsers.add_parser(
            'query',
            help='Show images matching query (dry-run)'
        )
        query_parser.add_argument(
            '--tags',
            required=True,
            help='Tag query (e.g., "blowjob" or "blowjob,succubus")'
        )
        query_parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Show first N results (default: 20)'
        )
        query_parser.set_defaults(func=self.do_query)

        # Export subcommand
        export_parser = subparsers.add_parser(
            'export',
            help='Export matching images to batch folder'
        )
        export_parser.add_argument(
            '--tags',
            required=True,
            help='Tag query (e.g., "blowjob" or "blowjob,succubus")'
        )
        export_parser.add_argument(
            '--output',
            default='./batch_exports',
            help='Output directory for batch folders (default: ./batch_exports)'
        )
        export_parser.add_argument(
            '--mode',
            choices=['copy', 'symlink'],
            default='copy',
            help='Export mode: copy files or create symlinks (default: copy)'
        )
        export_parser.add_argument(
            '--name',
            help='Custom batch folder name'
        )
        export_parser.set_defaults(func=self.do_export)

        # List subcommand
        list_parser = subparsers.add_parser(
            'list',
            help='List all available tags'
        )
        list_parser.add_argument(
            '--sort',
            choices=['count', 'name'],
            default='count',
            help='Sort by count (default) or name'
        )
        list_parser.set_defaults(func=self.do_list)

        # Parse arguments
        args = parser.parse_args(argv)

        # Execute command
        if not hasattr(args, 'func'):
            parser.print_help()
            return 0

        try:
            return args.func(args)
        except KeyboardInterrupt:
            print("\n\nAborted by user")
            return 130
        except Exception as e:
            logger.exception("Unexpected error")
            print(f"\nERROR: {e}")
            return 1


def main():
    """Main entry point."""
    cli = ExportBatchCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
