"""
Trash Cleanup Dialog - "Take Out the Trash"

Scans output folders for directories with role='trash', shows file counts
and sizes, and lets the user select which to delete.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import shutil
import threading
from ui_theme import Theme as ModernStyle


class TrashCleanupDialog:
    """Dialog for reviewing and deleting trash-role output folders."""

    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.trash_info = []  # list of dicts with folder info + tk vars

        self.window = tk.Toplevel(parent)
        self.window.title("Take Out the Trash")
        self.window.geometry("700x500")
        self.window.resizable(True, True)
        self.window.configure(bg=ModernStyle.BG_DARK)
        ModernStyle.apply(self.window)

        if parent:
            self.window.transient(parent)
            self.window.grab_set()

        self._build_ui()
        self._scan_trash()

    def _build_ui(self):
        main = ttk.Frame(self.window, padding="15")
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Take Out the Trash", style="Title.TLabel").pack(pady=(0, 5))
        ttk.Label(main, text="Select trash-role folders to delete. Contents will be permanently removed.",
                  style="Dim.TLabel").pack(pady=(0, 10))

        # Scrollable list of trash folders
        list_frame = ttk.Frame(main)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        canvas = tk.Canvas(list_frame, bg=ModernStyle.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Summary and buttons
        self.summary_label = ttk.Label(main, text="Scanning...", style="Dim.TLabel")
        self.summary_label.pack(pady=(0, 10))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x")

        self.select_all_var = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(btn_frame, text="Select All",
                       variable=self.select_all_var,
                       command=self._toggle_all).pack(side="left")

        ttk.Button(btn_frame, text="Cancel",
                  command=self.window.destroy, width=12).pack(side="right", padx=(10, 0))
        self.delete_btn = ttk.Button(btn_frame, text="Delete Selected",
                                     command=self._delete_selected, width=16)
        self.delete_btn.pack(side="right")
        self.delete_btn.state(["disabled"])

    def _scan_trash(self):
        """Scan for all trash-role folders and populate the list."""
        trash_folders = self.config_manager.get_trash_folders()

        if not trash_folders:
            ttk.Label(self.scroll_frame, text="No trash-role folders found.",
                     style="Dim.TLabel").pack(pady=20)
            self.summary_label.config(text="No trash folders configured.")
            return

        total_files = 0
        total_size = 0

        for info in trash_folders:
            path = info['path']
            file_count, byte_size = self._count_folder(path)
            if file_count == 0:
                continue

            total_files += file_count
            total_size += byte_size

            var = tk.BooleanVar(master=self.window, value=False)
            var.trace_add('write', lambda *args: self._update_summary())

            row = ttk.Frame(self.scroll_frame)
            row.pack(fill="x", padx=5, pady=3)

            ttk.Checkbutton(row, variable=var).pack(side="left", padx=(0, 8))

            # Show relative path from project root
            script_dir = os.path.dirname(os.path.abspath(__file__))
            try:
                rel_path = os.path.relpath(path, script_dir)
            except ValueError:
                rel_path = path

            ttk.Label(row, text=rel_path).pack(side="left", fill="x", expand=True)

            size_str = self._format_size(byte_size)
            ttk.Label(row, text=f"{file_count} files, {size_str}",
                     style="Dim.TLabel").pack(side="right")

            self.trash_info.append({
                'path': path,
                'label': info['label'],
                'source': info['source'],
                'file_count': file_count,
                'byte_size': byte_size,
                'var': var
            })

        if not self.trash_info:
            ttk.Label(self.scroll_frame, text="All trash folders are empty.",
                     style="Dim.TLabel").pack(pady=20)
            self.summary_label.config(text="Nothing to clean up.")
        else:
            self._update_summary()
            self.delete_btn.state(["!disabled"])

    def _count_folder(self, path):
        """Count files and total size in a folder (non-recursive for speed)."""
        count = 0
        size = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    count += 1
                    try:
                        size += entry.stat().st_size
                    except OSError:
                        pass
                elif entry.is_dir():
                    # Recurse into subdirs
                    sub_count, sub_size = self._count_folder(entry.path)
                    count += sub_count
                    size += sub_size
        except (PermissionError, OSError):
            pass
        return count, size

    def _format_size(self, byte_size):
        """Format byte size into human-readable string."""
        if byte_size < 1024:
            return f"{byte_size} B"
        elif byte_size < 1024 * 1024:
            return f"{byte_size / 1024:.1f} KB"
        elif byte_size < 1024 * 1024 * 1024:
            return f"{byte_size / (1024 * 1024):.1f} MB"
        else:
            return f"{byte_size / (1024 * 1024 * 1024):.2f} GB"

    def _toggle_all(self):
        """Toggle all checkboxes."""
        val = self.select_all_var.get()
        for info in self.trash_info:
            info['var'].set(val)

    def _update_summary(self):
        """Update the summary label with selected totals."""
        selected_files = 0
        selected_size = 0
        for info in self.trash_info:
            if info['var'].get():
                selected_files += info['file_count']
                selected_size += info['byte_size']

        if selected_files > 0:
            self.summary_label.config(
                text=f"Selected: {selected_files} files, {self._format_size(selected_size)}")
        else:
            total_files = sum(i['file_count'] for i in self.trash_info)
            total_size = sum(i['byte_size'] for i in self.trash_info)
            self.summary_label.config(
                text=f"Total: {total_files} files, {self._format_size(total_size)}")

    def _delete_selected(self):
        """Delete contents of selected trash folders."""
        selected = [info for info in self.trash_info if info['var'].get()]
        if not selected:
            messagebox.showinfo("Nothing Selected", "Select at least one folder to delete.",
                              parent=self.window)
            return

        total_files = sum(i['file_count'] for i in selected)
        total_size = self._format_size(sum(i['byte_size'] for i in selected))
        folder_names = "\n".join(
            f"  {os.path.relpath(i['path'], os.path.dirname(os.path.abspath(__file__)))}"
            for i in selected
        )

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Permanently delete {total_files} files ({total_size}) from:\n\n"
            f"{folder_names}\n\n"
            f"This cannot be undone. Continue?",
            parent=self.window
        )
        if not confirm:
            return

        # Delete contents (keep the folder structure)
        deleted = 0
        errors = 0
        for info in selected:
            path = info['path']
            try:
                for entry in os.scandir(path):
                    try:
                        if entry.is_dir():
                            shutil.rmtree(entry.path)
                        else:
                            os.remove(entry.path)
                        deleted += 1
                    except Exception:
                        errors += 1
            except (PermissionError, OSError):
                errors += 1

        if errors > 0:
            messagebox.showwarning("Partial Cleanup",
                                  f"Deleted {deleted} items with {errors} errors.",
                                  parent=self.window)
        else:
            messagebox.showinfo("Cleanup Complete",
                               f"Deleted {deleted} items successfully.",
                               parent=self.window)

        self.window.destroy()
