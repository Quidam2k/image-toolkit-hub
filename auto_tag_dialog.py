"""
Auto-Tag Dialog for Image Toolkit Hub

Dialog for generating descriptive tags using WD14 AI tagger.
Tags are written to .txt files - original images are never modified.

Author: Claude Code Implementation
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pathlib import Path

from ui_theme import Theme
import toast_manager
from help_texts import get_tooltip


class AutoTagDialog(tk.Toplevel):
    """Dialog for configuring and running auto-tag operations."""

    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}

    def __init__(self, parent, source_folders=None, output_folders=None):
        super().__init__(parent)
        self.parent = parent
        self.source_folders = source_folders or []
        self.output_folders = output_folders or []

        self.title("Auto-Tag Images")
        self.configure(bg=Theme.BG_PRIMARY)
        self.resizable(False, False)

        # State
        self.custom_folder = tk.StringVar()
        self.source_type = tk.StringVar(value="custom")
        self.include_subfolders = tk.BooleanVar(value=True)
        self.retag_existing = tk.BooleanVar(value=False)
        self.threshold = tk.DoubleVar(value=0.35)

        # Preview data
        self.preview_images = []
        self.preview_tagged = 0
        self.preview_to_process = 0

        # Processing state
        self.processing = False
        self.cancelled = False
        self.generator = None

        Theme.apply(self)
        self.setup_ui()
        self.center_on_parent()

        # Modal
        self.transient(parent)
        self.grab_set()

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Build the dialog interface."""
        main = tk.Frame(self, bg=Theme.BG_PRIMARY, padx=25, pady=20)
        main.pack(fill="both", expand=True)

        # Title
        tk.Label(main,
            text="Auto-Tag Images",
            font=Theme.FONT_TITLE,
            fg=Theme.TEXT,
            bg=Theme.BG_PRIMARY
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(main,
            text="Generate descriptive tags using WD14 AI model",
            font=Theme.FONT_SMALL,
            fg=Theme.TEXT_DIM,
            bg=Theme.BG_PRIMARY
        ).pack(anchor="w", pady=(0, 20))

        # Source selection frame
        source_frame = tk.LabelFrame(main,
            text="Select Folder",
            font=Theme.FONT_HEADING,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            padx=15, pady=10
        )
        source_frame.pack(fill="x", pady=(0, 15))

        # Radio buttons for source type
        if self.source_folders:
            rb1 = tk.Radiobutton(source_frame,
                text=f"Active source folders ({len(self.source_folders)})",
                variable=self.source_type,
                value="sources",
                font=Theme.FONT_BODY,
                fg=Theme.TEXT,
                bg=Theme.BG_CARD,
                activebackground=Theme.BG_CARD,
                activeforeground=Theme.TEXT,
                selectcolor=Theme.BG_PRIMARY,
                command=self.update_preview
            )
            rb1.pack(anchor="w", pady=2)
            Theme.create_tooltip(rb1, get_tooltip('autotag_source_active'))

        if self.output_folders:
            rb2 = tk.Radiobutton(source_frame,
                text=f"Output folders ({len(self.output_folders)})",
                variable=self.source_type,
                value="outputs",
                font=Theme.FONT_BODY,
                fg=Theme.TEXT,
                bg=Theme.BG_CARD,
                activebackground=Theme.BG_CARD,
                activeforeground=Theme.TEXT,
                selectcolor=Theme.BG_PRIMARY,
                command=self.update_preview
            )
            rb2.pack(anchor="w", pady=2)
            Theme.create_tooltip(rb2, get_tooltip('autotag_source_output'))

        # Custom folder option
        rb3_frame = tk.Frame(source_frame, bg=Theme.BG_CARD)
        rb3_frame.pack(fill="x", pady=2)

        rb3 = tk.Radiobutton(rb3_frame,
            text="Custom folder:",
            variable=self.source_type,
            value="custom",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.TEXT,
            selectcolor=Theme.BG_PRIMARY,
            command=self.update_preview
        )
        rb3.pack(side="left")
        Theme.create_tooltip(rb3, get_tooltip('autotag_source_custom'))

        # Custom folder entry and browse
        custom_frame = tk.Frame(source_frame, bg=Theme.BG_CARD)
        custom_frame.pack(fill="x", pady=(5, 0), padx=(20, 0))

        self.custom_entry = tk.Entry(custom_frame,
            textvariable=self.custom_folder,
            font=Theme.FONT_SMALL,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            width=40
        )
        self.custom_entry.pack(side="left", fill="x", expand=True)

        browse_btn = ttk.Button(custom_frame,
            text="Browse...",
            command=self.browse_folder,
            style="Secondary.TButton"
        )
        browse_btn.pack(side="left", padx=(10, 0))

        # Options frame
        options_frame = tk.LabelFrame(main,
            text="Options",
            font=Theme.FONT_HEADING,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            padx=15, pady=10
        )
        options_frame.pack(fill="x", pady=(0, 15))

        # Include subfolders checkbox
        cb1 = tk.Checkbutton(options_frame,
            text="Include subfolders",
            variable=self.include_subfolders,
            font=Theme.FONT_BODY,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.TEXT,
            selectcolor=Theme.BG_PRIMARY,
            command=self.update_preview
        )
        cb1.pack(anchor="w", pady=2)
        Theme.create_tooltip(cb1, get_tooltip('autotag_include_subfolders'))

        # Re-tag existing checkbox
        cb2 = tk.Checkbutton(options_frame,
            text="Re-tag files with existing tags",
            variable=self.retag_existing,
            font=Theme.FONT_BODY,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            activebackground=Theme.BG_CARD,
            activeforeground=Theme.TEXT,
            selectcolor=Theme.BG_PRIMARY,
            command=self.update_preview
        )
        cb2.pack(anchor="w", pady=2)
        Theme.create_tooltip(cb2, get_tooltip('autotag_retag_existing'))

        # Threshold slider
        threshold_frame = tk.Frame(options_frame, bg=Theme.BG_CARD)
        threshold_frame.pack(fill="x", pady=(10, 0))

        threshold_label = tk.Label(threshold_frame,
            text="Confidence threshold:",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD
        )
        threshold_label.pack(side="left")
        Theme.create_tooltip(threshold_label, get_tooltip('autotag_threshold'))

        self.threshold_value_label = tk.Label(threshold_frame,
            text="0.35",
            font=Theme.FONT_BODY,
            fg=Theme.ACCENT,
            bg=Theme.BG_CARD,
            width=5
        )
        self.threshold_value_label.pack(side="right")

        self.threshold_slider = ttk.Scale(threshold_frame,
            from_=0.1,
            to=0.8,
            variable=self.threshold,
            orient="horizontal",
            command=self.on_threshold_change
        )
        self.threshold_slider.pack(side="right", fill="x", expand=True, padx=(10, 5))

        # Preview frame
        preview_frame = tk.Frame(main, bg=Theme.BG_CARD, padx=15, pady=12)
        preview_frame.pack(fill="x", pady=(0, 15))
        preview_frame.configure(highlightthickness=1, highlightbackground=Theme.BORDER)

        tk.Label(preview_frame,
            text="Preview",
            font=Theme.FONT_HEADING,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD
        ).pack(anchor="w", pady=(0, 8))

        self.preview_total_label = tk.Label(preview_frame,
            text="Images found: --",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT_DIM,
            bg=Theme.BG_CARD
        )
        self.preview_total_label.pack(anchor="w")

        self.preview_tagged_label = tk.Label(preview_frame,
            text="Already tagged: --",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT_DIM,
            bg=Theme.BG_CARD
        )
        self.preview_tagged_label.pack(anchor="w")

        self.preview_process_label = tk.Label(preview_frame,
            text="To process: --",
            font=Theme.FONT_BODY,
            fg=Theme.ACCENT,
            bg=Theme.BG_CARD
        )
        self.preview_process_label.pack(anchor="w")

        # Progress frame (hidden initially)
        self.progress_frame = tk.Frame(main, bg=Theme.BG_CARD, padx=15, pady=12)
        self.progress_frame.configure(highlightthickness=1, highlightbackground=Theme.BORDER)

        tk.Label(self.progress_frame,
            text="Processing",
            font=Theme.FONT_HEADING,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD
        ).pack(anchor="w", pady=(0, 8))

        self.progress_bar = ttk.Progressbar(self.progress_frame,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill="x", pady=(0, 8))

        self.progress_status = tk.Label(self.progress_frame,
            text="",
            font=Theme.FONT_SMALL,
            fg=Theme.TEXT_DIM,
            bg=Theme.BG_CARD
        )
        self.progress_status.pack(anchor="w")

        self.progress_file = tk.Label(self.progress_frame,
            text="",
            font=Theme.FONT_SMALL,
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_CARD,
            wraplength=400
        )
        self.progress_file.pack(anchor="w")

        # Buttons
        btn_frame = tk.Frame(main, bg=Theme.BG_PRIMARY)
        btn_frame.pack(fill="x", pady=(10, 0))

        self.cancel_btn = ttk.Button(btn_frame,
            text="Cancel",
            command=self.on_close,
            style="Secondary.TButton"
        )
        self.cancel_btn.pack(side="left")

        self.start_btn = ttk.Button(btn_frame,
            text="Start Tagging",
            command=self.start_tagging,
            style="Accent.TButton"
        )
        self.start_btn.pack(side="right")

        # Initial preview update
        self.after(100, self.update_preview)

    def center_on_parent(self):
        """Center dialog on parent window."""
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()

        dialog_w = self.winfo_reqwidth()
        dialog_h = self.winfo_reqheight()

        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self.geometry(f"+{x}+{y}")

    def browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Folder to Tag")
        if folder:
            self.custom_folder.set(folder)
            self.source_type.set("custom")
            self.update_preview()

    def on_threshold_change(self, value):
        """Update threshold display."""
        self.threshold_value_label.config(text=f"{float(value):.2f}")

    def get_selected_folders(self):
        """Get list of folders based on selection."""
        source_type = self.source_type.get()

        if source_type == "sources":
            return self.source_folders
        elif source_type == "outputs":
            return self.output_folders
        elif source_type == "custom":
            custom = self.custom_folder.get().strip()
            if custom and os.path.isdir(custom):
                return [custom]
        return []

    def update_preview(self):
        """Update preview counts (runs scan in background thread)."""
        folders = self.get_selected_folders()
        recursive = self.include_subfolders.get()
        retag = self.retag_existing.get()

        if not folders:
            self.preview_total_label.config(text="Images found: --")
            self.preview_tagged_label.config(text="Already tagged: --")
            self.preview_process_label.config(text="To process: --")
            self.preview_images = []
            return

        # Show scanning state immediately
        self.preview_total_label.config(text="Scanning folders...")
        self.preview_tagged_label.config(text="")
        self.preview_process_label.config(text="")
        self.start_btn.config(state="disabled")

        # Increment scan generation so stale results are ignored
        if not hasattr(self, '_scan_gen'):
            self._scan_gen = 0
        self._scan_gen += 1
        current_gen = self._scan_gen

        def scan_worker():
            images = []
            tagged = 0
            last_update = [0]  # mutable for closure

            def maybe_update_count():
                """Send periodic count updates to UI."""
                count = len(images)
                if count - last_update[0] >= 500:  # Update every 500 images
                    last_update[0] = count
                    try:
                        self.after(0, lambda c=count: self._update_scan_count(c, current_gen))
                    except RuntimeError:
                        pass

            for folder in folders:
                if not os.path.isdir(folder):
                    continue

                if recursive:
                    for root, dirs, files in os.walk(folder):
                        for f in files:
                            if os.path.splitext(f)[1].lower() in self.IMAGE_EXTENSIONS:
                                img_path = os.path.join(root, f)
                                images.append(img_path)
                                if os.path.exists(img_path + '.txt'):
                                    tagged += 1
                                maybe_update_count()
                else:
                    try:
                        for f in os.listdir(folder):
                            if os.path.splitext(f)[1].lower() in self.IMAGE_EXTENSIONS:
                                img_path = os.path.join(folder, f)
                                images.append(img_path)
                                if os.path.exists(img_path + '.txt'):
                                    tagged += 1
                                maybe_update_count()
                    except (PermissionError, OSError):
                        pass

            # Post final results to main thread
            try:
                self.after(0, lambda: self._apply_preview(images, tagged, retag, current_gen))
            except RuntimeError:
                pass

        thread = threading.Thread(target=scan_worker, daemon=True)
        thread.start()

    def _update_scan_count(self, count, scan_gen):
        """Show live count during scanning."""
        if not self.winfo_exists() or scan_gen != self._scan_gen:
            return
        self.preview_total_label.config(text=f"Scanning... {count:,} images found")

    def _apply_preview(self, images, tagged, retag, scan_gen):
        """Apply scan results to the preview UI (main thread)."""
        if not self.winfo_exists():
            return
        # Ignore stale results from a previous scan
        if scan_gen != self._scan_gen:
            return

        self.preview_images = images
        self.preview_tagged = tagged

        if retag:
            to_process = len(images)
        else:
            to_process = len(images) - tagged

        self.preview_to_process = to_process

        self.preview_total_label.config(text=f"Images found: {len(images):,}")
        self.preview_tagged_label.config(text=f"Already tagged: {tagged:,} (will skip)")
        self.preview_process_label.config(text=f"To process: {to_process:,} images")

        if retag:
            self.preview_tagged_label.config(text=f"Already tagged: {tagged:,} (will re-tag)")

        self.start_btn.config(state="normal")

    def start_tagging(self):
        """Start the tagging process."""
        if self.processing:
            return

        if self.preview_to_process == 0:
            messagebox.showinfo("Nothing to Process",
                "No images to tag. Check your folder selection and options.")
            return

        # Show progress UI
        self.progress_frame.pack(fill="x", pady=(0, 15), before=self.start_btn.master)
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(text="Stop")
        self.processing = True
        self.cancelled = False

        # Start processing thread
        thread = threading.Thread(target=self.run_tagging, daemon=True)
        thread.start()

    def run_tagging(self):
        """Run tagging in background thread."""
        try:
            # Import and initialize generator
            from tag_generator import DescriptiveTagGenerator

            self.generator = DescriptiveTagGenerator(threshold=self.threshold.get())

            if not self.generator.loaded:
                self.after(0, lambda: self.show_error(
                    "WD14 model not loaded. Check that model files exist."
                ))
                return

            # Filter images to process
            retag = self.retag_existing.get()
            images_to_process = []

            for img in self.preview_images:
                if self.cancelled:
                    break
                if retag or not os.path.exists(img + '.txt'):
                    images_to_process.append(img)

            total = len(images_to_process)
            processed = 0
            success = 0
            failed = 0

            for i, img_path in enumerate(images_to_process):
                if self.cancelled:
                    break

                # Check if generator was cancelled
                if hasattr(self.generator, 'cancelled') and self.generator.cancelled:
                    break

                # Update progress
                self.after(0, lambda p=i+1, t=total, f=os.path.basename(img_path):
                    self.update_progress(p, t, f))

                try:
                    # Generate tags
                    result = self.generator.generate_tags_for_image(img_path)

                    if result['status'] == 'success':
                        # Save tags to file
                        save_result = self.generator.save_tags_to_file(img_path, result['tags'])
                        if save_result['status'] == 'success':
                            success += 1
                        else:
                            failed += 1
                    else:
                        failed += 1

                    processed += 1

                except Exception as e:
                    failed += 1
                    print(f"Error tagging {img_path}: {e}")

            # Completed
            self.after(0, lambda: self.tagging_complete(processed, success, failed))

        except Exception as e:
            self.after(0, lambda: self.show_error(str(e)))

    def update_progress(self, current, total, filename):
        """Update progress UI from main thread."""
        if not self.winfo_exists():
            return

        pct = (current / total) * 100 if total > 0 else 0
        self.progress_bar['value'] = pct
        self.progress_status.config(text=f"{current} / {total} ({pct:.1f}%)")
        self.progress_file.config(text=filename)

    def tagging_complete(self, processed, success, failed):
        """Handle tagging completion."""
        if not self.winfo_exists():
            return

        self.processing = False
        self.progress_bar['value'] = 100
        self.progress_status.config(text="Complete!")
        self.progress_file.config(text="")

        self.start_btn.config(state="normal", text="Done")
        self.start_btn.config(command=self.destroy)
        self.cancel_btn.pack_forget()

        if self.cancelled:
            msg = f"Tagging cancelled. {success} images tagged before stopping."
            toast_manager.show_warning("Tagging Cancelled", msg)
        else:
            msg = f"Tagged {success} images"
            if failed > 0:
                msg += f" ({failed} failed)"
            toast_manager.show_success("Auto-Tag Complete", msg)

    def show_error(self, message):
        """Show error and reset UI."""
        if not self.winfo_exists():
            return

        self.processing = False
        self.progress_frame.pack_forget()
        self.start_btn.config(state="normal")
        self.cancel_btn.config(text="Cancel")

        messagebox.showerror("Error", message)

    def on_close(self):
        """Handle dialog close."""
        if self.processing:
            self.cancelled = True
            if self.generator and hasattr(self.generator, 'cancel'):
                self.generator.cancel()
            # Wait a moment then close
            self.after(500, self.destroy)
        else:
            self.destroy()


def show_auto_tag_dialog(parent, source_folders=None, output_folders=None):
    """
    Show the auto-tag dialog.

    Args:
        parent: Parent window
        source_folders: List of source folders (optional)
        output_folders: List of output folders (optional)

    Returns:
        The dialog instance
    """
    dialog = AutoTagDialog(parent, source_folders, output_folders)
    return dialog
