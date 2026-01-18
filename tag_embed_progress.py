import tkinter as tk
from tkinter import ttk
import threading
import time

import toast_manager


class TagEmbedProgressDialog(tk.Toplevel):
    """Progress dialog for tag embedding operations."""
    
    def __init__(self, parent, folder_path):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = folder_path
        self.cancelled = False
        self.paused = False
        
        self.setup_ui()
        self.setup_modal_behavior()
        
    def setup_ui(self):
        """Create the progress dialog interface."""
        self.title("Embedding Tag Files into Images")
        self.geometry("600x300")
        self.resizable(True, True)
        
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Embedding Tag Files into Image Metadata",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Folder info
        folder_label = ttk.Label(
            main_frame,
            text=f"Processing folder: {self.folder_path}",
            wraplength=550
        )
        folder_label.pack(pady=(0, 20))
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill="x", pady=(0, 20))
        
        # Overall progress bar
        self.overall_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.overall_progress.pack(fill="x", pady=(0, 10))
        
        # Progress labels
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill="x")
        
        self.progress_label = ttk.Label(progress_info_frame, text="Scanning for images...")
        self.progress_label.pack(side="left")
        
        self.percentage_label = ttk.Label(progress_info_frame, text="0%")
        self.percentage_label.pack(side="right")
        
        # Current file info
        self.current_file_label = ttk.Label(
            progress_frame,
            text="",
            foreground="gray",
            font=("Arial", 9)
        )
        self.current_file_label.pack(anchor="w", pady=(5, 0))
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill="x", pady=(0, 20))
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x")
        
        # Statistics labels
        ttk.Label(stats_grid, text="Images found:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.total_images_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"))
        self.total_images_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_grid, text="Processed:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.processed_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"))
        self.processed_label.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_grid, text="Embedded:").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.success_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"), foreground="green")
        self.success_label.grid(row=1, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_grid, text="Failed:").grid(row=1, column=2, sticky="w", padx=(0, 10))
        self.failed_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"), foreground="red")
        self.failed_label.grid(row=1, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_grid, text="No tags:").grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.no_tags_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"), foreground="orange")
        self.no_tags_label.grid(row=2, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_grid, text="Already embedded:").grid(row=2, column=2, sticky="w", padx=(0, 10))
        self.skipped_label = ttk.Label(stats_grid, text="0", font=("Arial", 9, "bold"), foreground="blue")
        self.skipped_label.grid(row=2, column=3, sticky="w")
        
        # Time estimates
        time_frame = ttk.Frame(stats_frame)
        time_frame.pack(fill="x", pady=(10, 0))
        
        self.elapsed_label = ttk.Label(time_frame, text="Elapsed: 0s", font=("Arial", 8))
        self.elapsed_label.pack(side="left")
        
        self.eta_label = ttk.Label(time_frame, text="", font=("Arial", 8))
        self.eta_label.pack(side="right")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, 10))
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.cancel_operation)
        self.cancel_button.pack(side="left")
        
        self.close_button = ttk.Button(button_frame, text="Close", command=self.destroy, state="disabled")
        self.close_button.pack(side="right")
        
        # Initialize timing
        self.start_time = time.time()
        
    def setup_modal_behavior(self):
        """Set up modal behavior."""
        self.transient(self.parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        # Prevent closing during operation
        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)
        
    def set_total_images(self, total):
        """Set the total number of images to process."""
        self.total_images = total
        self.overall_progress['maximum'] = total
        self.total_images_label.config(text=str(total))
        
    def update_progress(self, processed, success, failed, no_tags, skipped, current_file=""):
        """Update the progress display."""
        # Update progress bar
        self.overall_progress['value'] = processed
        
        # Update percentage
        if self.total_images > 0:
            percentage = (processed / self.total_images) * 100
            self.percentage_label.config(text=f"{percentage:.1f}%")
        
        # Update progress text
        self.progress_label.config(text=f"Processing image {processed} of {self.total_images}")
        
        # Update current file
        if current_file:
            filename = current_file.split('/')[-1] if '/' in current_file else current_file.split('\\')[-1]
            if len(filename) > 50:
                filename = filename[:47] + "..."
            self.current_file_label.config(text=f"Current: {filename}")
        
        # Update statistics
        self.processed_label.config(text=str(processed))
        self.success_label.config(text=str(success))
        self.failed_label.config(text=str(failed))
        self.no_tags_label.config(text=str(no_tags))
        self.skipped_label.config(text=str(skipped))
        
        # Update time estimates
        elapsed = time.time() - self.start_time
        self.elapsed_label.config(text=f"Elapsed: {self.format_time(elapsed)}")
        
        if processed > 0 and processed < self.total_images:
            remaining = self.total_images - processed
            rate = processed / elapsed
            eta = remaining / rate if rate > 0 else 0
            self.eta_label.config(text=f"ETA: {self.format_time(eta)}")
        elif processed >= self.total_images:
            self.eta_label.config(text="Complete!")
        
        # Force UI update
        self.update_idletasks()
        
    def format_time(self, seconds):
        """Format time in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds//60:.0f}m {seconds%60:.0f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
        
    def toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            self.pause_button.config(text="Resume")
            self.progress_label.config(text="Paused...")
        else:
            self.pause_button.config(text="Pause")
            
    def cancel_operation(self):
        """Cancel the operation."""
        self.cancelled = True
        self.progress_label.config(text="Cancelling...")
        self.pause_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        
    def operation_complete(self, stats=None):
        """Called when the operation is complete."""
        self.pause_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.close_button.config(state="normal")
        self.progress_label.config(text="Operation complete!")

        # Show toast notification
        if stats:
            embedded = stats.get('embedded', 0)
            toast_manager.show_success("Tag Embedding Complete", f"{embedded} images processed")
        else:
            toast_manager.show_success("Tag Embedding Complete")

        # Allow normal window closing
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
    def on_close_attempt(self):
        """Handle attempts to close the window during operation."""
        if self.cancelled or not hasattr(self, 'total_images'):
            self.destroy()
        else:
            # Ask if user wants to cancel
            from tkinter import messagebox
            if messagebox.askyesno("Cancel Operation", 
                                 "Do you want to cancel the tag embedding operation?",
                                 parent=self):
                self.cancel_operation()