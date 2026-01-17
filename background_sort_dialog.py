"""
Background Sort Dialog for T-Shirt/POD Image Selection

Provides a modern UI for finding and copying images with simple, removable backgrounds.

Author: Claude Code Implementation
Version: 1.1 - Updated with modern styling
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
from datetime import datetime
from pathlib import Path

from background_classifier import (
    BackgroundClassifier, BackgroundType, BackgroundClassification,
    copy_suitable_images
)
from ui_theme import Theme as ModernStyle


class BackgroundSortDialog(tk.Toplevel):
    """Dialog for finding and copying t-shirt-suitable images."""

    def __init__(self, parent, config_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.classifier = None
        self.source_folders = []
        self.suitable_images = []
        self.all_classifications = []
        self.is_scanning = False
        self.is_copying = False
        self.cancel_requested = False

        # Window setup
        self.title("T-Shirt Ready Image Finder")
        self.geometry("1000x850")
        self.minsize(900, 750)
        self.configure(bg=ModernStyle.BG_DARK)

        # Apply styling
        ModernStyle.apply(self)

        self.setup_ui()
        self.setup_modal()

    def setup_ui(self):
        """Create the dialog UI."""
        # Main container
        main = tk.Frame(self, bg=ModernStyle.BG_DARK, padx=25, pady=20)
        main.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(main, bg=ModernStyle.BG_DARK)
        header.pack(fill="x", pady=(0, 20))

        tk.Label(header,
            text="👕 T-Shirt Ready Finder",
            font=ModernStyle.FONT_TITLE,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_DARK
        ).pack(side="left")

        tk.Label(header,
            text="Find images with simple, removable backgrounds",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_DARK
        ).pack(side="left", padx=(15, 0), pady=(8, 0))

        # Content - two columns
        content = tk.Frame(main, bg=ModernStyle.BG_DARK)
        content.pack(fill="both", expand=True)

        # Left column - folders and options
        left = tk.Frame(content, bg=ModernStyle.BG_DARK)
        left.pack(side="left", fill="both", expand=True)

        # Source folders card
        folders_card = tk.Frame(left, bg=ModernStyle.BG_CARD,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        folders_card.pack(fill="x", pady=(0, 15))

        folders_inner = tk.Frame(folders_card, bg=ModernStyle.BG_CARD, padx=15, pady=12)
        folders_inner.pack(fill="x")

        # Header row
        header_row = tk.Frame(folders_inner, bg=ModernStyle.BG_CARD)
        header_row.pack(fill="x", pady=(0, 10))

        tk.Label(header_row,
            text="Source Folders",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(side="left")

        # Buttons
        btn_frame = tk.Frame(header_row, bg=ModernStyle.BG_CARD)
        btn_frame.pack(side="right")

        add_btn = tk.Label(btn_frame,
            text="+ Add",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD,
            cursor="hand2"
        )
        add_btn.pack(side="left", padx=(0, 10))
        add_btn.bind("<Button-1>", lambda e: self._add_folder())
        add_btn.bind("<Enter>", lambda e: add_btn.configure(fg=ModernStyle.ACCENT_HOVER))
        add_btn.bind("<Leave>", lambda e: add_btn.configure(fg=ModernStyle.ACCENT))

        if self.config_manager:
            use_btn = tk.Label(btn_frame,
                text="Use Global",
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.ACCENT,
                bg=ModernStyle.BG_CARD,
                cursor="hand2"
            )
            use_btn.pack(side="left")
            use_btn.bind("<Button-1>", lambda e: self._use_config_sources())
            use_btn.bind("<Enter>", lambda e: use_btn.configure(fg=ModernStyle.ACCENT_HOVER))
            use_btn.bind("<Leave>", lambda e: use_btn.configure(fg=ModernStyle.ACCENT))

        # Folder list with scrollable container (fixed height)
        list_container = tk.Frame(folders_inner, bg=ModernStyle.BG_CARD, height=120)
        list_container.pack(fill="x")
        list_container.pack_propagate(False)  # Prevent expansion

        # Canvas for scrolling
        self.folder_canvas = tk.Canvas(list_container, bg=ModernStyle.BG_CARD,
            highlightthickness=0, height=120)
        scrollbar = tk.Scrollbar(list_container, orient="vertical",
            command=self.folder_canvas.yview)

        self.folder_list_frame = tk.Frame(self.folder_canvas, bg=ModernStyle.BG_CARD)

        self.folder_canvas.create_window((0, 0), window=self.folder_list_frame, anchor="nw")
        self.folder_canvas.configure(yscrollcommand=scrollbar.set)

        self.folder_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Update scroll region when folder list changes
        self.folder_list_frame.bind("<Configure>",
            lambda e: self.folder_canvas.configure(scrollregion=self.folder_canvas.bbox("all")))

        self._refresh_folder_list()

        # Options card
        options_card = tk.Frame(left, bg=ModernStyle.BG_CARD,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        options_card.pack(fill="x", pady=(0, 15))

        options_inner = tk.Frame(options_card, bg=ModernStyle.BG_CARD, padx=15, pady=12)
        options_inner.pack(fill="x")

        tk.Label(options_inner,
            text="Options",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(anchor="w", pady=(0, 10))

        # Threshold
        thresh_frame = tk.Frame(options_inner, bg=ModernStyle.BG_CARD)
        thresh_frame.pack(fill="x", pady=(0, 8))

        tk.Label(thresh_frame,
            text="Detection confidence:",
            font=ModernStyle.FONT_BODY,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD
        ).pack(side="left")

        self.threshold_var = tk.DoubleVar(value=0.35)
        self.threshold_label = tk.Label(thresh_frame,
            text="0.35",
            font=ModernStyle.FONT_BODY,
            fg=ModernStyle.ACCENT,
            bg=ModernStyle.BG_CARD,
            width=5
        )
        self.threshold_label.pack(side="right")

        thresh_scale = tk.Scale(thresh_frame,
            from_=0.1, to=0.7,
            resolution=0.05,
            orient="horizontal",
            variable=self.threshold_var,
            showvalue=False,
            bg=ModernStyle.BG_CARD,
            fg=ModernStyle.TEXT,
            highlightthickness=0,
            troughcolor=ModernStyle.BG_DARK,
            activebackground=ModernStyle.ACCENT,
            command=self._update_threshold
        )
        thresh_scale.pack(side="right", padx=(10, 5))

        # Include gradients checkbox
        self.include_gradient_var = tk.BooleanVar(value=True)
        gradient_cb = tk.Checkbutton(options_inner,
            text="Include gradient backgrounds (borderline cases)",
            variable=self.include_gradient_var,
            font=ModernStyle.FONT_BODY,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            activebackground=ModernStyle.BG_CARD,
            activeforeground=ModernStyle.TEXT,
            selectcolor=ModernStyle.BG_DARK
        )
        gradient_cb.pack(anchor="w")

        # Results card
        results_card = tk.Frame(left, bg=ModernStyle.BG_CARD,
            highlightthickness=1, highlightbackground=ModernStyle.BORDER)
        results_card.pack(fill="both", expand=True)

        results_inner = tk.Frame(results_card, bg=ModernStyle.BG_CARD, padx=15, pady=12)
        results_inner.pack(fill="both", expand=True)

        tk.Label(results_inner,
            text="Results",
            font=ModernStyle.FONT_HEADING,
            fg=ModernStyle.TEXT,
            bg=ModernStyle.BG_CARD
        ).pack(anchor="w", pady=(0, 10))

        # Stats label
        self.stats_label = tk.Label(results_inner,
            text="Add folders and click 'Scan' to find t-shirt ready images.",
            font=ModernStyle.FONT_BODY,
            fg=ModernStyle.TEXT_DIM,
            bg=ModernStyle.BG_CARD,
            wraplength=400,
            justify="left"
        )
        self.stats_label.pack(anchor="w", pady=(0, 10))

        # Results tree
        tree_frame = tk.Frame(results_inner, bg=ModernStyle.BG_CARD)
        tree_frame.pack(fill="both", expand=True)

        columns = ("type", "count", "percent")
        self.results_tree = ttk.Treeview(tree_frame,
            columns=columns, show="headings", height=6)

        self.results_tree.heading("type", text="Background Type")
        self.results_tree.heading("count", text="Count")
        self.results_tree.heading("percent", text="Percent")

        self.results_tree.column("type", width=180)
        self.results_tree.column("count", width=70, anchor="center")
        self.results_tree.column("percent", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
            command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Progress section
        progress_frame = tk.Frame(main, bg=ModernStyle.BG_DARK)
        progress_frame.pack(fill="x", pady=(15, 0))

        self.progress_bar = ttk.Progressbar(progress_frame,
            mode="determinate", length=400)
        self.progress_bar.pack(fill="x", pady=(0, 8))

        self.status_label = tk.Label(progress_frame,
            text="Ready",
            font=ModernStyle.FONT_SMALL,
            fg=ModernStyle.TEXT_MUTED,
            bg=ModernStyle.BG_DARK
        )
        self.status_label.pack(anchor="w")

        # Buttons
        button_frame = tk.Frame(main, bg=ModernStyle.BG_DARK)
        button_frame.pack(fill="x", pady=(20, 0))

        # Left side - cancel
        self.cancel_btn = ttk.Button(button_frame,
            text="Cancel",
            command=self._cancel_operation,
            state="disabled"
        )
        self.cancel_btn.pack(side="left")

        # Right side - main actions
        ttk.Button(button_frame,
            text="Close",
            command=self.destroy
        ).pack(side="right", padx=(10, 0))

        self.copy_btn = ttk.Button(button_frame,
            text="Copy Images",
            command=self._copy_images,
            state="disabled"
        )
        self.copy_btn.pack(side="right", padx=(10, 0))

        self.scan_btn = ttk.Button(button_frame,
            text="Scan Folders",
            command=self._start_scan
        )
        self.scan_btn.pack(side="right")

    def _update_threshold(self, value):
        """Update threshold label."""
        self.threshold_label.config(text=f"{float(value):.2f}")

    def _refresh_folder_list(self):
        """Refresh the folder list display."""
        for widget in self.folder_list_frame.winfo_children():
            widget.destroy()

        if not self.source_folders:
            tk.Label(self.folder_list_frame,
                text="No folders selected",
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.TEXT_MUTED,
                bg=ModernStyle.BG_CARD
            ).pack(anchor="w", pady=5)
            return

        for folder in self.source_folders:
            row = tk.Frame(self.folder_list_frame, bg=ModernStyle.BG_CARD)
            row.pack(fill="x", pady=2)

            # Shortened path
            display = self._shorten_path(folder, 50)
            tk.Label(row,
                text=f"📁 {display}",
                font=ModernStyle.FONT_SMALL,
                fg=ModernStyle.TEXT_DIM,
                bg=ModernStyle.BG_CARD
            ).pack(side="left")

            # Remove button
            remove_btn = tk.Label(row,
                text="×",
                font=("Segoe UI", 12),
                fg=ModernStyle.TEXT_MUTED,
                bg=ModernStyle.BG_CARD,
                cursor="hand2"
            )
            remove_btn.pack(side="right")
            remove_btn.bind("<Button-1>", lambda e, f=folder: self._remove_folder(f))
            remove_btn.bind("<Enter>", lambda e, b=remove_btn: b.configure(fg=ModernStyle.ERROR))
            remove_btn.bind("<Leave>", lambda e, b=remove_btn: b.configure(fg=ModernStyle.TEXT_MUTED))

    def _shorten_path(self, path, max_len=50):
        """Shorten a path for display."""
        if len(path) <= max_len:
            return path
        parts = Path(path).parts
        if len(parts) <= 2:
            return "..." + path[-(max_len-3):]
        return f"{parts[0]}\\...\\{parts[-1]}"

    def _add_folder(self):
        """Add a source folder."""
        folder = filedialog.askdirectory(title="Select Source Folder", parent=self)
        if folder and folder not in self.source_folders:
            self.source_folders.append(folder)
            self._refresh_folder_list()

    def _remove_folder(self, folder):
        """Remove a source folder."""
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            self._refresh_folder_list()

    def _use_config_sources(self):
        """Load folders from config manager."""
        if not self.config_manager:
            return

        # get_active_source_folders() returns only the enabled folders
        active_folders = self.config_manager.get_active_source_folders()

        for folder in active_folders:
            if folder not in self.source_folders:
                self.source_folders.append(folder)

        self._refresh_folder_list()

    def _cancel_operation(self):
        """Request cancellation."""
        self.cancel_requested = True
        self.status_label.config(text="Cancelling...")

    def _start_scan(self):
        """Start scanning for suitable images."""
        if not self.source_folders:
            messagebox.showinfo("Info", "Please add at least one source folder.", parent=self)
            return

        if self.is_scanning or self.is_copying:
            return

        self.is_scanning = True
        self.cancel_requested = False
        self.suitable_images = []
        self.all_classifications = []

        # Clear results
        self.results_tree.delete(*self.results_tree.get_children())

        # Update UI
        self.scan_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar['value'] = 0
        self.status_label.config(text="Initializing classifier...")
        self.update_idletasks()

        def scan_thread():
            try:
                # Load WD14 - results are cached to disk for fast subsequent runs
                self.classifier = BackgroundClassifier()

                threshold = self.threshold_var.get()

                def progress_callback(current, total, filename, status):
                    if self.cancel_requested:
                        return
                    progress = current / total * 100
                    stats = self.classifier.stats
                    cache_pct = (stats['cache_hits'] / max(1, current)) * 100
                    self.after(0, lambda: self._update_progress(
                        progress, current, total, filename, status,
                        f"Cache: {stats['cache_hits']}, WD14: {stats['wd14_calls']}"
                    ))

                def cancel_check():
                    return self.cancel_requested

                self.suitable_images, self.all_classifications = \
                    self.classifier.find_suitable_images(
                        self.source_folders,
                        threshold=threshold,
                        progress_callback=progress_callback,
                        cancel_check=cancel_check
                    )

                # Store stats for results display
                self.scan_stats = self.classifier.stats
                self.after(0, self._display_results)

            except Exception as e:
                self.after(0, lambda: self._scan_error(str(e)))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _update_progress(self, progress, current, total, filename, status, stats_str=""):
        """Update progress display."""
        self.progress_bar['value'] = progress
        status_text = f"Scanning: {current}/{total} - {filename}"
        if stats_str:
            status_text += f" ({stats_str})"
        self.status_label.config(text=status_text)

    def _scan_error(self, message):
        """Handle scan error."""
        self.is_scanning = False
        self.scan_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="Scan failed")
        messagebox.showerror("Error", message, parent=self)

    def _display_results(self):
        """Display scan results."""
        self.is_scanning = False
        self.scan_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        total = len(self.all_classifications)
        suitable_count = len(self.suitable_images)

        # Build stats message
        stats = getattr(self, 'scan_stats', {})
        cache_hits = stats.get('cache_hits', 0)
        wd14_calls = stats.get('wd14_calls', 0)
        stats_msg = f" (Cache: {cache_hits}, WD14: {wd14_calls})" if stats else ""

        if self.cancel_requested:
            self.status_label.config(text=f"Cancelled. Processed {total} images.{stats_msg}")
        else:
            self.status_label.config(text=f"Complete. {total} images scanned.{stats_msg}")

        # Update stats
        if total > 0:
            percent = suitable_count / total * 100
            self.stats_label.config(
                text=f"Found {suitable_count} suitable images ({percent:.1f}% of {total} total)",
                fg=ModernStyle.SUCCESS if suitable_count > 0 else ModernStyle.TEXT_DIM
            )
        else:
            self.stats_label.config(text="No images found in selected folders.")

        # Group by type
        type_counts = {}
        suitable_types = {}

        for result in self.all_classifications:
            bg_type = result.background_type.value
            type_counts[bg_type] = type_counts.get(bg_type, 0) + 1
            if result.is_suitable:
                suitable_types[bg_type] = suitable_types.get(bg_type, 0) + 1

        # Display in tree
        self.results_tree.delete(*self.results_tree.get_children())

        for bg_type in sorted(suitable_types.keys()):
            count = suitable_types[bg_type]
            pct = count / total * 100 if total > 0 else 0
            self.results_tree.insert("", "end",
                values=(f"✓ {bg_type}", count, f"{pct:.1f}%"),
                tags=("suitable",))

        unsuitable = {k: v for k, v in type_counts.items() if k not in suitable_types}
        for bg_type in sorted(unsuitable.keys()):
            count = unsuitable[bg_type]
            pct = count / total * 100 if total > 0 else 0
            self.results_tree.insert("", "end",
                values=(f"✗ {bg_type}", count, f"{pct:.1f}%"),
                tags=("unsuitable",))

        # Enable copy if results
        if suitable_count > 0:
            self.copy_btn.config(state="normal")

    def _copy_images(self):
        """Copy suitable images."""
        if not self.suitable_images:
            return

        if self.is_copying:
            return

        count = len(self.suitable_images)
        if not messagebox.askyesno("Confirm",
            f"Copy {count} images to a new folder?\n\n"
            f"A timestamped folder will be created.",
            parent=self):
            return

        self.is_copying = True
        self.cancel_requested = False

        self.scan_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar['value'] = 0
        self.status_label.config(text="Copying...")
        self.update_idletasks()

        def copy_thread():
            try:
                def progress_callback(current, total, filename):
                    if self.cancel_requested:
                        return
                    progress = current / total * 100
                    self.after(0, lambda: self._update_copy_progress(progress, current, total, filename))

                def cancel_check():
                    return self.cancel_requested

                result = copy_suitable_images(
                    self.suitable_images,
                    output_folder=None,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check
                )

                self.after(0, lambda: self._display_copy_results(result))

            except Exception as e:
                self.after(0, lambda: self._copy_error(str(e)))

        threading.Thread(target=copy_thread, daemon=True).start()

    def _update_copy_progress(self, progress, current, total, filename):
        """Update copy progress."""
        self.progress_bar['value'] = progress
        self.status_label.config(text=f"Copying: {current}/{total} - {filename}")

    def _copy_error(self, message):
        """Handle copy error."""
        self.is_copying = False
        self.scan_btn.config(state="normal")
        self.copy_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="Copy failed")
        messagebox.showerror("Error", message, parent=self)

    def _display_copy_results(self, result):
        """Display copy results."""
        self.is_copying = False
        self.scan_btn.config(state="normal")
        self.copy_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        output_folder = result['output_folder']
        copied = result['copied']

        self.status_label.config(text=f"Done. {copied} images copied.")

        msg = f"Copied {copied} images to:\n{output_folder}"
        if result['failed'] > 0:
            msg += f"\n\n{result['failed']} files failed."

        messagebox.showinfo("Complete", msg, parent=self)

        if messagebox.askyesno("Open Folder", "Open the output folder?", parent=self):
            os.startfile(output_folder)

    def setup_modal(self):
        """Setup modal behavior."""
        self.transient(self.parent)
        self.grab_set()

        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


def show_background_sort_dialog(parent, config_manager=None):
    """Show the background sort dialog."""
    dialog = BackgroundSortDialog(parent, config_manager)
    parent.wait_window(dialog)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Test")
    root.geometry("400x200")
    root.configure(bg="#1a1a2e")

    ttk.Button(root, text="Open Dialog",
        command=lambda: show_background_sort_dialog(root)).pack(expand=True)

    root.mainloop()
