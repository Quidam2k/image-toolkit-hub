"""
Image Toolkit Hub - Main Launcher

A modern hub interface for the image management toolkit.
Provides quick access to all tools without requiring the grid sorter.

Author: Claude Code Implementation
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
from pathlib import Path


class ModernStyle:
    """Modern color scheme and styling."""

    # Colors - Dark theme with purple accent
    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    BG_HOVER = "#1f3460"
    ACCENT = "#7c3aed"
    ACCENT_HOVER = "#8b5cf6"
    TEXT = "#e2e8f0"
    TEXT_DIM = "#94a3b8"
    TEXT_MUTED = "#64748b"
    SUCCESS = "#10b981"
    BORDER = "#334155"

    # Fonts
    FONT_TITLE = ("Segoe UI", 24, "bold")
    FONT_HEADING = ("Segoe UI", 14, "bold")
    FONT_BODY = ("Segoe UI", 11)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_ICON = ("Segoe UI", 20)

    @classmethod
    def apply(cls, root):
        """Apply modern styling to ttk widgets."""
        style = ttk.Style(root)

        # Use clam as base - it's the most customizable
        style.theme_use('clam')

        # Configure colors
        style.configure(".",
            background=cls.BG_DARK,
            foreground=cls.TEXT,
            font=cls.FONT_BODY
        )

        # Frame styles
        style.configure("Card.TFrame", background=cls.BG_CARD)
        style.configure("Dark.TFrame", background=cls.BG_DARK)

        # Label styles
        style.configure("Title.TLabel",
            background=cls.BG_DARK,
            foreground=cls.TEXT,
            font=cls.FONT_TITLE
        )
        style.configure("Heading.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            font=cls.FONT_HEADING
        )
        style.configure("Body.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT_DIM,
            font=cls.FONT_BODY
        )
        style.configure("Muted.TLabel",
            background=cls.BG_DARK,
            foreground=cls.TEXT_MUTED,
            font=cls.FONT_SMALL
        )
        style.configure("Icon.TLabel",
            background=cls.BG_CARD,
            foreground=cls.ACCENT,
            font=cls.FONT_ICON
        )

        # Button styles
        style.configure("Accent.TButton",
            background=cls.ACCENT,
            foreground=cls.TEXT,
            font=cls.FONT_BODY,
            padding=(20, 10)
        )
        style.map("Accent.TButton",
            background=[("active", cls.ACCENT_HOVER)]
        )

        # Checkbutton - with visible checkmark
        style.configure("TCheckbutton",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            indicatorbackground=cls.BG_DARK,
            indicatorforeground=cls.SUCCESS,  # Green checkmark
            indicatorcolor=cls.BG_DARK
        )
        style.map("TCheckbutton",
            indicatorcolor=[
                ("selected", cls.SUCCESS),  # Green when checked
                ("!selected", cls.BG_DARK)  # Dark when unchecked
            ],
            background=[
                ("active", cls.BG_HOVER)
            ]
        )

        # LabelFrame
        style.configure("Card.TLabelframe",
            background=cls.BG_CARD,
            foreground=cls.TEXT
        )
        style.configure("Card.TLabelframe.Label",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            font=cls.FONT_HEADING
        )


class ToolCard(tk.Frame):
    """A clickable card representing a tool."""

    def __init__(self, parent, icon, title, description, command, **kwargs):
        super().__init__(parent, **kwargs)

        self.command = command
        self.configure(
            bg=ModernStyle.BG_CARD,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=ModernStyle.BORDER,
            highlightcolor=ModernStyle.ACCENT
        )

        # Padding frame
        inner = tk.Frame(self, bg=ModernStyle.BG_CARD, padx=20, pady=15)
        inner.pack(fill="both", expand=True)

        # Icon
        icon_label = tk.Label(inner,
            text=icon,
            font=("Segoe UI", 28),
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD
        )
        icon_label.pack(anchor="w")

        # Title
        title_label = tk.Label(inner,
            text=title,
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        title_label.pack(fill="x", pady=(8, 4))

        # Description
        desc_label = tk.Label(inner,
            text=description,
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            anchor="w",
            wraplength=220,
            justify="left"
        )
        desc_label.pack(fill="x")

        # Bind click events to all children
        for widget in [self, inner, icon_label, title_label, desc_label]:
            widget.bind("<Button-1>", lambda e: self.on_click())
            widget.bind("<Enter>", lambda e: self.on_enter())
            widget.bind("<Leave>", lambda e: self.on_leave())

    def on_click(self):
        if self.command:
            self.command()

    def on_enter(self):
        self.configure(bg=ModernStyle.BG_HOVER, highlightbackground=ModernStyle.ACCENT)
        for widget in self.winfo_children():
            self._update_bg(widget, ModernStyle.BG_HOVER)

    def on_leave(self):
        self.configure(bg=ModernStyle.BG_CARD, highlightbackground=ModernStyle.BORDER)
        for widget in self.winfo_children():
            self._update_bg(widget, ModernStyle.BG_CARD)

    def _update_bg(self, widget, color):
        try:
            widget.configure(bg=color)
            for child in widget.winfo_children():
                self._update_bg(child, color)
        except tk.TclError:
            pass


class SourceFolderPanel(tk.Frame):
    """Panel for managing source folders."""

    def __init__(self, parent, hub, **kwargs):
        super().__init__(parent, bg=ModernStyle.BG_CARD, **kwargs)
        self.hub = hub

        # Header
        header = tk.Frame(self, bg=ModernStyle.BG_CARD)
        header.pack(fill="x", padx=15, pady=(15, 10))

        tk.Label(header,
            text="Source Folders",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(side="left")

        # Add button
        add_btn = tk.Label(header,
            text="+ Add",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        add_btn.pack(side="right")
        add_btn.bind("<Button-1>", lambda e: self.add_folder())
        add_btn.bind("<Enter>", lambda e: add_btn.configure(fg=ModernStyle.ACCENT_HOVER))
        add_btn.bind("<Leave>", lambda e: add_btn.configure(fg=ModernStyle.ACCENT))

        # Folder list
        self.list_frame = tk.Frame(self, bg=ModernStyle.BG_CARD)
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.refresh_list()

    def refresh_list(self):
        """Refresh the folder list display."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        folders = self.hub.source_folders
        active = self.hub.active_sources

        if not folders:
            tk.Label(self.list_frame,
                text="No folders configured.\nClick '+ Add' to add source folders.",
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.TEXT_MUTED,
                bg=ModernStyle.BG_CARD,
                justify="center"
            ).pack(pady=20)
            return

        for folder in folders:
            self._create_folder_row(folder, active.get(folder, True))

    def _create_folder_row(self, folder, is_active):
        """Create a row for a folder."""
        row = tk.Frame(self.list_frame, bg=ModernStyle.BG_CARD)
        row.pack(fill="x", pady=2)

        # Checkbox
        var = tk.BooleanVar(value=is_active)
        self.hub.folder_vars[folder] = var

        cb = tk.Checkbutton(row,
            variable=var,
            bg=ModernStyle.BG_CARD,
            activebackground=ModernStyle.BG_CARD,
            fg=ModernStyle.TEXT,
            selectcolor=ModernStyle.SUCCESS,  # Green background when checked - black checkmark visible
            activeforeground=ModernStyle.TEXT,
            highlightthickness=0,
            command=lambda: self.hub.toggle_folder(folder, var.get())
        )
        cb.pack(side="left")

        # Folder name (shortened)
        display_name = self._shorten_path(folder)
        label = tk.Label(row,
            text=display_name,
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT if is_active else ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        label.pack(side="left", fill="x", expand=True)

        # Tooltip for full path
        self._create_tooltip(label, folder)

        # Remove button
        remove_btn = tk.Label(row,
            text="×",
            font=("Segoe UI", 14),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        remove_btn.pack(side="right", padx=(5, 0))
        remove_btn.bind("<Button-1>", lambda e, f=folder: self.remove_folder(f))
        remove_btn.bind("<Enter>", lambda e: remove_btn.configure(fg="#ef4444"))
        remove_btn.bind("<Leave>", lambda e: remove_btn.configure(fg=ModernStyle.TEXT_MUTED))

    def _shorten_path(self, path, max_len=45):
        """Shorten a path for display."""
        if len(path) <= max_len:
            return path

        parts = Path(path).parts
        if len(parts) <= 2:
            return "..." + path[-(max_len-3):]

        # Show drive + ... + last 2 parts
        return f"{parts[0]}\\...\\{parts[-2]}\\{parts[-1]}"

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        tooltip = None

        def show(event):
            nonlocal tooltip
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            label = tk.Label(tooltip,
                text=text,
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.TEXT,
                bg=ModernStyle.BG_DARK,
                padx=8, pady=4,
                relief="solid",
                borderwidth=1
            )
            label.pack()

        def hide(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def add_folder(self):
        """Add a new source folder."""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            if folder not in self.hub.source_folders:
                self.hub.source_folders.append(folder)
                self.hub.active_sources[folder] = True
                self.hub.save_config()
                self.refresh_list()
            else:
                messagebox.showinfo("Info", "Folder already in list.")

    def remove_folder(self, folder):
        """Remove a source folder."""
        if folder in self.hub.source_folders:
            self.hub.source_folders.remove(folder)
            if folder in self.hub.active_sources:
                del self.hub.active_sources[folder]
            if folder in self.hub.folder_vars:
                del self.hub.folder_vars[folder]
            self.hub.save_config()
            self.refresh_list()


class ImageToolkitHub(tk.Tk):
    """Main hub window for the image toolkit."""

    CONFIG_FILE = "hub_config.json"

    def __init__(self):
        super().__init__()

        self.title("Image Toolkit")
        self.geometry("1100x750")
        self.minsize(900, 650)
        self.configure(bg=ModernStyle.BG_DARK)

        # Load configuration
        self.source_folders = []
        self.active_sources = {}
        self.folder_vars = {}
        self.load_config()

        # Apply styling
        ModernStyle.apply(self)

        # Build UI
        self.setup_ui()

        # Center window
        self.center_window()

        # Check for interrupted operations after a short delay (let UI settle)
        self.after(500, self.check_interrupted_operations)

    def center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def load_config(self):
        """Load hub configuration."""
        # Try hub config first
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.source_folders = config.get('source_folders', [])
                    self.active_sources = config.get('active_sources', {})
                    return
            except:
                pass

        # Fall back to legacy config
        if os.path.exists('imagesorter_config.json'):
            try:
                with open('imagesorter_config.json', 'r') as f:
                    config = json.load(f)
                    self.source_folders = config.get('source_folders', [])
                    self.active_sources = config.get('active_sources', {})
            except:
                pass

    def save_config(self):
        """Save hub configuration."""
        config = {
            'source_folders': self.source_folders,
            'active_sources': self.active_sources
        }
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def toggle_folder(self, folder, active):
        """Toggle a folder's active state."""
        self.active_sources[folder] = active
        self.save_config()

    def get_active_folders(self):
        """Get list of currently active source folders."""
        return [f for f in self.source_folders if self.active_sources.get(f, True)]

    def setup_ui(self):
        """Build the hub interface."""
        # Main container with padding
        main = tk.Frame(self, bg=ModernStyle.BG_DARK, padx=30, pady=25)
        main.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(main, bg=ModernStyle.BG_DARK)
        header.pack(fill="x", pady=(0, 25))

        tk.Label(header,
            text="Image Toolkit",
            font=ModernStyle.FONT_TITLE,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_DARK
        ).pack(side="left")

        tk.Label(header,
            text="v2.0",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(side="left", padx=(10, 0), pady=(12, 0))

        # Content area - two columns
        content = tk.Frame(main, bg=ModernStyle.BG_DARK)
        content.pack(fill="both", expand=True)

        # Left column - Tools
        left = tk.Frame(content, bg=ModernStyle.BG_DARK)
        left.pack(side="left", fill="both", expand=True)

        # Section: Sorting Tools
        tk.Label(left,
            text="SORTING TOOLS",
            font=("Segoe UI", 10, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 10))

        # Tool cards grid
        sort_grid = tk.Frame(left, bg=ModernStyle.BG_DARK)
        sort_grid.pack(fill="x", pady=(0, 25))

        # Row 1
        ToolCard(sort_grid,
            icon="🖼️",
            title="Manual Grid Sorter",
            description="Visual grid for manual sorting into categories with keyboard shortcuts",
            command=self.launch_grid_sorter
        ).grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")

        ToolCard(sort_grid,
            icon="🏷️",
            title="Auto-Sort by Tags",
            description="Automatically sort images based on metadata and prompt content",
            command=self.launch_auto_sort
        ).grid(row=0, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")

        # Row 2
        ToolCard(sort_grid,
            icon="👁️",
            title="Visual Classification",
            description="Sort by shot type, person count, or rating using AI vision",
            command=self.launch_visual_sort
        ).grid(row=1, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")

        ToolCard(sort_grid,
            icon="👕",
            title="T-Shirt Ready Finder",
            description="Find images with simple backgrounds for print-on-demand",
            command=self.launch_tshirt_finder
        ).grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")

        sort_grid.columnconfigure(0, weight=1)
        sort_grid.columnconfigure(1, weight=1)

        # Section: Data Tools
        tk.Label(left,
            text="DATA & EXPORT",
            font=("Segoe UI", 10, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 10))

        data_grid = tk.Frame(left, bg=ModernStyle.BG_DARK)
        data_grid.pack(fill="x")

        ToolCard(data_grid,
            icon="📤",
            title="Batch Export",
            description="Query and export images by tags for WAN 2.2 i2v workflows",
            command=self.launch_batch_export
        ).grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        ToolCard(data_grid,
            icon="🗃️",
            title="Tag Database",
            description="Manage and rebuild the tag frequency database",
            command=self.launch_tag_database
        ).grid(row=0, column=1, padx=(0, 10), sticky="nsew")

        data_grid.columnconfigure(0, weight=1)
        data_grid.columnconfigure(1, weight=1)

        # Right column - Source folders
        right = tk.Frame(content, bg=ModernStyle.BG_DARK, width=280)
        right.pack(side="right", fill="y", padx=(25, 0))
        right.pack_propagate(False)

        # Source folders panel
        self.folder_panel = SourceFolderPanel(right, self)
        self.folder_panel.pack(fill="both", expand=True)
        self.folder_panel.configure(highlightthickness=1, highlightbackground=ModernStyle.BORDER)

        # Settings link at bottom of folders panel
        settings_frame = tk.Frame(right, bg=ModernStyle.BG_DARK)
        settings_frame.pack(fill="x", pady=(15, 0))

        settings_link = tk.Label(settings_frame,
            text="⚙️ Term Manager",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_DARK,
            cursor="hand2"
        )
        settings_link.pack(anchor="w")
        settings_link.bind("<Button-1>", lambda e: self.launch_term_manager())
        settings_link.bind("<Enter>", lambda e: settings_link.configure(fg=ModernStyle.ACCENT))
        settings_link.bind("<Leave>", lambda e: settings_link.configure(fg=ModernStyle.TEXT_DIM))

        # Footer
        footer = tk.Frame(main, bg=ModernStyle.BG_DARK)
        footer.pack(fill="x", pady=(25, 0))

        tk.Label(footer,
            text="Select a tool to get started. Source folders on the right are shared across all tools.",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(side="left")

    # Tool launchers
    def launch_grid_sorter(self):
        """Launch the manual grid sorter."""
        try:
            from config_manager import ConfigManager

            # Pass source folders to config
            config_manager = ConfigManager()

            # Update config with current source folders
            config_manager.config['source_folders'] = self.source_folders
            config_manager.config['active_sources'] = self.active_sources
            config_manager.save_config()

            # Hide hub and launch sorter as subprocess
            self.withdraw()

            import subprocess
            proc = subprocess.Popen([sys.executable, 'image_sorter_enhanced.py'])

            # Show hub again when grid closes
            def check_closed():
                if proc.poll() is not None:
                    self.deiconify()
                else:
                    self.after(500, check_closed)

            check_closed()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch grid sorter:\n{e}")
            self.deiconify()

    def launch_auto_sort(self):
        """Launch auto-sort tool."""
        try:
            active = self.get_active_folders()
            if not active:
                messagebox.showwarning("No Folders", "Please add and enable at least one source folder.")
                return

            from config_manager import ConfigManager
            from auto_sorter import AutoSorter
            from auto_sort_progress import AutoSortProgressDialog
            from auto_sort_confirm import show_auto_sort_confirm

            config_manager = ConfigManager()
            config_manager.config['source_folders'] = self.source_folders
            config_manager.config['active_sources'] = self.active_sources

            sorter = AutoSorter(config_manager)

            # Show confirmation
            terms = config_manager.get_auto_sort_terms()
            enabled_terms = [t for t in terms if t.get('enabled', True)]

            if not enabled_terms:
                messagebox.showwarning("No Terms", "No auto-sort terms configured. Open Term Manager to add some.")
                return

            result = show_auto_sort_confirm(self, config_manager, len(active), enabled_terms)

            if result:
                # Run the sort
                progress = AutoSortProgressDialog(self, "Auto-Sort by Tags")
                progress.start_sort(sorter, active)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch auto-sort:\n{e}")

    def launch_visual_sort(self):
        """Launch visual classification tool."""
        try:
            active = self.get_active_folders()
            if not active:
                messagebox.showwarning("No Folders", "Please add and enable at least one source folder.")
                return

            from config_manager import ConfigManager
            from visual_sort_dialog import show_visual_sort_dialog

            config_manager = ConfigManager()

            # Get image files
            from image_sorter_enhanced import load_images
            images = load_images(active, [], False, True)
            if images and isinstance(images[0], dict):
                images = [item['path'] for item in images]

            if not images:
                messagebox.showinfo("No Images", "No images found in the selected folders.")
                return

            show_visual_sort_dialog(self, config_manager, images)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch visual sort:\n{e}")

    def launch_tshirt_finder(self):
        """Launch T-shirt ready image finder."""
        try:
            from background_sort_dialog import show_background_sort_dialog
            from config_manager import ConfigManager

            config_manager = ConfigManager()
            config_manager.config['source_folders'] = self.source_folders
            config_manager.config['active_sources'] = self.active_sources

            show_background_sort_dialog(self, config_manager)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch T-shirt finder:\n{e}")

    def launch_batch_export(self):
        """Launch batch export tool."""
        try:
            from batch_export_dialog import BatchExportDialog
            BatchExportDialog(self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch batch export:\n{e}")

    def launch_tag_database(self):
        """Launch tag database manager."""
        try:
            # Simple dialog for now - can be expanded
            result = messagebox.askyesno(
                "Tag Database",
                "Rebuild the tag database from your image collection?\n\n"
                "This scans all images and updates tag frequency data."
            )

            if result:
                from scripts.rebuild_tag_database import TagDatabaseRebuilder
                # Would need a progress dialog here
                messagebox.showinfo("Info", "Tag database rebuild would start here.\n(Full implementation pending)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch tag database:\n{e}")

    def launch_term_manager(self):
        """Launch term manager."""
        try:
            from config_manager import ConfigManager
            from term_manager import TermManagerDialog

            config_manager = ConfigManager()
            TermManagerDialog(self, config_manager)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch term manager:\n{e}")

    def check_interrupted_operations(self):
        """Check for and offer to resume interrupted copy operations."""
        try:
            from copy_operation_tracker import check_for_interrupted_copy

            pending = check_for_interrupted_copy()
            if not pending:
                return

            # Build info message
            op_type = pending.get('operation_type', 'copy')
            remaining = pending.get('remaining_count', 0)
            copied = pending.get('copied_count', 0)
            total = pending.get('total_files', 0)
            output_folder = pending.get('output_folder', 'unknown')
            started_at = pending.get('started_at', 'unknown time')

            if op_type == 'tshirt_copy':
                title = "Resume T-Shirt Copy"
                op_desc = "T-Shirt ready image copy"
            else:
                title = "Resume Copy Operation"
                op_desc = "Copy operation"

            message = (
                f"An interrupted {op_desc} was detected.\n\n"
                f"Started: {started_at[:19] if len(started_at) > 19 else started_at}\n"
                f"Output: {output_folder}\n"
                f"Progress: {copied}/{total} files copied\n"
                f"Remaining: {remaining} files\n\n"
                f"Would you like to resume this operation?"
            )

            result = messagebox.askyesnocancel(title, message)

            if result is True:
                # Resume
                self.resume_interrupted_copy()
            elif result is False:
                # Discard
                from copy_operation_tracker import get_tracker
                get_tracker().cancel_operation()
                messagebox.showinfo("Discarded", "The interrupted operation has been discarded.")

        except ImportError:
            pass  # Tracker not available
        except Exception as e:
            print(f"Error checking for interrupted operations: {e}")

    def resume_interrupted_copy(self):
        """Resume an interrupted copy operation with progress dialog."""
        try:
            from copy_operation_tracker import get_tracker

            tracker = get_tracker()
            info = tracker.get_pending_info()
            if not info:
                messagebox.showinfo("Info", "No operation to resume.")
                return

            # Create progress window
            progress_window = tk.Toplevel(self)
            progress_window.title("Resuming Copy Operation")
            progress_window.geometry("500x180")
            progress_window.resizable(False, False)
            progress_window.configure(bg=ModernStyle.BG_DARK)
            progress_window.transient(self)
            progress_window.grab_set()

            ModernStyle.apply(progress_window)

            frame = tk.Frame(progress_window, bg=ModernStyle.BG_DARK, padx=20, pady=20)
            frame.pack(fill="both", expand=True)

            tk.Label(frame,
                text=f"Resuming: {info['remaining_count']} files remaining",
                font=ModernStyle.FONT_HEADING,
                fg=ModernStyle.TEXT,
                bg=ModernStyle.BG_DARK
            ).pack(anchor="w", pady=(0, 10))

            progress_bar = ttk.Progressbar(frame, length=450, mode="determinate")
            progress_bar.pack(fill="x", pady=(0, 10))

            status_label = tk.Label(frame,
                text="Starting...",
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.TEXT_DIM,
                bg=ModernStyle.BG_DARK
            )
            status_label.pack(anchor="w")

            cancel_requested = [False]

            def cancel():
                cancel_requested[0] = True
                cancel_btn.config(state="disabled")
                status_label.config(text="Cancelling...")

            cancel_btn = ttk.Button(frame, text="Cancel", command=cancel)
            cancel_btn.pack(pady=(10, 0))

            progress_window.update()

            import threading

            def resume_thread():
                def progress_callback(current, total, filename):
                    progress = current / total * 100
                    progress_window.after(0, lambda: update_progress(progress, current, total, filename))

                def update_progress(pct, cur, tot, name):
                    progress_bar['value'] = pct
                    status_label.config(text=f"{cur}/{tot} - {name}")

                def cancel_check():
                    return cancel_requested[0]

                result = tracker.resume_operation(
                    progress_callback=progress_callback,
                    cancel_check=cancel_check
                )

                progress_window.after(0, lambda: show_result(result))

            def show_result(result):
                progress_window.destroy()

                if result.get('error'):
                    messagebox.showerror("Error", result['error'])
                else:
                    copied = result.get('resumed_copied', 0)
                    total_copied = result.get('copied', 0)
                    failed = result.get('failed', 0)
                    output = result.get('output_folder', '')

                    msg = f"Resumed and copied {copied} additional files.\n"
                    msg += f"Total copied: {total_copied}\n"
                    if failed > 0:
                        msg += f"\n{failed} files failed."
                    msg += f"\n\nOutput: {output}"

                    messagebox.showinfo("Resume Complete", msg)

                    if messagebox.askyesno("Open Folder", "Open the output folder?"):
                        import os
                        os.startfile(output)

            threading.Thread(target=resume_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to resume operation:\n{e}")


def main():
    """Main entry point."""
    app = ImageToolkitHub()
    app.mainloop()


if __name__ == '__main__':
    main()
