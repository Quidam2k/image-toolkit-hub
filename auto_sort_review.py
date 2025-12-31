import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import json
import shutil
from datetime import datetime

class AutoSortReviewDialog(tk.Toplevel):
    """Review and undo auto-sort results."""
    
    def __init__(self, parent, sort_results, config_manager):
        super().__init__(parent)
        self.parent = parent
        self.sort_results = sort_results
        self.config_manager = config_manager
        self.metadata_parser = None
        
        # Import metadata parser
        try:
            from metadata_parser import MetadataParser
            self.metadata_parser = MetadataParser()
        except ImportError:
            pass
        
        self.current_category = None
        self.category_files = {}
        self.image_cache = {}
        
        self.setup_ui()
        self.setup_modal_behavior()
        self.populate_categories()
    
    def setup_ui(self):
        """Create the review interface."""
        self.title("Auto-Sort Review")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title and summary
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(title_frame, text="Auto-Sort Review", 
                 font=("Arial", 16, "bold")).pack(side="left")
        
        # Summary info
        summary_text = f"Sorted: {self.sort_results.get('sorted', 0)} | Errors: {len(self.sort_results.get('errors', []))}"
        ttk.Label(title_frame, text=summary_text, 
                 font=("Arial", 10)).pack(side="right")
        
        # Create paned window for layout
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, pady=(0, 10))
        
        # Left panel - Categories
        left_frame = ttk.LabelFrame(paned, text="Categories", padding="10")
        paned.add(left_frame, weight=1)
        
        # Category listbox
        self.category_listbox = tk.Listbox(left_frame, font=("Arial", 11))
        self.category_listbox.pack(fill="both", expand=True, pady=(0, 10))
        self.category_listbox.bind('<<ListboxSelect>>', self.on_category_select)
        
        # Category buttons
        cat_btn_frame = ttk.Frame(left_frame)
        cat_btn_frame.pack(fill="x")
        
        ttk.Button(cat_btn_frame, text="Browse Folder", 
                  command=self.browse_category_folder).pack(side="left", padx=(0, 5))
        
        # Right panel - Images
        right_frame = ttk.LabelFrame(paned, text="Images", padding="10")
        paned.add(right_frame, weight=3)
        
        # Image grid
        self.setup_image_grid(right_frame)
        
        # Bottom panel - Actions
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        # Undo button
        ttk.Button(action_frame, text="Undo All Changes", 
                  command=self.undo_auto_sort).pack(side="left")
        
        # Error summary (only show if there are actual errors)
        actual_errors = len([e for e in self.sort_results.get('errors', []) if e.get('category') != 'no_matches'])
        if actual_errors > 0:
            ttk.Button(action_frame, text=f"View Errors ({actual_errors})", 
                      command=self.show_error_summary).pack(side="left", padx=(10, 0))
        
        # Close button
        ttk.Button(action_frame, text="Close", 
                  command=self.destroy).pack(side="right")
    
    def setup_image_grid(self, parent):
        """Set up the image grid display."""
        # Create scrollable frame
        canvas = tk.Canvas(parent, bg="white")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.image_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configure scrolling
        canvas.create_window((0, 0), window=self.image_frame, anchor="nw")
        self.image_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.canvas = canvas
    
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
    
    def populate_categories(self):
        """Populate the categories list."""
        term_counts = self.sort_results.get('term_counts', {})
        
        for term, count in sorted(term_counts.items(), key=lambda x: x[1], reverse=True):
            display_text = f"{term} ({count} images)"
            self.category_listbox.insert(tk.END, display_text)
            self.category_files[term] = self.find_files_for_term(term)
    
    def find_files_for_term(self, term):
        """Find files that were sorted to this term."""
        files = []
        
        try:
            if term == 'Unmatched':
                # For unmatched, files are still in original location
                unmatched_files = self.sort_results.get('unmatched_files', [])
                return [item['file'] for item in unmatched_files]
            else:
                # Get the auto-sort base folder
                auto_sort_folder = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
                term_folder = os.path.join(auto_sort_folder, term)
                
                if os.path.exists(term_folder):
                    for file in os.listdir(term_folder):
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                            files.append(os.path.join(term_folder, file))
        except Exception as e:
            print(f"Error finding files for term {term}: {e}")
        
        return files
    
    def on_category_select(self, event):
        """Handle category selection."""
        selection = self.category_listbox.curselection()
        if not selection:
            return
        
        # Extract term name from display text
        display_text = self.category_listbox.get(selection[0])
        term = display_text.split(' (')[0]
        
        self.current_category = term
        self.load_category_images(term)
    
    def load_category_images(self, term):
        """Load and display images for the selected category."""
        # Clear existing images
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        
        files = self.category_files.get(term, [])
        if not files:
            ttk.Label(self.image_frame, text=f"No images found for '{term}'").pack(pady=20)
            return
        
        # Create grid of images
        row = 0
        col = 0
        max_cols = 4
        
        for file_path in files[:20]:  # Limit to first 20 for performance
            try:
                self.create_image_thumbnail(file_path, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            except Exception as e:
                print(f"Error creating thumbnail for {file_path}: {e}")
        
        # Update scroll region
        self.image_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_image_thumbnail(self, file_path, row, col):
        """Create a clickable image thumbnail."""
        try:
            # Load and resize image
            with Image.open(file_path) as img:
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
            
            # Create frame for thumbnail
            thumb_frame = ttk.Frame(self.image_frame)
            thumb_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
            
            # Image label
            img_label = tk.Label(thumb_frame, image=photo, cursor="hand2")
            img_label.pack()
            img_label.image = photo  # Keep reference
            
            # Filename label
            filename = os.path.basename(file_path)
            if len(filename) > 20:
                filename = filename[:17] + "..."
            ttk.Label(thumb_frame, text=filename, font=("Arial", 8)).pack()
            
            # Bind click event
            img_label.bind("<Button-1>", lambda e, path=file_path: self.show_image_metadata(path))
            
        except Exception as e:
            # Create error placeholder
            error_frame = ttk.Frame(self.image_frame)
            error_frame.grid(row=row, column=col, padx=5, pady=5)
            ttk.Label(error_frame, text="Error loading\nimage", 
                     background="lightgray", width=15).pack()
    
    def show_image_metadata(self, file_path):
        """Show metadata for the selected image."""
        if not self.metadata_parser:
            messagebox.showwarning("Warning", "Metadata parser not available")
            return
        
        # Create metadata dialog
        metadata_dialog = tk.Toplevel(self)
        metadata_dialog.title(f"Metadata - {os.path.basename(file_path)}")
        metadata_dialog.geometry("600x500")
        metadata_dialog.transient(self)
        
        # Create scrollable text widget
        main_frame = ttk.Frame(metadata_dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Image preview
        try:
            with Image.open(file_path) as img:
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(main_frame, image=photo)
            img_label.pack(pady=(0, 10))
            img_label.image = photo  # Keep reference
        except:
            ttk.Label(main_frame, text="Could not load image preview").pack(pady=(0, 10))
        
        # Metadata text
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Extract and display metadata
        metadata = self.metadata_parser.extract_metadata(file_path)
        
        if metadata:
            text_widget.insert(tk.END, f"File: {os.path.basename(file_path)}\n")
            text_widget.insert(tk.END, f"Path: {file_path}\n\n")

            for key, value in metadata.items():
                text_widget.insert(tk.END, f"{key}:\n")
                if isinstance(value, str):
                    # Format long strings nicely
                    if len(value) > 80:
                        lines = [value[i:i+80] for i in range(0, len(value), 80)]
                        for line in lines:
                            text_widget.insert(tk.END, f"  {line}\n")
                    else:
                        text_widget.insert(tk.END, f"  {value}\n")
                else:
                    text_widget.insert(tk.END, f"  {value}\n")
                text_widget.insert(tk.END, "\n")
        else:
            text_widget.insert(tk.END, "No metadata found for this image.")
        
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(main_frame, text="Close", 
                  command=metadata_dialog.destroy).pack(pady=(10, 0))
    
    def browse_category_folder(self):
        """Open the category folder in file explorer."""
        if not self.current_category:
            messagebox.showwarning("Warning", "Please select a category first")
            return
        
        auto_sort_folder = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
        folder_path = os.path.join(auto_sort_folder, self.current_category)
        
        if os.path.exists(folder_path):
            # Open in file explorer (Windows/Mac/Linux compatible)
            try:
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    subprocess.run(["explorer", folder_path])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", folder_path])
                else:  # Linux
                    subprocess.run(["xdg-open", folder_path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")
        else:
            messagebox.showwarning("Warning", f"Folder not found: {folder_path}")
    
    def show_error_summary(self):
        """Show detailed error summary."""
        error_categories = self.sort_results.get('error_categories', {})
        errors = self.sort_results.get('errors', [])
        
        # Create error dialog
        error_dialog = tk.Toplevel(self)
        error_dialog.title("Auto-Sort Errors")
        error_dialog.geometry("700x500")
        error_dialog.transient(self)
        
        main_frame = ttk.Frame(error_dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Summary
        summary_text = "Actual Errors Summary:\n"
        for category, count in error_categories.items():
            if count > 0 and category != 'no_matches':
                summary_text += f"• {category.replace('_', ' ').title()}: {count}\n"
        
        ttk.Label(main_frame, text=summary_text, font=("Arial", 10)).pack(anchor="w", pady=(0, 10))
        
        # Detailed errors
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Show first 50 errors
        for i, error in enumerate(errors[:50]):
            filename = os.path.basename(error['file'])
            category = error.get('category', 'unknown')
            text_widget.insert(tk.END, f"{i+1}. [{category}] {filename}\n")
            text_widget.insert(tk.END, f"   {error['error']}\n")
            if error.get('debug'):
                text_widget.insert(tk.END, f"   Debug: {error['debug']}\n")
            text_widget.insert(tk.END, "\n")
        
        if len(errors) > 50:
            text_widget.insert(tk.END, f"... and {len(errors) - 50} more errors")
        
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(main_frame, text="Close", 
                  command=error_dialog.destroy).pack(pady=(10, 0))
    
    def undo_auto_sort(self):
        """Undo the auto-sort operation."""
        movements = self.sort_results.get('file_movements', [])
        
        if not movements:
            messagebox.showinfo("Nothing to Undo", "No file movements to undo in this auto-sort operation.")
            return
        
        # Show detailed confirmation
        move_count = len([m for m in movements if m['operation'] == 'move'])
        copy_count = len([m for m in movements if m['operation'] == 'copy'])
        
        confirm_msg = f"This will undo the auto-sort operation:\n\n"
        if move_count > 0:
            confirm_msg += f"• Move {move_count} files back to original locations\n"
        if copy_count > 0:
            confirm_msg += f"• Delete {copy_count} copied files\n"
        confirm_msg += f"\nTotal operations: {len(movements)}\n\nContinue?"
        
        if not messagebox.askyesno("Confirm Undo", confirm_msg):
            return
        
        # Create progress dialog
        progress_dialog = tk.Toplevel(self)
        progress_dialog.title("Undoing Auto-Sort")
        progress_dialog.geometry("400x200")
        progress_dialog.transient(self)
        progress_dialog.grab_set()
        
        # Center the dialog
        progress_dialog.update_idletasks()
        x = (self.winfo_x() + self.winfo_width() // 2 - progress_dialog.winfo_width() // 2)
        y = (self.winfo_y() + self.winfo_height() // 2 - progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        # Progress widgets
        ttk.Label(progress_dialog, text="Undoing auto-sort...", font=("Arial", 12)).pack(pady=20)
        progress_var = tk.StringVar(value="Starting...")
        progress_label = ttk.Label(progress_dialog, textvariable=progress_var)
        progress_label.pack(pady=10)
        
        progress_bar = ttk.Progressbar(progress_dialog, maximum=len(movements))
        progress_bar.pack(pady=20, padx=20, fill='x')
        
        def update_ui(text, value):
            """Thread-safe UI update via after()."""
            if progress_dialog.winfo_exists():
                progress_var.set(text)
                progress_bar['value'] = value

        def show_completion(success_count, error_count, errors):
            """Show completion message on main thread."""
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()

            result_msg = f"Undo completed!\n\n"
            result_msg += f"Successfully undone: {success_count}\n"
            if error_count > 0:
                result_msg += f"Errors: {error_count}\n\n"
                result_msg += "\n".join(errors[:5])
                if len(errors) > 5:
                    result_msg += f"\n... and {len(errors) - 5} more errors"

            if error_count == 0:
                messagebox.showinfo("Undo Complete", result_msg)
            else:
                messagebox.showwarning("Undo Complete with Errors", result_msg)

            # Close the review dialog since the sort has been undone
            self.destroy()

        def show_error(error_msg):
            """Show error message on main thread."""
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()
            messagebox.showerror("Undo Failed", f"Failed to undo auto-sort: {error_msg}")

        def run_undo():
            success_count = 0
            error_count = 0
            errors = []

            try:
                # Reverse the movements (newest first)
                for i, movement in enumerate(reversed(movements)):
                    # Schedule UI update on main thread
                    text = f"Undoing {i+1}/{len(movements)}: {os.path.basename(movement['destination'])}"
                    progress_dialog.after(0, lambda t=text, v=i+1: update_ui(t, v))

                    try:
                        if movement['operation'] == 'move':
                            # Move file back to original location
                            if os.path.exists(movement['destination']):
                                # Ensure original directory exists
                                os.makedirs(os.path.dirname(movement['source']), exist_ok=True)
                                shutil.move(movement['destination'], movement['source'])
                                success_count += 1
                            else:
                                errors.append(f"File not found: {movement['destination']}")
                                error_count += 1

                        elif movement['operation'] == 'copy':
                            # Delete the copied file
                            if os.path.exists(movement['destination']):
                                os.remove(movement['destination'])
                                success_count += 1
                            else:
                                errors.append(f"Copy not found: {movement['destination']}")
                                error_count += 1

                    except Exception as e:
                        error_msg = f"Error undoing {movement['destination']}: {e}"
                        errors.append(error_msg)
                        error_count += 1

                # Schedule completion on main thread
                progress_dialog.after(0, lambda: show_completion(success_count, error_count, errors))

            except Exception as e:
                # Schedule error display on main thread
                progress_dialog.after(0, lambda err=str(e): show_error(err))

        # Run undo in separate thread
        import threading
        threading.Thread(target=run_undo, daemon=True).start()

def show_auto_sort_review(parent, sort_results, config_manager):
    """Show the auto-sort review dialog."""
    dialog = AutoSortReviewDialog(parent, sort_results, config_manager)
    return dialog