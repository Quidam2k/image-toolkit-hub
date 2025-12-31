# PHASE 4: Tag Query & Export Tool - Implementation Plan

## Overview
Build a command-line tool that dynamically queries the tag database and exports matching images to batch folders for WAN 2.2 i2v processing.

## Why This Approach

### Problem Statement
User needs to create temporary batch folders with specific image sets for different processing scenarios:
- Some clips need images with [blowjob] only
- Some clips need images with [blowjob AND succubus] for variety
- Some clips might need images with [elf OR succubus]

### Current Limitations
- Multi-copy folder structure is static and pre-computed
- Requires managing hundreds of combination folders
- Difficult to create ad-hoc batches on demand
- Not flexible for new requirements

### Proposed Solution
**Query & Export Tool:**
- Accepts flexible tag queries (AND/OR/NOT)
- Looks up matching images in database
- Exports to temporary batch folder
- Non-destructive (doesn't modify originals)
- Fast and simple

## Implementation Plan

### Phase 4.1: Design Query Engine

**Goal:** Define query syntax and matching algorithm

#### Query Syntax
```
# Simple queries
blowjob
succubus
elf

# Boolean queries
"blowjob AND succubus"        # Both tags required
"blowjob OR succubus"         # Either tag (or both)
"blowjob AND NOT elf"         # Has blowjob, doesn't have elf
"(blowjob OR succubus) AND elf"  # Complex: advanced feature

# Practical examples
--tags blowjob
--tags "blowjob,succubus"     # Comma-separated = AND
--tags "blowjob|succubus"     # Pipe-separated = OR
```

#### Matching Algorithm
```python
Query: "blowjob AND succubus"

For each image in database:
  IF image.tags contains "blowjob" AND image.tags contains "succubus":
    add to results

Return: list of matching image paths
```

#### Database Structure (from tag_frequency.json)
```json
{
  "tags": {
    "blowjob": {
      "count": 2921,
      "images": ["img1.jpg", "img2.png", ...]
    },
    "succubus": {
      "count": 1632,
      "images": ["img2.png", "img5.jpg", ...]
    }
  }
}
```

#### Design Decisions
1. **Query format:** Simple comma-separated (AND) or pipe-separated (OR)
   - Keep it simple: most queries are single tag or AND combinations
   - Add NOT with "!" prefix
2. **Case sensitivity:** Normalize tags to lowercase
3. **Partial matching:** Don't support (requires exact tag names)
4. **Error handling:**
   - Unknown tag → warn, return 0 results
   - Invalid syntax → error message with examples
   - Empty result → warn, show similar tags

### Phase 4.2: Implement Query Engine

**Goal:** Build working query parser and matcher

#### Core Classes
```python
class TagQueryEngine:
    def __init__(self, db_file='tag_frequency.json')
    def load_database()
    def parse_query(query_string) -> dict
    def find_matching_images(parsed_query) -> list
    def validate_query(query_string) -> bool
    def list_available_tags() -> list
```

#### Methods Detail

**load_database()**
- Load tag_frequency.json
- Build reverse index: image → tags (for fast lookup)
- Cache in memory

**parse_query(query_string)**
- Input: "blowjob AND succubus"
- Output: {"operator": "AND", "tags": ["blowjob", "succubus"]}
- Also handle: "blowjob" → {"operator": "SINGLE", "tags": ["blowjob"]}
- Handle NOT: "blowjob AND NOT elf" → {"operator": "AND", "tags": ["blowjob"], "exclude": ["elf"]}

**find_matching_images(parsed_query)**
- Get all images with first tag
- Filter by additional tags based on operator
- Return sorted list of image paths

**validate_query(query_string)**
- Check all tag names are valid
- Check syntax is valid
- Return True/False with error message

**list_available_tags()**
- Return all 80 tags with counts
- Sort by frequency

#### Testing Strategy
```python
def test_query_engine():
    # Test 1: Single tag
    results = engine.find_matching_images({"operator": "SINGLE", "tags": ["blowjob"]})
    assert len(results) == 2921

    # Test 2: AND query
    results = engine.find_matching_images({"operator": "AND", "tags": ["blowjob", "succubus"]})
    assert len(results) > 0
    assert all images have both tags

    # Test 3: OR query
    results = engine.find_matching_images({"operator": "OR", "tags": ["blowjob", "succubus"]})
    assert len(results) >= max(single tag results)

    # Test 4: NOT query
    results = engine.find_matching_images({"operator": "AND", "tags": ["blowjob"], "exclude": ["elf"]})
    assert no images have elf tag

    # Test 5: Invalid tag
    assert validate_query("nonexistent_tag") == False
```

### Phase 4.3: Implement Export Tool

**Goal:** Copy matching images and generate batch metadata

#### Core Classes
```python
class BatchExporter:
    def __init__(self, output_dir='./batch_exports')
    def export_images(image_paths, batch_name, mode='copy')
    def generate_manifest(batch_path, images, query)
    def create_batch_folder(batch_name) -> path
    def report_statistics(batch_path)
```

#### Methods Detail

**export_images(image_paths, batch_name, mode='copy')**
- Input: list of 2,921 image paths, batch name, copy/symlink mode
- Create batch folder: `./batch_exports/batch_20251020_blowjob/`
- Copy/symlink all images to folder
- Generate manifest.json
- Return batch path and statistics

**generate_manifest(batch_path, images, query)**
```json
{
  "batch_name": "batch_20251020_blowjob",
  "created": "2025-10-20T12:34:56",
  "query": "blowjob",
  "total_images": 2921,
  "manifest": {
    "images": [
      {"filename": "img1.jpg", "path": "..."},
      {"filename": "img2.png", "path": "..."}
    ]
  }
}
```

**create_batch_folder(batch_name)**
- Create timestamped folder: `batch_YYYYMMDD_HHMMSS_<name>/`
- Return path

**report_statistics(batch_path)**
```
Batch Export Summary
====================
Batch: batch_20251020_blowjob
Created: 2025-10-20 12:34:56
Query: blowjob

Statistics:
- Total images: 2,921
- Total size: 8.5 GB
- Export mode: copy
- Time taken: 45 seconds

Location: H:\batch_exports\batch_20251020_blowjob
Manifest: batch_20251020_blowjob\manifest.json
```

#### Export Modes
1. **Copy** (default): Physical copy of images
   - Safest, no dependencies on source
   - Slower, uses disk space
   - Best for: final batches

2. **Symlink** (advanced): Symbolic links to originals
   - Fast, minimal disk space
   - Works on Windows 10+
   - Best for: testing, preview

#### Testing Strategy
```python
def test_batch_exporter():
    # Test 1: Export single tag
    exporter.export_images(paths, "test_blowjob", mode='copy')
    assert folder exists
    assert files copied
    assert manifest created

    # Test 2: Check statistics
    stats = exporter.report_statistics(batch_path)
    assert stats['total_images'] == len(paths)

    # Test 3: Symlink mode
    exporter.export_images(paths, "test_symlink", mode='symlink')
    assert symlinks created
    assert files accessible through symlinks
```

### Phase 4.4: Create CLI Interface

**Goal:** User-friendly command-line interface

#### Command Structure
```
python export_batch.py <COMMAND> [OPTIONS]

Commands:
  query       - Show images matching query (dry-run)
  export      - Export matching images to batch folder
  list        - List all available tags
  help        - Show help
```

#### Command Examples

**Query Command**
```bash
python export_batch.py query --tags blowjob
python export_batch.py query --tags "blowjob AND succubus"

Output:
Query Results: "blowjob"
=======================
Found: 2,921 matching images

Sample images:
  - 00001-1234567890.jpg
  - 00002-1234567890.png
  - 00003-1234567890.jpg
  ...

Tip: Use 'export' command to save to batch folder
```

**Export Command**
```bash
python export_batch.py export --tags blowjob --output ./my_batch
python export_batch.py export --tags "blowjob OR succubus" --mode symlink

Output:
Exporting: "blowjob OR succubus"
==================================
Exporting 4,553 images...
[████████████████████░░░░░░░░░] 67%
Export complete!

Batch folder: H:\batch_exports\batch_20251020_blowjob_succubus
  - 4,553 images copied
  - manifest.json created
  - Ready for WAN 2.2 i2v

Location: batch_20251020_blowjob_succubus
```

**List Command**
```bash
python export_batch.py list

Output:
Available Tags (80 total)
==========================
  1. blowjob          - 2,921 images (38.1%)
  2. succubus         - 1,632 images (21.3%)
  3. girl             - 1,548 images (20.2%)
  4. 1girl            - 1,096 images (14.3%)
  5. kneeling         - 1,072 images (14.0%)
  ...
  80. hair_ribbon     - 7 images (0.1%)
```

#### Implementation Details
```python
import argparse
import logging

def main():
    parser = argparse.ArgumentParser(description='Query and export images by tags')
    subparsers = parser.add_subparsers(dest='command')

    # Query subcommand
    query_parser = subparsers.add_parser('query')
    query_parser.add_argument('--tags', required=True, help='Tag query')
    query_parser.add_argument('--limit', type=int, default=20, help='Show first N results')

    # Export subcommand
    export_parser = subparsers.add_parser('export')
    export_parser.add_argument('--tags', required=True, help='Tag query')
    export_parser.add_argument('--output', default='./batch_exports', help='Output directory')
    export_parser.add_argument('--mode', choices=['copy', 'symlink'], default='copy')
    export_parser.add_argument('--name', help='Custom batch name')

    # List subcommand
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--sort', choices=['name', 'count'], default='count')

    args = parser.parse_args()

    if args.command == 'query':
        do_query(args)
    elif args.command == 'export':
        do_export(args)
    elif args.command == 'list':
        do_list(args)
```

### Phase 4.5: Testing & Documentation

**Goal:** Validate tool works correctly and document usage

#### Test Scenarios
1. **Single tag exports**
   - Export blowjob (2,921 images)
   - Export succubus (1,632 images)
   - Export rare tag (7+ images)

2. **Combined queries**
   - AND: blowjob AND succubus
   - OR: blowjob OR succubus
   - NOT: blowjob AND NOT elf

3. **Error handling**
   - Unknown tag
   - Invalid syntax
   - Empty results
   - Disk space full

4. **Performance**
   - Simple query: <100ms
   - Complex AND: <500ms
   - Export 2,921 images: <30s

#### Documentation Needed
1. **README_EXPORT_TOOL.md**
   - Overview and purpose
   - Installation and setup
   - Command reference
   - Examples

2. **USAGE_EXAMPLES.md**
   - Common export scenarios
   - Tips and tricks
   - Troubleshooting

3. **Code comments**
   - Module docstrings
   - Function docstrings
   - Complex algorithm explanations

#### Test Plan
```python
def run_all_tests():
    print("=" * 70)
    print("PHASE 4: QUERY & EXPORT TOOL - TEST SUITE")
    print("=" * 70)

    # Part 1: Query Engine Tests
    test_query_engine()

    # Part 2: Batch Exporter Tests
    test_batch_exporter()

    # Part 3: CLI Tests
    test_cli_interface()

    # Part 4: Integration Tests
    test_end_to_end()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
```

## Success Criteria

### Functional Requirements
- ✓ Query single tags accurately
- ✓ Query AND combinations
- ✓ Query OR combinations
- ✓ Query NOT exclusions
- ✓ Export images to batch folder
- ✓ Generate batch manifests
- ✓ Report statistics accurately
- ✓ Handle errors gracefully

### Performance Requirements
- ✓ Simple query: <100ms
- ✓ Complex query: <500ms
- ✓ Export 2,921 images: <30s
- ✓ CLI responsive to user input

### Quality Requirements
- ✓ No data loss during export
- ✓ Batch folders independently usable
- ✓ Manifests accurate and useful
- ✓ Error messages helpful
- ✓ Code well-documented

### User Experience
- ✓ Simple command syntax
- ✓ Clear output/feedback
- ✓ Helpful error messages
- ✓ Good documentation

## Files to Create

### Core Implementation
- `tag_query_engine.py` - Query parsing and matching
- `batch_exporter.py` - Image export and manifest generation
- `export_batch.py` - CLI interface (main entry point)

### Testing
- `test_query_engine.py` - Query engine tests
- `test_batch_exporter.py` - Export tool tests
- `test_export_batch_cli.py` - CLI tests

### Documentation
- `README_EXPORT_TOOL.md` - User guide
- `USAGE_EXAMPLES.md` - Practical examples
- Inline code documentation

## Timeline Estimate

| Phase | Task | Est. Time |
|-------|------|-----------|
| 4.1 | Design query engine | 30 min |
| 4.2 | Implement query engine | 45 min |
| 4.3 | Implement export tool | 45 min |
| 4.4 | Create CLI interface | 30 min |
| 4.5 | Testing & documentation | 60 min |
| **Total** | | **3.5 hours** |

## Success Indicators

When Phase 4 is complete, user will be able to:
1. Query: `python export_batch.py query --tags blowjob`
   - See 2,921 results instantly
2. Export: `python export_batch.py export --tags "blowjob AND succubus"`
   - Get temporary batch folder ready for WAN 2.2
3. Iterate: Create multiple batch exports for different clip sets
   - Fast, non-destructive, flexible

---

**Next Step:** Approve this plan, then proceed with Phase 4.1 (Design)
