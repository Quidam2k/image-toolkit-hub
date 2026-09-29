"""
Centralized Help Text and Tooltips for Image Toolkit Hub

All user-facing tooltip and help text strings in one place for consistency
and easy maintenance.

Author: Claude Code Implementation
Version: 1.0
"""

# ============================================================================
# TOOLTIPS - Short hover text for UI elements
# ============================================================================

TOOLTIPS = {
    # -------------------------------------------------------------------------
    # Hub Tool Cards
    # -------------------------------------------------------------------------
    'card_manual_sorter': (
        "Visual grid for sorting images into 3 categories.\n\n"
        "Keyboard shortcuts:\n"
        "  1 / Left-click = Sort to folder 1\n"
        "  2 / Mouse4 = Sort to folder 2\n"
        "  3 / Mouse5 = Sort to folder 3\n"
        "  Space / Right-click = Next page\n"
        "  R = Reload images\n"
        "  Shift+R = Open Image Ranker"
    ),

    'card_auto_sort': (
        "Automatically organize images based on metadata tags.\n\n"
        "Searches image prompts and .txt tag files for matching terms.\n"
        "Supports word boundary, substring, and regex matching.\n"
        "Multi-tag mode copies images to multiple folders when they\n"
        "match multiple terms."
    ),

    'card_auto_tag': (
        "Generate descriptive tags using WD14 AI model.\n\n"
        "Analyzes image content and writes tags to .txt files.\n"
        "Original image files are never modified.\n"
        "Tags can then be used for auto-sort or search."
    ),

    'card_visual_sort': (
        "Sort by shot type, person count, or content rating.\n\n"
        "Uses WD14 tagger to classify images:\n"
        "  Shot types: closeup, portrait, cowboy shot, full body, etc.\n"
        "  Person count: solo, duo, group\n"
        "  Rating: general, sensitive, questionable, explicit"
    ),

    'card_tshirt_finder': (
        "Find images with simple backgrounds for print-on-demand.\n\n"
        "Identifies images that would work well on t-shirts by looking\n"
        "for solid or simple backgrounds and centered subjects."
    ),

    'card_image_ranker': (
        "Find your best images using pairwise comparison.\n\n"
        "Uses OpenSkill algorithm (Plackett-Luce model) which:\n"
        "  - Tracks skill estimate and uncertainty\n"
        "  - Makes transitive inferences\n"
        "  - Prioritizes uncertain matchups\n\n"
        "Typically needs 0.5-1 comparisons per image for ranking."
    ),

    'card_batch_export': (
        "Query and export images by tags.\n\n"
        "Search your collection using tag queries and export\n"
        "matching images to a folder. Useful for WAN i2v workflows."
    ),

    'card_tag_database': (
        "Manage the tag frequency database.\n\n"
        "Rebuilds the database by scanning all images and extracting\n"
        "tags. Use this when you've added many new images or changed\n"
        "your tagging approach."
    ),

    # -------------------------------------------------------------------------
    # Settings Panel
    # -------------------------------------------------------------------------
    'setting_grid_rows': (
        "Number of image rows displayed in the grid.\n"
        "More rows = smaller thumbnails but more images visible."
    ),

    'setting_random_order': (
        "Shuffle images randomly instead of alphabetical order.\n"
        "Helps avoid bias when sorting similar images."
    ),

    'setting_copy_mode': (
        "Copy files instead of moving them.\n\n"
        "Original files remain in place - safer but uses more disk space.\n"
        "Enable 'Hide already-sorted' to avoid seeing duplicates."
    ),

    'setting_include_subfolders': (
        "Scan subdirectories recursively for images.\n"
        "Disable to only process images in the top-level folder."
    ),

    'setting_handle_tag_files': (
        "Move/copy companion .txt files with their images.\n"
        "Keeps tag files together with the images they describe."
    ),

    'setting_hover_tip_delay': (
        "Seconds to hover over a grid image before its prompt\n"
        "tooltip appears.\n\n"
        "The tooltip opens over a neighbouring image, never over\n"
        "the one you're pointing at. 0 = show immediately."
    ),

    'setting_hide_already_sorted': (
        "Skip images already in destination folders.\n\n"
        "Only works in copy mode. Allows multi-session sorting\n"
        "without seeing the same images repeatedly."
    ),

    # -------------------------------------------------------------------------
    # Source Folders Panel
    # -------------------------------------------------------------------------
    'source_folder_add': "Add a new folder to scan for images.",
    'source_folder_checkbox': "Enable or disable this folder without removing it from the list.",
    'source_folder_remove': "Remove this folder from the source list.",

    # -------------------------------------------------------------------------
    # Output Folders Panel
    # -------------------------------------------------------------------------
    'output_folder_row': "Click to select this folder for processing.",
    'output_clear_removed': (
        "Move all files in 'removed/' to the Recycle Bin.\n"
        "Files can be recovered from the Recycle Bin if needed."
    ),
    'output_refresh': "Rescan output folders to update counts and sizes.",
    'output_warning': (
        "This folder has grown large.\n"
        "Consider clearing it to free up disk space."
    ),

    # -------------------------------------------------------------------------
    # Auto-Tag Dialog
    # -------------------------------------------------------------------------
    'autotag_source_active': "Tag images in your configured source folders.",
    'autotag_source_output': "Tag images in output folders (1/, 2/, 3/).",
    'autotag_source_custom': "Select a specific folder to tag.",
    'autotag_include_subfolders': "Process images in subdirectories as well.",
    'autotag_retag_existing': (
        "Re-generate tags for images that already have .txt files.\n"
        "By default, images with existing tags are skipped."
    ),
    'autotag_threshold': (
        "Minimum confidence threshold for including a tag.\n"
        "Lower = more tags but potentially less accurate.\n"
        "Default: 0.35 (35% confidence)"
    ),

    # -------------------------------------------------------------------------
    # Term Manager
    # -------------------------------------------------------------------------
    'term_enabled': "Enable or disable this term for auto-sorting.",
    'term_match_type': (
        "How to match the search term:\n"
        "  Word boundary: Matches whole words only\n"
        "  Substring: Matches anywhere in text\n"
        "  Regex: Regular expression pattern"
    ),
    'term_search_scope': (
        "Where to search for the term:\n"
        "  Prompt: Image metadata/embedded prompt\n"
        "  Tags: Companion .txt tag files\n"
        "  Either: Match in prompt OR tags\n"
        "  Both: Must match in prompt AND tags"
    ),
    'term_priority': (
        "Higher priority terms take precedence in conflicts.\n"
        "When an image matches multiple terms, higher priority wins\n"
        "(unless multi-copy is enabled)."
    ),
    'term_allow_multi_copy': (
        "Allow this term to create copies alongside other matches.\n"
        "When enabled, images can appear in multiple folders."
    ),
}

# ============================================================================
# HELP DIALOGS - Longer explanatory text for help screens
# ============================================================================

HELP_DIALOGS = {
    'auto_tag_guide': """
Auto-Tag uses the WD14 model to analyze images and generate descriptive tags.

HOW IT WORKS:
1. Each image is processed through the WD14 neural network
2. The model identifies visual elements with confidence scores
3. Tags above the threshold are written to a .txt file

IMPORTANT:
- Original image files are NEVER modified
- Tags are saved to companion .txt files (image.png -> image.png.txt)
- Existing prompts in image metadata are preserved

WHEN TO USE:
- After importing new images that lack tags
- To improve auto-sort accuracy with visual descriptors
- Before building/updating the tag database

THRESHOLD GUIDE:
- 0.5+ : High confidence, fewer but more accurate tags
- 0.35 : Balanced (default)
- 0.2  : More tags, may include less certain matches
""",

    'output_folders_guide': """
Output folders are where sorted images go after manual sorting.

FOLDER STRUCTURE:
- 1/ : First category (left-click or press 1)
- 2/ : Second category (mouse button 4 or press 2)
- 3/ : Third category (mouse button 5 or press 3)
- removed/ : Images you've dismissed

CLEARING REMOVED:
The 'removed/' folder can grow large over time. Use 'Clear Removed'
to send these files to the Recycle Bin, freeing disk space while
still allowing recovery if needed.

PROCESSING OUTPUT FOLDERS:
You can run Auto-Tag or other tools on output folders to further
process your sorted images.
""",

    'multi_tag_modes': """
Multi-tag modes control how images matching multiple terms are handled.

MODES:
- Single Folder: First match wins (uses priority to resolve conflicts)
- Multi Folder: Creates separate copy for each matching term
- Smart Combination: Combines tags using predefined logic
- All Combinations: Individual folders + all valid combinations

EXAMPLE (All Combinations):
Image matches: [cowgirl, fellatio]
Creates copies in:
  - cowgirl/
  - fellatio/
  - cowgirl_fellatio/

This mode uses the most disk space but provides maximum organization.
""",
}


def get_tooltip(key: str) -> str:
    """
    Get tooltip text by key, with fallback.

    Args:
        key: The tooltip key

    Returns:
        Tooltip text or empty string if not found
    """
    return TOOLTIPS.get(key, "")


def get_help(key: str) -> str:
    """
    Get help dialog text by key.

    Args:
        key: The help dialog key

    Returns:
        Help text or empty string if not found
    """
    return HELP_DIALOGS.get(key, "")
