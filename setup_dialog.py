import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from batch_export_dialog import BatchExportDialog
from ui_theme import Theme as ModernStyle

class SetupDialog:
    def __init__(self, parent=None, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
        # Create dialog window
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Image Sorter - Setup & Tools")
        self.window.geometry("1000x750")
        self.window.resizable(True, True)
        self.window.configure(bg=ModernStyle.BG_DARK)

        # Apply modern styling
        ModernStyle.apply(self.window)
        

        # Center the window
        if parent:
            self.window.transient(parent)
            self.window.grab_set()
        
        # Load existing settings if available
        if config_manager:
            settings = config_manager.get_basic_settings()
            self.source_folders = config_manager.get_source_folders().copy()
            self.active_sources = config_manager.config.get('active_sources', {}).copy()
            
            # Backward compatibility: if no source folders but last_folder exists, add it
            if not self.source_folders and settings['last_folder']:
                self.source_folders.append(settings['last_folder'])
                self.active_sources[settings['last_folder']] = True
        else:
            settings = {
                'last_folder': '',
                'num_rows': 4,
                'random_order': False,
                'copy_instead_of_move': False
            }
            self.source_folders = []
            self.active_sources = {}
        
        self.setup_ui(settings)
        
        # Center the dialog
        self.center_window()
        
    def center_window(self):
        """Center the dialog on screen or parent."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        if self.parent:
            x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
            y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        else:
            x = (self.window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.window.winfo_screenheight() // 2) - (height // 2)
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self, settings):
        """Set up the configuration dialog UI."""
        # Create scrollable main frame
        main_canvas = tk.Canvas(self.window, bg=ModernStyle.BG_DARK, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=main_canvas.yview)
        main_scrollable_frame = ttk.Frame(main_canvas)
        
        main_scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=main_scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")
        
        main_frame = ttk.Frame(main_scrollable_frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Setup & Tools", style="Title.TLabel")
        title_label.pack(pady=(0, 10))
        
        # Source folders selection
        source_frame = ttk.LabelFrame(main_frame, text="Source Folders", padding="10")
        source_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Add folder button and info
        add_frame = ttk.Frame(source_frame)
        add_frame.pack(fill="x", pady=(0, 8))

        ttk.Button(add_frame, text="+ Add Folder",
                  command=self.add_source_folder, width=15).pack(side="left")

        info_label = ttk.Label(add_frame, text="Folders containing images to sort", style="Dim.TLabel")
        info_label.pack(side="left", padx=(10, 0))

        # Scrollable frame for source folders (taller)
        self.create_source_folders_list(source_frame)
        
        # Two-column layout for settings
        settings_container = ttk.Frame(main_frame)
        settings_container.pack(fill="x", pady=(0, 10))

        # LEFT COLUMN: Display Settings
        display_frame = ttk.LabelFrame(settings_container, text="Display Settings", padding="10")
        display_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Number of rows
        rows_frame = ttk.Frame(display_frame)
        rows_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(rows_frame, text="Grid rows:").pack(side="left")
        self.rows_var = tk.IntVar(master=self.window, value=settings['num_rows'])
        rows_spinbox = ttk.Spinbox(rows_frame, from_=2, to=8, width=8,
                                  textvariable=self.rows_var)
        rows_spinbox.pack(side="right")

        # Random order checkbox
        self.random_var = tk.BooleanVar(master=self.window, value=settings['random_order'])
        ttk.Checkbutton(display_frame, text="Random order",
                       variable=self.random_var).pack(anchor="w", pady=(0, 5))

        # Include subfolders checkbox
        default_include_subfolders = True
        if hasattr(settings, 'get'):
            default_include_subfolders = settings.get('include_subfolders', True)
        self.include_subfolders_var = tk.BooleanVar(master=self.window, value=default_include_subfolders)
        subfolder_check = ttk.Checkbutton(display_frame, text="Include subfolders",
                                         variable=self.include_subfolders_var)
        subfolder_check.pack(anchor="w")

        # Add tooltip for subfolder handling
        self.create_tooltip(subfolder_check,
                           "Include images in subdirectories")

        # RIGHT COLUMN: File Handling
        file_frame = ttk.LabelFrame(settings_container, text="File Handling", padding="10")
        file_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # Copy mode checkbox
        self.copy_var = tk.BooleanVar(master=self.window, value=settings['copy_instead_of_move'])
        copy_check = ttk.Checkbutton(file_frame, text="Copy (don't move)",
                                    variable=self.copy_var)
        copy_check.pack(anchor="w", pady=(0, 5))

        # Add tooltip for copy mode
        self.create_tooltip(copy_check,
                           "Copy images instead of moving them")

        # Tag file handling checkbox
        default_handle_tags = True
        if hasattr(settings, 'get'):
            default_handle_tags = settings.get('handle_tag_files', True)
        self.handle_tags_var = tk.BooleanVar(master=self.window, value=default_handle_tags)
        tag_check = ttk.Checkbutton(file_frame, text="Handle .txt tag files",
                                   variable=self.handle_tags_var)
        tag_check.pack(anchor="w")

        # Add tooltip for tag handling
        self.create_tooltip(tag_check,
                           "Move/copy .txt tag files with images")

        # Hide already sorted checkbox (for copy mode)
        default_hide_sorted = True
        if self.config_manager:
            default_hide_sorted = self.config_manager.config.get('ui_preferences', {}).get('hide_already_sorted', True)
        self.hide_sorted_var = tk.BooleanVar(master=self.window, value=default_hide_sorted)
        hide_sorted_check = ttk.Checkbutton(file_frame, text="Hide already-copied images",
                                            variable=self.hide_sorted_var)
        hide_sorted_check.pack(anchor="w")

        # Add tooltip for hide sorted
        self.create_tooltip(hide_sorted_check,
                           "Don't show images that already exist in destination folders (copy mode)")

        # Destination folder setup section
        dest_frame = ttk.LabelFrame(main_frame, text="Destination Folders", padding="10")
        dest_frame.pack(fill="x", pady=(0, 10))

        # Get current preferences from config
        dest_in_script = True  # default
        dest_in_source = False  # default
        if self.config_manager:
            dest_settings = self.config_manager.config.get('destination_settings', {})
            dest_in_script = dest_settings.get('script_dir', True)
            dest_in_source = dest_settings.get('source_dirs', False)

        # Script directory checkbox
        self.dest_script_var = tk.BooleanVar(master=self.window, value=dest_in_script)
        script_check = ttk.Checkbutton(dest_frame,
                                      text="Script directory - organized by source (sorted_SourceName/1, 2, 3...)",
                                      variable=self.dest_script_var)
        script_check.pack(anchor="w", pady=(0, 5))

        # Source directory checkbox
        self.dest_source_var = tk.BooleanVar(master=self.window, value=dest_in_source)
        source_check = ttk.Checkbutton(dest_frame,
                                      text="Inside each source directory (1, 2, 3 folders in each source)",
                                      variable=self.dest_source_var)
        source_check.pack(anchor="w", pady=(0, 5))

        # Auto-create checkbox
        self.auto_create_var = tk.BooleanVar(master=self.window, value=True)
        ttk.Checkbutton(dest_frame, text="Auto-create destination folders",
                       variable=self.auto_create_var).pack(anchor="w")
        
        # Tool Buttons frame - 2x2 grid
        tool_frame = ttk.LabelFrame(main_frame, text="Tools", padding="15")
        tool_frame.pack(fill="x", pady=(0, 10))

        # Grid layout for tools
        auto_sort_btn = ttk.Button(tool_frame, text="Auto-Sort Images...",
                                   command=self.open_auto_sort, width=25)
        auto_sort_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.create_tooltip(auto_sort_btn, "Sort images by metadata tags")

        term_mgr_btn = ttk.Button(tool_frame, text="Term Manager...",
                                 command=self.open_term_manager, width=25)
        term_mgr_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.create_tooltip(term_mgr_btn, "Manage auto-sort search terms")

        rebuild_db_btn = ttk.Button(tool_frame, text="Rebuild Tag Database...",
                                    command=self.rebuild_tag_database, width=25)
        rebuild_db_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.create_tooltip(rebuild_db_btn, "Rebuild SQLite tag database")

        batch_export_btn = ttk.Button(tool_frame, text="Batch Export Tool...",
                                      command=self.open_batch_export, width=25)
        batch_export_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.create_tooltip(batch_export_btn, "Query and export images by tags")

        # Make columns expand equally
        tool_frame.columnconfigure(0, weight=1)
        tool_frame.columnconfigure(1, weight=1)

        # Keyboard shortcuts at bottom
        shortcuts_label = ttk.Label(main_frame,
            text="Shortcuts: 1/2/3→Sort  Space→Next  C→Settings  R→Reload  Ctrl+A→Auto-Sort  Ctrl+T→Terms",
            style="Dim.TLabel")
        shortcuts_label.pack(pady=(0, 10))

        # Bottom buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Exit",
                  command=self.exit_app, width=12).pack(side="left")
        ttk.Button(button_frame, text="Cancel",
                  command=self.cancel, width=12).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="OK",
                  command=self.ok, width=12).pack(side="right")
    
    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget."""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background=ModernStyle.BG_HOVER,
                           foreground=ModernStyle.TEXT, relief="solid", borderwidth=1,
                           font=ModernStyle.FONT_SMALL)
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_source_folders_list(self, parent):
        """Create the scrollable list of source folders with checkboxes."""
        # Create frame with scrollbar
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True)
        
        # Scrollable frame (taller for better visibility)
        canvas = tk.Canvas(list_frame, height=120, bg=ModernStyle.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store references
        self.source_canvas = canvas
        self.source_scrollbar = scrollbar
        
        # Initialize folder variables
        self.folder_vars = {}
        
        # Populate with existing folders
        self.refresh_source_folders_list()
    
    def refresh_source_folders_list(self):
        """Refresh the display of source folders."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.folder_vars.clear()
        
        if not self.source_folders:
            # Show message if no folders
            no_folders_label = ttk.Label(self.scrollable_frame, 
                                        text="No source folders added yet. Click 'Add Source Folder...' to begin.",
                                        foreground="gray")
            no_folders_label.pack(pady=20)
            return
        
        for i, folder in enumerate(self.source_folders):
            self.create_folder_row(folder, i)
    
    def create_folder_row(self, folder, index):
        """Create a row for a single source folder."""
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill="x", pady=2, padx=5)
        
        # Checkbox for enabling/disabling this source
        folder_var = tk.BooleanVar(master=self.window, value=self.active_sources.get(folder, True))
        self.folder_vars[folder] = folder_var
        
        checkbox = ttk.Checkbutton(row_frame, variable=folder_var)
        checkbox.pack(side="left", padx=(0, 10))
        
        # Folder path (truncated if too long)
        folder_display = folder
        if len(folder_display) > 60:
            folder_display = "..." + folder_display[-57:]
        
        folder_label = ttk.Label(row_frame, text=folder_display)
        folder_label.pack(side="left", fill="x", expand=True)
        
        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove", width=8,
                               command=lambda f=folder: self.remove_source_folder(f))
        remove_btn.pack(side="right", padx=(10, 0))
        
        # Add tooltip showing full path if truncated
        if len(folder) > 60:
            self.create_tooltip(folder_label, folder)
    
    def add_source_folder(self):
        """Add a new source folder."""
        folder = filedialog.askdirectory(
            title="Select source folder containing images",
            initialdir=os.path.expanduser("~")
        )
        
        if folder and folder not in self.source_folders:
            self.source_folders.append(folder)
            self.active_sources[folder] = True
            self.refresh_source_folders_list()
        elif folder in self.source_folders:
            messagebox.showinfo("Folder Already Added", 
                              "This folder is already in the source list.")
    
    def remove_source_folder(self, folder):
        """Remove a source folder from the list."""
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            if folder in self.active_sources:
                del self.active_sources[folder]
            self.refresh_source_folders_list()
    
    def validate_settings(self):
        """Validate the current settings."""
        # Check that at least one source folder is selected and enabled
        active_folders = [folder for folder, var in self.folder_vars.items() if var.get()]
        
        if not active_folders:
            messagebox.showerror("Error", "Please add and enable at least one source folder.")
            return False
        
        # Validate that all enabled folders exist
        for folder in active_folders:
            if not os.path.exists(folder):
                messagebox.showerror("Error", f"Source folder does not exist:\n{folder}")
                return False
            
            if not os.path.isdir(folder):
                messagebox.showerror("Error", f"Source path is not a folder:\n{folder}")
                return False
        
        return True
    
    def create_folders_if_needed(self, active_folders):
        """Create destination folders based on user preference."""
        if not self.auto_create_var.get():
            return True
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folders_to_create = ['1', '2', '3', 'removed', 'auto_sorted', 'unmatched']
        created_folders = []
        
        try:
            for source_folder in active_folders:
                source_name = self.sanitize_folder_name(os.path.basename(source_folder))
                
                # Script directory organized folders
                if self.dest_script_var.get():
                    source_dest_dir = os.path.join(script_dir, f"sorted_{source_name}")
                    
                    # Create the main destination directory for this source
                    if not os.path.exists(source_dest_dir):
                        os.makedirs(source_dest_dir)
                        created_folders.append(f"sorted_{source_name}/")
                    
                    # Create subdirectories within this source's destination
                    for folder_name in folders_to_create:
                        folder_path = os.path.join(source_dest_dir, folder_name)
                        if not os.path.exists(folder_path):
                            os.makedirs(folder_path)
                            created_folders.append(f"sorted_{source_name}/{folder_name}")
                
                # Source directory folders
                if self.dest_source_var.get():
                    for folder_name in folders_to_create:
                        folder_path = os.path.join(source_folder, folder_name)
                        if not os.path.exists(folder_path):
                            os.makedirs(folder_path)
                            created_folders.append(f"{os.path.basename(source_folder)}/{folder_name}")
            
            if created_folders:
                locations = []
                if self.dest_script_var.get():
                    locations.append("script directory")
                if self.dest_source_var.get():
                    locations.append("source directories")
                location_desc = " and ".join(locations)
                
                messagebox.showinfo("Folders Created", 
                                   f"Created destination folders in {location_desc}:\n\n" + 
                                   "\n".join(created_folders[:15]) +
                                   (f"\n... and {len(created_folders)-15} more" if len(created_folders) > 15 else ""))
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create destination folders: {e}")
            return False
    
    def sanitize_folder_name(self, name):
        """Sanitize a folder name for filesystem compatibility."""
        import re
        # Remove invalid characters and replace with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized
    
    def ok(self):
        """Handle OK button click."""
        if not self.validate_settings():
            return
        
        # Get active folders
        active_folders = [folder for folder, var in self.folder_vars.items() if var.get()]
        
        # Update active sources from checkboxes
        for folder, var in self.folder_vars.items():
            self.active_sources[folder] = var.get()
        
        # Create organized folders if needed
        if not self.create_folders_if_needed(active_folders):
            return
        
        # For backward compatibility, use the first active folder as the primary
        primary_folder = active_folders[0] if active_folders else ""
        
        # Collect settings
        self.result = {
            'folder': primary_folder,
            'source_folders': active_folders,
            'active_sources': self.active_sources.copy(),
            'destination_settings': {
                'script_dir': self.dest_script_var.get(),
                'source_dirs': self.dest_source_var.get()
            },
            'num_rows': self.rows_var.get(),
            'random_order': self.random_var.get(),
            'copy_instead_of_move': self.copy_var.get(),
            'handle_tag_files': self.handle_tags_var.get(),
            'hide_already_sorted': self.hide_sorted_var.get(),
            'include_subfolders': self.include_subfolders_var.get()
        }
        
        # Update config manager if available
        if self.config_manager:
            # Update basic settings
            self.config_manager.update_basic_settings(
                last_folder=primary_folder,
                num_rows=self.rows_var.get(),
                random_order=self.random_var.get(),
                copy_instead_of_move=self.copy_var.get(),
                include_subfolders=self.include_subfolders_var.get()
            )
            
            # Update source folders and active sources
            self.config_manager.config['source_folders'] = self.source_folders
            self.config_manager.config['active_sources'] = self.active_sources
            self.config_manager.config['destination_settings'] = {
                'script_dir': self.dest_script_var.get(),
                'source_dirs': self.dest_source_var.get()
            }
            
            # Update UI preferences for tag handling
            if 'ui_preferences' not in self.config_manager.config:
                self.config_manager.config['ui_preferences'] = {}
            self.config_manager.config['ui_preferences']['handle_tag_files'] = self.handle_tags_var.get()
            self.config_manager.config['ui_preferences']['hide_already_sorted'] = self.hide_sorted_var.get()
            
            self.config_manager.save_config()
        
        self.window.destroy()

    def open_batch_export(self):
        """Open the batch export tool dialog."""
        try:
            dialog = BatchExportDialog(self.window)
            # Dialog is modal and will block until closed
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Batch Export Tool:\n{e}")

    def open_auto_sort(self):
        """Open auto-sort functionality."""
        try:
            # Save current configuration first
            if not self.validate_and_save():
                return

            # Close setup dialog
            self.ok()

            # The main image sorter will be launched by the caller
            # This just closes the setup dialog so auto-sort can run
            messagebox.showinfo(
                "Auto-Sort",
                "Setup saved. Launch the image sorter and press Ctrl+A to start auto-sorting."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare auto-sort:\n{e}")

    def open_term_manager(self):
        """Open the term manager dialog."""
        try:
            from term_manager import TermManagerDialog
            TermManagerDialog(self.window, self.config_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Term Manager:\n{e}")

    def rebuild_tag_database(self):
        """Rebuild the tag database from images."""
        try:
            from rebuild_tag_database import TagDatabaseRebuilder
            from pathlib import Path
            import threading

            # Ask for confirmation
            result = messagebox.askyesno(
                "Rebuild Tag Database",
                "This will scan all images and rebuild the tag database.\n\n"
                "This may take several minutes for large collections.\n\n"
                "Continue?"
            )

            if not result:
                return

            # Create progress window
            progress_window = tk.Toplevel(self.window)
            progress_window.title("Rebuilding Tag Database")
            progress_window.geometry("500x180")
            progress_window.resizable(False, False)
            progress_window.configure(bg=ModernStyle.BG_DARK)
            ModernStyle.apply(progress_window)

            frame = ttk.Frame(progress_window, padding="20")
            frame.pack(fill="both", expand=True)

            title_label = ttk.Label(frame, text="Rebuilding tag database...", style="Heading.TLabel")
            title_label.pack(pady=(0, 10))

            progress_bar = ttk.Progressbar(frame, length=450, mode="determinate")
            progress_bar.pack(pady=(0, 10))

            status_label = ttk.Label(frame, text="Starting...")
            status_label.pack(pady=(0, 5))

            detail_label = ttk.Label(frame, text="", style="Dim.TLabel")
            detail_label.pack()

            # Track rebuild state
            rebuild_state = {'done': False, 'success': False, 'stats': None}

            def update_progress(current, total, message):
                if total > 0:
                    pct = (current / total) * 100
                    progress_bar["value"] = pct
                    status_label.config(text=f"{current}/{total} images processed")
                    detail_label.config(text=message[:60])

            def run_rebuild():
                try:
                    rebuilder = TagDatabaseRebuilder('tag_database.db')

                    # Determine folder to scan
                    master_images = Path('master_images')
                    auto_sorted = Path('auto_sorted')

                    if master_images.exists():
                        folder = str(master_images)
                    elif auto_sorted.exists():
                        folder = str(auto_sorted)
                    else:
                        rebuild_state['done'] = True
                        rebuild_state['success'] = False
                        rebuild_state['error'] = "No images folder found"
                        return

                    # Run rebuild
                    stats = rebuilder.rebuild_from_folder(
                        folder,
                        recursive=True,
                        clear_existing=True,
                        progress_callback=update_progress
                    )

                    rebuild_state['done'] = True
                    rebuild_state['success'] = stats.get('success', False)
                    rebuild_state['stats'] = stats

                except Exception as e:
                    rebuild_state['done'] = True
                    rebuild_state['success'] = False
                    rebuild_state['error'] = str(e)

            # Start rebuild
            threading.Thread(target=run_rebuild, daemon=True).start()

            # Poll for completion
            def check_completion():
                if not rebuild_state['done']:
                    progress_window.after(500, check_completion)
                    return

                # Complete
                if rebuild_state['success']:
                    stats = rebuild_state['stats']
                    title_label.config(text="Rebuild Complete!", foreground="green")
                    status_label.config(text=f"Processed {stats['images_processed']} images")
                    detail_label.config(
                        text=f"Found {stats['tags_discovered']} unique tags in {stats['time_taken']:.1f}s"
                    )
                    progress_bar["value"] = 100

                    # Auto-close after 3 seconds
                    progress_window.after(3000, progress_window.destroy)
                else:
                    title_label.config(text="Rebuild Failed", foreground="red")
                    error = rebuild_state.get('error', 'Unknown error')
                    detail_label.config(text=error[:80])

                    # Close after 5 seconds
                    progress_window.after(5000, progress_window.destroy)

            check_completion()

        except ImportError:
            messagebox.showerror(
                "Error",
                "Tag database tools not available.\n\n"
                "Make sure rebuild_tag_database.py is present."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rebuild tag database:\n{e}")

    def cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.window.destroy()

    def exit_app(self):
        """Exit the entire application."""
        import sys
        self.window.destroy()
        if self.parent:
            self.parent.destroy()
        sys.exit(0)
    
    def show(self):
        """Show the dialog and return the result."""
        self.window.wait_window()
        return self.result

def show_setup_dialog(parent=None, config_manager=None):
    """Convenience function to show the setup dialog."""
    dialog = SetupDialog(parent, config_manager)
    return dialog.show()