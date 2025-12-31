# UI Enhancement Requirements

## Overview
This document specifies the user interface changes needed to support the metadata-based auto-sorting feature while maintaining the existing visual sorting workflow.

## Main Window Enhancements

### Menu Bar Updates
Extend the existing menu structure:

```
File
├── Settings (existing)
├── Auto-Sort Images... (NEW)
├── Term Manager... (NEW)
├── ─────────────
└── Exit (existing)

Tools (NEW MENU)
├── Scan Metadata
├── Export Terms
├── Import Terms
└── Clear Metadata Cache

Help (NEW MENU)
├── Keyboard Shortcuts (existing functionality)
├── Auto-Sort Guide
└── About
```

### Toolbar Addition
Add a new toolbar below the existing controls:

```python
def setup_auto_sort_toolbar(self):
    """Add auto-sort controls to the main window."""
    auto_sort_frame = ttk.LabelFrame(self.parent, text="Auto-Sort")
    auto_sort_frame.pack(fill="x", padx=5, pady=2)
    
    # Quick auto-sort button
    ttk.Button(
        auto_sort_frame, 
        text="Auto-Sort All", 
        command=self.callbacks['auto_sort_all']
    ).pack(side="left", padx=5)
    
    # Term quick-select dropdown
    self.quick_term_var = tk.StringVar()
    term_combo = ttk.Combobox(
        auto_sort_frame,
        textvariable=self.quick_term_var,
        values=self.get_active_terms(),
        state="readonly",
        width=15
    )
    term_combo.pack(side="left", padx=5)
    
    # Sort by selected term
    ttk.Button(
        auto_sort_frame,
        text="Sort by Term",
        command=self.callbacks['sort_by_term']
    ).pack(side="left", padx=5)
    
    # Metadata status indicator
    self.metadata_status = ttk.Label(
        auto_sort_frame,
        text="Metadata: Ready"
    )
    self.metadata_status.pack(side="right", padx=5)
```

## Enhanced Settings Dialog

### New Auto-Sort Tab
Extend `ConfigDialog` with a new tab for auto-sort configuration:

```python
def create_auto_sort_tab(self):
    """Create the auto-sort configuration tab."""
    auto_tab = ttk.Frame(self.notebook)
    self.notebook.add(auto_tab, text="Auto-Sort")
    
    # Terms management section
    terms_frame = ttk.LabelFrame(auto_tab, text="Search Terms")
    terms_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Terms list with reordering
    self.create_terms_list(terms_frame)
    
    # Auto-sort options
    options_frame = ttk.LabelFrame(auto_tab, text="Sorting Options")
    options_frame.pack(fill="x", padx=5, pady=5)
    
    self.create_auto_sort_options(options_frame)
```

### Terms Management Interface
```python
def create_terms_list(self, parent):
    """Create the terms management interface."""
    # List frame with scrollbar
    list_frame = ttk.Frame(parent)
    list_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Terms listbox with checkboxes
    self.terms_tree = ttk.Treeview(
        list_frame,
        columns=("enabled", "priority"),
        show="tree headings",
        height=8
    )
    self.terms_tree.heading("#0", text="Term")
    self.terms_tree.heading("enabled", text="Enabled")
    self.terms_tree.heading("priority", text="Priority")
    
    # Scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.terms_tree.yview)
    self.terms_tree.configure(yscrollcommand=scrollbar.set)
    
    self.terms_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Control buttons
    btn_frame = ttk.Frame(parent)
    btn_frame.pack(fill="x", padx=5, pady=5)
    
    ttk.Button(btn_frame, text="Add Term", command=self.add_term).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Remove", command=self.remove_term).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Move Up", command=self.move_term_up).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Move Down", command=self.move_term_down).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Test Terms", command=self.test_terms).pack(side="right", padx=2)
```

## Auto-Sort Progress Dialog

### Progress Window Design
```python
class AutoSortProgressDialog(tk.Toplevel):
    def __init__(self, parent, operation_name="Auto-Sorting"):
        super().__init__(parent)
        self.title(f"{operation_name} Progress")
        self.setup_ui()
        self.setup_modal_behavior(parent)
    
    def setup_ui(self):
        """Create the progress dialog interface."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Initializing...",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # Current file label
        self.file_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 8),
            foreground="gray"
        )
        self.file_label.pack(pady=(0, 10))
        
        # Statistics frame
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        self.processed_label = ttk.Label(stats_frame, text="Processed: 0")
        self.processed_label.pack(side="left")
        
        self.matched_label = ttk.Label(stats_frame, text="Matched: 0")
        self.matched_label.pack(side="right")
        
        # Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()
        
        self.cancel_button = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.cancel_operation
        )
        self.cancel_button.pack(side="left", padx=5)
        
        self.pause_button = ttk.Button(
            btn_frame,
            text="Pause",
            command=self.pause_operation,
            state="disabled"
        )
        self.pause_button.pack(side="left", padx=5)
```

## Term Testing Dialog

### Quick Test Interface
```python
class TermTestDialog(tk.Toplevel):
    def __init__(self, parent, terms):
        super().__init__(parent)
        self.title("Test Search Terms")
        self.terms = terms
        self.setup_ui()
    
    def setup_ui(self):
        """Create the term testing interface."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Sample text input
        ttk.Label(main_frame, text="Test Text (e.g., image prompt):").pack(anchor="w")
        self.test_text = tk.Text(main_frame, height=4, width=60)
        self.test_text.pack(fill="x", pady=(5, 10))
        
        # Test button
        ttk.Button(
            main_frame,
            text="Test Terms",
            command=self.test_terms
        ).pack(pady=(0, 10))
        
        # Results area
        ttk.Label(main_frame, text="Matching Terms:").pack(anchor="w")
        self.results_tree = ttk.Treeview(
            main_frame,
            columns=("match_type",),
            show="tree headings",
            height=6
        )
        self.results_tree.heading("#0", text="Term")
        self.results_tree.heading("match_type", text="Match Type")
        self.results_tree.pack(fill="both", expand=True)
```

## Context Menu Enhancements

### Image Right-Click Menu
Extend existing context menus for individual images:

```python
def create_image_context_menu(self, event, image_file):
    """Create context menu for image items."""
    context_menu = tk.Menu(self, tearoff=0)
    
    # Existing options
    context_menu.add_command(label="Sort to 1", command=lambda: self.sort_image(event, '1', image_file))
    context_menu.add_command(label="Sort to 2", command=lambda: self.sort_image(event, '2', image_file))
    context_menu.add_command(label="Sort to 3", command=lambda: self.sort_image(event, '3', image_file))
    context_menu.add_separator()
    
    # New auto-sort options
    context_menu.add_command(label="View Metadata", command=lambda: self.show_metadata(image_file))
    context_menu.add_command(label="Auto-Sort This Image", command=lambda: self.auto_sort_single(image_file))
    context_menu.add_separator()
    
    # Quick term sorting
    for term in self.get_active_terms()[:5]:  # Show first 5 terms
        context_menu.add_command(
            label=f"Sort to '{term}'",
            command=lambda t=term: self.sort_to_term(image_file, t)
        )
    
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()
```

## Metadata Viewer Dialog

### Image Metadata Display
```python
class MetadataViewerDialog(tk.Toplevel):
    def __init__(self, parent, image_file, metadata):
        super().__init__(parent)
        self.title(f"Metadata - {os.path.basename(image_file)}")
        self.setup_ui(metadata)
    
    def setup_ui(self, metadata):
        """Create the metadata viewer interface."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Notebook for different metadata sections
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Prompt tab
        if 'positive_prompt' in metadata or 'negative_prompt' in metadata:
            self.create_prompt_tab(notebook, metadata)
        
        # Parameters tab
        if 'parameters' in metadata:
            self.create_parameters_tab(notebook, metadata)
        
        # Raw metadata tab
        self.create_raw_tab(notebook, metadata)
        
        # Close button
        ttk.Button(
            main_frame,
            text="Close",
            command=self.destroy
        ).pack(pady=(10, 0))
```

## Status Bar Addition

### Main Window Status Bar
```python
def setup_status_bar(self):
    """Add status bar to the main window."""
    self.status_bar = ttk.Frame(self.parent)
    self.status_bar.pack(side="bottom", fill="x")
    
    # Left side - current operation status
    self.operation_status = ttk.Label(
        self.status_bar,
        text="Ready",
        relief="sunken",
        width=20
    )
    self.operation_status.pack(side="left", padx=(5, 0))
    
    # Center - progress info
    self.progress_info = ttk.Label(
        self.status_bar,
        text="",
        relief="sunken"
    )
    self.progress_info.pack(side="left", fill="x", expand=True, padx=5)
    
    # Right side - statistics
    self.stats_label = ttk.Label(
        self.status_bar,
        text="Images: 0 | Sorted: 0",
        relief="sunken",
        width=25
    )
    self.stats_label.pack(side="right", padx=(0, 5))
```

## Keyboard Shortcuts

### New Shortcuts for Auto-Sort
```python
def setup_auto_sort_bindings(self):
    """Set up keyboard shortcuts for auto-sort features."""
    # Ctrl+A: Auto-sort all visible images
    self.bind('<Control-a>', self.auto_sort_all)
    
    # Ctrl+T: Open term manager
    self.bind('<Control-t>', self.open_term_manager)
    
    # Ctrl+M: View metadata for image under cursor
    self.bind('<Control-m>', self.view_metadata_under_cursor)
    
    # F5: Refresh metadata cache
    self.bind('<F5>', self.refresh_metadata_cache)
    
    # Ctrl+Shift+A: Auto-sort current batch only
    self.bind('<Control-Shift-a>', self.auto_sort_batch)
```

## Accessibility Considerations

### Screen Reader Support
- Add appropriate ARIA labels and descriptions
- Ensure keyboard navigation for all new controls
- Provide text alternatives for progress indicators

### High Contrast Mode
- Support system high contrast themes
- Ensure sufficient color contrast for status indicators
- Use text labels in addition to color coding

### Keyboard-Only Operation
- All auto-sort functions accessible via keyboard
- Tab order logical for new UI elements
- Keyboard shortcuts documented and consistent