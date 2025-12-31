# Auto-Sort Feature Specification

## Feature Overview
Automatically sort images based on metadata content, specifically targeting terms found in Stable Diffusion generation parameters.

## User Workflow

### 1. Term Configuration
- User defines search terms through the settings dialog
- Terms can be added, removed, and reordered
- Each term becomes a potential destination subfolder
- Terms are case-insensitive by default

### 2. Auto-Sort Operation
- User initiates auto-sort from menu or button
- System scans all images in active source folders
- Metadata is extracted and parsed for each image
- Images are sorted into subfolders based on matching terms
- Progress is displayed with cancellation option

### 3. Conflict Resolution
- Multiple term matches: User-configurable priority order
- No matches: Move to "unmatched" folder or leave in place
- Existing files: Auto-rename with numeric suffix

## Implementation Components

### Term Management System

```python
class TermManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.terms = self.load_terms()
    
    def add_term(self, term):
        """Add a new search term."""
        pass
    
    def remove_term(self, term):
        """Remove a search term."""
        pass
    
    def reorder_terms(self, new_order):
        """Change term priority order."""
        pass
    
    def get_terms(self):
        """Get current list of terms in priority order."""
        pass
```

### Auto-Sorter Engine

```python
class AutoSorter:
    def __init__(self, config_manager, metadata_parser, progress_callback=None):
        self.config_manager = config_manager
        self.metadata_parser = metadata_parser
        self.progress_callback = progress_callback
        self.cancelled = False
    
    def sort_by_metadata(self, source_folders, terms):
        """Sort images based on metadata terms."""
        pass
    
    def process_image(self, image_path, terms):
        """Process a single image for auto-sorting."""
        pass
    
    def cancel_operation(self):
        """Cancel the current sorting operation."""
        pass
```

## Folder Structure

### Auto-Sort Output Organization
```
destination_folder/
├── auto_sorted/
│   ├── term1/
│   ├── term2/
│   ├── term3/
│   └── unmatched/
└── manual_sorted/
    ├── 1/
    ├── 2/
    ├── 3/
    └── removed/
```

### Configuration Structure
```json
{
  "auto_sort_terms": [
    {
      "term": "portrait",
      "enabled": true,
      "priority": 1
    },
    {
      "term": "landscape",
      "enabled": true,
      "priority": 2
    }
  ],
  "auto_sort_settings": {
    "create_unmatched_folder": true,
    "handle_multiple_matches": "first_match",
    "case_sensitive": false,
    "word_boundaries": true
  }
}
```

## UI Integration

### Settings Dialog Extensions
- New "Auto-Sort" tab in settings dialog
- Term list with add/remove/reorder functionality
- Options for matching behavior and conflict resolution
- Preview functionality to test terms against sample images

### Main Window Additions
- "Auto-Sort" button in toolbar or menu
- Progress dialog for auto-sort operations
- Integration with existing undo system for auto-sort operations

### Progress Dialog
```python
class AutoSortProgressDialog(tk.Toplevel):
    def __init__(self, parent, total_images):
        super().__init__(parent)
        self.setup_ui(total_images)
    
    def update_progress(self, current, total, current_file=""):
        """Update progress bar and status."""
        pass
    
    def set_cancellable(self, can_cancel):
        """Enable/disable cancel button."""
        pass
```

## Matching Algorithms

### Basic Text Matching
```python
def basic_match(self, text, term, case_sensitive=False, word_boundaries=True):
    """Basic string matching with options."""
    if not case_sensitive:
        text = text.lower()
        term = term.lower()
    
    if word_boundaries:
        import re
        pattern = r'\b' + re.escape(term) + r'\b'
        return bool(re.search(pattern, text))
    else:
        return term in text
```

### Advanced Pattern Matching
```python
def pattern_match(self, text, pattern):
    """Regex pattern matching for complex terms."""
    import re
    try:
        return bool(re.search(pattern, text, re.IGNORECASE))
    except re.error:
        return False
```

### Tag-Based Matching
```python
def tag_match(self, prompt, tags):
    """Match specific tags in comma-separated prompts."""
    prompt_tags = [tag.strip() for tag in prompt.split(',')]
    return any(tag.lower() in [t.lower() for t in prompt_tags] for tag in tags)
```

## Conflict Resolution Strategies

### Multiple Matches
1. **First Match**: Use the first matching term in priority order
2. **Most Specific**: Use the longest/most specific matching term
3. **Duplicate**: Copy image to all matching term folders
4. **User Choice**: Prompt user for each conflict

### File Naming Conflicts
1. **Auto-rename**: Add numeric suffix (file_1.jpg, file_2.jpg)
2. **Skip**: Leave file in original location
3. **Overwrite**: Replace existing file (with confirmation)

## Integration with Existing System

### Undo Support
- Track auto-sort operations in undo history
- Support batch undo for entire auto-sort operations
- Maintain undo compatibility with manual sorting

### Configuration Persistence
- Save auto-sort terms in existing config file
- Maintain backward compatibility
- Support import/export of term lists

### Performance Optimization
- Background processing with progress updates
- Metadata caching to avoid re-parsing
- Batch file operations for efficiency

## Error Handling

### Common Error Scenarios
1. **Metadata parsing failures**: Log and continue
2. **File access errors**: Retry and report
3. **Disk space issues**: Warn and stop operation
4. **Permission errors**: Report specific files and continue

### Logging and Reporting
- Detailed operation log for debugging
- Summary report of sorting results
- Error report with failed files and reasons

## Testing Strategy

### Unit Tests
- Metadata parser with various image formats
- Term matching algorithms with edge cases
- File operation error handling

### Integration Tests
- Full auto-sort workflow with sample images
- UI interaction testing
- Configuration persistence testing

### Performance Tests
- Large batch processing (1000+ images)
- Memory usage during extended operations
- Thread safety and cancellation handling