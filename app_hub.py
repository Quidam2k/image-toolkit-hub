"""
Image Toolkit Hub - Main Launcher

A modern hub interface for the image management toolkit.
Provides quick access to all tools without requiring the grid sorter.

Author: Claude Code Implementation
Version: 3.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import gc
import threading
from pathlib import Path

from ui_theme import Theme as ModernStyle
import toast_manager
from help_texts import get_tooltip, TOOLTIPS

try:
    from send2trash import send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False


class ToolCard(tk.Frame):
    """A clickable card representing a tool."""

    def __init__(self, parent, icon, title, description, command,
                 status_text=None, status_color=None, **kwargs):
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

        # Top row: icon + title side by side
        top_row = tk.Frame(inner, bg=ModernStyle.BG_CARD)
        top_row.pack(fill="x", pady=(0, 6))

        icon_label = tk.Label(top_row,
            text=icon,
            font=("Segoe UI", 22),
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = tk.Label(top_row,
            text=title,
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)

        # Description - wider wraplength
        desc_label = tk.Label(inner,
            text=description,
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            anchor="w",
            wraplength=320,
            justify="left"
        )
        desc_label.pack(fill="x")

        # Optional status/prerequisite line
        self.status_label = None
        if status_text:
            self.status_label = tk.Label(inner,
                text=status_text,
                font=ModernStyle.FONT_TINY,
                fg=status_color or ModernStyle.TEXT_MUTED,
                bg=ModernStyle.BG_CARD,
                anchor="w"
            )
            self.status_label.pack(fill="x", pady=(6, 0))

        # Bind click events to all children
        self._all_widgets = [self, inner, top_row, icon_label, title_label, desc_label]
        if self.status_label:
            self._all_widgets.append(self.status_label)
        for widget in self._all_widgets:
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


class SidebarButton(tk.Frame):
    """A vertical navigation button for the sidebar.

    Shows an accent left-border when active. Used both for panel-switching
    entries (Home/Config) and for action entries that launch tools.
    """

    def __init__(self, parent, icon, label, command, **kwargs):
        super().__init__(parent, bg=ModernStyle.BG_CARD, cursor="hand2", **kwargs)

        self.command = command
        self.active = False

        # Accent strip on the left edge - shown only when active.
        self.accent_strip = tk.Frame(self, bg=ModernStyle.BG_CARD, width=3)
        self.accent_strip.pack(side="left", fill="y")

        self.inner = tk.Frame(self, bg=ModernStyle.BG_CARD)
        self.inner.pack(side="left", fill="both", expand=True, padx=(10, 12), pady=9)

        self.icon_lbl = tk.Label(self.inner,
            text=icon,
            font=("Segoe UI", 14),
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            width=2
        )
        self.icon_lbl.pack(side="left")

        self.text_lbl = tk.Label(self.inner,
            text=label,
            font=ModernStyle.FONT_BODY,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        self.text_lbl.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._widgets = [self, self.inner, self.icon_lbl, self.text_lbl]
        for w in self._widgets:
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", lambda e: self._on_enter())
            w.bind("<Leave>", lambda e: self._on_leave())

    def _bg(self):
        return ModernStyle.BG_HOVER if (self.active or self._hovering()) else ModernStyle.BG_CARD

    def _hovering(self):
        return getattr(self, '_hover', False)

    def _apply_bg(self, color):
        for w in (self, self.inner, self.icon_lbl, self.text_lbl):
            w.configure(bg=color)

    def _on_enter(self):
        self._hover = True
        self._apply_bg(ModernStyle.BG_HOVER)
        self.icon_lbl.configure(fg=ModernStyle.TEXT)
        self.text_lbl.configure(fg=ModernStyle.TEXT)

    def _on_leave(self):
        self._hover = False
        self._refresh()

    def set_active(self, active):
        self.active = active
        self._refresh()

    def _refresh(self):
        if self.active:
            self._apply_bg(ModernStyle.BG_HOVER)
            self.accent_strip.configure(bg=ModernStyle.ACCENT)
            self.icon_lbl.configure(fg=ModernStyle.ACCENT)
            self.text_lbl.configure(fg=ModernStyle.TEXT)
        else:
            self._apply_bg(ModernStyle.BG_CARD)
            self.accent_strip.configure(bg=ModernStyle.BG_CARD)
            self.icon_lbl.configure(fg=ModernStyle.TEXT_DIM)
            self.text_lbl.configure(fg=ModernStyle.TEXT_DIM)


class FolderTreePanel(tk.Frame):
    """Treeview panel for browsing folders with stats and tag coverage."""

    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}

    def __init__(self, parent, hub, title, **kwargs):
        super().__init__(parent, bg=ModernStyle.BG_CARD, **kwargs)
        self.hub = hub
        self.title_text = title
        self._scan_cache = {}  # path -> {images, tagged, size}
        self._folder_paths = {}  # tree item id -> filesystem path
        self._scanning = False

        self._build_ui()

    def _build_ui(self):
        """Build the treeview UI."""
        # Header
        header = tk.Frame(self, bg=ModernStyle.BG_CARD)
        header.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(header,
            text=self.title_text,
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(side="left")

        self.action_frame = tk.Frame(header, bg=ModernStyle.BG_CARD)
        self.action_frame.pack(side="right")

        # Treeview with columns
        tree_frame = tk.Frame(self, bg=ModernStyle.BG_CARD)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.tree = ttk.Treeview(tree_frame,
            columns=("count", "tagged"),
            show="tree headings",
            height=6,
            selectmode="browse"
        )

        # Column config
        self.tree.heading("#0", text="Folder", anchor="w")
        self.tree.heading("count", text="Files", anchor="e")
        self.tree.heading("tagged", text="Tagged", anchor="e")

        self.tree.column("#0", width=160, minwidth=100)
        self.tree.column("count", width=50, minwidth=40, anchor="e")
        self.tree.column("tagged", width=55, minwidth=40, anchor="e")

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Expand/collapse on double-click is default; lazy-load children on expand
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)

        # Right-click context menu
        self.context_menu = tk.Menu(self, tearoff=0,
            bg=ModernStyle.BG_ELEVATED, fg=ModernStyle.TEXT,
            activebackground=ModernStyle.ACCENT,
            activeforeground=ModernStyle.TEXT,
            font=ModernStyle.FONT_SMALL)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _on_right_click(self, event):
        """Show context menu on right-click."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        path = self._folder_paths.get(item)
        if not path:
            return

        self.context_menu.delete(0, "end")
        self._build_context_menu(item, path)
        self.context_menu.post(event.x_root, event.y_root)

    def _build_context_menu(self, item, path):
        """Override in subclasses for custom menu items."""
        self.context_menu.add_command(
            label="Open in Explorer",
            command=lambda: os.startfile(path)
        )

    def _on_expand(self, event):
        """Lazy-load children when a node is expanded."""
        item = self.tree.focus()
        path = self._folder_paths.get(item)
        if not path:
            return

        # Check if children are placeholder
        children = self.tree.get_children(item)
        if len(children) == 1 and self.tree.item(children[0], "text") == "...":
            # Remove placeholder and load real children
            self.tree.delete(children[0])
            self._populate_children(item, path)

    def _populate_children(self, parent_item, parent_path):
        """Add child folders to a tree node."""
        try:
            subdirs = []
            for entry in os.scandir(parent_path):
                if entry.is_dir() and not entry.name.startswith('.'):
                    # Check if folder has any content (skip empty)
                    try:
                        has_content = any(os.scandir(entry.path))
                    except (PermissionError, OSError):
                        has_content = False
                    if has_content:
                        subdirs.append(entry)

            subdirs.sort(key=lambda e: e.name.lower())

            for entry in subdirs:
                child_id = self.tree.insert(parent_item, "end",
                    text=entry.name + "/",
                    values=("...", ""),
                    open=False
                )
                self._folder_paths[child_id] = entry.path

                # Add placeholder for expandability
                try:
                    has_subdirs = any(
                        e.is_dir() and not e.name.startswith('.')
                        for e in os.scandir(entry.path)
                    )
                    if has_subdirs:
                        self.tree.insert(child_id, "end", text="...")
                except (PermissionError, OSError):
                    pass

                # Queue stats scan for this child
                self._queue_scan(child_id, entry.path)

        except (PermissionError, OSError) as e:
            print(f"Error scanning {parent_path}: {e}")

    def _queue_scan(self, item_id, path):
        """Scan a folder's stats in background and update the tree."""
        def scan():
            images = 0
            tagged = 0
            size = 0
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.IMAGE_EXTENSIONS:
                            images += 1
                            fpath = os.path.join(root, f)
                            try:
                                size += os.path.getsize(fpath)
                            except OSError:
                                pass
                            if os.path.exists(fpath + '.txt'):
                                tagged += 1
            except (PermissionError, OSError):
                pass

            self._scan_cache[path] = {'images': images, 'tagged': tagged, 'size': size}
            try:
                self.after(0, lambda: self._update_tree_item(item_id, images, tagged))
            except RuntimeError:
                pass  # Main loop may have exited

        thread = threading.Thread(target=scan, daemon=True)
        thread.start()

    def _update_tree_item(self, item_id, images, tagged):
        """Update a tree item's stats columns."""
        if not self.winfo_exists():
            return
        try:
            if images == 0:
                self.tree.item(item_id, values=("-", ""))
            else:
                pct = f"{tagged/images*100:.0f}%" if tagged > 0 else "0%"
                self.tree.item(item_id, values=(f"{images:,}", pct))
        except tk.TclError:
            pass  # Item may have been deleted

    @staticmethod
    def _format_size(size_bytes):
        """Format bytes as human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class SourceFolderPanel(FolderTreePanel):
    """Source folders treeview with add/remove and tag coverage."""

    def __init__(self, parent, hub, **kwargs):
        super().__init__(parent, hub, "Source Folders", **kwargs)

        # Add button in header
        add_btn = tk.Label(self.action_frame,
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

        # Left-click on a top-level source's label toggles its active state
        # (the ☑/☐ box). Bound here rather than the base so it uses this
        # subclass's _toggle_source. Right-click menu is kept as well.
        self.tree.bind("<Button-1>", self._on_left_click)

        self.populate()

    def _on_left_click(self, event):
        """Toggle a source's active state when its label (not the expander) is clicked."""
        # Ignore clicks on the expand/collapse triangle so folders still expand.
        element = self.tree.identify_element(event.x, event.y)
        if "indicator" in element:
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Only top-level sources have a ☑/☐ checkbox.
        if self.tree.parent(item) != "":
            return

        path = self._folder_paths.get(item)
        if not path:
            return

        is_active = self.hub.active_sources.get(path, True)
        self._toggle_source(item, path, not is_active)

    def populate(self):
        """Populate the tree with configured source folders."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._folder_paths.clear()

        folders = self.hub.source_folders
        active = self.hub.active_sources

        if not folders:
            return

        for folder in folders:
            if not os.path.isdir(folder):
                continue

            is_active = active.get(folder, True)
            display = Path(folder).name or folder

            item_id = self.tree.insert("", "end",
                text=("☑ " if is_active else "☐ ") + display + "/",
                values=("...", ""),
                open=False,
                tags=("active" if is_active else "inactive",)
            )
            self._folder_paths[item_id] = folder

            # Add placeholder for expansion
            try:
                has_subdirs = any(
                    e.is_dir() and not e.name.startswith('.')
                    for e in os.scandir(folder)
                )
                if has_subdirs:
                    self.tree.insert(item_id, "end", text="...")
            except (PermissionError, OSError):
                pass

            # Scan stats for the source folder itself
            self._queue_scan(item_id, folder)

        # Style tags for active/inactive
        self.tree.tag_configure("active", foreground=ModernStyle.TEXT)
        self.tree.tag_configure("inactive", foreground=ModernStyle.TEXT_MUTED)

    def _build_context_menu(self, item, path):
        """Build context menu for source folder items."""
        # Check if this is a top-level source
        parent = self.tree.parent(item)
        is_source = parent == ""

        self.context_menu.add_command(
            label="Open in Explorer",
            command=lambda: os.startfile(path)
        )

        if is_source:
            is_active = self.hub.active_sources.get(path, True)
            self.context_menu.add_command(
                label="Disable" if is_active else "Enable",
                command=lambda: self._toggle_source(item, path, not is_active)
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Remove from sources",
                command=lambda: self._remove_source(path)
            )
        else:
            # Subfolder - offer to add as source
            if path not in self.hub.source_folders:
                self.context_menu.add_command(
                    label="Add as Source Folder",
                    command=lambda: self._add_as_source(path)
                )

    def _toggle_source(self, item, path, active):
        """Toggle a source folder's active state."""
        self.hub.active_sources[path] = active
        self.hub.save_config()
        display = Path(path).name or path
        self.tree.item(item,
            text=("☑ " if active else "☐ ") + display + "/",
            tags=("active" if active else "inactive",)
        )

    def _remove_source(self, path):
        """Remove a folder from sources."""
        if path in self.hub.source_folders:
            self.hub.source_folders.remove(path)
            if path in self.hub.active_sources:
                del self.hub.active_sources[path]
            self.hub.save_config()
            self.populate()

    def _add_as_source(self, path):
        """Add a subfolder as a new top-level source."""
        if path not in self.hub.source_folders:
            self.hub.source_folders.append(path)
            self.hub.active_sources[path] = True
            self.hub.save_config()
            self.populate()
            toast_manager.show_success("Source Added", f"Added: {Path(path).name}")

    def add_folder(self):
        """Add a new source folder via dialog."""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            if folder not in self.hub.source_folders:
                self.hub.source_folders.append(folder)
                self.hub.active_sources[folder] = True
                self.hub.save_config()
                self.populate()
            else:
                messagebox.showinfo("Info", "Folder already in list.")


class OutputFolderPanel(FolderTreePanel):
    """Output folders treeview with removed tally and clear button."""

    def __init__(self, parent, hub, **kwargs):
        super().__init__(parent, hub, "Output Folders", **kwargs)

        # Refresh button in header
        refresh_btn = tk.Label(self.action_frame,
            text="↻",
            font=("Segoe UI", 12),
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        refresh_btn.pack(side="right")
        refresh_btn.bind("<Button-1>", lambda e: self.populate())
        refresh_btn.bind("<Enter>", lambda e: refresh_btn.configure(fg=ModernStyle.ACCENT_HOVER))
        refresh_btn.bind("<Leave>", lambda e: refresh_btn.configure(fg=ModernStyle.ACCENT))

        # Removed tally at bottom
        self.removed_frame = tk.Frame(self, bg=ModernStyle.BG_CARD)
        self.removed_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.removed_label = tk.Label(self.removed_frame,
            text="",
            font=ModernStyle.FONT_TINY,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        self.removed_label.pack(side="left")

        self.clear_btn = tk.Label(self.removed_frame,
            text="Clear All Removed",
            font=ModernStyle.FONT_TINY,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        self.clear_btn.pack(side="right")
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_all_removed())
        self.clear_btn.bind("<Enter>", lambda e: self.clear_btn.configure(fg=ModernStyle.ERROR))
        self.clear_btn.bind("<Leave>", lambda e: self.clear_btn.configure(fg=ModernStyle.TEXT_MUTED))

        self.folder_stats = {}
        self.populate()

    def populate(self):
        """Populate the tree with output folders from script directory."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._folder_paths.clear()
        self.folder_stats.clear()

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Scan for output folders: new output/ structure + legacy sorted_* folders
        output_names = []
        try:
            for entry in os.scandir(script_dir):
                if not entry.is_dir() or entry.name.startswith('.'):
                    continue
                name = entry.name
                # Skip known non-output directories
                skip = ('__pycache__', 'models', 'tests', 'scripts',
                        'docs', 'logs', 'data', 'archive', 'backups',
                        'screengrab', 'prompt_backups', 'prompt_backup_emergency',
                        'processed_batches', '.git')
                if name in skip:
                    continue
                if (name == 'output' or
                        name in ('1', '2', '3', 'removed', 'auto_sorted') or
                        name.startswith('sorted_') or
                        name.startswith('tshirt_ready') or
                        name.startswith('batch_export') or
                        name.startswith('master_images')):
                    # Check not empty
                    try:
                        has_content = any(os.scandir(entry.path))
                    except (PermissionError, OSError):
                        has_content = False
                    if has_content:
                        output_names.append(entry)
        except (PermissionError, OSError):
            pass

        output_names.sort(key=lambda e: e.name.lower())

        total_removed_count = 0
        total_removed_size = 0

        for entry in output_names:
            item_id = self.tree.insert("", "end",
                text=entry.name + "/",
                values=("...", ""),
                open=False
            )
            self._folder_paths[item_id] = entry.path

            # Add placeholder for expansion
            try:
                has_subdirs = any(
                    e.is_dir() and not e.name.startswith('.')
                    for e in os.scandir(entry.path)
                )
                if has_subdirs:
                    self.tree.insert(item_id, "end", text="...")
            except (PermissionError, OSError):
                pass

            self._queue_scan(item_id, entry.path)

            # Track removed folder stats
            if entry.name == 'removed':
                count, size = self._count_recursive(entry.path)
                total_removed_count += count
                total_removed_size += size
                self.folder_stats['removed'] = {
                    'path': entry.path, 'count': count, 'size': size
                }

        # Also scan for 'removed' inside source folders
        for source in self.hub.source_folders:
            removed_path = os.path.join(source, 'removed')
            if os.path.isdir(removed_path):
                count, size = self._count_recursive(removed_path)
                total_removed_count += count
                total_removed_size += size

        # Update removed tally
        if total_removed_count > 0:
            size_str = self._format_size(total_removed_size)
            self.removed_label.config(
                text=f"Removed: {total_removed_count:,} files ({size_str})",
                fg=ModernStyle.WARNING
            )
            self.clear_btn.config(fg=ModernStyle.TEXT_DIM)
        else:
            self.removed_label.config(text="No removed files", fg=ModernStyle.TEXT_MUTED)
            self.clear_btn.config(fg=ModernStyle.TEXT_DISABLED)

    def _count_recursive(self, path):
        """Count files and total size recursively."""
        count = 0
        size = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    count += 1
                    try:
                        size += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except (PermissionError, OSError):
            pass
        return count, size

    def _build_context_menu(self, item, path):
        """Build context menu for output folder items."""
        self.context_menu.add_command(
            label="Open in Explorer",
            command=lambda: os.startfile(path)
        )

        # Offer to add as source for refinement
        if path not in self.hub.source_folders:
            self.context_menu.add_command(
                label="Use as Source Folder",
                command=lambda: self._use_as_source(path)
            )

        # If this is a 'removed' folder, offer to clear it
        if os.path.basename(path) == 'removed':
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Clear this removed folder",
                command=lambda: self._clear_single_removed(path)
            )

    def _use_as_source(self, path):
        """Add an output folder as a source for refinement sorting."""
        if path not in self.hub.source_folders:
            self.hub.source_folders.append(path)
            self.hub.active_sources[path] = True
            self.hub.save_config()
            # Refresh the source panel
            if hasattr(self.hub, 'folder_panel'):
                self.hub.folder_panel.populate()
            toast_manager.show_success("Source Added",
                f"Added for refinement: {Path(path).name}/")

    def _clear_single_removed(self, path):
        """Clear a single removed folder."""
        if not SEND2TRASH_AVAILABLE:
            messagebox.showerror("Not Available",
                "send2trash module not installed.\nInstall with: pip install send2trash")
            return

        count, size = self._count_recursive(path)
        if count == 0:
            messagebox.showinfo("Empty", "This removed folder is already empty.")
            return

        size_str = self._format_size(size)
        if not messagebox.askyesno("Clear Removed",
                f"Send {count:,} files ({size_str}) to Recycle Bin?",
                icon='warning'):
            return

        self._trash_folder_contents(path)
        self.populate()

    def clear_all_removed(self):
        """Clear all removed folders across script dir and sources."""
        if not SEND2TRASH_AVAILABLE:
            messagebox.showerror("Not Available",
                "send2trash module not installed.\nInstall with: pip install send2trash")
            return

        # Gather all removed folders
        removed_paths = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_removed = os.path.join(script_dir, 'removed')
        if os.path.isdir(script_removed):
            removed_paths.append(script_removed)

        for source in self.hub.source_folders:
            src_removed = os.path.join(source, 'removed')
            if os.path.isdir(src_removed) and src_removed not in removed_paths:
                removed_paths.append(src_removed)

        if not removed_paths:
            messagebox.showinfo("Nothing to Clear", "No removed folders found.")
            return

        total_count = 0
        total_size = 0
        for rp in removed_paths:
            c, s = self._count_recursive(rp)
            total_count += c
            total_size += s

        if total_count == 0:
            messagebox.showinfo("Nothing to Clear", "All removed folders are empty.")
            return

        size_str = self._format_size(total_size)
        if not messagebox.askyesno("Clear All Removed",
                f"Send {total_count:,} files ({size_str}) from "
                f"{len(removed_paths)} folder(s) to Recycle Bin?",
                icon='warning'):
            return

        total_deleted = 0
        total_failed = 0
        for rp in removed_paths:
            deleted, failed = self._trash_folder_contents(rp)
            total_deleted += deleted
            total_failed += failed

        self.populate()

        if total_failed > 0:
            toast_manager.show_warning("Partial Clear",
                f"Sent {total_deleted} to Recycle Bin, {total_failed} failed")
        else:
            toast_manager.show_success("All Cleared",
                f"Sent {total_deleted} files to Recycle Bin")

    def _trash_folder_contents(self, folder_path):
        """Send all contents of a folder to Recycle Bin."""
        deleted = 0
        failed = 0
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                try:
                    send2trash(item_path)
                    deleted += 1
                except Exception as e:
                    failed += 1
                    print(f"Failed to trash {item_path}: {e}")
        except Exception as e:
            print(f"Error clearing {folder_path}: {e}")
        return deleted, failed

    def get_output_folders(self):
        """Get list of all output folder paths with content."""
        result = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        skip = ('__pycache__', 'models', 'tests', 'scripts', 'docs',
                'logs', 'data', 'archive', 'backups', 'screengrab',
                'prompt_backups', 'prompt_backup_emergency',
                'processed_batches', '.git', 'removed')
        try:
            for entry in os.scandir(script_dir):
                if not entry.is_dir() or entry.name.startswith('.'):
                    continue
                name = entry.name
                if name in skip:
                    continue
                if (name == 'output' or
                        name in ('1', '2', '3', 'auto_sorted') or
                        name.startswith('sorted_') or
                        name.startswith('tshirt_ready') or
                        name.startswith('batch_export') or
                        name.startswith('master_images')):
                    try:
                        if any(os.scandir(entry.path)):
                            result.append(entry.path)
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return result


class ImageToolkitHub(tk.Tk):
    """Main hub window for the image toolkit."""

    def __init__(self):
        super().__init__()

        self.title("Image Toolkit")
        self.configure(bg=ModernStyle.BG_DARK)

        # Single source of truth for all configuration
        from config_manager import ConfigManager
        self.config_manager = ConfigManager()
        self.folder_vars = {}

        # Apply styling
        ModernStyle.apply(self)

        # Initialize toast notifications
        self.toast = toast_manager.init(self)

        # Build UI
        self.setup_ui()

        # Chrome toggles. F9/F8 deliberately avoid F10 (Tk posts the menubar
        # the Sort panel attaches) and every key ImageSorter.activate() claims.
        self.bind("<F9>", self.toggle_sidebar)
        self.bind("<F8>", self.toggle_rail)

        # Auto-size window to fit content, then center (sets restored-window
        # geometry and minsize), then maximize so the full UI is visible on
        # startup without a manual resize.
        self.auto_size_window()
        self.state('zoomed')

        # Check for interrupted operations after a short delay (let UI settle)
        self.after(500, self.check_interrupted_operations)

    # Properties that delegate to ConfigManager so panels can still use
    # self.hub.source_folders and self.hub.active_sources transparently.
    @property
    def source_folders(self):
        return self.config_manager.config.get('source_folders', [])

    @source_folders.setter
    def source_folders(self, value):
        self.config_manager.config['source_folders'] = value

    @property
    def active_sources(self):
        return self.config_manager.config.get('active_sources', {})

    @active_sources.setter
    def active_sources(self, value):
        self.config_manager.config['active_sources'] = value

    def auto_size_window(self):
        """Auto-size window to fit content, then center on screen."""
        self.update_idletasks()

        # Get required size from content
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()

        # Add padding and set reasonable minimums
        width = max(1150, req_width + 60)
        height = max(800, req_height + 60)

        # Cap at 90% of screen size
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, int(screen_w * 0.9))
        height = min(height, int(screen_h * 0.9))

        # Set minimum size
        self.minsize(1050, 750)

        # Center on screen
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def create_settings_panel(self, parent):
        """Create the grid settings panel."""
        self.settings_config = self.config_manager

        # Settings card
        settings_card = tk.Frame(parent, bg=ModernStyle.BG_CARD,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        settings_card.pack(fill="x", pady=(15, 0))

        inner = tk.Frame(settings_card, bg=ModernStyle.BG_CARD, padx=15, pady=12)
        inner.pack(fill="x")

        # Header
        tk.Label(inner,
            text="Grid Settings",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(anchor="w", pady=(0, 10))

        # Grid rows
        rows_frame = tk.Frame(inner, bg=ModernStyle.BG_CARD)
        rows_frame.pack(fill="x", pady=(0, 8))

        rows_label = tk.Label(rows_frame,
            text="Grid rows:",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD
        )
        rows_label.pack(side="left")
        ModernStyle.create_tooltip(rows_label, get_tooltip('setting_grid_rows'))

        self.rows_var = tk.IntVar(value=self.settings_config.get_setting('num_rows', 3))
        rows_spin = tk.Spinbox(rows_frame,
            from_=1, to=10,
            textvariable=self.rows_var,
            width=4,
            font=ModernStyle.FONT_SMALL,
            bg=ModernStyle.BG_INPUT,
            fg=ModernStyle.TEXT,
            buttonbackground=ModernStyle.BG_CARD,
            command=self.save_settings
        )
        rows_spin.pack(side="right")
        rows_spin.bind('<Return>', lambda e: self.save_settings())
        rows_spin.bind('<FocusOut>', lambda e: self.save_settings())

        # Hover prompt delay - shown in seconds, stored in ui_preferences as ms.
        delay_frame = tk.Frame(inner, bg=ModernStyle.BG_CARD)
        delay_frame.pack(fill="x", pady=(0, 8))

        delay_label = tk.Label(delay_frame,
            text="Hover prompt delay (s):",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD
        )
        delay_label.pack(side="left")
        ModernStyle.create_tooltip(delay_label, get_tooltip('setting_hover_tip_delay'))

        self.hover_delay_var = tk.DoubleVar(value=self._hover_delay_seconds())
        delay_spin = tk.Spinbox(delay_frame,
            from_=0.0, to=10.0, increment=0.1, format="%.1f",
            textvariable=self.hover_delay_var,
            width=5,
            font=ModernStyle.FONT_SMALL,
            bg=ModernStyle.BG_INPUT,
            fg=ModernStyle.TEXT,
            buttonbackground=ModernStyle.BG_CARD,
            command=self.save_settings
        )
        delay_spin.pack(side="right")
        delay_spin.bind('<Return>', lambda e: self.save_settings())
        delay_spin.bind('<FocusOut>', lambda e: self.save_settings())

        # Checkboxes with tooltips
        # Note: handle_tag_files / hide_already_sorted live in ui_preferences
        # (that's where the grid sorter reads them), everything else is top-level.
        ui_prefs = self.settings_config.config.get('ui_preferences', {})
        self.random_var = tk.BooleanVar(value=self.settings_config.get_setting('random_order', False))
        self.copy_var = tk.BooleanVar(value=self.settings_config.get_setting('copy_instead_of_move', False))
        self.subfolders_var = tk.BooleanVar(value=self.settings_config.get_setting('include_subfolders', True))
        self.tagfiles_var = tk.BooleanVar(value=ui_prefs.get('handle_tag_files', True))
        self.hide_sorted_var = tk.BooleanVar(value=ui_prefs.get('hide_already_sorted', True))

        checkboxes = [
            (self.random_var, "Randomize order", 'setting_random_order'),
            (self.copy_var, "Copy mode (don't move)", 'setting_copy_mode'),
            (self.subfolders_var, "Include subfolders", 'setting_include_subfolders'),
            (self.tagfiles_var, "Handle .txt tag files", 'setting_handle_tag_files'),
            (self.hide_sorted_var, "Hide already-sorted", 'setting_hide_already_sorted'),
        ]

        for var, text, tooltip_key in checkboxes:
            cb = ttk.Checkbutton(inner,
                text=text,
                variable=var,
                style="TCheckbutton",
                command=self.save_settings
            )
            cb.pack(anchor="w", pady=2)
            ModernStyle.create_tooltip(cb, get_tooltip(tooltip_key))

    HOVER_DELAY_DEFAULT_MS = 1300

    def _hover_delay_seconds(self):
        """Stored hover dwell as seconds for the spinbox, clamped to 0-10s."""
        try:
            ms = int(self.settings_config.config.get('ui_preferences', {}).get(
                'hover_tip_delay_ms', self.HOVER_DELAY_DEFAULT_MS))
        except (TypeError, ValueError):
            ms = self.HOVER_DELAY_DEFAULT_MS
        return round(max(0, min(10000, ms)) / 1000.0, 1)

    def save_settings(self):
        """Save settings to config.

        Each key is written where its consumer (the grid sorter) reads it:
        - num_rows / random_order / copy_instead_of_move / include_subfolders are
          top-level basic settings (grid sorter reads via get_basic_settings()).
        - handle_tag_files / hide_already_sorted live in ui_preferences.
        Note: the top-level copy_instead_of_move (manual grid copy mode) is a
        separate setting from auto_sort_settings.copy_instead_of_move; they are
        intentionally not merged.
        """
        try:
            self.settings_config.update_basic_settings(
                num_rows=self.rows_var.get(),
                random_order=self.random_var.get(),
                copy_instead_of_move=self.copy_var.get(),
                include_subfolders=self.subfolders_var.get(),
            )
            if 'ui_preferences' not in self.settings_config.config:
                self.settings_config.config['ui_preferences'] = {}
            self.settings_config.config['ui_preferences']['handle_tag_files'] = self.tagfiles_var.get()
            self.settings_config.config['ui_preferences']['hide_already_sorted'] = self.hide_sorted_var.get()

            try:
                delay_ms = int(round(float(self.hover_delay_var.get()) * 1000))
            except (tk.TclError, TypeError, ValueError):
                delay_ms = self.HOVER_DELAY_DEFAULT_MS
            delay_ms = max(0, min(10000, delay_ms))
            self.settings_config.config['ui_preferences']['hover_tip_delay_ms'] = delay_ms
            # An already-open sorter has its own ConfigManager, so push the new
            # dwell straight at it instead of waiting for the panel to be rebuilt.
            sorter = self.panels.get('sort') if hasattr(self, 'panels') else None
            if sorter is not None and hasattr(sorter, 'apply_hover_tip_delay'):
                sorter.apply_hover_tip_delay(delay_ms)

            self.settings_config.save_config()
        except Exception as e:
            print(f"Error saving settings: {e}")

    def save_config(self):
        """Save configuration through ConfigManager (single source of truth)."""
        self.config_manager.save_config()

    def reload_config_from_disk(self):
        """Reload config from disk and sync Hub UI vars to reflect any changes made by subprocesses."""
        self.config_manager.config = self.config_manager.load_config()
        self.config_manager.setup_folders()
        # Sync UI vars so they reflect what was saved (e.g. by the setup dialog inside the sorter)
        if hasattr(self, 'rows_var'):
            self.rows_var.set(self.config_manager.get_setting('num_rows', 3))
        if hasattr(self, 'random_var'):
            self.random_var.set(self.config_manager.get_setting('random_order', False))
        if hasattr(self, 'copy_var'):
            self.copy_var.set(self.config_manager.get_setting('copy_instead_of_move', False))
        if hasattr(self, 'subfolders_var'):
            self.subfolders_var.set(self.config_manager.get_setting('include_subfolders', True))
        if hasattr(self, 'tagfiles_var'):
            self.tagfiles_var.set(self.config_manager.get_setting('handle_tag_files', True))
        if hasattr(self, 'hide_sorted_var'):
            self.hide_sorted_var.set(self.config_manager.get_setting('hide_already_sorted', True))
        if hasattr(self, 'hover_delay_var'):
            self.hover_delay_var.set(self._hover_delay_seconds())

    def toggle_folder(self, folder, active):
        """Toggle a folder's active state."""
        self.active_sources[folder] = active
        self.save_config()

    def get_active_folders(self):
        """Get list of currently active source folders."""
        return [f for f in self.source_folders if self.active_sources.get(f, True)]

    def setup_ui(self):
        """Build the single-window hub shell: sidebar + content + rail + status bar."""
        # Registered content panels, keyed by name. show_panel() raises one.
        self.panels = {}
        self.sidebar_buttons = {}
        self._current_panel = None

        # Chrome collapse state. _pre_sort_panel_state is non-None only while
        # the Sort panel is up, holding the (sidebar, rail) pair to restore.
        self._sidebar_collapsed = False
        self._rail_collapsed = False
        self._pre_sort_panel_state = None

        # Root layout: a body row (sidebar | content | rail) above a status bar.
        outer = tk.Frame(self, bg=ModernStyle.BG_DARK)
        outer.pack(fill="both", expand=True)

        body = tk.Frame(outer, bg=ModernStyle.BG_DARK)
        body.pack(fill="both", expand=True)

        # --- Left sidebar --------------------------------------------------
        self._build_sidebar(body)

        # --- Middle content container (swappable panels) -------------------
        self.content = tk.Frame(body, bg=ModernStyle.BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)

        # --- Right rail (persistent folder trees) --------------------------
        rail = tk.Frame(body, bg=ModernStyle.BG_DARK, width=340)
        rail.pack(side="right", fill="y", padx=(0, 20), pady=20)
        rail.pack_propagate(False)
        self.rail = rail

        # Thin header above the trees carrying the collapse chevron.
        rail_header = tk.Frame(rail, bg=ModernStyle.BG_DARK)
        rail_header.pack(fill="x", pady=(0, 4))
        rail_collapse = tk.Label(rail_header,
            text="»",
            font=("Segoe UI", 12, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK,
            cursor="hand2",
            padx=6
        )
        rail_collapse.pack(side="right")
        ModernStyle.create_tooltip(rail_collapse, "Collapse folder panel (F8)")
        rail_collapse.bind("<Button-1>", lambda e: self.toggle_rail())
        rail_collapse.bind("<Enter>",
            lambda e: rail_collapse.configure(fg=ModernStyle.ACCENT), add="+")
        rail_collapse.bind("<Leave>",
            lambda e: rail_collapse.configure(fg=ModernStyle.TEXT_MUTED), add="+")

        self.folder_panel = SourceFolderPanel(rail, self)
        self.folder_panel.pack(fill="both", expand=True)
        self.folder_panel.configure(highlightthickness=1, highlightbackground=ModernStyle.BORDER)

        self.output_panel = OutputFolderPanel(rail, self)
        self.output_panel.pack(fill="both", expand=True, pady=(12, 0))
        self.output_panel.configure(highlightthickness=1, highlightbackground=ModernStyle.BORDER)

        # --- Collapsed stubs (built now, packed only while collapsed) ------
        # The sidebar stub must be anchored before self.content: self.content
        # is packed side="left" with expand=True, so a later side="left" pack
        # would land to its right instead of at the window edge.
        self.sidebar_stub = self._build_stub(body, "»", self.toggle_sidebar,
                                             "Show sidebar (F9)")
        self.rail_stub = self._build_stub(body, "«", self.toggle_rail,
                                          "Show folder panel (F8)")

        # --- Bottom status bar --------------------------------------------
        self._build_status_bar(outer)

        # --- Build & register content panels ------------------------------
        self.panels['home'] = self._build_home_panel(self.content)
        self.panels['config'] = self._build_config_panel(self.content)

        self.show_panel('home')

        # Restore saved collapse state before auto_size_window() runs, so a
        # collapsed startup doesn't get measured at full width.
        self._set_sidebar_collapsed(
            bool(self.config_manager.get_setting('sidebar_collapsed', False)),
            persist=False)
        self._set_rail_collapsed(
            bool(self.config_manager.get_setting('rail_collapsed', False)),
            persist=False)

    def _build_stub(self, parent, chevron, command, tooltip):
        """Build (but don't pack) a thin reopen strip for a collapsed panel."""
        stub = tk.Frame(parent, bg=ModernStyle.BG_CARD, width=22,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        stub.pack_propagate(False)

        lbl = tk.Label(stub,
            text=chevron,
            font=("Segoe UI", 11, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        lbl.pack(fill="x", pady=(14, 0))
        ModernStyle.create_tooltip(lbl, tooltip)
        for w in (stub, lbl):
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", lambda e: lbl.configure(fg=ModernStyle.ACCENT), add="+")
            w.bind("<Leave>", lambda e: lbl.configure(fg=ModernStyle.TEXT_MUTED), add="+")
        stub.configure(cursor="hand2")
        return stub

    def _build_sidebar(self, parent):
        """Build the left navigation sidebar."""
        sidebar = tk.Frame(parent, bg=ModernStyle.BG_CARD, width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        # Title header
        title_frame = tk.Frame(sidebar, bg=ModernStyle.BG_CARD)
        title_frame.pack(fill="x", padx=16, pady=(20, 24))
        tk.Label(title_frame,
            text="Image Toolkit",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(side="left")
        tk.Label(title_frame,
            text="v3.0",
            font=ModernStyle.FONT_TINY,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD
        ).pack(side="left", padx=(6, 0), pady=(4, 0))

        # Nav entries: (name, icon, label, command, is_panel)
        # Panel entries switch the middle content; action entries launch tools.
        nav = [
            ('home',   "🏠", "Home",    lambda: self.show_panel('home'),  True),
            ('sort',   "🖼️", "Sort",    self.open_sort_panel,             True),
            ('rank',   "🏆", "Rank",    self.launch_image_ranker,         False),
            ('auto',   "🏷️", "Auto",    self.launch_auto_sort,            False),
            ('export', "📤", "Export",  self.launch_batch_export,         False),
            ('config', "⚙️", "Config",  lambda: self.show_panel('config'), True),
        ]

        # Collapse affordance sits at the bottom so it stays put as nav grows.
        collapse_row = tk.Frame(sidebar, bg=ModernStyle.BG_CARD, cursor="hand2")
        collapse_row.pack(side="bottom", fill="x")
        collapse_lbl = tk.Label(collapse_row,
            text="«  Collapse",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        collapse_lbl.pack(fill="x", padx=14, pady=10)
        # Tooltip first: create_tooltip() binds <Enter>/<Leave> without add="+",
        # so it would clobber the hover styling if attached afterwards.
        ModernStyle.create_tooltip(collapse_lbl, "Collapse sidebar (F9)")
        for w in (collapse_row, collapse_lbl):
            w.bind("<Button-1>", lambda e: self.toggle_sidebar())
            w.bind("<Enter>", lambda e: (collapse_row.configure(bg=ModernStyle.BG_HOVER),
                                         collapse_lbl.configure(bg=ModernStyle.BG_HOVER,
                                                                fg=ModernStyle.TEXT)),
                   add="+")
            w.bind("<Leave>", lambda e: (collapse_row.configure(bg=ModernStyle.BG_CARD),
                                         collapse_lbl.configure(bg=ModernStyle.BG_CARD,
                                                                fg=ModernStyle.TEXT_MUTED)),
                   add="+")

        for name, icon, label, command, is_panel in nav:
            btn = SidebarButton(sidebar, icon, label, command)
            btn.pack(fill="x")
            if is_panel:
                self.sidebar_buttons[name] = btn

        return sidebar

    def _build_status_bar(self, parent):
        """Build the bottom status bar with a set_status() target label."""
        bar = tk.Frame(parent, bg=ModernStyle.BG_CARD,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        bar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(bar,
            text="Ready",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            anchor="w"
        )
        self.status_label.pack(side="left", padx=14, pady=6)

    def set_status(self, text):
        """Update the bottom status bar text."""
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.config(text=text)

    # ------------------------------------------------------------------
    # Collapsible chrome (left sidebar / right folder rail)
    # ------------------------------------------------------------------

    def _save_ui_pref(self, key, value):
        """Persist a single ui_preferences key."""
        try:
            prefs = self.config_manager.config.setdefault('ui_preferences', {})
            prefs[key] = value
            self.config_manager.save_config()
        except Exception as e:
            print(f"Error saving UI preference {key}: {e}")

    def _set_sidebar_collapsed(self, collapsed, persist=True):
        """Swap the left sidebar for its thin stub (or back)."""
        collapsed = bool(collapsed)
        if collapsed == self._sidebar_collapsed:
            return
        self._sidebar_collapsed = collapsed
        # before=self.content keeps the stub/sidebar at the window edge:
        # self.content is packed side="left" with expand=True, so anything
        # re-packed after it would land on its right.
        if collapsed:
            self.sidebar.pack_forget()
            self.sidebar_stub.pack(side="left", fill="y", before=self.content)
        else:
            self.sidebar_stub.pack_forget()
            self.sidebar.pack(side="left", fill="y", before=self.content)
        if persist:
            self._save_ui_pref('sidebar_collapsed', collapsed)

    def _set_rail_collapsed(self, collapsed, persist=True):
        """Swap the right folder rail for its thin stub (or back)."""
        collapsed = bool(collapsed)
        if collapsed == self._rail_collapsed:
            return
        self._rail_collapsed = collapsed
        if collapsed:
            self.rail.pack_forget()
            self.rail_stub.pack(side="right", fill="y")
        else:
            self.rail_stub.pack_forget()
            # Same pack options as setup_ui() so the rail returns at its
            # original width and padding.
            self.rail.pack(side="right", fill="y", padx=(0, 20), pady=20)
        if persist:
            self._save_ui_pref('rail_collapsed', collapsed)

    def toggle_sidebar(self, event=None):
        """Collapse/expand the left sidebar (button or F9)."""
        target = not self._sidebar_collapsed
        in_sort = self._pre_sort_panel_state is not None
        self._set_sidebar_collapsed(target, persist=not in_sort)
        if in_sort:
            # Track the choice in the sort stash instead of the saved config,
            # so a temporary tweak never rewrites the Home preference.
            self._pre_sort_panel_state = (target, self._pre_sort_panel_state[1])
        return "break"

    def toggle_rail(self, event=None):
        """Collapse/expand the right folder rail (button or F8)."""
        target = not self._rail_collapsed
        in_sort = self._pre_sort_panel_state is not None
        self._set_rail_collapsed(target, persist=not in_sort)
        if in_sort:
            self._pre_sort_panel_state = (self._pre_sort_panel_state[0], target)
        return "break"

    def _collapse_panels_for_sort(self):
        """Hide both chrome panels while the Sort grid is up."""
        if self._pre_sort_panel_state is not None:
            return  # already in sort
        self._pre_sort_panel_state = (self._sidebar_collapsed, self._rail_collapsed)
        self._set_sidebar_collapsed(True, persist=False)
        self._set_rail_collapsed(True, persist=False)

    def _restore_panels_after_sort(self):
        """Put the chrome panels back the way they were before Sort."""
        state = self._pre_sort_panel_state
        self._pre_sort_panel_state = None
        if state is None:
            return
        self._set_sidebar_collapsed(state[0], persist=False)
        self._set_rail_collapsed(state[1], persist=False)

    def show_panel(self, name):
        """Raise exactly one registered content panel.

        The embedded Sort panel is special: switching away from a live Sort
        panel destroys the ImageSorter frame (+ gc) first, mirroring the memory
        isolation the old subprocess provided for large-image collections.
        """
        # Tear down a live Sort panel when navigating elsewhere.
        if (name != 'sort'
                and 'sort' in self.panels
                and self._current_panel is self.panels.get('sort')):
            self._close_sort_panel_internal()
            self._restore_panels_after_sort()

        panel = self.panels.get(name)
        if panel is None:
            return

        # The grid needs every pixel it can get: hide both chrome panels for
        # the duration of the Sort panel, remembering what to restore. This
        # happens BEFORE packing so the sorter's first <Configure> already
        # reports the widened frame and sizes correctly on first measurement,
        # instead of sizing narrow and immediately paying for a reflow reload.
        if name == 'sort':
            self._collapse_panels_for_sort()

        if self._current_panel is not None and self._current_panel is not panel:
            self._current_panel.pack_forget()
        panel.pack(fill="both", expand=True)
        self._current_panel = panel

        # Update sidebar active state for panel entries.
        for btn_name, btn in self.sidebar_buttons.items():
            btn.set_active(btn_name == name)

    def _build_config_panel(self, parent):
        """Build the Config panel: relocated grid settings + quick links."""
        panel = tk.Frame(parent, bg=ModernStyle.BG_DARK, padx=30, pady=25)

        tk.Label(panel,
            text="Configuration",
            font=ModernStyle.FONT_TITLE,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(panel,
            text="Grid sorter settings and tool configuration.",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 16))

        # Constrain settings width so the card doesn't stretch the whole panel.
        settings_holder = tk.Frame(panel, bg=ModernStyle.BG_DARK, width=460)
        settings_holder.pack(anchor="w", fill="x")
        self.create_settings_panel(settings_holder)

        # Quick links
        links_frame = tk.Frame(panel, bg=ModernStyle.BG_DARK)
        links_frame.pack(anchor="w", fill="x", pady=(20, 0))

        term_link = tk.Label(links_frame,
            text="⚙️ Term Manager",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_DARK,
            cursor="hand2"
        )
        term_link.pack(anchor="w")
        term_link.bind("<Button-1>", lambda e: self.launch_term_manager())
        term_link.bind("<Enter>", lambda e: term_link.configure(fg=ModernStyle.ACCENT))
        term_link.bind("<Leave>", lambda e: term_link.configure(fg=ModernStyle.TEXT_DIM))

        return panel

    def _build_home_panel(self, parent):
        """Build the Home panel: scrollable tool cards (all tools)."""
        panel = tk.Frame(parent, bg=ModernStyle.BG_DARK, padx=30, pady=25)

        left_canvas = tk.Canvas(panel, bg=ModernStyle.BG_DARK,
            highlightthickness=0, bd=0)
        left_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=left_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        left_canvas.configure(yscrollcommand=scrollbar.set)

        left = tk.Frame(left_canvas, bg=ModernStyle.BG_DARK)
        canvas_window = left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _on_left_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        left.bind("<Configure>", _on_left_configure)

        def _on_canvas_configure(event):
            left_canvas.itemconfig(canvas_window, width=event.width)
        left_canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel scrolling (scoped to canvas area)
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")

        left_canvas.bind("<Enter>", _bind_mousewheel)
        left_canvas.bind("<Leave>", _unbind_mousewheel)

        # Section: Sorting Tools
        tk.Label(left,
            text="SORTING",
            font=("Segoe UI", 10, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w")
        tk.Label(left,
            text="Organize images into folders manually or automatically",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 10))

        # Tool cards grid
        sort_grid = tk.Frame(left, bg=ModernStyle.BG_DARK)
        sort_grid.pack(fill="x", pady=(0, 20))

        # Row 1
        manual_card = ToolCard(sort_grid,
            icon="🖼️",
            title="Manual Grid Sorter",
            description="Browse images in a visual grid and sort into 3 category folders "
                        "using keyboard shortcuts or mouse clicks. No setup needed - "
                        "just add source folders and go.",
            command=self.open_sort_panel,
            status_text="Ready - no prerequisites",
            status_color=ModernStyle.SUCCESS
        )
        manual_card.grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(manual_card, get_tooltip('card_manual_sorter'))

        auto_sort_card = ToolCard(sort_grid,
            icon="🏷️",
            title="Auto-Sort by Tags",
            description="Automatically match images to folders using search terms. "
                        "Searches embedded AI prompts and .txt tag files. "
                        "Works without tagging if images have prompts.",
            command=self.launch_auto_sort,
            status_text="Needs: search terms (Term Manager)",
            status_color=ModernStyle.TEXT_MUTED
        )
        auto_sort_card.grid(row=0, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(auto_sort_card, get_tooltip('card_auto_sort'))

        # Row 2
        visual_card = ToolCard(sort_grid,
            icon="👁️",
            title="Visual Classification",
            description="AI-powered sorting by shot type (closeup, full body), "
                        "person count, or content rating. Analyzes images on-the-fly "
                        "using the WD14 model - no pre-tagging required.",
            command=self.launch_visual_sort,
            status_text="Uses WD14 model at runtime",
            status_color=ModernStyle.TEXT_MUTED
        )
        visual_card.grid(row=1, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(visual_card, get_tooltip('card_visual_sort'))

        tshirt_card = ToolCard(sort_grid,
            icon="👕",
            title="T-Shirt Ready Finder",
            description="Find images with simple or solid backgrounds suitable "
                        "for print-on-demand products. Identifies centered subjects "
                        "against clean backgrounds.",
            command=self.launch_tshirt_finder,
            status_text="Uses WD14 model at runtime",
            status_color=ModernStyle.TEXT_MUTED
        )
        tshirt_card.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(tshirt_card, get_tooltip('card_tshirt_finder'))

        trash_card = ToolCard(sort_grid,
            icon="🗑️",
            title="Take Out the Trash",
            description="Review and delete contents of folders marked with the "
                        "'trash' role. Set category roles in Settings.",
            command=self.launch_trash_cleanup,
            status_text="Deletes trash-role folder contents",
            status_color=ModernStyle.TEXT_MUTED
        )
        trash_card.grid(row=2, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")

        sort_grid.columnconfigure(0, weight=1)
        sort_grid.columnconfigure(1, weight=1)

        # Section: Ranking & Quality
        tk.Label(left,
            text="RANKING",
            font=("Segoe UI", 10, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w")
        tk.Label(left,
            text="Find your best images through side-by-side comparison",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w", pady=(0, 10))

        rank_grid = tk.Frame(left, bg=ModernStyle.BG_DARK)
        rank_grid.pack(fill="x", pady=(0, 20))

        ranker_card = ToolCard(rank_grid,
            icon="🏆",
            title="Image Ranker",
            description="Compare images side-by-side to find your best work. "
                        "Uses the OpenSkill algorithm for smart pair selection and "
                        "transitive inference. Typically needs ~1 comparison per image.",
            command=self.launch_image_ranker,
            status_text="Ready - loads its own folders",
            status_color=ModernStyle.SUCCESS
        )
        ranker_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(ranker_card, get_tooltip('card_image_ranker'))

        rank_grid.columnconfigure(0, weight=1)
        rank_grid.columnconfigure(1, weight=1)

        # Section: Tagging & Data
        tk.Label(left,
            text="TAGGING & DATA",
            font=("Segoe UI", 10, "bold"),
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        ).pack(anchor="w")
        tk.Label(left,
            text="Generate tags, build databases, and export by query. "
                 "Tagging enriches auto-sort and enables batch export.",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK,
            wraplength=600,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        data_grid = tk.Frame(left, bg=ModernStyle.BG_DARK)
        data_grid.pack(fill="x")

        # Row 1
        auto_tag_card = ToolCard(data_grid,
            icon="🤖",
            title="Auto-Tag Images",
            description="Run the WD14 AI model to generate descriptive tags and "
                        "save them as .txt files alongside each image. Original "
                        "images are never modified. Run this to improve auto-sort "
                        "accuracy or enable batch export.",
            command=self.launch_auto_tag,
            status_text="Writes .txt files only - images untouched",
            status_color=ModernStyle.INFO
        )
        auto_tag_card.grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(auto_tag_card, get_tooltip('card_auto_tag'))

        batch_export_card = ToolCard(data_grid,
            icon="📤",
            title="Batch Export",
            description="Search your tagged collection using queries and export "
                        "matching images to a folder. Useful for curating sets "
                        "for specific workflows like WAN i2v.",
            command=self.launch_batch_export,
            status_text="Needs: tag database (run Auto-Tag first)",
            status_color=ModernStyle.WARNING
        )
        batch_export_card.grid(row=0, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")
        ModernStyle.create_tooltip(batch_export_card, get_tooltip('card_batch_export'))

        data_grid.columnconfigure(0, weight=1)
        data_grid.columnconfigure(1, weight=1)

        # Footer - workflow tip
        footer = tk.Frame(left, bg=ModernStyle.BG_DARK)
        footer.pack(fill="x", pady=(20, 0))

        tk.Label(footer,
            text="Typical workflow:  Manual Sort or Auto-Sort  -->  Auto-Tag for richer data  -->  Batch Export or Tag Database",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK,
            wraplength=640,
            justify="left"
        ).pack(side="left")

        return panel

    # Tool launchers
    def open_sort_panel(self):
        """Build and show the manual grid sorter embedded as a content panel.

        A FRESH ImageSorter frame is constructed each time and destroyed on
        leave (see _close_sort_panel_internal) so background threads and
        large-image memory don't accumulate across sessions.
        """
        # Already open -> just raise it.
        if 'sort' in self.panels:
            self.show_panel('sort')
            return

        try:
            from image_sorter_enhanced import ImageSorter

            # Make sure any pending config edits are on disk, then read the
            # basic grid settings the sorter needs.
            self.config_manager.save_config()
            settings = self.config_manager.get_basic_settings()
            active = self.get_active_folders()
            folder = active[0] if active else ''

            sorter = ImageSorter(
                self.content,
                self,  # hub
                folder,
                settings['num_rows'],
                settings['random_order'],
                settings['copy_instead_of_move'],
            )
            self.panels['sort'] = sorter
            self.show_panel('sort')
            sorter.activate()
            self.set_status("Manual grid sorter")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to open grid sorter:\n{e}")

    def close_sort_panel(self):
        """Tear down the Sort panel and return Home.

        Called by the embedded sorter's Exit/Escape. The actual teardown runs
        inside show_panel() via _close_sort_panel_internal().
        """
        self.show_panel('home')

    def _close_sort_panel_internal(self):
        """Deactivate + destroy the embedded ImageSorter frame and free memory."""
        sorter = self.panels.pop('sort', None)
        if sorter is None:
            return
        try:
            sorter.deactivate()
        except Exception as e:
            print(f"Error deactivating sort panel: {e}")
        try:
            sorter.pack_forget()
            sorter.destroy()
        except tk.TclError:
            pass
        if self._current_panel is sorter:
            self._current_panel = None
        # Pick up any settings the sorter's setup dialog may have changed.
        try:
            self.reload_config_from_disk()
        except Exception:
            pass
        self.set_status("Ready")
        gc.collect()

    # Backwards-compatible alias (older references / external callers).
    def launch_grid_sorter(self):
        """Alias for open_sort_panel (kept for compatibility)."""
        self.open_sort_panel()

    def launch_auto_sort(self):
        """Launch auto-sort tool."""
        try:
            active = self.get_active_folders()
            if not active:
                messagebox.showwarning("No Folders", "Please add and enable at least one source folder.")
                return

            from auto_sorter import AutoSorter
            from auto_sort_progress import AutoSortProgressDialog
            from auto_sort_confirm import show_auto_sort_confirm

            config_manager = self.config_manager

            # Show confirmation first (before scanning - fast)
            terms = config_manager.get_auto_sort_terms()
            enabled_terms = [t for t in terms if t.get('enabled', True)]

            if not enabled_terms:
                messagebox.showwarning("No Terms", "No auto-sort terms configured. Open Term Manager to add some.")
                return

            result = show_auto_sort_confirm(self, config_manager, len(active), enabled_terms)

            if result:
                # Create progress dialog
                progress_dialog = AutoSortProgressDialog(self, "Auto-Sort by Tags")
                progress_dialog.enable_pause_resume()

                def progress_callback(current, total, current_file="", **stats):
                    try:
                        if progress_dialog.winfo_exists():
                            progress_dialog.update_progress(current, total, current_file, **stats)
                    except RuntimeError:
                        pass

                # Create sorter with progress callback
                sorter = AutoSorter(config_manager, progress_callback=progress_callback)

                # Wire pause/cancel from progress dialog to sorter
                original_toggle = progress_dialog.toggle_pause
                def patched_toggle():
                    original_toggle()
                    if progress_dialog.paused:
                        sorter.pause()
                    else:
                        sorter.resume()
                progress_dialog.toggle_pause = patched_toggle

                original_cancel = progress_dialog.cancel_operation
                def patched_cancel():
                    sorter.cancel()
                    original_cancel()
                progress_dialog.cancel_operation = patched_cancel

                def run_sort():
                    try:
                        # Scan for image files (this runs on the thread, not UI)
                        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
                        image_files = []
                        progress_callback(0, 0, "Scanning folders for images...")

                        for folder in active:
                            if not os.path.isdir(folder):
                                continue
                            include_subs = config_manager.get_setting('include_subfolders', True)
                            if include_subs:
                                for root, dirs, files in os.walk(folder):
                                    for f in files:
                                        if os.path.splitext(f)[1].lower() in image_extensions:
                                            image_files.append(os.path.join(root, f))
                            else:
                                for f in os.listdir(folder):
                                    if os.path.splitext(f)[1].lower() in image_extensions:
                                        image_files.append(os.path.join(folder, f))

                        if not image_files:
                            if progress_dialog.winfo_exists():
                                progress_dialog.after(0, lambda: progress_dialog.operation_completed(
                                    success=False,
                                    message="No images found in the selected folders."
                                ))
                            return

                        progress_callback(0, len(image_files), f"Found {len(image_files):,} images, starting sort...")

                        results = sorter.sort_by_metadata(image_files)

                        # Update output panel after sort
                        try:
                            self.after(0, lambda: self.output_panel.populate())
                        except RuntimeError:
                            pass

                        if progress_dialog.winfo_exists():
                            progress_dialog.after(0, lambda: progress_dialog.operation_completed(
                                success=True,
                                stats=results
                            ))
                    except Exception as e:
                        if progress_dialog.winfo_exists():
                            progress_dialog.after(0, lambda: progress_dialog.operation_completed(
                                success=False,
                                message=str(e)
                            ))

                thread = threading.Thread(target=run_sort, daemon=True)
                thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch auto-sort:\n{e}")

    def launch_visual_sort(self):
        """Launch visual classification tool."""
        try:
            active = self.get_active_folders()
            if not active:
                messagebox.showwarning("No Folders", "Please add and enable at least one source folder.")
                return

            from visual_sort_dialog import show_visual_sort_dialog

            config_manager = self.config_manager

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

            show_background_sort_dialog(self, self.config_manager)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch T-shirt finder:\n{e}")

    def launch_trash_cleanup(self):
        """Launch the trash cleanup dialog."""
        try:
            from trash_cleanup_dialog import TrashCleanupDialog
            TrashCleanupDialog(self, self.config_manager)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch trash cleanup:\n{e}")

    def launch_batch_export(self):
        """Launch batch export tool."""
        try:
            from batch_export_dialog import BatchExportDialog
            BatchExportDialog(self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch batch export:\n{e}")

    def launch_auto_tag(self):
        """Launch auto-tag dialog."""
        try:
            from auto_tag_dialog import show_auto_tag_dialog

            # Get active source folders and output folders
            source_folders = self.get_active_folders()
            output_folders = self.output_panel.get_output_folders() if hasattr(self, 'output_panel') else []

            show_auto_tag_dialog(self, source_folders, output_folders)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch auto-tag:\n{e}")

    def launch_term_manager(self):
        """Launch term manager."""
        try:
            from term_manager import TermManagerDialog

            TermManagerDialog(self, self.config_manager)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch term manager:\n{e}")

    def launch_image_ranker(self):
        """Launch the image ranker tool."""
        try:
            from image_ranker_dialog import ImageRankerDialog

            ImageRankerDialog(self, self.config_manager)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch image ranker:\n{e}")

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
