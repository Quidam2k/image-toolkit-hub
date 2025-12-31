# Implementation Plan - Auto-Sort Feature

## Overview
This document provides a step-by-step implementation plan for adding metadata-based auto-sorting functionality to the Image Sorter application.

## Phase 1: Core Infrastructure (Priority: High)

### Step 1.1: Create Metadata Parser Module
**File:** `metadata_parser.py`

```python
# Core functionality to implement:
class MetadataParser:
    def __init__(self):
        self.cache = {}
        self.supported_formats = ['.png', '.jpg', '.jpeg']
    
    def extract_metadata(self, image_path):
        """Main entry point for metadata extraction."""
        # Check cache first
        # Determine file type and call appropriate extractor
        # Parse and structure the metadata
        # Cache the results
        pass
    
    def extract_png_metadata(self, image_path):
        """Extract PNG text chunks containing SD metadata."""
        pass
    
    def extract_jpeg_metadata(self, image_path):
        """Extract JPEG EXIF data containing SD metadata."""
        pass
    
    def parse_sd_parameters(self, param_string):
        """Parse Stable Diffusion parameter string."""
        pass
```

**Dependencies to add:**
- PIL/Pillow (already in use)
- `json` for metadata structure
- `re` for text parsing

### Step 1.2: Extend Configuration Manager
**File:** `config_manager.py` (modify existing)

```python
# Methods to add to existing ConfigManager class:
def get_auto_sort_terms(self):
    """Get configured auto-sort terms."""
    pass

def add_auto_sort_term(self, term, **kwargs):
    """Add new auto-sort term."""
    pass

def setup_auto_sort_folders(self):
    """Create auto-sort destination folders."""
    pass

def migrate_config(self, old_config, from_version):
    """Handle configuration version migration."""
    pass
```

**Configuration schema updates:**
- Add auto_sort_terms array
- Add auto_sort_settings object
- Add metadata_cache settings
- Update output_folders with auto_sorted

### Step 1.3: Create Auto-Sorter Engine
**File:** `auto_sorter.py`

```python
class AutoSorter:
    def __init__(self, config_manager, metadata_parser):
        self.config_manager = config_manager
        self.metadata_parser = metadata_parser
        self.cancelled = False
        self.paused = False
    
    def sort_by_metadata(self, source_folders, progress_callback=None):
        """Main auto-sort operation."""
        pass
    
    def process_image(self, image_path, terms):
        """Process single image for auto-sorting."""
        pass
    
    def find_matching_terms(self, metadata, terms):
        """Find which terms match the image metadata."""
        pass
    
    def resolve_conflicts(self, matches, strategy):
        """Handle multiple term matches."""
        pass
```

## Phase 2: User Interface Integration (Priority: High)

### Step 2.1: Extend Settings Dialog
**File:** `config_dialog.py` (modify existing)

```python
# Methods to add to ConfigDialog class:
def create_auto_sort_tab(self):
    """Create auto-sort configuration tab."""
    pass

def create_terms_list(self, parent):
    """Create terms management interface."""
    pass

def add_term(self):
    """Handle adding new term."""
    pass

def remove_term(self):
    """Handle removing selected term."""
    pass

def test_terms(self):
    """Open term testing dialog."""
    pass
```

### Step 2.2: Update UI Manager
**File:** `ui_manager.py` (modify existing)

```python
# Methods to add to UIManager class:
def setup_auto_sort_toolbar(self):
    """Add auto-sort controls to main window."""
    pass

def setup_auto_sort_menu_items(self):
    """Add auto-sort items to menu bar."""
    pass

def show_auto_sort_progress(self, operation_name):
    """Display auto-sort progress dialog."""
    pass

def update_metadata_status(self, status):
    """Update metadata processing status."""
    pass
```

### Step 2.3: Create Progress Dialog
**File:** `progress_dialog.py`

```python
class AutoSortProgressDialog(tk.Toplevel):
    def __init__(self, parent, operation_name):
        super().__init__(parent)
        self.setup_ui()
        self.setup_callbacks()
    
    def update_progress(self, current, total, current_file=""):
        """Update progress display."""
        pass
    
    def set_status(self, status):
        """Update operation status."""
        pass
    
    def enable_pause_resume(self):
        """Enable pause/resume functionality."""
        pass
```

## Phase 3: Advanced Features (Priority: Medium)

### Step 3.1: Metadata Caching System
**File:** `metadata_cache.py`

```python
class MetadataCache:
    def __init__(self, cache_file, max_entries=10000):
        self.cache_file = cache_file
        self.max_entries = max_entries
        self.cache = self.load_cache()
    
    def get(self, image_path, file_mtime):
        """Get cached metadata if still valid."""
        pass
    
    def set(self, image_path, file_mtime, metadata):
        """Cache metadata for image."""
        pass
    
    def cleanup_expired(self, expire_days=30):
        """Remove expired cache entries."""
        pass
```

### Step 3.2: Term Testing Dialog
**File:** `term_test_dialog.py`

```python
class TermTestDialog(tk.Toplevel):
    def __init__(self, parent, terms):
        super().__init__(parent)
        self.terms = terms
        self.setup_ui()
    
    def test_terms(self):
        """Test terms against sample text."""
        pass
    
    def highlight_matches(self, text, matches):
        """Highlight matching terms in text."""
        pass
```

### Step 3.3: Metadata Viewer
**File:** `metadata_viewer.py`

```python
class MetadataViewerDialog(tk.Toplevel):
    def __init__(self, parent, image_file, metadata):
        super().__init__(parent)
        self.setup_ui(metadata)
    
    def create_prompt_tab(self, notebook, metadata):
        """Create tab showing prompts."""
        pass
    
    def create_parameters_tab(self, notebook, metadata):
        """Create tab showing generation parameters."""
        pass
    
    def create_raw_tab(self, notebook, metadata):
        """Create tab showing raw metadata."""
        pass
```

## Phase 4: Integration and Testing (Priority: High)

### Step 4.1: Update Main Application
**File:** `app.py` (modify existing)

```python
# Methods to add to ImageSorter class:
def initialize_auto_sort_components(self):
    """Initialize auto-sort related components."""
    self.metadata_parser = MetadataParser()
    self.auto_sorter = AutoSorter(self.config_manager, self.metadata_parser)

def auto_sort_all(self, event=None):
    """Start auto-sort operation for all images."""
    pass

def auto_sort_batch(self, event=None):
    """Auto-sort current batch only."""
    pass

def sort_to_term(self, image_file, term):
    """Sort specific image to term folder."""
    pass

def show_metadata_viewer(self, image_file):
    """Show metadata viewer for image."""
    pass
```

### Step 4.2: Update Callbacks and Event Handling
```python
# Add to UIManager callbacks dictionary:
callbacks = {
    'show_settings': self.show_settings,
    'undo': self.undo_last_sort,
    'sort_image': self.sort_image,
    'next_page': self.next_page,
    'reload_images': self.reload_images,
    'show_preview': self.show_preview,
    # New auto-sort callbacks:
    'auto_sort_all': self.auto_sort_all,
    'auto_sort_batch': self.auto_sort_batch,
    'sort_by_term': self.sort_by_term,
    'show_term_manager': self.show_term_manager,
    'view_metadata': self.view_metadata
}
```

## Implementation Priority Order

### Week 1: Core Foundation
1. Create `metadata_parser.py` with basic PNG/JPEG metadata extraction
2. Extend `config_manager.py` with auto-sort configuration support
3. Create `auto_sorter.py` with basic sorting logic
4. Write unit tests for metadata parsing

### Week 2: UI Integration
1. Extend `config_dialog.py` with auto-sort tab
2. Update `ui_manager.py` with auto-sort toolbar
3. Create `progress_dialog.py` for operation feedback
4. Add auto-sort menu items and keyboard shortcuts

### Week 3: Advanced Features
1. Implement `metadata_cache.py` for performance
2. Create `term_test_dialog.py` for term validation
3. Add `metadata_viewer.py` for metadata inspection
4. Implement batch processing and threading

### Week 4: Polish and Testing
1. Integrate all components with main application
2. Add error handling and logging
3. Comprehensive testing with various image types
4. Documentation and user guide updates

## Testing Strategy

### Unit Tests
```python
# test_metadata_parser.py
def test_png_metadata_extraction():
    """Test PNG metadata extraction."""
    pass

def test_jpeg_metadata_extraction():
    """Test JPEG metadata extraction."""
    pass

def test_sd_parameter_parsing():
    """Test Stable Diffusion parameter parsing."""
    pass

# test_auto_sorter.py
def test_term_matching():
    """Test term matching algorithms."""
    pass

def test_conflict_resolution():
    """Test multiple match handling."""
    pass

# test_config_manager.py
def test_config_migration():
    """Test configuration version migration."""
    pass
```

### Integration Tests
```python
# test_full_workflow.py
def test_auto_sort_workflow():
    """Test complete auto-sort workflow."""
    pass

def test_undo_auto_sort():
    """Test undo functionality for auto-sort."""
    pass
```

## Performance Considerations

### Optimization Targets
1. **Metadata parsing**: Cache parsed metadata to avoid re-parsing
2. **File operations**: Batch file moves for efficiency
3. **UI responsiveness**: Use threading for long operations
4. **Memory usage**: Process images in batches to limit memory usage

### Threading Strategy
```python
# Background tasks that need threading:
1. Metadata extraction from large image sets
2. Auto-sort file operations
3. Metadata cache maintenance
4. Progress updates without blocking UI
```

## Error Handling Strategy

### Error Categories
1. **File access errors**: Missing files, permission issues
2. **Metadata parsing errors**: Corrupted or invalid metadata
3. **Configuration errors**: Invalid terms or settings
4. **UI errors**: Dialog creation or update failures

### Recovery Mechanisms
```python
# Error handling patterns:
try:
    # Risky operation
    pass
except SpecificError as e:
    # Log error
    # Attempt recovery
    # Continue with next item
except Exception as e:
    # Log unexpected error
    # Notify user
    # Graceful degradation
```

## Documentation Requirements

### User Documentation
1. Auto-sort feature overview
2. Term configuration guide
3. Metadata format explanation
4. Troubleshooting guide

### Developer Documentation
1. API documentation for new classes
2. Integration guide for extending functionality
3. Configuration schema documentation
4. Testing and debugging guide

## Deployment Considerations

### Backward Compatibility
- Existing configurations must continue to work
- Graceful handling of missing auto-sort configuration
- Migration path for users upgrading from older versions

### Dependencies
- No new external dependencies beyond existing PIL/Pillow
- Ensure compatibility with Python 3.7+
- Cross-platform file handling (Windows/Linux/Mac)

### Installation
- Auto-sort functionality should be available immediately after update
- Configuration migration should be automatic
- No manual setup required for basic functionality