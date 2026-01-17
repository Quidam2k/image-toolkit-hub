"""
Rankings View Dialog - Leaderboard and export functionality

Displays ranked images in a sortable table with thumbnails,
and provides export functionality for top-N images.

Author: Claude Code Implementation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import logging
import threading
from typing import Optional

from image_ranker import ImageRanker, RankedImage
from ui_theme import Theme as ModernStyle

logger = logging.getLogger(__name__)


class RankingsViewDialog(tk.Toplevel):
    """
    Dialog showing ranked images as a sortable table.

    Features:
    - Thumbnail preview column
    - Sortable by rank, score, mu, sigma, comparisons
    - Export top N to folder
    - Export to CSV
    - Image preview on selection
    """

    THUMB_SIZE = 50

    def __init__(self, parent, ranker: ImageRanker):
        super().__init__(parent)
        self.parent = parent
        self.ranker = ranker

        # Thumbnail cache
        self.thumb_cache: dict = {}

        self.setup_window()
        self.setup_ui()
        self.load_rankings()

    def setup_window(self):
        """Configure the dialog window."""
        self.title("Image Rankings")
        self.geometry("1200x800")
        self.minsize(900, 600)
        self.configure(bg=ModernStyle.BG_DARK)

        ModernStyle.apply(self)

        # Modal behavior
        self.transient(self.parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        if self.parent:
            x = self.parent.winfo_x() + (self.parent.winfo_width() - 1200) // 2
            y = self.parent.winfo_y() + (self.parent.winfo_height() - 800) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Build the UI components."""
        # Title bar
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            title_frame,
            text="Image Rankings",
            style="Title.TLabel"
        ).pack(side="left")

        # Stats summary
        stats = self.ranker.get_stats()
        ttk.Label(
            title_frame,
            text=f"{stats['total_images']} images | {stats['total_comparisons']} comparisons | "
                 f"{stats['stability_percent']:.0f}% stability",
            style="Dim.TLabel"
        ).pack(side="right")

        # Main content - paned window
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Left side: rankings table
        self.create_rankings_table(paned)

        # Right side: preview panel
        self.create_preview_panel(paned)

        # Bottom: export controls
        self.create_export_bar()

    def create_rankings_table(self, parent):
        """Create the rankings treeview."""
        table_frame = ttk.Frame(parent)
        parent.add(table_frame, weight=3)

        # Treeview with columns
        columns = ("rank", "filename", "score", "mu", "sigma", "comparisons")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Configure columns
        self.tree.heading("rank", text="Rank", command=lambda: self.sort_by("rank"))
        self.tree.heading("filename", text="Filename", command=lambda: self.sort_by("filename"))
        self.tree.heading("score", text="Score", command=lambda: self.sort_by("score"))
        self.tree.heading("mu", text="\u03bc", command=lambda: self.sort_by("mu"))
        self.tree.heading("sigma", text="\u03c3", command=lambda: self.sort_by("sigma"))
        self.tree.heading("comparisons", text="Comparisons", command=lambda: self.sort_by("comparisons"))

        self.tree.column("rank", width=60, anchor="center")
        self.tree.column("filename", width=300, anchor="w")
        self.tree.column("score", width=80, anchor="center")
        self.tree.column("mu", width=80, anchor="center")
        self.tree.column("sigma", width=80, anchor="center")
        self.tree.column("comparisons", width=100, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Selection binding
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Store sort state
        self.sort_column = "rank"
        self.sort_reverse = False

    def create_preview_panel(self, parent):
        """Create the image preview panel."""
        preview_frame = ttk.Frame(parent, style="Card.TFrame")
        parent.add(preview_frame, weight=1)

        # Preview canvas
        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg=ModernStyle.BG_CARD,
            highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Preview photo reference
        self.preview_photo = None

        # Info labels
        info_frame = ttk.Frame(preview_frame, style="Card.TFrame")
        info_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.preview_name = ttk.Label(
            info_frame,
            text="Select an image",
            style="Heading.TLabel",
            wraplength=350
        )
        self.preview_name.pack(anchor="w")

        self.preview_stats = ttk.Label(
            info_frame,
            text="",
            style="Card.TLabel"
        )
        self.preview_stats.pack(anchor="w")

        self.preview_path = ttk.Label(
            info_frame,
            text="",
            style="Dim.TLabel",
            wraplength=350
        )
        self.preview_path.pack(anchor="w")

        # Open button
        ttk.Button(
            info_frame,
            text="Open in Explorer",
            command=self.open_selected_in_explorer,
            style="Secondary.TButton"
        ).pack(anchor="w", pady=(10, 0))

    def create_export_bar(self):
        """Create the export controls bar."""
        export_frame = ttk.Frame(self, style="Card.TFrame")
        export_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Export top N
        topn_frame = ttk.Frame(export_frame, style="Card.TFrame")
        topn_frame.pack(side="left", padx=10, pady=10)

        ttk.Label(
            topn_frame,
            text="Export top",
            style="Card.TLabel"
        ).pack(side="left")

        self.topn_var = tk.StringVar(value="100")
        topn_entry = ttk.Entry(
            topn_frame,
            textvariable=self.topn_var,
            width=6
        )
        topn_entry.pack(side="left", padx=5)

        ttk.Label(
            topn_frame,
            text="images to folder:",
            style="Card.TLabel"
        ).pack(side="left")

        ttk.Button(
            topn_frame,
            text="Export...",
            command=self.export_top_n,
            style="TButton"
        ).pack(side="left", padx=(10, 0))

        # CSV export
        ttk.Button(
            export_frame,
            text="Export CSV",
            command=self.export_csv,
            style="Secondary.TButton"
        ).pack(side="left", padx=10, pady=10)

        # Refresh button
        ttk.Button(
            export_frame,
            text="Refresh",
            command=self.load_rankings,
            style="Secondary.TButton"
        ).pack(side="right", padx=10, pady=10)

        # Close button
        ttk.Button(
            export_frame,
            text="Close",
            command=self.on_close,
            style="Secondary.TButton"
        ).pack(side="right", padx=10, pady=10)

    def load_rankings(self):
        """Load rankings into the treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get all images sorted by ordinal
        images = self.ranker.get_all_images(order_by='ordinal')

        # Insert into treeview
        for rank, img in enumerate(images, 1):
            # Store image ID as item ID for lookup
            self.tree.insert(
                "",
                "end",
                iid=str(img.id),
                values=(
                    rank,
                    img.filename,
                    f"{img.ordinal:.1f}",
                    f"{img.mu:.1f}",
                    f"{img.sigma:.2f}",
                    img.comparison_count
                )
            )

        # Store images for lookup
        self.images_by_id = {img.id: img for img in images}

    def sort_by(self, column: str):
        """Sort the treeview by column."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        # Get all items
        items = [(self.tree.item(item)["values"], item) for item in self.tree.get_children()]

        # Determine sort key
        col_idx = {"rank": 0, "filename": 1, "score": 2, "mu": 3, "sigma": 4, "comparisons": 5}[column]

        # Sort
        if column in ("rank", "score", "mu", "sigma", "comparisons"):
            # Numeric sort
            items.sort(key=lambda x: float(x[0][col_idx]), reverse=self.sort_reverse)
        else:
            # String sort
            items.sort(key=lambda x: str(x[0][col_idx]).lower(), reverse=self.sort_reverse)

        # Reorder items
        for idx, (values, item) in enumerate(items):
            self.tree.move(item, "", idx)

    def on_select(self, event):
        """Handle selection change."""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = int(selection[0])
        img = self.images_by_id.get(item_id)
        if img:
            self.show_preview(img)

    def on_double_click(self, event):
        """Handle double-click to open in explorer."""
        self.open_selected_in_explorer()

    def show_preview(self, img: RankedImage):
        """Display image preview."""
        self.preview_canvas.delete("all")

        try:
            # Load image
            pil_img = Image.open(img.filepath)

            # Resize to fit preview
            self.preview_canvas.update_idletasks()
            max_w = self.preview_canvas.winfo_width() - 20
            max_h = self.preview_canvas.winfo_height() - 20

            if max_w < 100:
                max_w = 400
            if max_h < 100:
                max_h = 400

            ratio = min(max_w / pil_img.width, max_h / pil_img.height)
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

            self.preview_photo = ImageTk.PhotoImage(pil_img)

            # Center on canvas
            x = self.preview_canvas.winfo_width() // 2
            y = self.preview_canvas.winfo_height() // 2
            self.preview_canvas.create_image(x, y, image=self.preview_photo, anchor="center")

        except Exception as e:
            logger.error(f"Error loading preview: {e}")
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                text=f"Error: {e}",
                fill=ModernStyle.ERROR
            )

        # Update info
        self.preview_name.config(text=img.filename)
        self.preview_stats.config(
            text=f"Score: {img.ordinal:.1f} | \u03bc={img.mu:.1f} | \u03c3={img.sigma:.2f} | "
                 f"Comparisons: {img.comparison_count}"
        )
        self.preview_path.config(text=str(Path(img.filepath).parent))

    def open_selected_in_explorer(self):
        """Open selected image location in file explorer."""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = int(selection[0])
        img = self.images_by_id.get(item_id)
        if img and img.exists:
            import subprocess
            # Windows: select file in explorer
            subprocess.run(['explorer', '/select,', img.filepath])

    def export_top_n(self):
        """Export top N images to a folder."""
        try:
            n = int(self.topn_var.get())
            if n < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Invalid Number",
                "Please enter a valid number of images to export.",
                parent=self
            )
            return

        folder = filedialog.askdirectory(
            title=f"Select folder to export top {n} images",
            parent=self
        )

        if not folder:
            return

        try:
            exported = self.ranker.export_top_images(n, folder, copy=True)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {len(exported)} images to:\n{folder}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                str(e),
                parent=self
            )
            logger.exception("Error exporting images")

    def export_csv(self):
        """Export rankings to CSV file."""
        filepath = filedialog.asksaveasfilename(
            title="Export rankings to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfilename="rankings.csv",
            parent=self
        )

        if not filepath:
            return

        try:
            count = self.ranker.export_rankings_csv(filepath)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {count} rankings to:\n{filepath}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                str(e),
                parent=self
            )
            logger.exception("Error exporting CSV")

    def on_close(self):
        """Handle dialog close."""
        self.destroy()
