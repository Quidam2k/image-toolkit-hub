# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Enhanced Image Grid Sorter** - A comprehensive Python/Tkinter application for visually sorting and organizing large image collections with AI-powered auto-sorting capabilities. The tool processes tens of thousands of images using metadata-based term matching, multi-tag support, and intelligent categorization.

**Current Version:** 2.1 (includes all_combinations mode and re-sort functionality)

## Development Commands

### Running the Application

```bash
# Start via Windows batch file (recommended for users)
start.bat

# Start directly via Python
python image_sorter_enhanced.py
```

### Running Tests

```bash
# Test auto-sort functionality
python tests/test_auto_sort.py

# Test module imports
python tests/test_imports.py

# Test tag embedder functionality
python tests/tag_embedder_tester.py
```

### Development Utilities

```bash
# Install/update required packages
python scripts/install_piexif.py

# Quick metadata backup
python scripts/quick_prompt_backup.py

# Test metadata parser
python metadata_parser.py
```

## Project Structure (Updated November 2025)

```
image_grid_sorter/
├── *.py                    # Core application modules (main files)
├── tests/                  # Test files
├── scripts/                # Utility and one-off scripts
├── docs/                   # Documentation
│   └── sessions/           # Session notes
├── logs/                   # Log files
├── data/                   # Data files (tag_frequency.json, vocabularies)
├── archive/                # Old/deprecated files
├── models/                 # ML models (CLIP)
├── backups/                # Config backups
├── 1/, 2/, 3/, removed/    # Manual sorting destinations
├── auto_sorted/            # Auto-sort output
└── sorted_*/               # Source-specific sorted outputs
```

## Architecture Overview

### Core Module Organization

The application follows a modular architecture with clear separation of concerns:

**Main Application Layer:**
- `image_sorter_enhanced.py` - Main application entry point with full UI
  - Grid-based image display with keyboard/mouse controls
  - Menu system (File, Tools, Help)
  - Threading for async operations
  - Tkinter event loop management

**Configuration & State Management:**
- `config_manager.py` - JSON-based configuration with migration support
  - Version 2.1 with backward compatibility
  - Auto-save on changes with backup creation
  - Supports all multi-tag modes: `single_folder`, `multi_folder`, `smart_combination`, `all_combinations`
  - Default `multi_tag_mode: "all_combinations"` (images appear in individual + combination folders)

**Auto-Sorting Engine:**
- `auto_sorter.py` - Core sorting logic and re-sort functionality
  - `sort_by_metadata()` - Main sorting with progress callbacks
  - `resort_auto_sorted()` - Re-sort existing collections with updated rules
  - Comprehensive error tracking and statistics
  - File movement tracking for potential undo operations
  - Supports exclusion rules, priority handling, and search scope control

**Metadata & Parsing:**
- `metadata_parser.py` - Image metadata extraction
  - Reads embedded prompts from AI-generated images
  - Parses tag files (.txt) accompanying images
  - Handles both positive and negative prompts
  - Caching layer for performance optimization

**UI Dialogs & Components:**
- `setup_dialog.py` - Configuration and settings UI
- `term_manager.py` - UI for managing auto-sort terms
- `auto_sort_progress.py` - Progress tracking dialog with pause/resume/cancel
- `auto_sort_confirm.py` - Pre-sort confirmation with statistics
- `auto_sort_review.py` - Post-sort review with results summary
- `tag_embed_progress.py` - Progress for tag file embedding

**Tag Generation & Analysis (NEW - October 2025):**
- `tag_generator.py` - Generate descriptive tags using CLIP Vision model
  - Analyzes image content with CLIP
  - Extracts tags from image prompts
  - Combines both sources for comprehensive tagging
  - Saves tags ONLY to .txt files (never modifies images directly)
- `tag_extractor.py` - Extract and deduplicate tags from multiple sources
  - Gets CLIP-generated tags from images
  - Extracts tags from prompts
  - Intelligent deduplication (removes redundant tags, tracks sources)
  - Returns clean tag lists with source information
- `tag_frequency_database.py` - Build comprehensive tag frequency database
  - Scans all images and extracts tags
  - Tracks tag frequency across collection
  - Identifies underrepresented tags
  - Generates frequency reports and statistics
  - Outputs `tag_frequency.json` with complete tag database

**Utility Modules:**
- `prompt_manager.py` - Prompt/metadata file handling
- `tag_embedder.py` - Embedding tag files into image metadata
  - Safety checks to preserve existing prompts
  - Multiple embedding strategies (PNG, JPEG with piexif)
  - Backup creation before modification
- `prompt_recovery.py` - Recovery utilities for metadata operations

### Data Flow

1. **Image Loading** → `load_images()` in `image_sorter_enhanced.py` recursively scans folders
2. **Configuration Load** → `ConfigManager` reads `imagesorter_config.json` with defaults
3. **Display** → Grid renders images from current page with Tkinter canvas
4. **User Interaction** → Mouse clicks (1/2/3/right) or keyboard (1/2/3/space) invoke sorting
5. **Auto-Sort** → `AutoSorter.sort_by_metadata()` matches terms against metadata, moves files
6. **Multi-Tag Handling** → Based on mode (all_combinations copies to multiple folders, smart_combination uses logic)

### Key Configuration File Structure

`imagesorter_config.json` contains:
- `source_folders` - Array of directories to scan for images
- `active_sources` - Boolean map for enabling/disabling sources
- `destination_location` - 'script_dir' or 'source_dirs' for output placement
- `auto_sort_terms` - Array of search terms with properties:
  - `term` - Search string
  - `folder_name` - Output folder name
  - `match_type` - 'word_boundary', 'substring', or 'regex'
  - `search_scope` - 'prompt', 'tags', 'either', or 'both'
  - `priority` - Integer for conflict resolution
  - `exclusion_terms` - Terms that prevent this match
  - `allow_multi_copy` - Allow image to appear in multiple category folders
- `auto_sort_settings` - Sorting behavior and modes
- `metadata_cache` - Caching configuration
- `ui_preferences` - UI customization options
  - `hide_already_sorted` - Filter out images already in destination folders (copy mode)

## Multi-Session Sorting (November 2025)

When using copy mode, the application can filter out images that have already been copied to destination folders. This allows working through large collections over multiple sessions without seeing the same images repeatedly.

**Settings:**
- Enable "Copy (don't move)" mode
- Enable "Hide already-copied images" checkbox (default: on)

**Behavior:**
- At load time, scans destination folders (1/, 2/, 3/) for existing filenames
- Filters source images whose basenames match (case-insensitive)
- Console shows count of filtered images

## Multi-Tag Modes

The application supports four multi-tag sorting strategies:

- **`single_folder`** - First matching term only (conflict resolution by priority)
- **`multi_folder`** - All matched terms get independent copies
- **`smart_combination`** - Combines matching terms based on predefined logic
- **`all_combinations`** (DEFAULT) - Every matching term appears individually PLUS all valid combinations

Example with all_combinations: Image with ["cowgirl", "fellatio"] appears in:
- `cowgirl/` (individual)
- `fellatio/` (individual)
- `cowgirl_fellatio/` (combination)

## Important Development Notes

### User Configuration
The active configuration has 12 enabled terms (cowgirl, deepthroat, fellatio, etc.) all using:
- `search_scope: "either"` (search in both prompt and tags)
- `allow_multi_copy: true` (allows multiple folder placement)
- `match_type: "word_boundary"`

### Windows Environment Considerations
- Always use Path operations that work on Windows (/ or \\ paths)
- The application uses `start.bat` for user-friendly launching
- Be careful with the `start` command - `start /B python` opens Explorer, not Python

### Testing the Application
Before claiming something is "fixed or ready":
1. Run the application yourself: `python image_sorter_enhanced.py`
2. Test the specific feature with actual images (if applicable)
3. Verify configuration persists across restarts
4. Check that threading operations don't block UI
5. Confirm no unhandled exceptions in the terminal

### Project Success Metrics
- User has successfully processed **tens of thousands of images**
- All 12 configured terms actively used with multi-tag features
- Multi-tag mode working reliably at scale
- Re-sort functionality proven stable for collection updates

## Known Workflows & Common Tasks

### Adding a New Auto-Sort Term
1. User opens "Term Manager" from menu (Ctrl+T or File menu)
2. Term Manager dialog in `term_manager.py` handles UI
3. New term written to config via `ConfigManager.set_auto_sort_terms()`
4. Automatic backup created before save
5. User can immediately run auto-sort with new term

### Re-Sorting Existing Collection
1. User goes to File → "Re-sort Auto-Sorted Images..."
2. Calls `AutoSorter.resort_auto_sorted()`
3. Scans auto_sorted folder for existing categorized images
4. Re-evaluates each against current/updated terms
5. Progress dialog shows real-time feedback
6. Can pause, resume, or cancel operation

### Manual Sorting Workflow
1. Grid displays images in configured number of rows
2. Left-click or press '1' → Sort to category 1
3. Right-click or press space → Next page
4. Mouse button 4 or press '2' → Sort to category 2
5. Mouse button 5 or press '3' → Sort to category 3
6. Press 'r' → Reload images from disk
7. Press 'R' (Shift+R) → Open ranker with category 1 folder
8. Ctrl+A → Start auto-sort process
9. Press Escape → Exit application

Note: Settings/configuration are now managed in the Hub, not via keyboard shortcut.

### Metadata Inspection
- Tools menu → "Scan Metadata" - Batch inspect image metadata/prompts
- Shows which prompts/tags are in current image batch
- Helps identify search terms needed for auto-sort

## Code Quality & Patterns

### Logging
All modules use Python logging with module-level loggers:
```python
logger = logging.getLogger(__name__)
```
This allows debugging specific modules without excessive console spam.

### Threading
Long operations (auto-sort, tag embedding) run on separate threads to keep UI responsive:
- All file operations happen on worker threads
- Progress callbacks marshal updates to main thread
- Support pause/resume/cancel flags

### Error Handling
- Comprehensive try/except blocks around file operations
- Error categorization: file_access, permission, format, processing, etc.
- Detailed error reporting in progress dialogs
- Graceful degradation for partial failures

### Configuration Validation
`ConfigManager` validates all loaded settings:
- Ensures folder paths exist or are skippable
- Validates term configurations have required fields
- Migrates legacy INI format to JSON automatically
- Creates backups before modification

## Performance Considerations

- **Metadata Caching**: Enabled by default, 10,000 entry cache, 30-day expiration
- **Image Loading**: Handles up to 300MP images without decompression warnings
- **Grid Rendering**: Only displays current page (configurable rows)
- **Multi-Threading**: Auto-sort and tag embedding run async to prevent UI freeze
- **Memory Management**: Garbage collection calls after grid updates

## New Tag Generation & Analysis Pipeline (October 2025)

### Overview
A complete end-to-end pipeline for analyzing image collections with CLIP Vision model. Enables data-driven decisions for auto-sort configuration.

### Pipeline Workflow

**Phase 1: Tag Frequency Database**
- Scans existing auto-sorted collection
- Extracts CLIP tags + prompt tags from all images
- Deduplicates intelligently (tracks source of each tag)
- Builds `tag_frequency.json` with complete database
- Generates frequency reports identifying most common tags

**Phase 2: Process New Batch** (4,368 images)
- Generate CLIP descriptive tags for all new images
- Extract tags from image prompts (deduplicated)
- Embed tags into image metadata while **preserving original prompts**
- Verify prompt preservation on sample (10 images)
- All operations safe: tags go to .txt files first, embedder has safety checks

**Phase 3: Analyze Combined Distribution**
- Add new batch tags to frequency database
- Generate combined reports (existing + new)
- Identify underrepresented tags
- Create recommendations for auto-sort term configuration

**Phase 4: Improve Multi-Tag Distribution Logic**
- Analyze current priority-based sorting behavior
- Design balanced distribution algorithm (soften priority when folders become imbalanced)
- Implement improved logic in `config_manager.py`
- Test on existing collection, generate before/after comparison

### Key Files & Scripts

**Testing & Validation:**
- `test_tag_pipeline.py` - Comprehensive pipeline safety test
- `test_frequency_database.py` - Database creation and reporting
- `prompt_preservation_audit.py` - Validates prompt safety during embedding

**Processing:**
- `process_new_batch.py` - Master Phase 2 script for batch processing
- `tag_generator.py` - CLIP-based tag generation
- `tag_extractor.py` - Multi-source tag extraction with deduplication
- `tag_frequency_database.py` - Frequency database builder

### CLIP Vision Model
- Location: `./models/clip_vision_model.safetensors` (3.9GB)
- Model: `wan21NSFWClipVisionH_v10` (trained for descriptive image analysis)
- Analyzes image content and generates descriptive tags
- Fast on CPU once loaded (processes 4,000+ images in 20-30 minutes)

### Performance Notes
- Tag generation: ~1 image/second on CPU
- Frequency scanning: ~1 image/second on CPU
- Full batch processing (4,368 images): 20-30 minutes
- Database operations fast (JSON-based)

## Image Ranker - Pairwise Comparison Ranking (January 2026)

### Purpose
Identify cream-of-the-crop images from large collections using pairwise comparison. Uses the OpenSkill algorithm (Plackett-Luce model) which tracks both skill estimate (mu) and uncertainty (sigma), enabling smart pair selection and transitive inference.

### Key Files
- `image_ranker.py` - Core ranking logic with OpenSkill integration, SQLite persistence, and project management functions
- `image_ranker_dialog.py` - Tkinter UI for side-by-side comparison with project switching
- `rankings_view_dialog.py` - Leaderboard view with export functionality

### Features
- **OpenSkill Algorithm**: Superior to basic Elo - tracks uncertainty, makes transitive inferences
- **Smart Pairing**: Prioritizes uncertain images and similar skill levels for efficient ranking
- **Multi-Project Support**: Separate ranking databases per project (e.g., rank "MJ 2025" independently from "MJ All Years")
- **SQLite Persistence**: Rankings survive sessions, stored in `data/rankings_[project].db`
- **Export**: Top-N images to folder (with rank prefix), CSV export of all rankings
- **Keyboard-Driven**: 1/Left = left wins, 2/Right = right wins, S = skip, U = undo

### Project Management
- **Project dropdown** in toolbar shows all projects with image counts
- **New button**: Create fresh project for different image sets
- **Save As button**: Name current rankings or copy to new project
- Projects stored as `data/rankings_[name].db`
- Same image can exist in multiple projects with different rankings

### Workflow
1. Open via Tools menu -> "Image Ranker..."
2. Select or create a project from dropdown
3. Add folder(s) containing images to rank (recursive by default)
4. Compare pairs using keyboard shortcuts
5. View rankings and export top images when ready

### Algorithm Details
- Default rating: mu=25, sigma=8.33
- Ordinal score (conservative estimate): mu - 3*sigma
- Stability indicator shows when rankings are reliable
- ~0.5-1 comparisons per image needed for basic ranking

### Performance Notes (for large collections 20k+ images)
- Pair selection uses SQL LIMIT to sample 500 candidates (not all images)
- File existence only checked on selected pair (2 files), not entire collection
- Async image loading with preloading for smooth transitions
- Tested with 26k images - pair selection is instant after initial load

## Visual Classification for WAN Video LoRA First Frames (December 2025)

### Purpose
When using WAN video LoRAs that depict specific actions (e.g., running, dancing, etc.), not all images make good first frames. The visual classifier helps sort through image collections to find suitable starting images for video generation with action-specific LoRAs.

### Key Files
- `visual_classifier.py` - Core classification logic using WD14 tagger
- `visual_sort_dialog.py` - UI dialog for visual sorting operations

### Classification Categories
- **Shot Type**: extreme_closeup, portrait, upper_body, cowboy_shot, full_body, wide_shot
- **Person Count**: solo, duo, group, none
- **NSFW Rating**: general, sensitive, questionable, explicit

### Features
- LoRA profile filtering with custom profiles (saved to `data/lora_profiles.json`)
- Preview/scan functionality before sorting
- WD14 tagger integration for visual analysis

---

## Future Improvement Areas (from FUTURE_CLAUDE_NOTES.md)

1. **Unmatched Images Handling** - Move unsorted images to unmatched folder
2. **Workflow Enhancements** - Better diagnostic logging, batch metadata improvements
3. **UX Improvements** - Tooltips, help documentation, performance monitoring
4. **Multi-Tag Optimization** - Balanced distribution algorithm implementation (in progress)

## UI Redesign Plan (January 2026)

**When user says "fix the UX" or asks about UI improvements, refer to: `docs/UI_REDESIGN_PLAN.md`**

Key issues identified:
- Current dark navy + purple color scheme feels dated ("Discord aesthetic")
- Duplicated `ModernStyle` class in multiple files
- Modal-heavy architecture (dialog-on-dialog) is clunky

Proposed solutions in the plan:
- New neutral color scheme following 60-30-10 rule
- Shared `ui_theme.py` module (single source of truth)
- Optional single-window architecture with tabs/modes instead of modals

---

Last Updated: January 17, 2026
- **Image Ranker multi-project support**: Separate ranking databases per project, dropdown selector, New/Save As buttons
- **Image Ranker performance fix**: Fixed 26k image slowdown - was doing 26k filesystem checks per pair, now only checks 2
- **Grid sorter bug fix**: Fixed preloaded images being silently discarded when rows were full (caused image count to drop by hundreds on page navigation)
- Image Ranker UI improvements: loading indicator, subfolder path display, fixed Clear All

Previous updates (January 8, 2026):
- Added UI Redesign Plan reference (docs/UI_REDESIGN_PLAN.md) - "fix the UX" trigger
- Added Image Ranker for pairwise comparison ranking using OpenSkill algorithm
- Added Visual Classification system for WAN video LoRA first frame selection
- Project reorganization (tests/, scripts/, docs/, data/, logs/, archive/ folders)
- Multi-session sorting feature (hide already-copied images)
