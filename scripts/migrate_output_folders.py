"""
Migration script: Move existing sorted_* folders into new output/ structure.

Moves:
  sorted_{name}/1/           -> output/manual/{name}/1/  (or label if configured)
  sorted_{name}/2/           -> output/manual/{name}/2/
  sorted_{name}/3/           -> output/manual/{name}/3/
  sorted_{name}/removed/     -> output/manual/{name}/removed/
  sorted_{name}/auto_sorted/ -> output/auto/{name}/
  sorted_{name}/unmatched/   -> output/auto/{name}/unmatched/
  Bare 1/                    -> output/manual/unnamed/1/
  Bare auto_sorted/          -> output/auto/unnamed/

Usage:
  python scripts/migrate_output_folders.py            # dry-run (default)
  python scripts/migrate_output_folders.py --execute  # actually move files
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_project_root():
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def count_files(path):
    """Count files recursively in a directory."""
    count = 0
    total_size = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                count += 1
                try:
                    total_size += entry.stat().st_size
                except OSError:
                    pass
            elif entry.is_dir():
                sub_count, sub_size = count_files(entry.path)
                count += sub_count
                total_size += sub_size
    except (PermissionError, OSError):
        pass
    return count, total_size


def format_size(byte_size):
    if byte_size < 1024:
        return f"{byte_size} B"
    elif byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    elif byte_size < 1024 * 1024 * 1024:
        return f"{byte_size / (1024 * 1024):.1f} MB"
    else:
        return f"{byte_size / (1024 * 1024 * 1024):.2f} GB"


def discover_folders(root):
    """Find all folders that need migration."""
    moves = []
    output_dir = root / 'output'

    manual_cats = {'1', '2', '3', 'removed'}
    auto_cats = {'auto_sorted', 'unmatched'}

    # 1. sorted_* folders
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith('sorted_'):
            continue

        source_name = entry.name[len('sorted_'):]  # strip "sorted_" prefix

        for sub in sorted(entry.iterdir()):
            if not sub.is_dir():
                continue

            if sub.name in manual_cats:
                dest = output_dir / 'manual' / source_name / sub.name
                moves.append((sub, dest))
            elif sub.name == 'auto_sorted':
                # Move contents of auto_sorted into output/auto/{source}/
                dest = output_dir / 'auto' / source_name
                for term_dir in sorted(sub.iterdir()):
                    if term_dir.is_dir():
                        moves.append((term_dir, dest / term_dir.name))
            elif sub.name == 'unmatched':
                dest = output_dir / 'auto' / source_name / 'unmatched'
                moves.append((sub, dest))

    # 2. Bare root-level folders
    for cat in sorted(manual_cats):
        bare = root / cat
        if bare.is_dir():
            files, _ = count_files(str(bare))
            if files > 0:
                dest = output_dir / 'manual' / 'unnamed' / cat
                moves.append((bare, dest))

    bare_auto = root / 'auto_sorted'
    if bare_auto.is_dir():
        for term_dir in sorted(bare_auto.iterdir()):
            if term_dir.is_dir():
                files, _ = count_files(str(term_dir))
                if files > 0:
                    dest = output_dir / 'auto' / 'unnamed' / term_dir.name
                    moves.append((term_dir, dest))

    bare_unmatched = root / 'unmatched'
    if bare_unmatched.is_dir():
        files, _ = count_files(str(bare_unmatched))
        if files > 0:
            dest = output_dir / 'auto' / 'unnamed' / 'unmatched'
            moves.append((bare_unmatched, dest))

    return moves


def print_plan(moves, root):
    """Print the migration plan."""
    if not moves:
        print("Nothing to migrate.")
        return

    total_files = 0
    total_size = 0

    print(f"\n{'='*70}")
    print("MIGRATION PLAN")
    print(f"{'='*70}\n")

    for src, dst in moves:
        files, size = count_files(str(src))
        total_files += files
        total_size += size

        rel_src = src.relative_to(root)
        rel_dst = dst.relative_to(root)

        if files > 0:
            print(f"  {rel_src}/")
            print(f"    -> {rel_dst}/  ({files} files, {format_size(size)})")
            print()

    print(f"{'='*70}")
    print(f"Total: {total_files} files, {format_size(total_size)}")
    print(f"Moves: {len(moves)} directories")
    print(f"{'='*70}")


def execute_moves(moves, root):
    """Execute the migration."""
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'moves': [],
        'errors': []
    }

    moved = 0
    errors = 0

    for src, dst in moves:
        files, size = count_files(str(src))
        if files == 0:
            continue

        rel_src = str(src.relative_to(root))
        rel_dst = str(dst.relative_to(root))

        try:
            # Create destination parent
            dst.parent.mkdir(parents=True, exist_ok=True)

            if dst.exists():
                # Merge: move individual files
                for item in src.iterdir():
                    dest_item = dst / item.name
                    if dest_item.exists():
                        # Handle naming conflict
                        base, ext = os.path.splitext(item.name)
                        counter = 1
                        while dest_item.exists():
                            dest_item = dst / f"{base}_{counter}{ext}"
                            counter += 1
                    shutil.move(str(item), str(dest_item))
                # Remove empty source
                try:
                    src.rmdir()
                except OSError:
                    pass  # Not empty (has subdirs that were also moved)
            else:
                shutil.move(str(src), str(dst))

            manifest['moves'].append({
                'from': rel_src,
                'to': rel_dst,
                'files': files,
                'size': size
            })
            moved += 1
            print(f"  [OK] {rel_src} -> {rel_dst} ({files} files)")

        except Exception as e:
            manifest['errors'].append({
                'from': rel_src,
                'to': rel_dst,
                'error': str(e)
            })
            errors += 1
            print(f"  [ERROR] {rel_src}: {e}")

    # Clean up empty sorted_* directories
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name.startswith('sorted_'):
            try:
                # Remove if completely empty (recursively)
                remaining = list(entry.rglob('*'))
                if not any(f.is_file() for f in remaining):
                    shutil.rmtree(str(entry))
                    print(f"  [CLEANUP] Removed empty {entry.name}/")
            except OSError:
                pass

    # Save manifest
    manifest_path = root / 'migration_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nMoved: {moved} directories, Errors: {errors}")
    print(f"Manifest saved to: {manifest_path}")

    return errors == 0


def main():
    root = get_project_root()
    execute = '--execute' in sys.argv

    print(f"Project root: {root}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN'}")

    moves = discover_folders(root)
    print_plan(moves, root)

    if not moves:
        return

    if not execute:
        print("\nThis was a dry run. To actually move files, run:")
        print(f"  python {sys.argv[0]} --execute")
        return

    print("\nExecuting migration...")
    success = execute_moves(moves, root)

    if success:
        print("\nMigration complete!")
    else:
        print("\nMigration completed with errors. Check the manifest for details.")


if __name__ == '__main__':
    main()
