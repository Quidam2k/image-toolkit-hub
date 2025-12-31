"""
Batch Export Dialog for Image Grid Sorter

Interactive UI for querying tags and exporting image batches for WAN 2.2 i2v processing.

Features:
- Visual tag selection with click-to-toggle
- Real-time result count updates
- Preview matching images
- Export with copy or symlink modes
- Progress tracking during export
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import logging
from pathlib import Path
from tag_database import TagDatabase
from batch_exporter import BatchExporter

logger = logging.getLogger(__name__)


class BatchExportDialog(tk.Toplevel):
    """Dialog for querying tags and exporting image batches."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Initialize backend
        self.tag_db = TagDatabase('tag_database.db')
        self.db_loaded = False

        self.title("Batch Export Tool")
        self.geometry("1100x800")  # Larger window for better visibility
        self.resizable(True, True)

        # State tracking: tags organized by type
        self.or_tags = set()      # Green: Include with OR logic
        self.and_tags = set()     # Blue: Include with AND logic
        self.not_tags = set()     # Red: Exclude with NOT logic
        self.current_results = []
        self.all_tags = []        # Store all tags for filtering
        self.tag_buttons = {}     # Store tag buttons for color updates
        self.show_hidden = False  # Toggle for showing hidden tags
        self.tags_displayed = 100  # Current number of tags displayed
        self.loading_more = False  # Flag to prevent multiple simultaneous loads

        self.setup_ui()
        self.load_database()  # Load before modal behavior to allow event processing
        self.setup_modal_behavior()

        # Close database on window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle window close event."""
        # Unbind mousewheel to prevent memory leaks
        self.tag_canvas.unbind_all("<MouseWheel>")
        if self.tag_db:
            self.tag_db.close()
        self.destroy()

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.tag_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_canvas_scroll(self, *args):
        """Handle canvas scroll and update scrollbar."""
        # Update scrollbar position
        self.tag_scrollbar.set(*args)

        # Check if we're near the bottom for infinite scroll
        if len(args) == 2:
            try:
                top = float(args[0])
                bottom = float(args[1])
                # If we can see the bottom 20% (bottom value > 0.8), load more
                if bottom > 0.8 and not self.loading_more:
                    logger.debug(f"Scroll position: top={top}, bottom={bottom} - triggering load")
                    self.load_more_tags()
            except (ValueError, IndexError) as e:
                logger.debug(f"Scroll args parse error: {e}")

    def setup_ui(self):
        """Create the batch export interface."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Batch Export Tool",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Create a paned window for left/right layout
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 10))

        # LEFT PANEL: Tag selection
        left_frame = ttk.Frame(paned, padding="10")
        paned.add(left_frame, weight=1)

        self.left_title = ttk.Label(
            left_frame,
            text="Loading tags...",
            font=("Arial", 11, "bold")
        )
        self.left_title.pack(anchor="w", pady=(0, 5))

        left_desc = ttk.Label(
            left_frame,
            text="Click to cycle: White → Green (OR) → Blue (AND) → Red (NOT) → White",
            font=("Arial", 8, "italic"),
            foreground="gray"
        )
        left_desc.pack(anchor="w", pady=(0, 5))

        # Show hidden tags toggle
        self.show_hidden_var = tk.BooleanVar(value=False)
        show_hidden_check = ttk.Checkbutton(
            left_frame,
            text="Show hidden/blocked tags",
            variable=self.show_hidden_var,
            command=self.toggle_show_hidden
        )
        show_hidden_check.pack(anchor="w", pady=(0, 5))

        # Search/filter box
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        # Bind to KeyRelease event instead of trace (more reliable)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_tags())

        # Clear search button
        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
            width=6
        ).pack(side="left", padx=2)

        # Scrollable tag frame
        tag_scroll_frame = ttk.Frame(left_frame)
        tag_scroll_frame.pack(fill="both", expand=True)

        self.tag_scrollbar = ttk.Scrollbar(tag_scroll_frame)
        self.tag_scrollbar.pack(side="right", fill="y")

        self.tag_canvas = tk.Canvas(
            tag_scroll_frame,
            yscrollcommand=self._on_canvas_scroll,
            bg="white",
            highlightthickness=0
        )
        self.tag_canvas.pack(side="left", fill="both", expand=True)
        self.tag_scrollbar.config(command=self.tag_canvas.yview)

        self.tag_container = ttk.Frame(self.tag_canvas)
        self.tag_canvas_window = self.tag_canvas.create_window(
            0, 0, window=self.tag_container, anchor="nw"
        )

        # RIGHT PANEL: Results and controls
        right_frame = ttk.Frame(paned, padding="10")
        paned.add(right_frame, weight=1)

        right_title = ttk.Label(
            right_frame,
            text="Query Results",
            font=("Arial", 11, "bold")
        )
        right_title.pack(anchor="w", pady=(0, 5))

        # Result count
        self.result_label = ttk.Label(
            right_frame,
            text="Select tags to see results",
            font=("Arial", 10),
            foreground="blue"
        )
        self.result_label.pack(anchor="w", pady=(0, 10))

        # Results listbox
        results_scroll_frame = ttk.Frame(right_frame)
        results_scroll_frame.pack(fill="both", expand=True, pady=(0, 10))

        results_scrollbar = ttk.Scrollbar(results_scroll_frame)
        results_scrollbar.pack(side="right", fill="y")

        self.results_listbox = tk.Listbox(
            results_scroll_frame,
            yscrollcommand=results_scrollbar.set,
            height=15
        )
        self.results_listbox.pack(side="left", fill="both", expand=True)
        results_scrollbar.config(command=self.results_listbox.yview)

        # Export controls
        controls_frame = ttk.LabelFrame(right_frame, text="Export Options", padding="10")
        controls_frame.pack(fill="x", pady=(0, 10))

        # Mode selection
        mode_frame = ttk.Frame(controls_frame)
        mode_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(mode_frame, text="Export Mode:").pack(side="left")
        self.export_mode = tk.StringVar(value="copy")
        ttk.Radiobutton(
            mode_frame,
            text="Copy (safe, independent)",
            variable=self.export_mode,
            value="copy"
        ).pack(side="left", padx=10)
        ttk.Radiobutton(
            mode_frame,
            text="Symlink (fast, for testing)",
            variable=self.export_mode,
            value="symlink"
        ).pack(side="left")

        # Batch name
        name_frame = ttk.Frame(controls_frame)
        name_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(name_frame, text="Batch Name:").pack(side="left")
        self.batch_name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.batch_name_var, width=30).pack(
            side="left", padx=5
        )

        # Output directory
        dir_frame = ttk.Frame(controls_frame)
        dir_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(dir_frame, text="Output Dir:").pack(side="left")
        self.output_dir_var = tk.StringVar(value="./batch_exports")
        self.output_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=30)
        self.output_entry.pack(side="left", padx=5)
        # Force initial value display
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, "./batch_exports")
        ttk.Button(
            dir_frame,
            text="Browse...",
            command=self.browse_output_dir
        ).pack(side="left")

        # Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill="x")

        ttk.Button(
            button_frame,
            text="Clear Selection",
            command=self.clear_selection
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Export",
            command=self.export_batch
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Close",
            command=self.destroy
        ).pack(side="right", padx=5)

        # Bind canvas scroll and scroll events
        self.tag_canvas.bind(
            "<Configure>",
            lambda e: self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all"))
        )

        # Bind mousewheel for scrolling
        self.tag_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def setup_modal_behavior(self):
        """Configure modal window behavior."""
        self.transient(self.parent)
        self.grab_set()

    def load_database(self):
        """Check database and load tags (SQLite is instant)."""
        logger.info("Checking database...")

        try:
            # Check if database file exists
            from pathlib import Path
            db_path = Path('tag_database.db')

            if not db_path.exists():
                messagebox.showerror(
                    "Database Not Found",
                    "Tag database not found!\n\n"
                    "Please rebuild the tag database first:\n"
                    "1. Go to setup dialog\n"
                    "2. Click 'Rebuild Tag Database'\n\n"
                    "Or run: python rebuild_tag_database.py"
                )
                self.destroy()
                return

            # Database exists, populate tags
            logger.info("Database found, loading tags...")
            self.db_loaded = True
            self.populate_tags()
            self.result_label.config(text="Select tags to see results", foreground="blue")

            # Search is already enabled via KeyRelease binding
            logger.info("Search functionality ready (KeyRelease binding active)")

        except Exception as e:
            logger.error(f"Error loading database: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to load tag database:\n{str(e)}")
            self.destroy()

    def populate_tags(self):
        """Populate tag buttons (initially showing top 100 by frequency)."""
        logger.info("populate_tags() called")

        # Get all tags from database (tag, count, is_favorite, is_hidden)
        self.all_tags = self.tag_db.list_tags(
            favorites_first=True,
            limit=None,
            include_hidden=self.show_hidden
        )
        logger.info(f"Retrieved {len(self.all_tags)} tags from database")

        # Update title with actual tag count
        hidden_count = " (showing hidden)" if self.show_hidden else ""
        self.left_title.config(text=f"Available Tags ({len(self.all_tags)} total){hidden_count}")

        if not self.all_tags:
            # Show error message if no tags loaded
            logger.warning("No tags to display")
            error_label = ttk.Label(
                self.tag_container,
                text="No tags found. Database may be empty.\nPlease rebuild the tag database.",
                foreground="red"
            )
            error_label.pack(pady=20)
            return

        # Show only top tags initially (use search to find others)
        self.tags_displayed = min(100, len(self.all_tags))
        logger.info(f"Displaying top {self.tags_displayed} tags initially")
        self.display_filtered_tags(self.all_tags[:self.tags_displayed])
        logger.info("Initial tag display complete")

    def display_filtered_tags(self, tags_to_show):
        """Display a filtered list of tags."""
        # Save current selection states before clearing
        current_or = self.or_tags.copy()
        current_and = self.and_tags.copy()
        current_not = self.not_tags.copy()

        # Clear existing tags
        for widget in self.tag_container.winfo_children():
            widget.destroy()
        self.tag_buttons.clear()

        if not tags_to_show:
            no_results = ttk.Label(
                self.tag_container,
                text="No tags match your search",
                foreground="gray"
            )
            no_results.pack(pady=20)
            return

        # Create buttons for filtered tags
        for tag, count, is_favorite, is_hidden in tags_to_show:
            frame = ttk.Frame(self.tag_container)
            frame.pack(fill="x", pady=2)

            # Tag button
            fav_marker = "* " if is_favorite else ""
            hidden_marker = "[HIDDEN] " if is_hidden else ""
            btn = tk.Button(
                frame,
                text=f"{fav_marker}{hidden_marker}{tag} ({count})",
                command=lambda t=tag: self.toggle_tag(t),
                width=32,
                bg="#D3D3D3" if is_hidden else "white",  # Gray if hidden
                justify="left",
                anchor="w"
            )
            btn.pack(side="left", fill="x", expand=True)

            # Hide toggle button (X)
            hide_btn = tk.Button(
                frame,
                text="X",
                command=lambda t=tag: self.toggle_hidden(t),
                width=2,
                bg="#FFB6C1" if is_hidden else "white",  # Pink if hidden
                font=("Arial", 8, "bold")
            )
            hide_btn.pack(side="right", padx=(2, 0))

            # Favorite toggle button (*)
            fav_btn = tk.Button(
                frame,
                text="*",
                command=lambda t=tag: self.toggle_favorite(t),
                width=2,
                bg="#FFD700" if is_favorite else "white",
                font=("Arial", 10, "bold")
            )
            fav_btn.pack(side="right", padx=(2, 0))

            # Store button references (btn, fav_btn, hide_btn, is_favorite, is_hidden)
            self.tag_buttons[tag] = (btn, fav_btn, hide_btn, is_favorite, is_hidden)

            # Restore selection state if this tag was selected
            if tag in current_or:
                self.or_tags.add(tag)
            if tag in current_and:
                self.and_tags.add(tag)
            if tag in current_not:
                self.not_tags.add(tag)

            # Apply current color state to main button
            if tag in self.or_tags:
                btn.config(bg="#90EE90", activebackground="#70CE70")
            elif tag in self.and_tags:
                btn.config(bg="#87CEEB", activebackground="#67AEDB")
            elif tag in self.not_tags:
                btn.config(bg="#FFB6C1", activebackground="#FF96B1")

        # Force canvas to update scroll region
        self.tag_container.update_idletasks()
        self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all"))

    def filter_tags(self):
        """Filter tags based on search text."""
        try:
            if not self.all_tags:
                print("ERROR: filter_tags called but all_tags is empty")
                return

            # Read directly from Entry widget (more reliable than StringVar)
            search_text = self.search_entry.get().lower().strip()
            print(f"=== SEARCH: '{search_text}' (len={len(search_text)}) ===")

            if not search_text:
                # Show current display limit when search is empty
                self.display_filtered_tags(self.all_tags[:self.tags_displayed])
                print(f"Empty search, showing {self.tags_displayed} tags")
                return

            # Filter tags that contain the search text (substring match)
            filtered = [(tag, count, is_fav, is_hidden) for tag, count, is_fav, is_hidden in self.all_tags
                       if search_text in tag.lower()]

            print(f"Found {len(filtered)} tags matching '{search_text}'")
            if len(filtered) > 0:
                print(f"First 5 matches: {[tag for tag, _, _, _ in filtered[:5]]}")

            # Show up to 200 search results
            self.display_filtered_tags(filtered[:200])

        except Exception as e:
            print(f"ERROR in filter_tags: {e}")
            import traceback
            traceback.print_exc()

    def toggle_favorite(self, tag):
        """Toggle a tag's favorite status."""
        # Get current status from button storage
        if tag in self.tag_buttons:
            btn, fav_btn, hide_btn, is_favorite, is_hidden = self.tag_buttons[tag]

            # Toggle in database
            new_favorite_status = not is_favorite
            self.tag_db.set_favorite(tag, new_favorite_status)

            # Update button appearance
            fav_btn.config(bg="#FFD700" if new_favorite_status else "white")

            # Update stored state
            self.tag_buttons[tag] = (btn, fav_btn, hide_btn, new_favorite_status, is_hidden)

            # Update main button text
            fav_marker = "* " if new_favorite_status else ""
            hidden_marker = "[HIDDEN] " if is_hidden else ""
            # Get count from current text
            count_text = btn.cget("text").split("(")[1].strip(")")
            btn.config(text=f"{fav_marker}{hidden_marker}{tag} ({count_text})")

            # Reload all_tags to reflect favorite change
            self.all_tags = self.tag_db.list_tags(
                favorites_first=True,
                limit=None,
                include_hidden=self.show_hidden
            )

            logger.info(f"Tag '{tag}' {'favorited' if new_favorite_status else 'unfavorited'}")

    def toggle_hidden(self, tag):
        """Toggle a tag's hidden/blocked status."""
        # Get current status from button storage
        if tag in self.tag_buttons:
            btn, fav_btn, hide_btn, is_favorite, is_hidden = self.tag_buttons[tag]

            # Toggle in database
            new_hidden_status = not is_hidden
            self.tag_db.set_hidden(tag, new_hidden_status)

            # Update button appearance
            hide_btn.config(bg="#FFB6C1" if new_hidden_status else "white")
            btn.config(bg="#D3D3D3" if new_hidden_status else "white")

            # Update stored state
            self.tag_buttons[tag] = (btn, fav_btn, hide_btn, is_favorite, new_hidden_status)

            # Update main button text
            fav_marker = "* " if is_favorite else ""
            hidden_marker = "[HIDDEN] " if new_hidden_status else ""
            # Get count from current text
            count_text = btn.cget("text").split("(")[1].strip(")")
            btn.config(text=f"{fav_marker}{hidden_marker}{tag} ({count_text})")

            logger.info(f"Tag '{tag}' {'hidden' if new_hidden_status else 'unhidden'}")

            # If we just hid a tag and aren't showing hidden tags, refresh the list
            if new_hidden_status and not self.show_hidden:
                self.populate_tags()
                self.filter_tags()

    def toggle_show_hidden(self):
        """Toggle showing/hiding blocked tags."""
        self.show_hidden = self.show_hidden_var.get()
        logger.info(f"Show hidden tags: {self.show_hidden}")
        self.tags_displayed = 100  # Reset display limit when toggling
        self.populate_tags()
        self.filter_tags()

    def load_more_tags(self):
        """Load more tags when scrolling to bottom (infinite scroll)."""
        if self.loading_more:
            return

        search_text = self.search_var.get().lower().strip()

        # Don't load more if searching (already limited to 200 results)
        if search_text:
            return

        # Check if there are more tags to load
        if self.tags_displayed >= len(self.all_tags):
            logger.debug("All tags already displayed")
            return

        self.loading_more = True
        logger.info(f"Loading more tags (current: {self.tags_displayed}/{len(self.all_tags)})")

        # Save current scroll position
        scroll_pos = self.tag_canvas.yview()[0]

        # Update title to show loading
        hidden_count = " (showing hidden)" if self.show_hidden else ""
        self.left_title.config(text=f"Available Tags ({len(self.all_tags)} total){hidden_count} - Loading...")

        # Load 50 more tags
        old_count = self.tags_displayed
        self.tags_displayed = min(self.tags_displayed + 50, len(self.all_tags))

        # Add new tags to display
        new_tags = self.all_tags[old_count:self.tags_displayed]

        for tag, count, is_favorite, is_hidden in new_tags:
            frame = ttk.Frame(self.tag_container)
            frame.pack(fill="x", pady=2)

            # Tag button
            fav_marker = "* " if is_favorite else ""
            hidden_marker = "[HIDDEN] " if is_hidden else ""
            btn = tk.Button(
                frame,
                text=f"{fav_marker}{hidden_marker}{tag} ({count})",
                command=lambda t=tag: self.toggle_tag(t),
                width=32,
                bg="#D3D3D3" if is_hidden else "white",
                justify="left",
                anchor="w"
            )
            btn.pack(side="left", fill="x", expand=True)

            # Hide toggle button (X)
            hide_btn = tk.Button(
                frame,
                text="X",
                command=lambda t=tag: self.toggle_hidden(t),
                width=2,
                bg="#FFB6C1" if is_hidden else "white",
                font=("Arial", 8, "bold")
            )
            hide_btn.pack(side="right", padx=(2, 0))

            # Favorite toggle button (*)
            fav_btn = tk.Button(
                frame,
                text="*",
                command=lambda t=tag: self.toggle_favorite(t),
                width=2,
                bg="#FFD700" if is_favorite else "white",
                font=("Arial", 10, "bold")
            )
            fav_btn.pack(side="right", padx=(2, 0))

            # Store button references
            self.tag_buttons[tag] = (btn, fav_btn, hide_btn, is_favorite, is_hidden)

            # Apply current color state
            if tag in self.or_tags:
                btn.config(bg="#90EE90", activebackground="#70CE70")
            elif tag in self.and_tags:
                btn.config(bg="#87CEEB", activebackground="#67AEDB")
            elif tag in self.not_tags:
                btn.config(bg="#FFB6C1", activebackground="#FF96B1")

        # Force canvas to update scroll region
        self.tag_container.update_idletasks()
        self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all"))

        # Restore scroll position (prevent jumping)
        self.tag_canvas.yview_moveto(scroll_pos)

        # Update title to show current count
        hidden_count = " (showing hidden)" if self.show_hidden else ""
        self.left_title.config(text=f"Available Tags ({len(self.all_tags)} total){hidden_count}")

        logger.info(f"Loaded {len(new_tags)} more tags (now showing {self.tags_displayed})")
        self.loading_more = False

    def toggle_tag(self, tag):
        """Toggle a tag between OR/AND/NOT/none states."""
        # Cycle: none → OR (green) → AND (blue) → NOT (red) → none
        if tag in self.or_tags:
            self.or_tags.remove(tag)
            self.and_tags.add(tag)
        elif tag in self.and_tags:
            self.and_tags.remove(tag)
            self.not_tags.add(tag)
        elif tag in self.not_tags:
            self.not_tags.remove(tag)
        else:
            self.or_tags.add(tag)

        # Update colors
        self.update_tag_colors()
        # Update results
        self.update_results()

    def update_tag_colors(self):
        """Update tag button colors based on selection state."""
        for tag, (btn, fav_btn, hide_btn, is_fav, is_hidden) in self.tag_buttons.items():
            if tag in self.or_tags:
                btn.config(bg="#90EE90", activebackground="#70CE70")  # Light green: OR
            elif tag in self.and_tags:
                btn.config(bg="#87CEEB", activebackground="#67AEDB")  # Light blue: AND
            elif tag in self.not_tags:
                btn.config(bg="#FFB6C1", activebackground="#FF96B1")  # Light red: NOT
            elif is_hidden:
                btn.config(bg="#D3D3D3", activebackground="#C0C0C0")  # Gray: hidden
            else:
                btn.config(bg="white", activebackground="#F0F0F0")    # White: none

    def update_results(self):
        """Update query results and show preview."""
        if not self.db_loaded or (not self.or_tags and not self.and_tags and not self.not_tags):
            self.result_label.config(text="Select tags to see results", foreground="blue")
            self.results_listbox.delete(0, tk.END)
            self.current_results = []
            return

        try:
            # Combine OR and AND tags for include list
            include_tags = list(self.or_tags) + list(self.and_tags)
            exclude_tags = list(self.not_tags)

            # Determine operator: if we have both OR and AND tags, we need to handle specially
            if self.or_tags and self.and_tags:
                # Get images with OR tags first
                or_images = set(self.tag_db.query_images(list(self.or_tags), [], 'OR'))
                # Get images with AND tags
                and_images = set(self.tag_db.query_images(list(self.and_tags), [], 'AND'))
                # Intersection (images must have OR match AND AND match)
                images = list(or_images & and_images)
            elif self.or_tags:
                # Just OR query
                images = self.tag_db.query_images(list(self.or_tags), [], 'OR')
            elif self.and_tags:
                # Just AND query
                images = self.tag_db.query_images(list(self.and_tags), [], 'AND')
            else:
                images = []

            # Apply exclusions
            if exclude_tags and images:
                excluded_set = set()
                for exclude_tag in exclude_tags:
                    excluded_set.update(self.tag_db.get_images_for_tag(exclude_tag))
                images = [img for img in images if img not in excluded_set]

            # Update results
            self.current_results = images
            self.result_label.config(
                text=f"Found {len(images):,} matching images",
                foreground="green"
            )

            # Show preview (first 50)
            self.results_listbox.delete(0, tk.END)
            for img in images[:50]:
                filename = Path(img).name
                self.results_listbox.insert(tk.END, filename)

            if len(images) > 50:
                self.results_listbox.insert(tk.END, f"... and {len(images)-50:,} more images")

        except Exception as e:
            logger.error(f"Error updating results: {e}")
            self.result_label.config(
                text=f"Error: {str(e)}",
                foreground="red"
            )
            self.results_listbox.delete(0, tk.END)
            self.current_results = []

    def clear_selection(self):
        """Clear all tag selections."""
        self.or_tags.clear()
        self.and_tags.clear()
        self.not_tags.clear()
        self.update_tag_colors()
        self.update_results()

    def clear_search(self):
        """Clear search box."""
        self.search_entry.delete(0, tk.END)
        self.filter_tags()

    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory for Batches"
        )
        if directory:
            # Clear and insert directly to ensure visibility
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)
            # Also update the StringVar
            self.output_dir_var.set(directory)
            logger.info(f"Output directory set to: {directory}")

    def export_batch(self):
        """Export batch with progress dialog."""
        if not self.current_results:
            messagebox.showwarning(
                "No Results",
                "Please select tags to query first."
            )
            return

        # Validate batch name
        batch_name = self.batch_name_var.get().strip()
        if not batch_name:
            # Auto-generate name from tags
            all_tags = list(self.or_tags) + list(self.and_tags) + list(self.not_tags)
            if all_tags:
                batch_name = "_".join(sorted(all_tags)[:3])[:30]  # First 3 tags
            else:
                batch_name = "batch"

        output_dir = self.output_dir_var.get().strip()
        # Safeguard: if empty, use default
        if not output_dir:
            output_dir = "./batch_exports"
            logger.warning("Output directory was empty, using default: ./batch_exports")
        mode = self.export_mode.get()

        # Build query string for manifest
        query_parts = []
        if self.or_tags:
            query_parts.append("|".join(sorted(self.or_tags)))
        if self.and_tags:
            query_parts.append(",".join(sorted(self.and_tags)))
        if self.not_tags:
            query_parts.append("!" + ",!".join(sorted(self.not_tags)))
        query_string = ",".join(query_parts)

        # Create new exporter with user-selected output directory
        exporter = BatchExporter(output_dir)

        # Create progress dialog
        progress_dialog = BatchExportProgressDialog(
            self,
            exporter,
            self.current_results,
            batch_name,
            query_string,
            output_dir,
            mode
        )
        self.wait_window(progress_dialog)


class BatchExportProgressDialog(tk.Toplevel):
    """Progress dialog for batch export."""

    def __init__(self, parent, exporter, images, batch_name, query, output_dir, mode):
        super().__init__(parent)
        self.parent = parent
        self.exporter = exporter
        self.images = images
        self.batch_name = batch_name
        self.query = query
        self.output_dir = output_dir
        self.mode = mode

        # Thread communication
        self.progress_state = {
            'current': 0,
            'total': len(images),
            'message': 'Preparing...',
            'complete': False,
            'result': None
        }
        self.cancel_requested = False

        self.title("Exporting Batch...")
        self.geometry("500x250")
        self.resizable(False, False)

        self.setup_ui()
        self.setup_modal_behavior()
        self.start_export()
        self.poll_progress()

    def setup_ui(self):
        """Create progress UI."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        title = ttk.Label(
            main_frame,
            text=f"Exporting {len(self.images):,} images...",
            font=("Arial", 12, "bold")
        )
        title.pack(pady=(0, 20))

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            length=400,
            mode="determinate",
            maximum=100
        )
        self.progress.pack(fill="x", pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Preparing...",
            font=("Arial", 10)
        )
        self.status_label.pack(anchor="w", pady=(0, 20))

        # Result label
        self.result_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 9),
            foreground="gray"
        )
        self.result_label.pack(anchor="w")

        # Cancel button
        self.cancel_button = ttk.Button(
            main_frame,
            text="Cancel",
            command=self.request_cancel
        )
        self.cancel_button.pack(pady=(10, 0))

    def setup_modal_behavior(self):
        """Configure modal window behavior."""
        self.transient(self.parent)
        self.grab_set()

    def start_export(self):
        """Start export in background thread."""
        thread = threading.Thread(target=self.run_export, daemon=True)
        thread.start()

    def request_cancel(self):
        """Request cancellation of export."""
        self.cancel_requested = True
        self.cancel_button.config(state='disabled')
        self.status_label.config(text="Cancelling...")

    def poll_progress(self):
        """Poll progress state from main thread and update UI."""
        if not self.winfo_exists():
            return

        # Update UI from progress state
        state = self.progress_state
        pct = int((state['current'] / state['total']) * 100) if state['total'] > 0 else 0
        self.progress["value"] = pct
        self.status_label.config(text=state['message'])

        # Check if complete
        if state['complete']:
            self.show_result(state['result'])
            return

        # Continue polling every 100ms
        self.after(100, self.poll_progress)

    def run_export(self):
        """Execute export with progress updates (runs in background thread)."""
        def progress_callback(current, total, message):
            # Update shared state (thread-safe for simple assignments)
            self.progress_state['current'] = current
            self.progress_state['total'] = total
            self.progress_state['message'] = message

            # Check for cancellation
            if self.cancel_requested:
                # Signal exporter to stop (if it supports it)
                return False  # Return False to signal cancellation
            return True

        try:
            result = self.exporter.export_images(
                self.images,
                self.batch_name,
                query=self.query,
                mode=self.mode,
                progress_callback=progress_callback
            )

            # Mark complete
            self.progress_state['complete'] = True
            self.progress_state['result'] = result

        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.progress_state['complete'] = True
            self.progress_state['result'] = {
                'success': False,
                'error': str(e)
            }

    def show_result(self, result):
        """Show export result."""
        # Disable cancel button
        self.cancel_button.config(state='disabled')

        if result['success']:
            self.progress["value"] = 100
            self.status_label.config(text="Export complete!")
            self.result_label.config(
                text=f"Batch: {Path(result['batch_path']).name}\n"
                     f"Copied: {result['copied']:,} images\n"
                     f"Size: {self.exporter.format_size(result['total_size'])}\n"
                     f"Time: {result['time_taken']:.1f}s",
                foreground="green"
            )

            # Auto-close after 3 seconds
            self.after(3000, self.destroy)
        else:
            self.status_label.config(text="Export failed!", foreground="red")
            self.result_label.config(text=result.get('error', 'Unknown error'), foreground="red")


# Convenience function for integration into main app
def show_batch_export_dialog(parent):
    """Show batch export dialog."""
    dialog = BatchExportDialog(parent)
    return dialog
