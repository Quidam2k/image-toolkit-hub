"""
Image Ranker Dialog - Tkinter UI for pairwise image comparison

Provides a side-by-side image display for ranking images using
the OpenSkill algorithm. Supports keyboard shortcuts for fast
comparison workflow.

Author: Claude Code Implementation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from image_ranker import (
    ImageRanker, RankedImage,
    list_projects, create_project, rename_legacy_project, get_project_path
)
from ui_theme import Theme as ModernStyle
from tkinter import simpledialog

logger = logging.getLogger(__name__)


class ImageRankerDialog(tk.Toplevel):
    """
    Main dialog for pairwise image ranking.

    Features:
    - Side-by-side image display
    - Comprehensive stats panel
    - Keyboard shortcuts (1/Left, 2/Right, S skip, U undo)
    - Progress tracking across sessions
    """

    MAX_IMAGE_SIZE = 700  # Sized for typical canvas area in 1600x1000 window

    def __init__(self, parent, config_manager=None, initial_folder=None):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager

        # Project management - determine which project to load
        self.current_project_name = None
        self.current_project_path = None
        self._select_initial_project()

        # Initialize ranker with selected project
        self.ranker = ImageRanker(self.current_project_path)

        # Current comparison state
        self.current_pair: tuple = None
        self.left_photo = None
        self.right_photo = None

        # Preloading for instant transitions
        # Store PIL images (thread-safe), convert to PhotoImage on main thread
        self.preloaded_pair: tuple = None
        self.preloaded_left_pil = None  # PIL Image (thread-safe)
        self.preloaded_right_pil = None  # PIL Image (thread-safe)
        self.preload_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.closing = False  # Flag to stop preloading on close

        # Session tracking
        self.session_comparisons = 0
        self.current_folders: list = []

        self.setup_window()
        self.setup_ui()
        self.bind_keys()

        # Load initial folder if provided (e.g., from grid sorter Shift+R)
        if initial_folder:
            self.current_folders.append(initial_folder)
            self.scan_folder(initial_folder)

        # Load initial state
        self.update_stats()
        self.update_folder_label()

        # If we have images, show loading indicator and load first pair async
        if self.ranker.get_image_count() > 1:
            self._show_loading_indicator()
            self.after(100, self._load_first_pair_async)
        else:
            self.show_no_images()

    def _select_initial_project(self):
        """Select the initial project to load."""
        projects = list_projects()

        if not projects:
            # No projects exist - create default
            self.current_project_path = "data/rankings.db"
            self.current_project_name = "(Unsaved Project)"
        elif len(projects) == 1:
            # Only one project - use it
            self.current_project_path = projects[0]['path']
            self.current_project_name = projects[0]['name']
        else:
            # Multiple projects - use the first one (user can switch via dropdown)
            # Prefer non-legacy projects
            non_legacy = [p for p in projects if not p.get('is_legacy', False)]
            if non_legacy:
                self.current_project_path = non_legacy[0]['path']
                self.current_project_name = non_legacy[0]['name']
            else:
                self.current_project_path = projects[0]['path']
                self.current_project_name = projects[0]['name']

    def setup_window(self):
        """Configure the dialog window."""
        self.title("Image Ranker")
        self.geometry("1600x1000")
        self.minsize(1300, 850)
        self.configure(bg=ModernStyle.BG_DARK)

        ModernStyle.apply(self)

        # Make modal
        self.transient(self.parent)
        self.grab_set()

        # Center on screen (more reliable than centering on parent)
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - 1600) // 2
        y = (screen_h - 1000) // 2
        self.geometry(f"1600x1000+{max(0, x)}+{max(0, y)}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Build the UI components."""
        # Main horizontal layout
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left side: comparison area (expandable)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True)

        self.create_toolbar(left_frame)
        self.create_comparison_area(left_frame)
        self.create_controls(left_frame)

        # Right side: stats panel (fixed width)
        self.create_stats_panel(main_frame)

    def create_toolbar(self, parent):
        """Create the top toolbar."""
        toolbar = ttk.Frame(parent, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))

        # Project selection section
        project_frame = ttk.Frame(toolbar, style="Card.TFrame")
        project_frame.pack(side="left", padx=(10, 15), pady=10)

        ttk.Label(
            project_frame,
            text="Project:",
            style="TLabel"
        ).pack(side="left", padx=(0, 5))

        self.project_var = tk.StringVar(value=self.current_project_name)
        self.project_dropdown = ttk.Combobox(
            project_frame,
            textvariable=self.project_var,
            state="readonly",
            width=20
        )
        self.project_dropdown.pack(side="left", padx=(0, 5))
        self.project_dropdown.bind("<<ComboboxSelected>>", self.on_project_selected)
        self._refresh_project_list()

        ttk.Button(
            project_frame,
            text="New",
            command=self.create_new_project,
            style="Secondary.TButton",
            width=5
        ).pack(side="left", padx=2)

        ttk.Button(
            project_frame,
            text="Save As",
            command=self.save_project_as,
            style="Secondary.TButton",
            width=7
        ).pack(side="left", padx=2)

        # Separator
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10, pady=5)

        ttk.Button(
            toolbar,
            text="Add Folder",
            command=self.add_folder,
            style="Secondary.TButton"
        ).pack(side="left", padx=5, pady=10)

        ttk.Button(
            toolbar,
            text="Rescan (R)",
            command=self.rescan_folders,
            style="Secondary.TButton"
        ).pack(side="left", padx=5, pady=10)

        ttk.Button(
            toolbar,
            text="Clear All",
            command=self.clear_all_data,
            style="Secondary.TButton"
        ).pack(side="left", padx=5, pady=10)

        self.folder_label = ttk.Label(
            toolbar,
            text="No folders loaded",
            style="Dim.TLabel",
            cursor="hand2"
        )
        self.folder_label.pack(side="left", padx=15, pady=10)
        self.folder_label.bind("<Button-1>", self.show_folder_list)

        ttk.Button(
            toolbar,
            text="View Rankings",
            command=self.show_rankings,
            style="TButton"
        ).pack(side="right", padx=10, pady=10)

    def create_comparison_area(self, parent):
        """Create the main image comparison area."""
        compare_frame = ttk.Frame(parent)
        compare_frame.pack(fill="both", expand=True)

        # Left image panel
        self.left_panel = self.create_image_panel(compare_frame, "left")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # VS divider
        vs_frame = ttk.Frame(compare_frame)
        vs_frame.pack(side="left", fill="y", padx=5)

        vs_label = ttk.Label(
            vs_frame,
            text="VS",
            font=("Segoe UI", 20, "bold"),
            foreground=ModernStyle.ACCENT
        )
        vs_label.pack(expand=True)

        # Right image panel
        self.right_panel = self.create_image_panel(compare_frame, "right")
        self.right_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

    def create_image_panel(self, parent, side: str) -> ttk.Frame:
        """Create an image display panel."""
        panel = ttk.Frame(parent, style="Card.TFrame")

        # Image canvas
        canvas = tk.Canvas(
            panel,
            bg=ModernStyle.BG_CARD,
            highlightthickness=0,
            cursor="hand2"
        )
        canvas.pack(fill="both", expand=True, padx=10, pady=10)

        if side == "left":
            self.left_canvas = canvas
            canvas.bind("<Button-1>", lambda e: self.select_winner("left"))
        else:
            self.right_canvas = canvas
            canvas.bind("<Button-1>", lambda e: self.select_winner("right"))

        # Stats below image
        stats_frame = ttk.Frame(panel, style="Card.TFrame")
        stats_frame.pack(fill="x", padx=10, pady=(0, 10))

        stats_label = ttk.Label(
            stats_frame,
            text="",
            style="Stats.TLabel"
        )
        stats_label.pack()

        if side == "left":
            self.left_stats = stats_label
        else:
            self.right_stats = stats_label

        name_label = ttk.Label(
            stats_frame,
            text="",
            style="Dim.TLabel",
            font=ModernStyle.FONT_SMALL,
            wraplength=400
        )
        name_label.pack()

        if side == "left":
            self.left_name = name_label
        else:
            self.right_name = name_label

        return panel

    def create_controls(self, parent):
        """Create the control buttons."""
        controls = ttk.Frame(parent, style="Card.TFrame")
        controls.pack(fill="x", pady=(10, 0))

        button_frame = ttk.Frame(controls, style="Card.TFrame")
        button_frame.pack(expand=True)

        ttk.Button(
            button_frame,
            text="Left Wins (1 / \u2190)",
            command=lambda: self.select_winner("left"),
            style="Winner.TButton",
            width=18
        ).pack(side="left", padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Skip (S)",
            command=self.skip_pair,
            style="Secondary.TButton",
            width=12
        ).pack(side="left", padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Undo (U)",
            command=self.undo_last,
            style="Secondary.TButton",
            width=12
        ).pack(side="left", padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Right Wins (2 / \u2192)",
            command=lambda: self.select_winner("right"),
            style="Winner.TButton",
            width=18
        ).pack(side="left", padx=10, pady=10)

        # Keyboard hints
        hints = ttk.Label(
            controls,
            text="Keys: 1/\u2190 Left | 2/\u2192 Right | S Skip | U Undo | R Rescan | Esc Close",
            style="Muted.TLabel"
        )
        hints.pack(pady=(0, 10))

    def create_stats_panel(self, parent):
        """Create the comprehensive stats panel."""
        stats_panel = ttk.Frame(parent, style="Card.TFrame", width=320)
        stats_panel.pack(side="right", fill="y", padx=(10, 0))
        stats_panel.pack_propagate(False)  # Fixed width

        # Title
        ttk.Label(
            stats_panel,
            text="Ranking Statistics",
            style="Title.TLabel"
        ).pack(pady=(15, 10), padx=15)

        # Session stats
        session_frame = ttk.LabelFrame(stats_panel, text="This Session", padding=10)
        session_frame.pack(fill="x", padx=10, pady=5)

        self.session_count_label = ttk.Label(
            session_frame,
            text="0",
            style="StatsLarge.TLabel"
        )
        self.session_count_label.pack()
        ttk.Label(session_frame, text="comparisons", style="Stats.TLabel").pack()

        # Overall progress
        progress_frame = ttk.LabelFrame(stats_panel, text="Overall Progress", padding=10)
        progress_frame.pack(fill="x", padx=10, pady=5)

        # Total images
        row = ttk.Frame(progress_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Total Images:", style="Stats.TLabel").pack(side="left")
        self.total_images_label = ttk.Label(row, text="0", style="Stats.TLabel")
        self.total_images_label.pack(side="right")

        # Total comparisons
        row = ttk.Frame(progress_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Comparisons:", style="Stats.TLabel").pack(side="left")
        self.total_comparisons_label = ttk.Label(row, text="0", style="Stats.TLabel")
        self.total_comparisons_label.pack(side="right")

        # Avg per image
        row = ttk.Frame(progress_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Avg per Image:", style="Stats.TLabel").pack(side="left")
        self.avg_per_image_label = ttk.Label(row, text="0", style="Stats.TLabel")
        self.avg_per_image_label.pack(side="right")

        # Coverage section
        coverage_frame = ttk.LabelFrame(stats_panel, text="Image Coverage", padding=10)
        coverage_frame.pack(fill="x", padx=10, pady=5)

        # Never compared
        row = ttk.Frame(coverage_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Never compared:", style="Stats.TLabel").pack(side="left")
        self.zero_comp_label = ttk.Label(row, text="0", style="Warning.TLabel")
        self.zero_comp_label.pack(side="right")

        # 1-3 comparisons
        row = ttk.Frame(coverage_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="1-3 comparisons:", style="Stats.TLabel").pack(side="left")
        self.low_comp_label = ttk.Label(row, text="0", style="Stats.TLabel")
        self.low_comp_label.pack(side="right")

        # 4-10 comparisons
        row = ttk.Frame(coverage_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="4-10 comparisons:", style="Stats.TLabel").pack(side="left")
        self.mid_comp_label = ttk.Label(row, text="0", style="Stats.TLabel")
        self.mid_comp_label.pack(side="right")

        # 10+ comparisons
        row = ttk.Frame(coverage_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="10+ comparisons:", style="Stats.TLabel").pack(side="left")
        self.high_comp_label = ttk.Label(row, text="0", style="Success.TLabel")
        self.high_comp_label.pack(side="right")

        # Confidence section
        conf_frame = ttk.LabelFrame(stats_panel, text="Ranking Confidence", padding=10)
        conf_frame.pack(fill="x", padx=10, pady=5)

        # Basic ranking progress
        ttk.Label(conf_frame, text="Basic Ranking (0.5x):", style="Stats.TLabel").pack(anchor="w")
        self.basic_progress = ttk.Progressbar(
            conf_frame, length=260, mode='determinate',
            style="Green.Horizontal.TProgressbar"
        )
        self.basic_progress.pack(fill="x", pady=(2, 5))
        self.basic_label = ttk.Label(conf_frame, text="0 more needed", style="Dim.TLabel")
        self.basic_label.pack(anchor="e")

        # Confident ranking progress
        ttk.Label(conf_frame, text="Confident Ranking (2x):", style="Stats.TLabel").pack(anchor="w", pady=(5, 0))
        self.confident_progress = ttk.Progressbar(
            conf_frame, length=260, mode='determinate',
            style="TProgressbar"
        )
        self.confident_progress.pack(fill="x", pady=(2, 5))
        self.confident_label = ttk.Label(conf_frame, text="0 more needed", style="Dim.TLabel")
        self.confident_label.pack(anchor="e")

        # Stability
        row = ttk.Frame(conf_frame, style="Card.TFrame")
        row.pack(fill="x", pady=(10, 2))
        ttk.Label(row, text="Stability:", style="Stats.TLabel").pack(side="left")
        self.stability_label = ttk.Label(row, text="0%", style="StatsLarge.TLabel")
        self.stability_label.pack(side="right")

        # Top score section
        score_frame = ttk.LabelFrame(stats_panel, text="Current Rankings", padding=10)
        score_frame.pack(fill="x", padx=10, pady=5)

        row = ttk.Frame(score_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Top Score:", style="Stats.TLabel").pack(side="left")
        self.top_score_label = ttk.Label(row, text="-", style="Success.TLabel")
        self.top_score_label.pack(side="right")

        row = ttk.Frame(score_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Score Range:", style="Stats.TLabel").pack(side="left")
        self.score_range_label = ttk.Label(row, text="-", style="Stats.TLabel")
        self.score_range_label.pack(side="right")

        row = ttk.Frame(score_frame, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Avg Uncertainty:", style="Stats.TLabel").pack(side="left")
        self.avg_sigma_label = ttk.Label(row, text="-", style="Stats.TLabel")
        self.avg_sigma_label.pack(side="right")

    def bind_keys(self):
        """Bind keyboard shortcuts."""
        self.bind("<Key-1>", lambda e: self.select_winner("left"))
        self.bind("<Left>", lambda e: self.select_winner("left"))
        self.bind("<Key-2>", lambda e: self.select_winner("right"))
        self.bind("<Right>", lambda e: self.select_winner("right"))
        self.bind("<Key-s>", lambda e: self.skip_pair())
        self.bind("<Key-S>", lambda e: self.skip_pair())
        self.bind("<Key-u>", lambda e: self.undo_last())
        self.bind("<Key-U>", lambda e: self.undo_last())
        self.bind("<Key-r>", lambda e: self.rescan_folders())
        self.bind("<Key-R>", lambda e: self.rescan_folders())
        self.bind("<Escape>", lambda e: self.on_close())
        self.focus_set()

    def add_folder(self):
        """Add a folder to rank."""
        folder = filedialog.askdirectory(
            title="Select folder containing images to rank",
            parent=self
        )

        if folder:
            self.current_folders.append(folder)
            self.scan_folder(folder)

    def scan_folder(self, folder: str):
        """Scan a folder for images."""
        try:
            result = self.ranker.scan_folder(folder, recursive=True)

            msg = f"Added {result['added']} new images"
            if result['existing'] > 0:
                msg += f" ({result['existing']} already in database)"

            self.update_folder_label()
            self.update_stats()

            if result['added'] > 0:
                messagebox.showinfo("Folder Scanned", msg, parent=self)

            if self.ranker.get_image_count() > 1 and self.current_pair is None:
                self.next_pair()

        except Exception as e:
            messagebox.showerror("Scan Error", str(e), parent=self)
            logger.exception("Error scanning folder")

    def rescan_folders(self):
        """Rescan all current folders."""
        if not self.current_folders:
            self.current_folders = self.ranker.get_folders()

        if not self.current_folders:
            messagebox.showinfo(
                "No Folders",
                "No folders to rescan. Add a folder first.",
                parent=self
            )
            return

        total_added = 0
        for folder in self.current_folders:
            try:
                result = self.ranker.scan_folder(folder, recursive=True)
                total_added += result['added']
            except Exception as e:
                logger.warning(f"Error rescanning {folder}: {e}")

        removed = self.ranker.remove_missing_images()

        self.update_stats()
        self.update_folder_label()

        if total_added > 0 or removed > 0:
            msg = f"Added {total_added} new images"
            if removed > 0:
                msg += f", removed {removed} missing"
            messagebox.showinfo("Rescan Complete", msg, parent=self)

    def update_folder_label(self):
        """Update the folder indicator."""
        if not self.current_folders:
            folders = self.ranker.get_folders()
            if folders:
                self.current_folders = folders

        image_count = self.ranker.get_image_count()

        if self.current_folders:
            if len(self.current_folders) == 1:
                folder_name = Path(self.current_folders[0]).name
                text = f"Folder: {folder_name} ({image_count} images)"
            else:
                text = f"{len(self.current_folders)} folders ({image_count} images) - click for list"
        else:
            if image_count > 0:
                text = f"{image_count} images from unknown folders - click for list"
            else:
                text = "No folders loaded"

        self.folder_label.config(text=text)

    def show_folder_list(self, event=None):
        """Show a popup with the list of all folders."""
        folders = self.ranker.get_folders()

        if not folders:
            messagebox.showinfo("Folders", "No folders loaded.", parent=self)
            return

        # Create a dialog showing all folders
        dialog = tk.Toplevel(self)
        dialog.title("Folders in Ranking Set")
        dialog.geometry("600x400")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 600) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(
            dialog,
            text=f"Folders containing images ({len(folders)} total):",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=(15, 10), padx=15, anchor="w")

        # Listbox with scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode="extended"
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        for folder in folders:
            listbox.insert("end", folder)

        ttk.Label(
            dialog,
            text="Use 'Clear All' to start fresh with a different folder.",
            style="Dim.TLabel"
        ).pack(pady=(0, 10))

        ttk.Button(
            dialog,
            text="Close",
            command=dialog.destroy
        ).pack(pady=(0, 15))

    def clear_all_data(self):
        """Clear all images and rankings to start fresh."""
        image_count = self.ranker.get_image_count()
        comparison_count = self.ranker.get_comparison_count()

        if image_count == 0:
            messagebox.showinfo("Clear All", "Database is already empty.", parent=self)
            return

        msg = f"This will remove:\n\n"
        msg += f"  - {image_count} images\n"
        msg += f"  - {comparison_count} comparisons/rankings\n\n"
        msg += "Are you sure you want to start fresh?"

        if messagebox.askyesno("Clear All Data", msg, parent=self):
            self.ranker.clear_database()
            self.current_folders.clear()
            self.current_pair = None
            self.session_comparisons = 0

            # Clear preloaded images
            with self.preload_lock:
                self.preloaded_pair = None
                self.preloaded_left_pil = None
                self.preloaded_right_pil = None

            # Clear displayed images
            self.left_canvas.delete("all")
            self.right_canvas.delete("all")
            self.left_photo = None
            self.right_photo = None
            self.left_name.config(text="")
            self.right_name.config(text="")
            self.left_stats.config(text="")
            self.right_stats.config(text="")

            self.update_folder_label()
            self.update_stats()
            self.show_no_images()

            messagebox.showinfo("Cleared", "Database cleared. Add a folder to begin.", parent=self)

    def _refresh_project_list(self):
        """Refresh the project dropdown with current projects."""
        projects = list_projects()
        names = [p['name'] for p in projects]

        # Add display info (image count)
        display_names = []
        for p in projects:
            if p['image_count'] > 0:
                display_names.append(f"{p['name']} ({p['image_count']:,} imgs)")
            else:
                display_names.append(p['name'])

        self.project_dropdown['values'] = display_names
        self._project_name_map = {d: p['name'] for d, p in zip(display_names, projects)}

        # Set current selection
        for display_name, actual_name in self._project_name_map.items():
            if actual_name == self.current_project_name:
                self.project_var.set(display_name)
                break

    def on_project_selected(self, event=None):
        """Handle project selection from dropdown."""
        display_name = self.project_var.get()
        actual_name = self._project_name_map.get(display_name, display_name)

        if actual_name == self.current_project_name:
            return  # No change

        # Confirm switch
        if self.ranker.get_image_count() > 0:
            if not messagebox.askyesno(
                "Switch Project",
                f"Switch to project '{actual_name}'?\n\nYour current session progress is already saved.",
                parent=self
            ):
                # Reset dropdown to current project
                self._refresh_project_list()
                return

        # Switch to new project
        self._switch_to_project(actual_name)

    def _switch_to_project(self, project_name: str):
        """Switch to a different project."""
        new_path = get_project_path(project_name)

        # Clear current state
        self.current_pair = None
        self.session_comparisons = 0
        self.current_folders.clear()

        with self.preload_lock:
            self.preloaded_pair = None
            self.preloaded_left_pil = None
            self.preloaded_right_pil = None

        # Switch ranker to new database
        self.current_project_name = project_name
        self.current_project_path = new_path
        self.ranker = ImageRanker(new_path)

        # Update UI
        self._refresh_project_list()
        self.update_folder_label()
        self.update_stats()

        # Load first pair if available
        if self.ranker.get_image_count() > 1:
            self._show_loading_indicator()
            self.after(100, self._load_first_pair_async)
        else:
            self.show_no_images()

    def create_new_project(self):
        """Create a new ranking project."""
        name = simpledialog.askstring(
            "New Project",
            "Enter a name for the new project:",
            parent=self
        )

        if not name:
            return

        # Create the project
        new_path = create_project(name)
        # Extract actual name (may have been sanitized/made unique)
        actual_name = Path(new_path).stem.replace("rankings_", "")

        # Switch to it
        self._switch_to_project(actual_name)

        messagebox.showinfo(
            "Project Created",
            f"Created new project '{actual_name}'.\n\nAdd a folder to start ranking images.",
            parent=self
        )

    def save_project_as(self):
        """Save current project with a new name (for legacy or rename)."""
        if self.current_project_name == "(Unsaved Project)":
            # This is the legacy database - rename it
            name = simpledialog.askstring(
                "Save Project",
                "Give your current rankings a project name:",
                parent=self
            )

            if not name:
                return

            try:
                new_path = rename_legacy_project(name)
                actual_name = Path(new_path).stem.replace("rankings_", "")

                self.current_project_name = actual_name
                self.current_project_path = new_path
                self.ranker = ImageRanker(new_path)

                self._refresh_project_list()

                messagebox.showinfo(
                    "Project Saved",
                    f"Project saved as '{actual_name}'.",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project: {e}", parent=self)
        else:
            # Copy current project to new name
            name = simpledialog.askstring(
                "Save Project As",
                f"Save a copy of '{self.current_project_name}' as:",
                parent=self
            )

            if not name:
                return

            try:
                import shutil
                new_path = create_project(name)
                shutil.copy2(self.current_project_path, new_path)

                actual_name = Path(new_path).stem.replace("rankings_", "")
                self._refresh_project_list()

                if messagebox.askyesno(
                    "Project Copied",
                    f"Project copied to '{actual_name}'.\n\nSwitch to the new project?",
                    parent=self
                ):
                    self._switch_to_project(actual_name)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy project: {e}", parent=self)

    def update_stats(self):
        """Update all statistics displays."""
        stats = self.ranker.get_stats()

        # Session stats
        self.session_count_label.config(text=str(self.session_comparisons))

        # Overall progress
        self.total_images_label.config(text=f"{stats['total_images']:,}")
        self.total_comparisons_label.config(text=f"{stats['total_comparisons']:,}")
        self.avg_per_image_label.config(text=f"{stats['avg_comparisons_per_image']:.1f}")

        # Coverage
        self.zero_comp_label.config(text=f"{stats['images_zero_comparisons']:,}")
        self.low_comp_label.config(text=f"{stats['images_1_to_3_comparisons']:,}")
        self.mid_comp_label.config(text=f"{stats['images_4_to_10_comparisons']:,}")
        self.high_comp_label.config(text=f"{stats['images_over_10_comparisons']:,}")

        # Confidence progress bars
        self.basic_progress['value'] = stats['basic_progress_percent']
        self.confident_progress['value'] = stats['confident_progress_percent']

        if stats['comparisons_for_basic'] > 0:
            self.basic_label.config(text=f"{stats['comparisons_for_basic']:,} more needed")
        else:
            self.basic_label.config(text="Complete!")

        if stats['comparisons_for_confident'] > 0:
            self.confident_label.config(text=f"{stats['comparisons_for_confident']:,} more needed")
        else:
            self.confident_label.config(text="Complete!")

        # Stability
        self.stability_label.config(text=f"{stats['stability_percent']:.0f}%")

        # Scores
        if stats['compared_images'] > 0:
            self.top_score_label.config(text=f"{stats['top_ordinal_score']:.1f}")
            score_range = f"{stats['min_mu']:.0f} - {stats['max_mu']:.0f}"
            self.score_range_label.config(text=score_range)
            self.avg_sigma_label.config(text=f"\u03c3 = {stats['average_sigma']:.2f}")
        else:
            self.top_score_label.config(text="-")
            self.score_range_label.config(text="-")
            self.avg_sigma_label.config(text="-")

    def _format_image_path(self, img: RankedImage) -> str:
        """Format image path to show subfolder + filename."""
        path = Path(img.filepath)
        # Show parent folder + filename for context
        parent = path.parent.name
        if parent:
            return f"{parent}/{img.filename}"
        return img.filename

    def _show_loading_indicator(self):
        """Show loading text on both canvases."""
        for canvas in [self.left_canvas, self.right_canvas]:
            canvas.delete("all")
            canvas.update_idletasks()
            canvas.create_text(
                canvas.winfo_width() // 2,
                canvas.winfo_height() // 2,
                text="Loading images...",
                fill=ModernStyle.ACCENT,
                font=ModernStyle.FONT_HEADING
            )
        self.update_idletasks()

    def _load_first_pair_async(self):
        """Load the first pair in a background thread, then display."""
        def load_and_display():
            try:
                pair = self.ranker.pick_pair()
                if pair is None:
                    self.after(0, self.show_no_images)
                    return

                # Load images in background
                left_pil = self._load_pil_image(pair[0])
                right_pil = self._load_pil_image(pair[1])

                # Display on main thread
                def display():
                    self.current_pair = pair
                    self.left_photo = ImageTk.PhotoImage(left_pil)
                    self.right_photo = ImageTk.PhotoImage(right_pil)
                    self._display_preloaded()
                    # Start preloading next pair
                    self.executor.submit(self._preload_next)

                self.after(0, display)

            except Exception as e:
                logger.error(f"Error loading first pair: {e}")
                self.after(0, self.show_no_images)

        self.executor.submit(load_and_display)

    def next_pair(self):
        """Get and display the next pair of images (uses preloading for speed)."""
        # Check if we have a preloaded pair ready
        with self.preload_lock:
            if self.preloaded_pair is not None:
                # Use the preloaded pair
                self.current_pair = self.preloaded_pair
                left_pil = self.preloaded_left_pil
                right_pil = self.preloaded_right_pil

                # Clear preload state
                self.preloaded_pair = None
                self.preloaded_left_pil = None
                self.preloaded_right_pil = None

                # Convert PIL to PhotoImage on main thread (required by Tkinter)
                self.left_photo = ImageTk.PhotoImage(left_pil)
                self.right_photo = ImageTk.PhotoImage(right_pil)

                # Display instantly
                self._display_preloaded()

                # Start preloading the next pair
                self.executor.submit(self._preload_next)
                return

        # No preload available, load synchronously (first load only)
        pair = self.ranker.pick_pair()

        if pair is None:
            self.show_no_images()
            return

        self.current_pair = pair
        self._load_and_display_image(pair[0], "left")
        self._load_and_display_image(pair[1], "right")

        # Start preloading the next pair
        self.executor.submit(self._preload_next)

    def _display_preloaded(self):
        """Display the preloaded images (instant, no disk I/O)."""
        pair = self.current_pair

        # Left image
        self.left_canvas.delete("all")
        x = self.left_canvas.winfo_width() // 2
        y = self.left_canvas.winfo_height() // 2
        self.left_canvas.create_image(x, y, image=self.left_photo, anchor="center")
        self.left_stats.config(
            text=f"\u03bc={pair[0].mu:.1f}  \u03c3={pair[0].sigma:.1f}  "
                 f"score={pair[0].ordinal:.1f}  #{pair[0].comparison_count}"
        )
        self.left_name.config(text=self._format_image_path(pair[0]))

        # Right image
        self.right_canvas.delete("all")
        x = self.right_canvas.winfo_width() // 2
        y = self.right_canvas.winfo_height() // 2
        self.right_canvas.create_image(x, y, image=self.right_photo, anchor="center")
        self.right_stats.config(
            text=f"\u03bc={pair[1].mu:.1f}  \u03c3={pair[1].sigma:.1f}  "
                 f"score={pair[1].ordinal:.1f}  #{pair[1].comparison_count}"
        )
        self.right_name.config(text=self._format_image_path(pair[1]))

    def _preload_next(self):
        """Preload the next pair of images in background thread."""
        if self.closing:
            return

        try:
            pair = self.ranker.pick_pair()
            if pair is None:
                return

            # Load and resize both images (PIL only - thread safe)
            left_pil = self._load_pil_image(pair[0])
            right_pil = self._load_pil_image(pair[1])

            # Store preloaded data (only if not closing)
            if not self.closing:
                with self.preload_lock:
                    self.preloaded_pair = pair
                    self.preloaded_left_pil = left_pil
                    self.preloaded_right_pil = right_pil

        except Exception as e:
            logger.error(f"Error preloading images: {e}")

    def _load_pil_image(self, img: RankedImage) -> Image.Image:
        """Load and resize an image, returning a PIL Image (thread-safe)."""
        pil_img = Image.open(img.filepath)

        # Convert to RGB if necessary (for RGBA, P mode images)
        if pil_img.mode not in ('RGB', 'L'):
            pil_img = pil_img.convert('RGB')

        # Use fixed max size for preloading
        max_size = self.MAX_IMAGE_SIZE

        ratio = min(max_size / pil_img.width, max_size / pil_img.height)
        if ratio < 1:
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

        return pil_img

    def _load_and_display_image(self, img: RankedImage, side: str):
        """Load and display an image (synchronous, for first load)."""
        canvas = self.left_canvas if side == "left" else self.right_canvas
        stats_label = self.left_stats if side == "left" else self.right_stats
        name_label = self.left_name if side == "left" else self.right_name

        canvas.delete("all")

        try:
            pil_img = Image.open(img.filepath)

            canvas.update_idletasks()
            max_w = canvas.winfo_width() - 20
            max_h = canvas.winfo_height() - 20

            if max_w < 100:
                max_w = self.MAX_IMAGE_SIZE
            if max_h < 100:
                max_h = self.MAX_IMAGE_SIZE

            ratio = min(max_w / pil_img.width, max_h / pil_img.height)
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(pil_img)

            if side == "left":
                self.left_photo = photo
            else:
                self.right_photo = photo

            x = canvas.winfo_width() // 2
            y = canvas.winfo_height() // 2
            canvas.create_image(x, y, image=photo, anchor="center")

        except Exception as e:
            logger.error(f"Error loading image {img.filepath}: {e}")
            canvas.create_text(
                canvas.winfo_width() // 2,
                canvas.winfo_height() // 2,
                text=f"Error loading image:\n{e}",
                fill=ModernStyle.ERROR,
                font=ModernStyle.FONT_BODY
            )

        stats_label.config(
            text=f"\u03bc={img.mu:.1f}  \u03c3={img.sigma:.1f}  "
                 f"score={img.ordinal:.1f}  #{img.comparison_count}"
        )
        name_label.config(text=self._format_image_path(img))

    def show_no_images(self):
        """Display message when no images available."""
        for canvas in [self.left_canvas, self.right_canvas]:
            canvas.delete("all")
            canvas.create_text(
                canvas.winfo_width() // 2,
                canvas.winfo_height() // 2,
                text="Add a folder to start ranking images",
                fill=ModernStyle.TEXT_DIM,
                font=ModernStyle.FONT_HEADING
            )

        self.left_stats.config(text="")
        self.right_stats.config(text="")
        self.left_name.config(text="")
        self.right_name.config(text="")

    def select_winner(self, side: str):
        """Record comparison result."""
        if self.current_pair is None:
            return

        left_img, right_img = self.current_pair

        if side == "left":
            self.ranker.record_comparison(left_img.id, right_img.id)
        else:
            self.ranker.record_comparison(right_img.id, left_img.id)

        self.session_comparisons += 1
        self.update_stats()
        self.next_pair()

    def skip_pair(self):
        """Skip current pair (treat as draw)."""
        if self.current_pair is None:
            return

        left_img, right_img = self.current_pair
        self.ranker.record_comparison(left_img.id, right_img.id, is_draw=True)

        self.session_comparisons += 1
        self.update_stats()
        self.next_pair()

    def undo_last(self):
        """Undo the last comparison."""
        result = self.ranker.undo_last_comparison()

        if result:
            if self.session_comparisons > 0:
                self.session_comparisons -= 1
            self.update_stats()
            messagebox.showinfo("Undo", "Last comparison undone.", parent=self)
        else:
            messagebox.showinfo("Undo", "Nothing to undo.", parent=self)

    def show_rankings(self):
        """Open the rankings view dialog."""
        from rankings_view_dialog import RankingsViewDialog
        RankingsViewDialog(self, self.ranker)

    def on_close(self):
        """Handle dialog close."""
        # Stop preloading
        self.closing = True

        # Shutdown executor gracefully
        self.executor.shutdown(wait=False)

        self.ranker.clear_session()
        self.destroy()


def show_image_ranker(parent, config_manager=None):
    """Convenience function to show the image ranker dialog."""
    dialog = ImageRankerDialog(parent, config_manager)
    return dialog
