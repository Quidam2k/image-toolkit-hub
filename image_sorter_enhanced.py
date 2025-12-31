"""
Enhanced Image Grid Sorter - Main Application

A comprehensive image management and sorting application with advanced features:

Core Features:
- Grid-based image viewing with keyboard and mouse controls
- Manual sorting into numbered categories (1, 2, 3) and removal folder
- Intelligent auto-sorting based on metadata/prompt content
- Multi-tag support with various sorting strategies
- Re-sorting of existing collections with updated rules

Auto-Sort Capabilities:
- Term-based matching with configurable search scopes (prompt, tags, both)
- Multi-tag modes: single_folder, multi_folder, smart_combination, all_combinations
- Exclusion rules and priority handling
- Progress tracking with pause/resume/cancel
- Comprehensive error handling and reporting

Advanced Features:
- Metadata caching for performance
- Tag embedding into image files
- Configuration backup and migration
- Extensive UI customization options
- Detailed statistics and operation logging

UI Components:
- Full-screen grid interface with dynamic resizing
- Comprehensive menu system
- Auto-sort toolbar with quick access controls
- Progress dialogs with detailed feedback
- Configuration dialogs for all settings

Author: Claude Code Implementation
Version: 2.1 (Added all_combinations mode and re-sort functionality)
Compatible with: PNG, JPG, JPEG, BMP, GIF, WebP image formats
"""

import os
import sys
import shutil
import random
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
import gc
import threading
import logging
import warnings

from undo_manager import UndoManager

# Configure PIL to handle large images safely
Image.MAX_IMAGE_PIXELS = 300000000  # ~300MB worth of pixels
warnings.filterwarnings("ignore", "Image size .* exceeds limit", UserWarning)

# Import our modular components
from config_manager import ConfigManager
from metadata_parser import MetadataParser
from auto_sorter import AutoSorter
from auto_sort_progress import AutoSortProgressDialog
from term_manager import TermManagerDialog
from setup_dialog import show_setup_dialog
from tag_embedder import TagEmbedder
from tag_embed_progress import TagEmbedProgressDialog
from auto_sort_review import show_auto_sort_review
from auto_sort_confirm import show_auto_sort_confirm
from batch_export_dialog import show_batch_export_dialog
from visual_sort_dialog import show_visual_sort_dialog
from background_sort_dialog import show_background_sort_dialog

# Configure application logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_images(folders, exclude_dirs, copy_mode=False, include_subfolders=True):
    """
    Load images from multiple folders, excluding specified directories.
    In copy mode, don't exclude any directories as we want to see all images.

    Args:
        folders: Single folder path or list of folder paths
        exclude_dirs: Directories to exclude (only applied outside source folders)
        copy_mode: Whether in copy mode
        include_subfolders: Whether to include images from subdirectories
    """
    # Handle single folder for backward compatibility
    if isinstance(folders, str):
        folders = [folders]

    # Normalize source folders for comparison
    normalized_sources = [os.path.normpath(f).replace('\\', '/') for f in folders]

    # Normalize exclude dirs for safer comparison
    normalized_excludes = [os.path.normpath(d).replace('\\', '/') for d in exclude_dirs] if exclude_dirs else []

    image_files = []
    for folder in folders:
        if not os.path.exists(folder):
            continue

        if include_subfolders:
            # Use os.walk to recursively scan subdirectories
            for root, dirs, files in os.walk(folder):
                # In copy mode, we don't exclude directories
                if not copy_mode and normalized_excludes:
                    # Only exclude directories that are NOT within any source folder
                    # This prevents accidentally excluding source subfolders with destination names
                    dirs[:] = [
                        d for d in dirs
                        if os.path.normpath(os.path.join(root, d)).replace('\\', '/') not in normalized_excludes
                        # AND check if this dir is not a source folder itself
                        and os.path.normpath(os.path.join(root, d)).replace('\\', '/') not in normalized_sources
                    ]

                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        image_path = os.path.join(root, file).replace('\\', '/')
                        # Add source folder info to track which folder each image came from
                        image_files.append({'path': image_path, 'source': folder})
        else:
            # Only scan the root folder, not subdirectories
            try:
                files = os.listdir(folder)
                for file in files:
                    file_path = os.path.join(folder, file)
                    # Only process regular files, not directories
                    if os.path.isfile(file_path) and file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        image_path = file_path.replace('\\', '/')
                        # Add source folder info to track which folder each image came from
                        image_files.append({'path': image_path, 'source': folder})
            except OSError:
                # Handle permission errors or other OS errors
                continue

    # For backward compatibility, return just paths if all images are from same source
    if len(folders) == 1:
        return [item['path'] for item in image_files]

    return image_files

def get_already_sorted_filenames(destination_folders):
    """
    Scan destination folders and return a set of filenames (basenames) that already exist.
    This is used to filter out images that have already been copied in copy mode.
    
    Args:
        destination_folders: Dict of category -> folder path mappings
        
    Returns:
        Set of filenames (basenames only, not full paths) found in destination folders
    """
    sorted_filenames = set()
    
    # Only scan the numbered category folders (1, 2, 3), not auto_sorted/removed/unmatched
    category_folders = ['1', '2', '3']
    
    for category in category_folders:
        folder_path = destination_folders.get(category)
        if folder_path and os.path.exists(folder_path):
            try:
                for filename in os.listdir(folder_path):
                    # Only consider image files
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        sorted_filenames.add(filename.lower())  # Case-insensitive matching
            except OSError:
                # Skip folders we can't read
                continue
    
    return sorted_filenames

class ImageSorter(tk.Tk):
    """
    Main application class for the Enhanced Image Grid Sorter.
    
    This class provides a full-screen grid interface for viewing and sorting images
    with both manual and automatic sorting capabilities. Inherits from tk.Tk to
    provide the main application window.
    
    Key Components:
    - Grid-based image display with configurable rows/columns
    - Keyboard and mouse control handling
    - Auto-sort integration with progress tracking
    - Menu system with comprehensive options
    - Statistics tracking and display
    - Configuration management integration
    
    Attributes:
        config_manager: Configuration and settings management
        metadata_parser: Image metadata extraction
        auto_sorter: Automatic sorting functionality
        tag_embedder: Tag file embedding capabilities
        folder: Source folder for images
        num_rows: Number of rows in the grid display
        random_order: Whether to randomize image order
        copy_instead_of_move: File operation mode
        sorted_folders: Dictionary of destination folders
        images: List of all available images
        current_batch: Currently displayed images
        stats: Operation statistics tracking
    """
    
    def __init__(self, folder, num_rows, random_order, copy_instead_of_move):
        super().__init__()
        
        # Initialize configuration manager
        self.config_manager = ConfigManager()
        
        # Initialize auto-sort components
        self.metadata_parser = MetadataParser()
        self.auto_sorter = AutoSorter(self.config_manager)
        self.tag_embedder = TagEmbedder()
        self.undo_manager = UndoManager(max_history=50)

        # Track last operation for status display
        self.last_operation_message = ""
        
        # Basic settings - support multiple source folders
        self.folder = folder  # Primary folder for backward compatibility
        self.source_folders = self.config_manager.get_active_source_folders()
        if not self.source_folders and folder:
            self.source_folders = [folder]
        
        self.num_rows = num_rows
        self.random_order = random_order
        self.copy_instead_of_move = copy_instead_of_move
        
        # Use folders from config manager
        self.sorted_folders = self.config_manager.sorted_folders
        
        # Track current image metadata for source-aware sorting
        self.current_image_metadata = {}
        
        self.images = []
        self.current_batch = []
        self.taskbar_height = 40
        self.is_loading = False
        
        # Smart loading parameters
        self.images_buffer_ahead = 100  # Always keep at least this many images loaded ahead
        self.min_images_to_display = 30  # Minimum images to show per batch
        
        # Background loading
        self.preloaded_images = []  # Cache of preloaded image data
        self.background_loading = False
        self.background_load_target = 150  # Target number of images to preload
        self.background_load_thread = None
        
        # Image tracking for better counting
        self.skipped_images = []  # Track images that couldn't be loaded
        self.total_original_count = 0  # Track original total count
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'sorted_to_1': 0,
            'sorted_to_2': 0,
            'sorted_to_3': 0,
            'moved_to_removed': 0,
            'auto_sorted': 0,
            'session_start_time': None,
            'total_images_at_start': 0
        }
        
        # Load key bindings from config
        self.load_key_bindings()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_auto_sort_toolbar()
        
        # Load images if we have source folders configured
        if self.source_folders:
            self.load_initial_images()
        else:
            # Show welcome message if no sources are configured
            self.show_welcome_message()

    def load_key_bindings(self):
        """Load key bindings from config manager."""
        self.bindings = self.config_manager.get_bindings()
    
    def setup_ui(self):
        """Set up the main user interface."""
        self.title('Enhanced Image Sorter')
        self.state('zoomed')
        self.attributes('-fullscreen', True)
        
        # Create main container
        self.main_container = tk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Set up keyboard bindings
        self.bind('<Escape>', self.handle_key_binding)
        self.bind('<F11>', self.toggle_fullscreen)  # F11 to toggle fullscreen
        self.bind('1', self.handle_key_binding)
        self.bind('2', self.handle_key_binding)
        self.bind('3', self.handle_key_binding)
        self.bind('<space>', self.handle_key_binding)
        self.bind('r', self.handle_key_binding)
        self.bind('c', self.handle_key_binding)
        self.bind('<Control-a>', self.auto_sort_all)
        self.bind('<Control-t>', self.open_term_manager)
        self.bind('<Control-z>', lambda e: self.undo_last_operation())
        self.bind('<Control-Shift-z>', lambda e: self.redo_operation())

        # Set up mouse bindings
        self.bind('<Button-1>', self.handle_mouse_binding)
        self.bind('<Button-2>', self.handle_mouse_binding)
        self.bind('<Button-3>', self.handle_mouse_binding)
        self.bind('<Button-4>', self.handle_mouse_binding)
        self.bind('<Button-5>', self.handle_mouse_binding)
        
        self.update_idletasks()
        
        # Calculate available space dynamically
        if self.attributes('-fullscreen'):
            self.screen_width = self.winfo_screenwidth()
            self.screen_height = self.winfo_screenheight()
            available_height = self.screen_height - 80  # Account for toolbar
        else:
            self.screen_width = self.winfo_width()
            self.screen_height = self.winfo_height()
            available_height = self.screen_height - 120  # Account for toolbar + menu + title bar
        
        self.row_height = available_height // self.num_rows

        # Create a canvas with a dark gray background for better contrast
        self.canvas = tk.Canvas(self.main_container, bg='#2d2d2d')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Add status bar at bottom
        self.setup_status_bar()

    def setup_status_bar(self):
        """Set up the status bar at the bottom of the window."""
        status_frame = ttk.Frame(self.main_container)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        # Status message label
        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Undo status indicator
        self.undo_status = ttk.Label(
            status_frame,
            text="Undo: None",
            relief=tk.FLAT,
            width=30,
            anchor=tk.E,
            foreground="gray"
        )
        self.undo_status.pack(side=tk.RIGHT, padx=(10, 0))

    def update_status_bar(self, message, undo_available=None):
        """Update status bar with new message."""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)

        # Update undo indicator if specified
        if undo_available is not None and hasattr(self, 'undo_status'):
            if undo_available:
                undo_desc = self.undo_manager.get_undo_description()
                self.undo_status.config(
                    text=f"Undo: {undo_desc}",
                    foreground="white"
                )
            else:
                self.undo_status.config(
                    text="Undo: None",
                    foreground="gray"
                )

        self.update_idletasks()

    def setup_menu(self):
        """Set up the menu bar."""
        # Don't use overrideredirect - keep fullscreen but add menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=lambda: self.change_folder(None))
        file_menu.add_separator()
        file_menu.add_command(label="Auto-Sort Images...", command=self.auto_sort_all)
        file_menu.add_command(label="Re-sort Auto-Sorted Images...", command=self.re_sort_auto_sorted_images)
        file_menu.add_command(label="Collect Unmatched Images...", command=self.collect_unmatched_images)
        file_menu.add_command(label="Term Manager...", command=self.open_term_manager)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        self.undo_menu_item = edit_menu.add_command(
            label="Undo (Ctrl+Z)",
            command=self.undo_last_operation,
            state=tk.DISABLED
        )
        self.redo_menu_item = edit_menu.add_command(
            label="Redo (Ctrl+Shift+Z)",
            command=self.redo_operation,
            state=tk.DISABLED
        )

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Scan Metadata", command=self.scan_metadata)
        tools_menu.add_command(label="Clear Metadata Cache", command=self.clear_metadata_cache)
        tools_menu.add_separator()
        tools_menu.add_command(label="Browse Unmatched Images...", command=self.browse_unmatched_images)
        tools_menu.add_separator()
        tools_menu.add_command(label="Batch Export for WAN 2.2 i2v...", command=self.open_batch_export)
        tools_menu.add_command(label="Visual Sort (LoRA Workflow)...", command=self.open_visual_sort)
        tools_menu.add_command(label="Find T-Shirt Ready Images...", command=self.open_background_sort)
        tools_menu.add_separator()
        tools_menu.add_command(label="Embed Tag Files in Images", command=self.embed_tag_files)
        tools_menu.add_separator()
        tools_menu.add_command(label="Export Terms", command=self.export_terms)
        tools_menu.add_command(label="Import Terms", command=self.import_terms)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_key_bindings)
        help_menu.add_command(label="Auto-Sort Guide", command=self.show_auto_sort_help)
        help_menu.add_command(label="Visual Sort Guide", command=self.show_visual_sort_help)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_auto_sort_toolbar(self):
        """Add auto-sort controls to the main window."""
        toolbar_frame = ttk.Frame(self.main_container)
        toolbar_frame.pack(fill="x", padx=5, pady=2)
        
        # Auto-sort section
        auto_sort_frame = ttk.LabelFrame(toolbar_frame, text="Auto-Sort")
        auto_sort_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Quick auto-sort button
        ttk.Button(
            auto_sort_frame, 
            text="Auto-Sort All", 
            command=self.auto_sort_all
        ).pack(side="left", padx=5, pady=2)
        
        # Current batch auto-sort
        ttk.Button(
            auto_sort_frame,
            text="Auto-Sort Batch",
            command=self.auto_sort_batch
        ).pack(side="left", padx=5, pady=2)
        
        # Term manager button
        ttk.Button(
            auto_sort_frame,
            text="Manage Terms",
            command=self.open_term_manager
        ).pack(side="left", padx=5, pady=2)
        
        # Metadata status
        self.metadata_status = ttk.Label(
            auto_sort_frame,
            text="Metadata: Ready"
        )
        self.metadata_status.pack(side="right", padx=5, pady=2)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(toolbar_frame, text="Statistics")
        stats_frame.pack(side="right", padx=(10, 0))
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="Images: 0 | Processed: 0"
        )
        self.stats_label.pack(padx=5, pady=2)

    def handle_key_binding(self, event):
        """Handle keyboard events based on the current bindings."""
        key_name = None
        
        # Map event to key_name format used in config
        if event.keysym == 'Escape':
            key_name = 'key_escape'
        elif event.keysym == 'space':
            key_name = 'key_space'
        elif event.char.isdigit() and 1 <= int(event.char) <= 3:
            key_name = f'key_{event.char}'
        elif event.char.lower() == 'r':
            key_name = 'key_r'
        elif event.char.lower() == 'c':
            key_name = 'key_c'
            
        if key_name and key_name in self.bindings:
            action = self.bindings[key_name]
            self.perform_action(action)
            
    def handle_mouse_binding(self, event):
        """Handle mouse events based on the current bindings."""
        button_name = None
        
        if event.num == 1:
            button_name = 'left_mouse'
        elif event.num == 2:
            button_name = 'middle_mouse'
        elif event.num == 3:
            button_name = 'right_mouse'
        elif event.num == 4:
            button_name = 'mouse_button_4'
        elif event.num == 5:
            button_name = 'mouse_button_5'
            
        if button_name and button_name in self.bindings:
            action = self.bindings[button_name]
            self.perform_action(action, event)
    
    def perform_action(self, action, event=None):
        """Perform the specified action."""
        if action in ('1', '2', '3'):
            # Sort the image under the cursor or mouse position
            if event:
                self.sort_image(event, action)
            else:
                self.sort_current_image(action)
        elif action == 'next':
            self.next_page(None)
        elif action == 'reload':
            self.load_initial_images()
        elif action == 'exit':
            self.destroy()
        elif action == 'config':
            self.change_folder(None)
        
    def sort_current_image(self, category):
        """Sort the image currently under the cursor using keyboard."""
        if self.is_loading:
            return
            
        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()
        
        items = self.canvas.find_overlapping(x, y, x, y)
        if items:
            for item in items:
                for img_item, _, file in self.image_labels:
                    if img_item == item:
                        self.sort_image(None, category, file)
                        return

    def load_initial_images(self):
        """Load initial set of images from the source folders."""
        # In copy mode, we want to see all images including ones in destination folders
        include_subfolders = self.config_manager.config.get('include_subfolders', True) if self.config_manager else True
        self.images = load_images(
            self.source_folders if self.source_folders else [self.folder], 
            list(self.sorted_folders.values()),
            self.copy_instead_of_move,
            include_subfolders
        )
        
        # Handle different return formats from load_images
        if self.images and isinstance(self.images[0], dict):
            # Multi-source format: store metadata and extract paths
            for item in self.images:
                self.current_image_metadata[item['path']] = item['source']
            self.images = [item['path'] for item in self.images]
        
        # Filter out already-copied images if enabled (copy mode only)
        if self.copy_instead_of_move:
            hide_sorted = self.config_manager.config.get('ui_preferences', {}).get('hide_already_sorted', True) if self.config_manager else True
            if hide_sorted:
                already_sorted = get_already_sorted_filenames(self.sorted_folders)
                if already_sorted:
                    original_count = len(self.images)
                    self.images = [
                        img for img in self.images 
                        if os.path.basename(img).lower() not in already_sorted
                    ]
                    filtered_count = original_count - len(self.images)
                    if filtered_count > 0:
                        print(f"Filtered out {filtered_count} already-sorted images from display")
        
        # Initialize session statistics and tracking
        if self.stats['session_start_time'] is None:
            self.stats['session_start_time'] = time.time()
            self.stats['total_images_at_start'] = len(self.images)
            self.total_original_count = len(self.images)
            self.skipped_images = []  # Reset skipped images for new session
        
        if self.random_order:
            # Use a seeded random to ensure better distribution
            random.shuffle(self.images)
            # Double shuffle for better randomness, especially with filesystem-ordered files
            random.shuffle(self.images)
        self.load_batch()
        self.update_stats_display()
        
        # Start background loading after initial load
        self.start_background_loading()

    def start_background_loading(self):
        """Start background loading of images to stay ahead."""
        if not self.background_loading and len(self.images) > 0:
            self.background_loading = True
            self.background_load_thread = threading.Thread(target=self._background_load_worker, daemon=True)
            self.background_load_thread.start()
            
            # Also schedule a check to restart background loading if needed
            self.after(5000, self._check_background_loading_status)

    def _background_load_worker(self):
        """Background worker to preload images."""
        batch_size = 10  # Process images in small batches to prevent blocking
        
        while len(self.images) > 0 and len(self.preloaded_images) < self.background_load_target:
            if not self.background_loading:  # Check if we should stop
                break
            
            # Process a small batch of images
            for _ in range(batch_size):
                if not self.images or not self.background_loading:
                    break
                    
                try:
                    # Take the next image from the queue
                    image_file = self.images.pop(0)
                    
                    # Quick size check - warn but don't skip, PIL can handle large files
                    file_size = os.path.getsize(image_file)
                    if file_size > 100 * 1024 * 1024:  # Only skip truly enormous files (>100MB)
                        self.skipped_images.append((image_file, "File too large (>100MB)"))
                        continue
                    elif file_size > 50 * 1024 * 1024:  # Warn about large files
                        print(f"Loading large file ({file_size // (1024*1024)}MB): {os.path.basename(image_file)}")
                    
                    # Load and process the image
                    img = Image.open(image_file)
                    total_pixels = img.width * img.height
                    
                    if total_pixels > 100000000:  # Generate thumbnail for very large images
                        original_size = f"{img.width}x{img.height}"
                        print(f"Generating thumbnail for large image: {os.path.basename(image_file)} ({original_size})")
                        try:
                            # Create thumbnail - maintains aspect ratio, modifies image in-place
                            img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                            total_pixels = img.width * img.height  # Recalculate after thumbnail
                            print(f"  Thumbnail created: {original_size} -> {img.width}x{img.height}")
                        except Exception as thumb_e:
                            print(f"  Failed to create thumbnail: {thumb_e}")
                            # If thumbnail fails, skip this image
                            img.close()
                            self.skipped_images.append((image_file, f"Thumbnail generation failed: {thumb_e}"))
                            continue
                    
                    # Calculate dimensions
                    aspect_ratio = img.width / img.height
                    new_height = self.row_height
                    new_width = int(new_height * aspect_ratio)
                    
                    # Resize image with better quality for background loading
                    if total_pixels > 25000000:
                        resized_img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
                    elif total_pixels > 10000000:
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    img.close()
                    
                    # Create PhotoImage
                    tk_img = ImageTk.PhotoImage(resized_img)
                    resized_img.close()
                    
                    # Store preloaded data
                    self.preloaded_images.append((image_file, tk_img, new_width, aspect_ratio))
                    
                except Exception as e:
                    # Track problematic images
                    self.skipped_images.append((image_file, f"Load error: {str(e)}"))
                    continue
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)
        
        self.background_loading = False

    def stop_background_loading(self):
        """Stop background loading."""
        self.background_loading = False

    def _check_background_loading_status(self):
        """Check if background loading should be restarted."""
        if not self.background_loading and len(self.images) > 0 and len(self.preloaded_images) < self.background_load_target:
            self.start_background_loading()
        elif len(self.images) > 0:
            # Schedule another check
            self.after(5000, self._check_background_loading_status)

    def load_batch(self):
        """Load and display images immediately as they become available, filling ALL rows."""
        self.canvas.delete("all")  # Clear the canvas
        self.image_labels = []
        row_widths = [0] * self.num_rows
        self.current_batch = []
        
        # Show preloaded images first, then continue loading until all rows are filled
        self.show_batch_loading_indicator()
        
        # Start with preloaded images
        preloaded_used = 0
        for _ in range(len(self.preloaded_images)):
            if self.preloaded_images:
                image_file, tk_img, img_width, aspect_ratio = self.preloaded_images.pop(0)
                self._try_place_image_immediately(image_file, tk_img, img_width, aspect_ratio, row_widths)
                preloaded_used += 1
        
        # Continue loading and placing images until ALL rows are filled or no more images
        images_processed = 0
        start_time = time.time()
        
        while self._has_unfilled_rows(row_widths) and self.images:
            image_file = self.images.pop(0)
            
            # Update loading indicator every 5 images
            if images_processed % 5 == 0:
                self.update_batch_loading_indicator(images_processed, len(self.images) + images_processed)
                self.update_idletasks()  # Allow UI updates
            
            try:
                # Quick size check - warn but don't skip, PIL can handle large files
                file_size = os.path.getsize(image_file)
                if file_size > 100 * 1024 * 1024:  # Only skip truly enormous files (>100MB)
                    self.skipped_images.append((image_file, "File too large (>100MB)"))
                    images_processed += 1
                    continue
                elif file_size > 50 * 1024 * 1024:  # Warn about large files
                    print(f"Loading large file ({file_size // (1024*1024)}MB): {os.path.basename(image_file)}")
                
                # Load and process image
                img = Image.open(image_file)
                total_pixels = img.width * img.height
                
                if total_pixels > 100000000:  # Generate thumbnail for very large images
                    original_size = f"{img.width}x{img.height}"
                    print(f"Generating thumbnail for large image: {os.path.basename(image_file)} ({original_size})")
                    try:
                        # Create thumbnail - maintains aspect ratio, modifies image in-place
                        img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                        total_pixels = img.width * img.height  # Recalculate after thumbnail
                        print(f"  Thumbnail created: {original_size} -> {img.width}x{img.height}")
                    except Exception as thumb_e:
                        print(f"  Failed to create thumbnail: {thumb_e}")
                        # If thumbnail fails, skip this image
                        img.close()
                        self.skipped_images.append((image_file, f"Thumbnail generation failed: {thumb_e}"))
                        images_processed += 1
                        continue
                
                # Calculate dimensions
                aspect_ratio = img.width / img.height
                new_height = self.row_height
                new_width = int(new_height * aspect_ratio)
                
                # Resize image
                if total_pixels > 25000000:
                    resized_img = img.resize((new_width, new_height), Image.Resampling.NEAREST)
                elif total_pixels > 10000000:
                    resized_img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
                else:
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                img.close()
                tk_img = ImageTk.PhotoImage(resized_img)
                resized_img.close()
                
                # Try to place the image immediately
                if self._try_place_image_immediately(image_file, tk_img, new_width, aspect_ratio, row_widths):
                    # Successfully placed - update display every few images
                    if images_processed % 3 == 0:
                        self.update_idletasks()
                else:
                    # If it can't be placed, put it back for next batch
                    self.images.append(image_file)
                    break
                    
            except Exception as e:
                print(f"Error loading {os.path.basename(image_file)}: {e}")
                self.skipped_images.append((image_file, f"Load error: {str(e)}"))
            
            images_processed += 1
            
            # Safety valve - don't load forever
            if time.time() - start_time > 10.0:
                break

        # Clear loading indicator
        self.clear_batch_loading_indicator()
        
        # Final statistics
        total_width_used = sum(row_widths)
        total_width_available = self.screen_width * self.num_rows
        fill_percentage = (total_width_used / total_width_available) * 100 if total_width_available > 0 else 0
        
        print(f"Loaded {len(self.image_labels)} images ({preloaded_used} preloaded, {images_processed} new)")
        print(f"Screen fill: {fill_percentage:.1f}% ({total_width_used}/{total_width_available} pixels)")
        
        # Check if we're truly out of processable images
        total_remaining = len(self.images) + len(self.preloaded_images)
        if not self.image_labels and total_remaining == 0:
            skipped_count = len(self.skipped_images)
            if skipped_count > 0:
                messagebox.showinfo("Finished", 
                    f"All processable images have been sorted.\n\n"
                    f"Note: {skipped_count} images were skipped (files >100MB or loading errors).\n"
                    f"Large images were processed using thumbnails. Check console for details.")
            else:
                messagebox.showinfo("Finished", "All images have been sorted.")

        self.is_loading = False
        self.update_stats_display()
        
        # Log skipped images for debugging
        if self.skipped_images:
            print(f"\nSkipped {len(self.skipped_images)} images:")
            for img_file, reason in self.skipped_images[-5:]:  # Show last 5 skipped
                print(f"  - {os.path.basename(img_file)}: {reason}")
            if len(self.skipped_images) > 5:
                print(f"  ... and {len(self.skipped_images) - 5} more")
        
        # Restart background loading
        if preloaded_used > 0 or len(self.preloaded_images) < self.background_load_target // 2:
            self.start_background_loading()

    def _has_unfilled_rows(self, row_widths):
        """Check if any rows still have significant space available."""
        min_useful_space = 150  # Minimum space worth trying to fill (increased for safety)
        for row_width in row_widths:
            remaining_space = self.screen_width - row_width
            # Only consider a row unfilled if it has substantial space AND isn't at screen edge
            if remaining_space > min_useful_space and row_width < self.screen_width * 0.95:
                return True
        return False

    def _try_place_image_immediately(self, image_file, tk_img, img_width, aspect_ratio, row_widths):
        """Try to place an image immediately and return True if successful."""
        # Find the best row for this image
        best_row = -1
        best_fit_score = float('inf')
        
        for row in range(self.num_rows):
            remaining_space = self.screen_width - row_widths[row]
            # Ensure the image will fit completely within screen bounds
            if remaining_space >= img_width and row_widths[row] + img_width <= self.screen_width:
                # Calculate fit score (prefer rows with less wasted space)
                wasted_space = remaining_space - img_width
                fit_score = wasted_space
                
                # Prefer fuller rows for better balance
                fullness_bonus = row_widths[row] / self.screen_width
                fit_score -= fullness_bonus * 50
                
                if fit_score < best_fit_score:
                    best_fit_score = fit_score
                    best_row = row
        
        if best_row >= 0:
            # Place the image
            self.place_image(image_file, tk_img, best_row, row_widths[best_row])
            row_widths[best_row] += img_width
            self.current_batch.append(image_file)
            return True
        else:
            # Try to force fit in the row with most space, but only if image actually fits
            max_space_row = max(range(self.num_rows), key=lambda r: self.screen_width - row_widths[r])
            available_space = self.screen_width - row_widths[max_space_row]
            
            # Only place if image fits within available space (don't crop/cut off)
            if available_space >= img_width and available_space > 50:
                self.place_image(image_file, tk_img, max_space_row, row_widths[max_space_row])
                row_widths[max_space_row] += img_width
                self.current_batch.append(image_file)
                return True
        
        return False

    def place_image(self, image_file, tk_img, row, x):
        """Place an image on the canvas."""
        img_item = self.canvas.create_image(x, row * self.row_height, anchor=tk.NW, image=tk_img)
        self.image_labels.append((img_item, tk_img, image_file))

    def sort_image(self, event, category, image_file=None):
        """Sort an image into the specified category."""
        if self.is_loading:
            return

        if image_file is None and event is not None:
            # Find the image at the click coordinates
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            items = self.canvas.find_overlapping(x, y, x, y)
            if items:
                for item in items:
                    for img_item, _, file in self.image_labels:
                        if img_item == item:
                            image_file = file
                            break
                    if image_file:
                        break
            if not image_file:
                return

        src_file = image_file.replace('\\', '/')
        
        # Determine the correct destination folder based on source
        source_folder = self.current_image_metadata.get(src_file, self.folder)
        if source_folder and len(self.source_folders) > 1:
            # Use source-specific destination folder
            dest_folder = self.config_manager.get_destination_folder_for_source(source_folder, category)
        else:
            # Use default destination folder
            dest_folder = self.sorted_folders[category]
        
        dest_file = os.path.join(dest_folder, os.path.basename(src_file)).replace('\\', '/')
        
        # Ensure destination folder exists
        os.makedirs(dest_folder, exist_ok=True)
        
        if os.path.exists(dest_file):
            base, ext = os.path.splitext(dest_file)
            counter = 1
            while os.path.exists(dest_file):
                dest_file = f"{base}_{counter}{ext}"
                counter += 1
        
        if os.path.exists(src_file):
            try:
                # Get tag handling preference from config
                handle_tags = self.config_manager.config.get('ui_preferences', {}).get('handle_tag_files', True)
                
                # Use tag-aware copy/move
                success = self.tag_embedder.copy_or_move_with_tags(
                    src_file, dest_file, 
                    copy_mode=self.copy_instead_of_move,
                    include_tags=handle_tags
                )
                
                if success:
                    if self.copy_instead_of_move:
                        # In copy mode, mark the image as copied with visual indication
                        self.mark_image_as_copied(src_file)
                    else:
                        self.clear_image(src_file)
                        if src_file in self.current_batch:
                            self.current_batch.remove(src_file)
                else:
                    raise Exception("Failed to copy/move file with tags")
                
                # Update statistics
                self.stats['total_processed'] += 1
                if category in ['1', '2', '3']:
                    self.stats[f'sorted_to_{category}'] += 1
                    
                self.update_stats_display()
                    
            except Exception as e:
                print(f"Error processing image {src_file}: {e}")
        else:
            print(f"File not found: {src_file}")

    def clear_image(self, image_file):
        """Remove an image from the display."""
        for i, (img_item, tk_img, file) in enumerate(self.image_labels):
            if file == image_file:
                self.canvas.delete(img_item)
                del self.image_labels[i]
                break

    def mark_image_as_copied(self, image_file):
        """Mark an image as copied with a visual overlay."""
        for img_item, tk_img, file in self.image_labels:
            if file == image_file:
                # Get the image bounds
                bbox = self.canvas.bbox(img_item)
                if bbox:
                    x1, y1, x2, y2 = bbox
                    # Create a semi-transparent overlay
                    overlay = self.canvas.create_rectangle(x1, y1, x2, y2, 
                                                         fill='gray', stipple='gray50',
                                                         outline='green', width=3)
                    # Add "COPIED" text
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    text = self.canvas.create_text(center_x, center_y, 
                                                 text="COPIED", 
                                                 font=("Arial", 16, "bold"), 
                                                 fill="green")
                break

    def next_page(self, event):
        """Move to the next page of images."""
        if self.is_loading:
            return

        # Check if we have enough preloaded images for instant page transition
        if len(self.preloaded_images) >= self.min_images_to_display:
            # Instant transition using preloaded images
            self.is_loading = True
            self.canvas.delete("all")
            
            # Move current batch to removed folder in background if in move mode
            if not self.copy_instead_of_move:
                threading.Thread(target=self._move_current_batch_to_removed, daemon=True).start()
            
            # Load next batch immediately
            self.load_batch()
        else:
            # Traditional loading with screen
            self.is_loading = True
            self.canvas.delete("all")
            self.show_loading_screen()
            threading.Thread(target=self._process_next_page, daemon=True).start()

    def show_loading_screen(self):
        """Display an informative loading screen with statistics."""
        # Calculate statistics
        remaining = len(self.images)
        total_in_session = self.stats['total_processed']
        session_time = time.time() - self.stats['session_start_time'] if self.stats['session_start_time'] else 0
        
        # Create a dark blue background rectangle for better contrast
        bg_rect = self.canvas.create_rectangle(0, 0, self.screen_width, self.screen_height, 
                                             fill='#1a1a2e', outline='')
        
        # Main title
        self.canvas.create_text(self.screen_width/2, self.screen_height*0.2, 
                               text="Loading Next Batch...", 
                               font=("Arial", 32, "bold"), fill="#4CAF50")
        
        # Session info section
        y_pos = self.screen_height * 0.35
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text="Session Statistics", 
                               font=("Arial", 24, "bold"), fill="#FFD700")
        
        y_pos += 60
        
        # Current folder
        folder_name = os.path.basename(self.folder) if self.folder else "Unknown"
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text=f"Processing folder: {folder_name}", 
                               font=("Arial", 16), fill="white")
        y_pos += 40
        
        # Mode indicator
        mode_text = "Copy Mode" if self.copy_instead_of_move else "Move Mode"
        mode_color = "#2196F3" if self.copy_instead_of_move else "#FF9800"
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text=f"Mode: {mode_text}", 
                               font=("Arial", 16), fill=mode_color)
        y_pos += 50
        
        # Images remaining
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text=f"Images Remaining: {remaining}", 
                               font=("Arial", 20, "bold"), fill="#FF5722")
        y_pos += 50
        
        # Processing stats
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text=f"Images Processed This Session: {total_in_session}", 
                               font=("Arial", 18), fill="#03DAC6")
        y_pos += 40
        
        # Auto-sort stats
        auto_sorted = self.stats.get('auto_sorted', 0)
        if auto_sorted > 0:
            self.canvas.create_text(self.screen_width/2, y_pos, 
                                   text=f"Auto-Sorted Images: {auto_sorted}", 
                                   font=("Arial", 18), fill="#9C27B0")
            y_pos += 40
        
        # Sorting breakdown
        if total_in_session > 0:
            self.canvas.create_text(self.screen_width/2, y_pos, 
                                   text="Manual Sorting Breakdown:", 
                                   font=("Arial", 16, "bold"), fill="#FFD700")
            y_pos += 35
            
            # Create colored bars for each category
            bar_width = 300
            bar_height = 20
            x_center = self.screen_width / 2
            
            categories = [('1', '#4CAF50'), ('2', '#2196F3'), ('3', '#FF9800')]
            for i, (cat, color) in enumerate(categories):
                count = self.stats[f'sorted_to_{cat}']
                percentage = (count / total_in_session) * 100 if total_in_session > 0 else 0
                
                # Category label and count
                self.canvas.create_text(x_center - bar_width/2 - 50, y_pos + 10, 
                                       text=f"Folder {cat}:", 
                                       font=("Arial", 14), fill="white", anchor="e")
                
                # Progress bar background
                self.canvas.create_rectangle(x_center - bar_width/2, y_pos, 
                                           x_center + bar_width/2, y_pos + bar_height, 
                                           fill="#333333", outline="white")
                
                # Progress bar fill
                fill_width = (count / max(total_in_session, 1)) * bar_width
                if fill_width > 0:
                    self.canvas.create_rectangle(x_center - bar_width/2, y_pos, 
                                               x_center - bar_width/2 + fill_width, y_pos + bar_height, 
                                               fill=color, outline="")
                
                # Count and percentage
                self.canvas.create_text(x_center + bar_width/2 + 20, y_pos + 10, 
                                       text=f"{count} ({percentage:.1f}%)", 
                                       font=("Arial", 14), fill="white", anchor="w")
                
                y_pos += 35
        
        # Session time
        y_pos += 20
        hours = int(session_time // 3600)
        minutes = int((session_time % 3600) // 60)
        seconds = int(session_time % 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.canvas.create_text(self.screen_width/2, y_pos, 
                               text=f"Session Time: {time_str}", 
                               font=("Arial", 16), fill="#9C27B0")
        
        # Progress indicator
        if self.stats['total_images_at_start'] > 0:
            progress = ((self.stats['total_images_at_start'] - remaining) / self.stats['total_images_at_start']) * 100
            y_pos += 50
            self.canvas.create_text(self.screen_width/2, y_pos, 
                                   text=f"Overall Progress: {progress:.1f}%", 
                                   font=("Arial", 18, "bold"), fill="#8BC34A")
        
        self.update_idletasks()

    def _move_current_batch_to_removed(self):
        """Move current batch to removed folder in background."""
        moved_count = 0
        for _, _, image_file in self.image_labels:
            if os.path.exists(image_file):
                dest_file = os.path.join(self.sorted_folders['removed'], os.path.basename(image_file))
                try:
                    shutil.move(image_file, dest_file)
                    moved_count += 1
                except Exception as e:
                    print(f"Error moving image {image_file} to removed folder: {e}")
        
        # Update statistics for removed images
        self.stats['moved_to_removed'] += moved_count

    def _process_next_page(self):
        """Process the next page in a background thread."""
        # Only move images to 'removed' folder if we're in move mode
        if not self.copy_instead_of_move:
            self._move_current_batch_to_removed()

        # Clear the current batch and preloaded cache
        self.current_batch.clear()
        self.image_labels.clear()
        
        # Perform garbage collection
        gc.collect()

        # Load new batch
        self.after(0, self.load_batch)

    def update_stats_display(self):
        """Update the statistics display."""
        processable_remaining = len(self.images) + len(self.image_labels) + len(self.preloaded_images)
        processed = self.stats['total_processed']
        skipped = len(self.skipped_images)
        
        if skipped > 0:
            self.title(f'Enhanced Image Sorter - {processable_remaining} remaining ({skipped} skipped)')
            self.stats_label.config(text=f"Images: {processable_remaining} | Processed: {processed} | Skipped: {skipped}")
        else:
            self.title(f'Enhanced Image Sorter - {processable_remaining} images remaining')
            self.stats_label.config(text=f"Images: {processable_remaining} | Processed: {processed}")
    
    def show_welcome_message(self):
        """Show a welcome message when no source folders are configured."""
        # Clear canvas and show welcome
        self.canvas.delete("all")
        
        # Create a welcoming background
        bg_rect = self.canvas.create_rectangle(0, 0, self.screen_width, self.screen_height, 
                                             fill='#1a1a2e', outline='')
        
        # Welcome message
        self.canvas.create_text(self.screen_width/2, self.screen_height*0.3, 
                               text="Welcome to Enhanced Image Sorter!", 
                               font=("Arial", 36, "bold"), fill="#4CAF50")
        
        self.canvas.create_text(self.screen_width/2, self.screen_height*0.45, 
                               text="Click 'Settings' in the menu or press 'C' to configure source folders", 
                               font=("Arial", 16), fill="white")
        
        self.canvas.create_text(self.screen_width/2, self.screen_height*0.55, 
                               text="Add the folders containing images you want to sort", 
                               font=("Arial", 14), fill="#FFD700")
        
        # Quick action button
        button_y = self.screen_height * 0.7
        button_rect = self.canvas.create_rectangle(
            self.screen_width/2 - 100, button_y - 20,
            self.screen_width/2 + 100, button_y + 20,
            fill="#4CAF50", outline="white", width=2
        )
        
        button_text = self.canvas.create_text(self.screen_width/2, button_y, 
                                            text="Open Settings", 
                                            font=("Arial", 14, "bold"), fill="white")
        
        # Make button clickable
        def on_button_click(event):
            self.change_folder()
        
        self.canvas.tag_bind(button_rect, "<Button-1>", on_button_click)
        self.canvas.tag_bind(button_text, "<Button-1>", on_button_click)
        
        self.update_idletasks()
    
    def show_initial_setup(self):
        """Show the settings dialog for initial setup."""
        self.change_folder()
    
    def show_batch_loading_indicator(self):
        """Show a simple loading indicator for batch operations."""
        # Create a small loading indicator in the corner
        self.loading_indicator = self.canvas.create_text(
            self.screen_width - 150, 30, 
            text="Loading batch...", 
            font=("Arial", 12), fill="#FFD700",
            anchor="ne"
        )
    
    def update_batch_loading_indicator(self, processed, total):
        """Update the batch loading indicator."""
        if hasattr(self, 'loading_indicator'):
            self.canvas.itemconfig(
                self.loading_indicator,
                text=f"Loading... {processed}/{total}"
            )
    
    def clear_batch_loading_indicator(self):
        """Clear the batch loading indicator."""
        if hasattr(self, 'loading_indicator'):
            self.canvas.delete(self.loading_indicator)
            delattr(self, 'loading_indicator')

    def auto_sort_all(self, event=None):
        """Start auto-sort operation for all images."""
        if self.is_loading:
            return
        
        # Get all image files from the source folders
        include_subfolders = self.config_manager.config.get('include_subfolders', True) if self.config_manager else True
        all_images = load_images(
            self.source_folders if self.source_folders else [self.folder], 
            list(self.sorted_folders.values()),
            False,  # Don't include destination folders for auto-sort
            include_subfolders
        )
        
        # Handle different return formats and extract just the paths
        if all_images and isinstance(all_images[0], dict):
            all_images = [item['path'] for item in all_images]
        
        if not all_images:
            messagebox.showinfo("Info", "No images found to sort.")
            return
        
        # Check if there are any terms configured
        terms = self.config_manager.get_auto_sort_terms()
        if not terms:
            if messagebox.askyesno("No Terms", 
                                 "No auto-sort terms are configured. Would you like to open the term manager?"):
                self.open_term_manager()
            return
        
        # Show enhanced confirmation dialog
        if self.config_manager.config['ui_preferences'].get('auto_sort_confirmation', True):
            mode_choice = show_auto_sort_confirm(self, self.config_manager, len(all_images), terms)
            
            if not mode_choice:  # User cancelled
                return
            
            # Update auto-sort settings with chosen mode
            self.config_manager.update_auto_sort_settings(
                copy_instead_of_move=(mode_choice == 'copy')
            )
        
        self.start_auto_sort_operation(all_images)

    def auto_sort_batch(self, event=None):
        """Auto-sort current batch only."""
        if self.is_loading or not self.current_batch:
            return
        
        # Check if there are any terms configured
        terms = self.config_manager.get_auto_sort_terms()
        if not terms:
            messagebox.showinfo("Info", "No auto-sort terms are configured.")
            return
        
        # For batch sorting, show a simpler confirmation
        enabled_terms = [t['term'] for t in terms if t.get('enabled', True)]
        auto_settings = self.config_manager.get_auto_sort_settings()
        current_mode = "copy" if auto_settings.get('copy_instead_of_move', False) else "move"
        
        if not messagebox.askyesno("Confirm Batch Auto-Sort", 
                                 f"Auto-sort {len(self.current_batch)} images (current batch) using {len(enabled_terms)} terms?\n\n"
                                 f"Mode: {current_mode.upper()}\n"
                                 f"Terms: {', '.join(enabled_terms[:5])}{'...' if len(enabled_terms) > 5 else ''}"):
            return
        
        self.start_auto_sort_operation(self.current_batch.copy())

    def re_sort_auto_sorted_images(self, event=None):
        """Re-sort existing auto-sorted images with current rules."""
        # Check if there are any terms configured
        terms = self.config_manager.get_auto_sort_terms()
        if not terms:
            if messagebox.askyesno("No Terms", 
                                 "No auto-sort terms are configured. Would you like to open the term manager?"):
                self.open_term_manager()
            return
        
        # Check for auto-sorted images
        auto_sorted_base = self.config_manager.sorted_folders.get('auto_sorted')
        if not auto_sorted_base or not os.path.exists(auto_sorted_base):
            messagebox.showinfo("Info", "No auto-sorted folder found.")
            return
        
        # Quick scan to estimate image count
        image_count = 0
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        for root, dirs, files in os.walk(auto_sorted_base):
            for filename in files:
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    image_count += 1
        
        if image_count == 0:
            messagebox.showinfo("Info", "No images found in auto-sorted folders.")
            return
        
        # Confirm with user
        enabled_terms = [t['term'] for t in terms if t.get('enabled', True)]
        if not messagebox.askyesno("Confirm Re-Sort", 
                                 f"Re-sort approximately {image_count} auto-sorted images using current term rules?\n\n"
                                 f"This will re-evaluate each image and move/copy to appropriate folders based on:\n"
                                 f"• {len(enabled_terms)} enabled terms\n"
                                 f"• Current multi-tag mode: {self.config_manager.get_multi_tag_mode()}\n\n"
                                 f"Note: This may take some time for large collections."):
            return
        
        self.start_re_sort_operation()

    def start_re_sort_operation(self):
        """Start the re-sort operation with progress dialog."""
        # Create progress dialog
        progress_dialog = AutoSortProgressDialog(self, "Re-sorting Auto-Sorted Images")
        progress_dialog.enable_pause_resume()
        
        def progress_callback(progress_info):
            if progress_dialog.winfo_exists():
                progress_dialog.update_progress(
                    progress_info.get('processed', 0),
                    progress_info.get('total', 1),
                    progress_info.get('current_file', ''),
                    moved=progress_info.get('moved', 0)
                )
        
        def run_re_sort():
            try:
                # Configure auto-sorter
                self.auto_sorter.reset_state()
                
                # Start re-sorting
                results = self.auto_sorter.re_sort_auto_sorted_images(progress_callback)
                
                # Show completion
                if progress_dialog.winfo_exists():
                    if results['errors']:
                        error_msg = f"Completed with {len(results['errors'])} errors"
                        progress_dialog.operation_completed(False, error_msg)
                    else:
                        progress_dialog.operation_completed(True)
                
                # Show results dialog
                if results.get('moved', 0) > 0 or results.get('errors'):
                    self.after(100, lambda: self.show_re_sort_results(results))
                
                # Refresh the display
                self.after(0, self.load_initial_images)
                
            except Exception as e:
                if progress_dialog.winfo_exists():
                    progress_dialog.operation_completed(False, str(e))
                messagebox.showerror("Re-Sort Error", f"Re-sort failed: {e}")
        
        # Connect cancellation
        def check_cancellation():
            if progress_dialog.is_cancelled():
                self.auto_sorter.cancel_operation()
            if progress_dialog.is_paused():
                self.auto_sorter.pause_operation()
            else:
                self.auto_sorter.resume_operation()
            
            if not progress_dialog.is_cancelled():
                self.after(100, check_cancellation)
        
        # Start the operation in a separate thread
        threading.Thread(target=run_re_sort, daemon=True).start()
        check_cancellation()

    def show_re_sort_results(self, results):
        """Show re-sort operation results."""
        total_processed = results.get('processed', 0)
        total_moved = results.get('moved', 0)
        errors = results.get('errors', [])
        
        message = f"Re-sort Operation Complete\n\n"
        message += f"Images processed: {total_processed}\n"
        message += f"Images moved/copied: {total_moved}\n"
        
        if errors:
            message += f"\nErrors encountered: {len(errors)}\n"
            if len(errors) <= 5:
                message += "\nError details:\n" + "\n".join(errors)
            else:
                message += f"\nFirst 5 errors:\n" + "\n".join(errors[:5])
                message += f"\n... and {len(errors) - 5} more errors"
        
        messagebox.showinfo("Re-Sort Results", message)

    def collect_unmatched_images(self, event=None):
        """Collect unmatched images from source folders."""
        # Check if there are any terms configured
        terms = self.config_manager.get_auto_sort_terms()
        if not terms:
            if messagebox.askyesno("No Terms", 
                                 "No auto-sort terms are configured. Would you like to open the term manager first?"):
                self.open_term_manager()
            return
        
        # Get source folders to scan
        source_folders = self.config_manager.get_source_folders()
        if not source_folders:
            source_folders = [self.folder]  # Use current folder if no sources configured
        
        # Quick scan to estimate unmatched count
        unmatched_estimate = self.estimate_unmatched_count(source_folders)
        
        if unmatched_estimate == 0:
            messagebox.showinfo("No Unmatched Images", 
                              "No unmatched images found in source folders.\n\n"
                              "All images appear to be either already sorted or match current terms.")
            return
        
        # Confirm with user
        enabled_terms = [t['term'] for t in terms if t.get('enabled', True)]
        copy_mode = self.config_manager.get_auto_sort_settings().get('copy_instead_of_move', False)
        operation = "copy" if copy_mode else "move"
        
        if not messagebox.askyesno("Confirm Collect Unmatched", 
                                 f"Scan source folders and {operation} unmatched images to the unmatched folder?\n\n"
                                 f"Estimated unmatched images: ~{unmatched_estimate}\n"
                                 f"Active terms: {len(enabled_terms)}\n"
                                 f"Operation: {operation.upper()}\n\n"
                                 f"Source folders to scan:\n" + "\n".join(f"• {folder}" for folder in source_folders[:3]) +
                                 (f"\n• ... and {len(source_folders)-3} more" if len(source_folders) > 3 else "")):
            return
        
        self.start_collect_unmatched_operation(source_folders)

    def estimate_unmatched_count(self, source_folders):
        """Quick estimation of unmatched images without full processing."""
        try:
            destination_folders = set(self.config_manager.sorted_folders.values())
            count = 0
            
            for source_folder in source_folders[:1]:  # Just check first folder for estimate
                if not os.path.exists(source_folder):
                    continue
                    
                for root, dirs, files in os.walk(source_folder):
                    # Skip destination folders
                    if any(dest_folder in root for dest_folder in destination_folders):
                        continue
                        
                    for filename in files:
                        _, ext = os.path.splitext(filename.lower())
                        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
                            count += 1
                            if count > 50:  # Cap estimation at reasonable number
                                return count
            
            return min(count * len(source_folders), 200)  # Extrapolate and cap
            
        except Exception:
            return 10  # Fallback estimate

    def start_collect_unmatched_operation(self, source_folders):
        """Start the unmatched collection operation with progress dialog."""
        # Create progress dialog
        progress_dialog = AutoSortProgressDialog(self, "Collecting Unmatched Images")
        progress_dialog.enable_pause_resume()
        
        def progress_callback(progress_info):
            if progress_dialog.winfo_exists():
                progress_dialog.update_progress(
                    progress_info.get('scanned', 0),
                    progress_info.get('total', 1),
                    progress_info.get('current_file', ''),
                    collected=progress_info.get('collected', 0),
                    already_sorted=progress_info.get('already_sorted', 0)
                )
        
        def run_collect_unmatched():
            try:
                # Configure auto-sorter
                self.auto_sorter.reset_state()
                
                # Start collection
                results = self.auto_sorter.collect_unmatched_from_source(source_folders, progress_callback)
                
                # Show completion
                if progress_dialog.winfo_exists():
                    if results['errors']:
                        error_msg = f"Completed with {len(results['errors'])} errors"
                        progress_dialog.operation_completed(False, error_msg)
                    else:
                        progress_dialog.operation_completed(True)
                
                # Show results dialog
                self.after(100, lambda: self.show_collect_unmatched_results(results))
                
                # Refresh the display
                self.after(0, self.load_initial_images)
                
            except Exception as e:
                if progress_dialog.winfo_exists():
                    progress_dialog.operation_completed(False, str(e))
                messagebox.showerror("Collection Error", f"Unmatched collection failed: {e}")
        
        # Connect cancellation
        def check_cancellation():
            if progress_dialog.is_cancelled():
                self.auto_sorter.cancel_operation()
            if progress_dialog.is_paused():
                self.auto_sorter.pause_operation()
            else:
                self.auto_sorter.resume_operation()
            
            if not progress_dialog.is_cancelled():
                self.after(100, check_cancellation)
        
        # Start the operation in a separate thread
        threading.Thread(target=run_collect_unmatched, daemon=True).start()
        check_cancellation()

    def show_collect_unmatched_results(self, results):
        """Show unmatched collection operation results."""
        scanned = results.get('scanned', 0)
        collected = results.get('collected', 0)
        already_sorted = results.get('already_sorted', 0)
        matched_terms = results.get('matched_terms', 0)
        errors = results.get('errors', [])
        
        message = f"Unmatched Collection Complete\n\n"
        message += f"Images scanned: {scanned}\n"
        message += f"Collected as unmatched: {collected}\n"
        message += f"Already sorted: {already_sorted}\n"
        message += f"Matched current terms: {matched_terms}\n"
        
        if errors:
            message += f"\nErrors encountered: {len(errors)}\n"
            if len(errors) <= 3:
                message += "\nError details:\n" + "\n".join(errors)
            else:
                message += f"\nFirst 3 errors:\n" + "\n".join(errors[:3])
                message += f"\n... and {len(errors) - 3} more errors"
        
        if collected > 0:
            message += f"\n\nUnmatched images are now in the 'unmatched' folder."
            message += f"\nYou can review them and add new terms as needed."
        
        messagebox.showinfo("Collection Results", message)

    def start_auto_sort_operation(self, image_files):
        """Start the auto-sort operation with progress dialog."""
        # Create progress dialog
        progress_dialog = AutoSortProgressDialog(self, "Auto-Sorting Images")
        progress_dialog.enable_pause_resume()
        
        def progress_callback(current, total, current_file="", **stats):
            if progress_dialog.winfo_exists():
                progress_dialog.update_progress(current, total, current_file, **stats)
        
        def run_auto_sort():
            try:
                # Configure auto-sorter
                self.auto_sorter.progress_callback = progress_callback
                self.auto_sorter.reset_state()
                
                # Start sorting
                results = self.auto_sorter.sort_by_metadata(image_files)
                
                # Update our statistics
                self.stats['auto_sorted'] += results['sorted']
                self.stats['total_processed'] += results['processed']
                
                # Show completion
                if progress_dialog.winfo_exists():
                    if results['errors']:
                        error_msg = f"Completed with {len(results['errors'])} errors"
                        progress_dialog.operation_completed(False, error_msg)
                    else:
                        progress_dialog.operation_completed(True)
                
                # Show review dialog if anything was sorted
                if results.get('sorted', 0) > 0 or results.get('errors'):
                    self.after(100, lambda: self.show_sort_review(results))

                # Auto-rebuild tag database if images were sorted
                if results.get('sorted', 0) > 0:
                    self.after(200, self.prompt_tag_database_rebuild)

                # Refresh the display and update undo/redo states
                self.after(0, lambda: (self.load_initial_images(), self.update_undo_redo_menu_states()))
                
            except Exception as e:
                if progress_dialog.winfo_exists():
                    progress_dialog.operation_completed(False, str(e))
                messagebox.showerror("Auto-Sort Error", f"Auto-sort failed: {e}")
        
        # Connect cancellation
        def check_cancellation():
            if progress_dialog.is_cancelled():
                self.auto_sorter.cancel_operation()
            if progress_dialog.is_paused():
                self.auto_sorter.pause_operation()
            else:
                self.auto_sorter.resume_operation()
            
            if not progress_dialog.is_cancelled():
                self.after(100, check_cancellation)
        
        # Start the operation in a separate thread
        threading.Thread(target=run_auto_sort, daemon=True).start()
        check_cancellation()

    def open_term_manager(self, event=None):
        """Open the term manager dialog."""
        TermManagerDialog(self, self.config_manager)

    def scan_metadata(self):
        """Scan metadata for current batch."""
        if not self.current_batch:
            messagebox.showinfo("Info", "No images in current batch to scan.")
            return
        
        found_metadata = 0
        self.metadata_status.config(text="Scanning...")
        self.update_idletasks()
        
        for image_file in self.current_batch:
            metadata = self.metadata_parser.extract_metadata(image_file)
            if metadata:
                found_metadata += 1
        
        self.metadata_status.config(text=f"Found: {found_metadata}/{len(self.current_batch)}")
        messagebox.showinfo("Metadata Scan", 
                          f"Found metadata in {found_metadata} out of {len(self.current_batch)} images.")

    def clear_metadata_cache(self):
        """Clear the metadata cache."""
        self.metadata_parser.clear_cache()
        self.metadata_status.config(text="Cache cleared")
        messagebox.showinfo("Cache Cleared", "Metadata cache has been cleared.")

    def embed_tag_files(self):
        """Embed tag files into image metadata with progress tracking."""
        if not messagebox.askyesno("Embed Tag Files", 
                                 "This will embed .txt tag file contents into image metadata.\n\n"
                                 "This allows tags to travel with images and eliminates the need "
                                 "to manage separate tag files.\n\n"
                                 "Original images will be backed up with .original extension.\n\n"
                                 "Continue?"):
            return
        
        # Create and show progress dialog
        progress_dialog = TagEmbedProgressDialog(self, self.folder)
        
        def progress_callback(action, data=None):
            """Handle progress updates from the tag embedder."""
            if action == 'total':
                progress_dialog.set_total_images(data)
                return False
            elif action == 'progress':
                progress_dialog.update_progress(
                    data['processed'],
                    data['success'], 
                    data['failed'],
                    data['no_tags'],
                    data['skipped'],
                    data['current_file']
                )
                return False
            elif action == 'check_cancelled':
                return progress_dialog.cancelled
            elif action == 'check_paused':
                return progress_dialog.paused
            elif action == 'complete':
                progress_dialog.operation_complete()
                
                # Show final results
                results = data
                message = (f"Tag embedding completed!\n\n"
                          f"Processed: {results['processed']} images\n"
                          f"Successfully embedded: {results['success']}\n"
                          f"Failed: {results['failed']}\n" 
                          f"No tag files: {results['no_tags']}\n"
                          f"Already embedded: {results['skipped']}")
                
                self.after(100, lambda: messagebox.showinfo("Embedding Complete", message))
                
                # Clear metadata cache since we've modified images
                self.after(200, self.clear_metadata_cache)
                return False
            
            return False
        
        def run_embedding():
            """Run the embedding process in a separate thread."""
            try:
                self.tag_embedder.embed_tags_in_folder(self.folder, progress_callback=progress_callback)
            except Exception as e:
                # Handle errors in the main thread
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to embed tag files: {e}"))
                self.after(0, progress_dialog.operation_complete)
        
        # Start embedding in background thread
        threading.Thread(target=run_embedding, daemon=True).start()

    def export_terms(self):
        """Export auto-sort terms."""
        filename = filedialog.asksaveasfilename(
            title="Export Terms",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.config_manager.export_terms(filename)
                messagebox.showinfo("Success", "Terms exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export terms: {e}")

    def import_terms(self):
        """Import auto-sort terms."""
        filename = filedialog.askopenfilename(
            title="Import Terms",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.config_manager.import_terms(filename, merge=True)
                messagebox.showinfo("Success", "Terms imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import terms: {e}")

    def browse_unmatched_images(self):
        """Open the unmatched images viewer dialog."""
        try:
            from unmatched_viewer import show_unmatched_viewer
            show_unmatched_viewer(self, self.config_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open unmatched viewer: {str(e)}")

    def open_batch_export(self):
        """Open the batch export dialog for WAN 2.2 i2v processing."""
        try:
            show_batch_export_dialog(self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open batch export tool: {str(e)}")

    def open_visual_sort(self):
        """Open the visual sort dialog for LoRA workflow sorting."""
        if self.is_loading:
            messagebox.showinfo("Info", "Please wait for images to finish loading.")
            return

        # Get all image files from the source folders
        include_subfolders = self.config_manager.config.get('include_subfolders', True) if self.config_manager else True
        all_images = load_images(
            self.source_folders if self.source_folders else [self.folder],
            list(self.sorted_folders.values()),
            False,
            include_subfolders
        )

        # Handle different return formats and extract just the paths
        if all_images and isinstance(all_images[0], dict):
            all_images = [item['path'] for item in all_images]

        if not all_images:
            messagebox.showinfo("Info", "No images found to sort.")
            return

        try:
            result = show_visual_sort_dialog(self, self.config_manager, all_images)

            if result:
                self._execute_visual_sort(result, all_images)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open visual sort tool: {str(e)}")

    def open_background_sort(self):
        """Open the background sort dialog for finding t-shirt ready images."""
        try:
            show_background_sort_dialog(self, self.config_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open background sort tool: {str(e)}")

    def _execute_visual_sort(self, sort_config, image_files):
        """Execute the visual sort operation based on dialog result."""
        from auto_sort_progress import AutoSortProgressDialog

        action = sort_config.get('action')
        use_yolo = sort_config.get('use_yolo', False)
        copy_mode = sort_config.get('copy_mode', True)

        # Update config for copy mode
        settings = self.config_manager.get_auto_sort_settings()
        settings['copy_instead_of_move'] = copy_mode
        self.config_manager.set_auto_sort_settings(settings)

        # Create progress dialog
        if action == 'visual_sort':
            sort_by = sort_config.get('sort_by', 'shot_type')
            progress_dialog = AutoSortProgressDialog(
                self, f"Visual Sort by {sort_by.replace('_', ' ').title()}"
            )
        elif action == 'profile_sort':
            profile = sort_config.get('profile')
            progress_dialog = AutoSortProgressDialog(
                self, f"LoRA Profile Sort: {profile.name}"
            )
        else:
            return

        def progress_callback(current, total, filename, **kwargs):
            if progress_dialog.winfo_exists():
                progress_dialog.after(0, lambda: progress_dialog.update_progress(
                    current, total, filename,
                    processed=kwargs.get('processed', current),
                    sorted=kwargs.get('sorted', 0) or kwargs.get('matched', 0),
                    errors=kwargs.get('errors', [])
                ))

        def sort_thread():
            try:
                if action == 'visual_sort':
                    results = self.auto_sorter.sort_by_visual_classification(
                        image_files,
                        sort_by=sort_config.get('sort_by', 'shot_type'),
                        use_yolo=use_yolo,
                        progress_callback=progress_callback
                    )
                elif action == 'profile_sort':
                    profile = sort_config.get('profile')
                    results = self.auto_sorter.sort_by_lora_profile(
                        image_files,
                        profile=profile,
                        use_yolo=use_yolo,
                        progress_callback=progress_callback
                    )
                else:
                    results = {'processed': 0, 'sorted': 0, 'errors': []}

                # Update UI on completion
                def on_complete():
                    if progress_dialog.winfo_exists():
                        progress_dialog.operation_completed(
                            success=len(results.get('errors', [])) == 0
                        )

                    # Show summary
                    sorted_count = results.get('sorted', 0) or results.get('matched', 0)
                    error_count = len(results.get('errors', []))

                    summary = f"Visual sort completed!\n\n"
                    summary += f"Processed: {results.get('processed', 0)}\n"
                    summary += f"Sorted: {sorted_count}\n"

                    if 'classification_counts' in results:
                        summary += "\nBy category:\n"
                        for cat, count in sorted(
                            results['classification_counts'].items(),
                            key=lambda x: -x[1]
                        ):
                            summary += f"  {cat}: {count}\n"

                    if error_count > 0:
                        summary += f"\nErrors: {error_count}"

                    messagebox.showinfo("Visual Sort Complete", summary)

                    # Reload images to reflect changes
                    self.reload_images()

                progress_dialog.after(100, on_complete)

            except Exception as e:
                def on_error():
                    if progress_dialog.winfo_exists():
                        progress_dialog.operation_completed(success=False, message=str(e))
                    messagebox.showerror("Error", f"Visual sort failed: {str(e)}")

                progress_dialog.after(0, on_error)

        # Start sort in background thread
        progress_dialog.enable_pause_resume()
        thread = threading.Thread(target=sort_thread, daemon=True)
        thread.start()

    def change_folder(self, event=None):
        """Change the source folder and reload images."""
        if self.is_loading:
            return
        
        # Stop background loading when changing folders
        self.stop_background_loading()
        # Clear preloaded cache
        self.preloaded_images.clear()

        # Show unified configuration dialog
        result = show_setup_dialog(self, self.config_manager)
        
        if result:
            old_num_rows = self.num_rows
            self.folder = result['folder']
            self.num_rows = result['num_rows']
            self.random_order = result['random_order']
            self.copy_instead_of_move = result['copy_instead_of_move']
            
            # Update source folders if provided
            if 'source_folders' in result:
                self.source_folders = result['source_folders']
            if 'active_sources' in result:
                self.current_image_metadata.clear()  # Clear old metadata
            
            # Refresh sorted folders from config manager
            self.config_manager.setup_folders()
            self.sorted_folders = self.config_manager.sorted_folders
            
            # If rows changed, recalculate dimensions; otherwise just reload images
            if old_num_rows != self.num_rows:
                self._recalculate_and_reload()
            else:
                self.load_initial_images()
            
    def show_key_bindings(self):
        """Show a dialog with the current key and mouse bindings."""
        bindings_text = "Enhanced Image Sorter - Controls:\n\n"
        
        # Mouse bindings
        bindings_text += "Mouse Controls:\n"
        for binding, action in self.bindings.items():
            if binding.endswith('mouse') or binding.startswith('wheel'):
                # Format the binding name for display
                name = binding.replace('_', ' ').title()
                bindings_text += f"• {name}: {self.get_action_description(action)}\n"
        
        # Keyboard bindings
        bindings_text += "\nKeyboard Controls:\n"
        for binding, action in self.bindings.items():
            if binding.startswith('key_'):
                # Format the key name for display
                key = binding.replace('key_', '').upper()
                bindings_text += f"• {key}: {self.get_action_description(action)}\n"
        
        # Auto-sort shortcuts
        bindings_text += "\nAuto-Sort Shortcuts:\n"
        bindings_text += "• Ctrl+A: Auto-sort all images\n"
        bindings_text += "• Ctrl+T: Open term manager\n"
        
        bindings_text += "\nYou can customize these bindings in the configuration."
        
        messagebox.showinfo("Enhanced Image Sorter - Controls", bindings_text)

    def show_auto_sort_help(self):
        """Show auto-sort help dialog."""
        help_text = """Auto-Sort Feature Guide

The auto-sort feature automatically categorizes images based on their metadata content, particularly useful for AI-generated images with embedded prompts.

How to use:
1. Configure search terms using 'Manage Terms' button
2. Add terms that match content in your images
3. Use 'Auto-Sort All' to process all images
4. Use 'Auto-Sort Batch' for current display only

Term Types:
• Word Boundary: Matches complete words (recommended)
• Contains: Matches text anywhere
• Exact: Exact text match
• Regex: Advanced pattern matching

The system will create subfolders for each term and sort images accordingly. Images with no matches can be left in place or moved to an 'unmatched' folder.

For best results with AI-generated images, use terms that commonly appear in prompts like 'portrait', 'landscape', 'anime', etc."""

        messagebox.showinfo("Auto-Sort Guide", help_text)

    def show_visual_sort_help(self):
        """Show visual sort help dialog."""
        help_text = """Visual Sort Guide - LoRA Workflow Helper

Visual Sort uses WD14 image analysis to classify images based on visual properties, perfect for organizing images for different LoRA workflows.

How to use:
1. Go to Tools > Visual Sort (LoRA Workflow)
2. Choose a sorting mode or LoRA profile
3. Preview your collection's composition first (recommended)
4. Start the sort operation

Sort by Classification:
- Shot Type: portrait, upper_body, cowboy_shot, full_body, wide_shot
- Person Count: solo, duo, group
- NSFW Rating: general, sensitive, questionable, explicit

LoRA Profiles:
Pre-configured filters for common LoRA types:
- portrait_lora: Close-ups/upper body with single subject
- action_lora: Full body/wide shots for motion LoRAs
- duo_lora: Two-person scenes
- sfw_portrait: SFW portrait content only

You can create custom profiles with any combination of:
- Shot types to include
- Person counts to include
- NSFW ratings to allow
- Required tags (must have)
- Excluded tags (must not have)

Output:
Images are sorted to: auto_sorted/visual_<mode>/<category>/
or: auto_sorted/lora_profiles/<profile_name>/

Tips:
- Use Preview & Scan first to understand your collection
- Copy mode (default) keeps originals safe
- YOLO option improves person count accuracy"""

        messagebox.showinfo("Visual Sort Guide", help_text)

    def undo_last_operation(self):
        """Undo the last auto-sort operation."""
        if not self.undo_manager.can_undo():
            self.update_status_bar("Nothing to undo")
            return

        undo_desc = self.undo_manager.get_undo_description()
        if not messagebox.askyesno("Confirm Undo", f"Undo: {undo_desc}?\n\nThis will reverse the operation."):
            return

        self.update_status_bar(f"Undoing: {undo_desc}...")
        success, message = self.undo_manager.undo_last_operation()

        if success:
            self.last_operation_message = f"UNDONE: {message}"
            self.update_status_bar(f"Successfully undone: {undo_desc}")
            self.update_undo_redo_menu_states()
            messagebox.showinfo("Undo Success", message)
        else:
            self.update_status_bar(f"Undo failed: {message}")
            messagebox.showerror("Undo Failed", message)

        self.load_initial_images()

    def redo_operation(self):
        """Redo the last undone operation."""
        if not self.undo_manager.can_redo():
            self.update_status_bar("Nothing to redo")
            return

        redo_desc = self.undo_manager.get_redo_description()
        if not messagebox.askyesno("Confirm Redo", f"Redo: {redo_desc}?\n\nThis will repeat the operation."):
            return

        self.update_status_bar(f"Redoing: {redo_desc}...")
        success, message = self.undo_manager.redo_operation()

        if success:
            self.last_operation_message = f"REDONE: {message}"
            self.update_status_bar(f"Successfully redone: {redo_desc}")
            self.update_undo_redo_menu_states()
            messagebox.showinfo("Redo Success", message)
        else:
            self.update_status_bar(f"Redo failed: {message}")
            messagebox.showerror("Redo Failed", message)

        self.load_initial_images()

    def update_undo_redo_menu_states(self):
        """Update the enabled/disabled state of undo/redo menu items."""
        if self.undo_manager.can_undo():
            undo_desc = self.undo_manager.get_undo_description()
            self.undo_menu_item.entryconfig(self.undo_menu_item, label=f"Undo: {undo_desc} (Ctrl+Z)", state=tk.NORMAL)
        else:
            self.undo_menu_item.entryconfig(self.undo_menu_item, label="Undo (Ctrl+Z)", state=tk.DISABLED)

        if self.undo_manager.can_redo():
            redo_desc = self.undo_manager.get_redo_description()
            self.redo_menu_item.entryconfig(self.redo_menu_item, label=f"Redo: {redo_desc} (Ctrl+Shift+Z)", state=tk.NORMAL)
        else:
            self.redo_menu_item.entryconfig(self.redo_menu_item, label="Redo (Ctrl+Shift+Z)", state=tk.DISABLED)

    def show_about(self):
        """Show about dialog."""
        about_text = """Enhanced Image Sorter v2.0

An advanced tool for sorting images with metadata-based auto-sorting capabilities.

Features:
• Visual grid-based sorting
• Metadata extraction from PNG/JPEG
• Automatic sorting based on content
• Configurable search terms
• Progress tracking and statistics
• Import/export term configurations

Perfect for organizing AI-generated images, photos, and other image collections."""
        
        messagebox.showinfo("About Enhanced Image Sorter", about_text)
        
    def get_action_description(self, action):
        """Get a human-readable description of an action."""
        if action in ('1', '2', '3'):
            return f"Sort to folder {action}"
        elif action == 'next':
            return "Go to next page"
        elif action == 'reload':
            return "Reload images"
        elif action == 'exit':
            return "Exit application"
        elif action == 'config':
            return "Open configuration dialog"
        else:
            return action
    
    def show_sort_review(self, results):
        """Show the auto-sort review dialog."""
        try:
            show_auto_sort_review(self, results, self.config_manager)
        except Exception as e:
            print(f"Error showing sort review: {e}")

    def prompt_tag_database_rebuild(self):
        """Prompt user to rebuild tag database after auto-sort."""
        # Check config setting
        auto_rebuild = self.config_manager.get_setting('auto_rebuild_tag_database', True)

        if not auto_rebuild:
            return

        # Start rebuild in background with non-blocking notification
        self.start_tag_database_rebuild_background()

    def start_tag_database_rebuild_background(self):
        """Start tag database rebuild in background with progress notification."""
        try:
            from rebuild_tag_database import TagDatabaseRebuilder
            from pathlib import Path

            # Create a simple progress window
            progress_window = tk.Toplevel(self)
            progress_window.title("Updating Tag Database")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)

            frame = ttk.Frame(progress_window, padding="20")
            frame.pack(fill="both", expand=True)

            status_label = ttk.Label(frame, text="Updating tag database...", font=("Arial", 10))
            status_label.pack(pady=(0, 10))

            progress_bar = ttk.Progressbar(frame, length=350, mode="determinate")
            progress_bar.pack(pady=(0, 10))

            detail_label = ttk.Label(frame, text="Starting...", font=("Arial", 8), foreground="gray")
            detail_label.pack()

            # Track completion
            rebuild_complete = {'done': False, 'success': False, 'stats': None}

            def update_progress(current, total, message):
                if total > 0:
                    pct = (current / total) * 100
                    progress_bar["value"] = pct
                    detail_label.config(text=f"{current}/{total} - {message[:50]}...")

            def run_rebuild():
                try:
                    rebuilder = TagDatabaseRebuilder('tag_database.db')

                    # Determine which folder to scan
                    master_images = Path('master_images')
                    auto_sorted = Path('auto_sorted')

                    if master_images.exists():
                        folder_to_scan = str(master_images)
                    elif auto_sorted.exists():
                        folder_to_scan = str(auto_sorted)
                    else:
                        rebuild_complete['done'] = True
                        rebuild_complete['success'] = False
                        return

                    # Run rebuild
                    stats = rebuilder.rebuild_from_folder(
                        folder_to_scan,
                        recursive=True,
                        clear_existing=True,
                        progress_callback=update_progress
                    )

                    rebuild_complete['done'] = True
                    rebuild_complete['success'] = stats.get('success', False)
                    rebuild_complete['stats'] = stats

                except Exception as e:
                    logger.error(f"Tag database rebuild failed: {e}")
                    rebuild_complete['done'] = True
                    rebuild_complete['success'] = False

            # Start rebuild thread
            threading.Thread(target=run_rebuild, daemon=True).start()

            # Poll for completion
            def check_completion():
                if not rebuild_complete['done']:
                    progress_window.after(500, check_completion)
                    return

                # Rebuild complete
                if rebuild_complete['success']:
                    stats = rebuild_complete['stats']
                    status_label.config(text="Tag database updated!", foreground="green")
                    detail_label.config(
                        text=f"Added {stats['images_processed']} images, "
                             f"{stats['tags_discovered']} unique tags"
                    )
                    progress_bar["value"] = 100

                    # Auto-close after 2 seconds
                    progress_window.after(2000, progress_window.destroy)
                else:
                    status_label.config(text="Update failed", foreground="red")
                    detail_label.config(text="See console for details")

                    # Close after 3 seconds
                    progress_window.after(3000, progress_window.destroy)

            # Start polling
            check_completion()

        except ImportError:
            # Rebuild tool not available
            logger.warning("Tag database rebuild tool not available")
        except Exception as e:
            logger.error(f"Failed to start tag database rebuild: {e}")

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        is_fullscreen = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not is_fullscreen)
        if not is_fullscreen:
            self.state('zoomed')
        
        # Recalculate dimensions and reload current batch
        self.after(100, self._recalculate_and_reload)  # Small delay to let window resize
    
    def _recalculate_and_reload(self):
        """Recalculate dimensions and reload the current batch."""
        self.update_idletasks()
        
        # Recalculate dimensions
        if self.attributes('-fullscreen'):
            self.screen_width = self.winfo_screenwidth()
            self.screen_height = self.winfo_screenheight()
            available_height = self.screen_height - 80
        else:
            self.screen_width = self.winfo_width()
            self.screen_height = self.winfo_height()
            available_height = self.screen_height - 120
        
        self.row_height = available_height // self.num_rows
        
        # Reload current batch with new dimensions
        if hasattr(self, 'current_batch') and self.current_batch:
            # Put current batch back into the main queue
            self.images = self.current_batch + self.images
            self.current_batch = []
            self.load_batch()

if __name__ == '__main__':
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        
        # Load basic settings
        settings = config_manager.get_basic_settings()
        
        # Always show configuration dialog on startup
        # Create a temporary root window for the dialog
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary window
        
        result = show_setup_dialog(None, config_manager)
        temp_root.destroy()
        
        if not result:
            print("Configuration cancelled by user.")
            sys.exit(0)
        
        # Use settings from dialog
        settings = result
        folder = result['folder']
        
        # Start the main application
        app = ImageSorter(
            folder, 
            settings['num_rows'], 
            settings['random_order'], 
            settings['copy_instead_of_move']
        )
        app.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to show error in a messagebox if tkinter is available
        try:
            messagebox.showerror("Error", f"Failed to start Image Sorter:\n\n{e}")
        except:
            pass
        
        sys.exit(1)