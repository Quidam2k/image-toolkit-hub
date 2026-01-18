import tkinter as tk
from tkinter import ttk
import threading
import time

import toast_manager


class AutoSortProgressDialog(tk.Toplevel):
    """Progress dialog for auto-sort operations."""
    
    def __init__(self, parent, operation_name="Auto-Sorting"):
        super().__init__(parent)
        self.parent = parent
        self.operation_name = operation_name
        self.cancelled = False
        self.paused = False
        
        self.setup_ui()
        self.setup_modal_behavior()
    
    def setup_ui(self):
        """Create the progress dialog interface."""
        self.title(f"{self.operation_name} Progress")
        self.geometry("500x350")
        self.resizable(False, False)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.operation_name,
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Initializing...",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=450,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # Progress text
        self.progress_text = ttk.Label(
            main_frame,
            text="0 / 0 (0%)",
            font=("Arial", 9)
        )
        self.progress_text.pack(pady=(0, 10))
        
        # Current file label
        self.file_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 8),
            foreground="gray",
            wraplength=450
        )
        self.file_label.pack(pady=(0, 15))
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill="x", pady=(0, 15))
        
        # Statistics labels
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x")
        
        self.processed_label = ttk.Label(stats_grid, text="Processed: 0")
        self.processed_label.grid(row=0, column=0, sticky="w", padx=(0, 20))
        
        self.sorted_label = ttk.Label(stats_grid, text="Sorted: 0")
        self.sorted_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        self.unmatched_label = ttk.Label(stats_grid, text="Unmatched: 0")
        self.unmatched_label.grid(row=1, column=0, sticky="w", padx=(0, 20))
        
        self.errors_label = ttk.Label(stats_grid, text="Errors: 0")
        self.errors_label.grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        # Time elapsed and ETA
        self.time_label = ttk.Label(stats_grid, text="Elapsed: 00:00")
        self.time_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self.eta_label = ttk.Label(stats_grid, text="ETA: --:--")
        self.eta_label.grid(row=2, column=1, sticky="w", pady=(5, 0))
        
        # Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(10, 0))
        
        self.pause_button = ttk.Button(
            btn_frame,
            text="Pause",
            command=self.toggle_pause,
            state="disabled"
        )
        self.pause_button.pack(side="left", padx=(0, 10))
        
        self.cancel_button = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.cancel_operation
        )
        self.cancel_button.pack(side="left")
        
        self.close_button = ttk.Button(
            btn_frame,
            text="Close",
            command=self.destroy,
            state="disabled"
        )
        self.close_button.pack(side="right")
        
        # Initialize timing
        self.start_time = time.time()
        self.update_timer()
    
    def setup_modal_behavior(self):
        """Set up modal dialog behavior."""
        self.transient(self.parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def update_progress(self, current, total, current_file="", **stats):
        """Update progress display including ETA calculation."""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
            self.progress_text.config(text=f"{current} / {total} ({percentage:.1f}%)")

            # Calculate ETA
            if current > 0 and hasattr(self, 'start_time'):
                elapsed = time.time() - self.start_time
                rate = current / elapsed  # items per second
                remaining = total - current
                if rate > 0:
                    eta_seconds = remaining / rate
                    eta_min = int(eta_seconds // 60)
                    eta_sec = int(eta_seconds % 60)
                    self.eta_label.config(text=f"ETA: {eta_min:02d}:{eta_sec:02d}")
                else:
                    self.eta_label.config(text="ETA: --:--")

        if current_file:
            # Truncate long filenames
            if len(current_file) > 60:
                current_file = current_file[:30] + "..." + current_file[-27:]
            self.file_label.config(text=f"Processing: {current_file}")

        # Update statistics
        if 'processed' in stats:
            self.processed_label.config(text=f"Processed: {stats['processed']}")
        if 'sorted' in stats:
            self.sorted_label.config(text=f"Sorted: {stats['sorted']}")
        if 'unmatched' in stats:
            self.unmatched_label.config(text=f"Unmatched: {stats['unmatched']}")
        if 'errors' in stats:
            error_count = len(stats['errors']) if isinstance(stats['errors'], list) else stats['errors']
            self.errors_label.config(text=f"Errors: {error_count}")

        self.update_idletasks()
    
    def set_status(self, status):
        """Update operation status."""
        self.status_label.config(text=status)
        self.update_idletasks()
    
    def enable_pause_resume(self):
        """Enable pause/resume functionality."""
        self.pause_button.config(state="normal")
    
    def toggle_pause(self):
        """Toggle pause/resume state."""
        if self.paused:
            self.paused = False
            self.pause_button.config(text="Pause")
            self.set_status("Resuming...")
        else:
            self.paused = True
            self.pause_button.config(text="Resume")
            self.set_status("Paused")
    
    def cancel_operation(self):
        """Cancel the current operation."""
        self.cancelled = True
        self.cancel_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.set_status("Cancelling...")
    
    def operation_completed(self, success=True, message="", stats=None):
        """Mark operation as completed."""
        self.pause_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.close_button.config(state="normal")

        if success:
            self.set_status("Completed successfully")
            self.progress_var.set(100)

            # Show toast notification with stats if available
            if stats:
                sorted_count = stats.get('sorted', 0)
                folder_count = len(stats.get('term_counts', {}))
                toast_msg = f"{sorted_count} images sorted to {folder_count} folders"
            else:
                toast_msg = ""
            toast_manager.show_success(f"{self.operation_name} Complete", toast_msg)
        else:
            self.set_status(f"Failed: {message}" if message else "Operation failed")
            toast_manager.show_error(f"{self.operation_name} Failed", message)

        self.file_label.config(text="")

        # Auto-close after a delay if successful
        if success:
            self.after(3000, self.auto_close)
    
    def auto_close(self):
        """Auto-close the dialog if not already closed."""
        if self.winfo_exists():
            self.destroy()
    
    def update_timer(self):
        """Update the elapsed time display."""
        if hasattr(self, 'start_time'):
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.config(text=f"Elapsed: {minutes:02d}:{seconds:02d}")
        
        # Schedule next update
        if not self.cancelled and self.winfo_exists():
            self.after(1000, self.update_timer)
    
    def on_closing(self):
        """Handle window close button."""
        if not self.cancelled:
            self.cancel_operation()
        else:
            self.destroy()
    
    def is_cancelled(self):
        """Check if operation was cancelled."""
        return self.cancelled
    
    def is_paused(self):
        """Check if operation is paused."""
        return self.paused