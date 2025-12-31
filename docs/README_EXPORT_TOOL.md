# Export Batch Tool - Documentation

## Overview

The **Export Batch Tool** is a command-line utility for querying the tag frequency database and exporting matching images to batch folders for WAN 2.2 i2v (image-to-video) processing.

Instead of managing hundreds of pre-computed combination folders, this tool lets you:
- Create flexible, on-demand queries (AND/OR/NOT logic)
- Export matching images to temporary batch folders
- Generate batch manifests with complete metadata
- Iterate quickly on different image sets for different video clips

## Quick Start

### List Available Tags
```bash
python export_batch.py list
```

Shows all 80 available tags with their frequencies and percentages.

### Query (Dry-Run)
```bash
python export_batch.py query --tags blowjob
```

Shows how many images match without copying anything.

### Export to Batch Folder
```bash
python export_batch.py export --tags blowjob
```

Creates a batch folder with all matching images (2,847 images for "blowjob").

## Installation & Setup

### Requirements
- Python 3.7+
- `tag_frequency.json` database in the current directory

### Files
```
tag_query_engine.py      - Core query engine (parser, matcher, validator)
batch_exporter.py        - Image export and manifest generation
export_batch.py          - CLI interface (main entry point)
tag_frequency.json       - Tag frequency database (7,287 images, 80 tags)
```

## Query Syntax

The tool supports flexible boolean queries:

### Single Tag
```bash
python export_batch.py query --tags blowjob
# Returns: 2,847 images tagged with "blowjob"
```

### AND Query (Comma-Separated)
```bash
python export_batch.py query --tags "blowjob,succubus"
# Returns: 128 images with BOTH tags
```

### OR Query (Pipe-Separated)
```bash
python export_batch.py query --tags "blowjob|succubus"
# Returns: 4,319 images with EITHER tag (or both)
```

### NOT Query (Exclamation Prefix)
```bash
python export_batch.py query --tags "blowjob,!elf"
# Returns: 2,716 images with "blowjob" but NOT "elf"
```

### Complex Query
```bash
python export_batch.py query --tags "(blowjob|succubus),!elf"
# Returns: 3,965 images with (blowjob OR succubus) AND NOT elf
```

**Note:** Parentheses are optional - they're removed during parsing.

## Commands

### `query` - Show Matching Images (Dry-Run)

```bash
python export_batch.py query --tags <query> [--limit N]
```

**Options:**
- `--tags <query>` (required) - Tag query string
- `--limit N` (default: 20) - Show first N results

**Example:**
```bash
python export_batch.py query --tags "blowjob|succubus" --limit 50
```

**Output:**
```
======================================================================
Query Results: "blowjob|succubus"
======================================================================
Found: 4,319 matching images

Sample images:
  - 00000-388802332.jpg
  - 00001-1301045905.jpg
  - 00001-348943310.png
  ... and 4,316 more images

Tip: Use 'export' command to save to batch folder
```

---

### `export` - Export Matching Images

```bash
python export_batch.py export --tags <query> [options]
```

**Options:**
- `--tags <query>` (required) - Tag query string
- `--output DIR` (default: `./batch_exports`) - Output directory
- `--mode {copy|symlink}` (default: `copy`) - Export mode
- `--name NAME` - Custom batch folder name

**Example:**
```bash
python export_batch.py export --tags blowjob --mode copy
```

**Output:**
```
======================================================================
Exporting: "blowjob"
======================================================================
Exporting 2,847 images...
[████████████████████░░░░░░░░░] 67%
Export complete!

Batch folder: H:\Development\image_grid_sorter\batch_exports\batch_20251018_120000_blowjob
  - 2,847 images copied
  - Total size: 8.2 GB
  - Time taken: 45.3 seconds

Manifest: batch_20251018_120000_blowjob\manifest.json
Ready for WAN 2.2 i2v processing
======================================================================
```

#### Export Modes

**Copy Mode** (default)
```bash
python export_batch.py export --tags blowjob --mode copy
```
- Physically copies all images to batch folder
- Safest, no dependencies on source
- Uses more disk space
- Best for: final batches, archival

**Symlink Mode**
```bash
python export_batch.py export --tags blowjob --mode symlink
```
- Creates symbolic links to original images
- Fast, minimal disk space
- Works on Windows 10+ with admin or Developer Mode
- Best for: testing, preview, quick iteration

#### Custom Batch Names

By default, batch folders are named from the query:
- Query: `blowjob` → Folder: `batch_20251018_120000_blowjob`
- Query: `blowjob|succubus` → Folder: `batch_20251018_120000_blowjob_succubus`

To use a custom name:
```bash
python export_batch.py export --tags "blowjob,succubus" --name my_custom_batch
# Creates: batch_20251018_120000_my_custom_batch
```

---

### `list` - Show Available Tags

```bash
python export_batch.py list [--sort {count|name}]
```

**Options:**
- `--sort {count|name}` (default: `count`) - Sort by frequency or name

**Example:**
```bash
python export_batch.py list --sort count
```

**Output:**
```
======================================================================
Available Tags (80 total)
======================================================================
   1. blowjob                   - 2,921 images ( 10.8%)
   2. succubus                  - 1,632 images (  6.0%)
   3. girl                      - 1,548 images (  5.7%)
   4. 1girl                     - 1,096 images (  4.1%)
   5. kneeling                  - 1,072 images (  4.0%)
   ...
  80. hair_ribbon               -     7 images (  0.1%)
======================================================================
```

## Batch Manifests

Each exported batch includes a `manifest.json` file with complete metadata:

```json
{
  "batch_name": "batch_20251018_120000_blowjob",
  "created": "2025-10-18T12:00:00.123456",
  "query": "blowjob",
  "total_images": 2847,
  "manifest": {
    "images": [
      {
        "original_path": "H:\\images\\00001-1301045905.jpg",
        "filename": "00001-1301045905.jpg",
        "size": 1234567,
        "modified": "2025-10-15T10:30:45.123456"
      },
      ...
    ]
  }
}
```

This manifest can be used to:
- Track which images were in each batch
- Preserve original file paths for reference
- Calculate total batch size
- Audit batch creation history

## Performance

Query engine performance is optimized for speed:

| Operation | Time |
|-----------|------|
| Single tag query | <1ms |
| AND query (2 tags) | <5ms |
| OR query (2 tags) | <5ms |
| Complex query with NOT | <5ms |
| Export 2,847 images | ~45 seconds (copy mode) |
| Export 2,847 images | ~2 seconds (symlink mode) |

Database: 7,287 images, 80 tags, optimized with set-based operations.

## Workflow Examples

### Example 1: Quick Preview
```bash
# See what images match
python export_batch.py query --tags blowjob --limit 10

# If satisfied, export quickly with symlinks for testing
python export_batch.py export --tags blowjob --mode symlink
```

### Example 2: Production Batch
```bash
# Create final batch for WAN 2.2 processing
python export_batch.py export --tags "blowjob,!elf" --name production_batch

# Check the manifest
cat batch_exports/batch_20251018_120000_production_batch/manifest.json
```

### Example 3: Multiple Variations
```bash
# Create multiple batches for different video clips
python export_batch.py export --tags blowjob --name clip_1
python export_batch.py export --tags "succubus|elf" --name clip_2
python export_batch.py export --tags "blowjob,succubus" --name clip_3
```

### Example 4: Excluding Tags
```bash
# Get all images except elf and futanari
python export_batch.py export --tags "!elf,!futanari" --name non_fantasy

# Wait - this doesn't work yet (need at least one include tag)
# Instead:
python export_batch.py query --tags girl  # Check baseline
# Then get subset excluding unwanted:
python export_batch.py export --tags "girl,!elf" --name realistic_girls
```

## Common Tasks

### List all tags sorted by name
```bash
python export_batch.py list --sort name
```

### Find images with multiple related tags
```bash
python export_batch.py query --tags "blowjob|fellatio|oral sex"
```

### Create batch with exclusions
```bash
python export_batch.py export --tags "girl,!futanari" --output D:/batches
```

### Use symlinks for fast testing
```bash
python export_batch.py export --tags succubus --mode symlink --name test_batch
```

### Create custom named batch
```bash
python export_batch.py export --tags "blowjob,succubus" --name my_fantasy_batch
```

## File Organization

After running exports, you'll have:

```
batch_exports/
  batch_20251018_120000_blowjob/
    00001-1301045905.jpg
    00001-348943310.png
    ... (2,847 images)
    manifest.json

  batch_20251018_120001_succubus/
    ... (1,632 images)
    manifest.json

  batch_20251018_120002_my_fantasy_batch/
    ... (images matching query)
    manifest.json
```

Each batch is self-contained and can be:
- Moved to other directories
- Copied to different drives
- Deleted when done
- Processed by WAN 2.2 i2v independently

## Troubleshooting

### Error: "Database file not found"
- Make sure `tag_frequency.json` is in the current directory
- Check the file exists: `ls tag_frequency.json`

### Error: "Unknown tags: xyz"
- Use `python export_batch.py list` to see available tags
- Check spelling (case-insensitive, but must be exact)
- Did you mean: XYZ? [similar tags suggested]

### Symlink mode not working on Windows
- Requires Windows 10+ and Developer Mode enabled
- Or run Python as Administrator
- Fallback: Use `--mode copy` instead

### Batch folder is huge (8GB+)
- This is expected for large exports (2,900+ images at 2-3MB each)
- Use `--mode symlink` for testing first
- After testing, create final `--mode copy` batch for production

### Export is slow
- Normal: ~45 seconds for 2,847 images
- Copying: Depends on disk speed (50-100 MB/s typical)
- Consider using symlink mode for testing

## Advanced Features (Future)

- Phase 5: GUI-based query builder (Tkinter)
  - Visual tag selection with click-to-toggle
  - Real-time preview of result counts
  - Drag-and-drop tag ordering

- Batch tagging
  - Apply additional tags to batch images
  - Post-process batches with new metadata

- Re-export and merge
  - Combine multiple batch exports
  - Create union/intersection of batches

## Integration with WAN 2.2 i2v

The exported batch folder is ready to use with WAN 2.2:

1. Point WAN 2.2 input to batch folder
2. WAN reads all images from folder
3. Processes them with specified model
4. Output: video clip

The manifest.json is available for reference but WAN doesn't require it.

## Support & Feedback

For issues or suggestions:
- Check USAGE_EXAMPLES.md for common scenarios
- Review error messages - they include helpful suggestions
- Ensure tag_frequency.json is current and valid

---

**Version:** 1.0
**Created:** October 18, 2025
**Phase:** 4 (Query & Export Tool)
