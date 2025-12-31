"""
Unmatched Images Viewer for Image Grid Sorter

Provides a comprehensive interface for browsing unmatched images and their metadata
to help users identify potential new search terms and categories.

Features:
- Grid view of unmatched images with thumbnails
- Detailed metadata display for selected images
- Quick term suggestion based on common patterns
- Direct integration with Term Manager for adding new categories
- Search and filter capabilities within unmatched collection

Author: Claude Code Implementation
Version: 2.1 (New metadata inspection tool)
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
from collections import Counter
import re
from metadata_parser import MetadataParser

class UnmatchedViewerDialog(tk.Toplevel):
    """
    Dialog for browsing unmatched images and analyzing their metadata.
    
    Helps users identify patterns in unmatched images to determine what
    new search terms should be added to improve auto-sorting coverage.
    """
    
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.metadata_parser = MetadataParser()
        
        # Data storage
        self.unmatched_images = []
        self.current_selection = None
        self.thumbnails = {}
        self.metadata_cache = {}
        
        self.setup_ui()
        self.setup_modal_behavior()
        self.load_unmatched_images()
    
    def setup_ui(self):
        """Create the unmatched viewer interface."""
        self.title("Unmatched Images Viewer")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title and info
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            title_frame,
            text="Unmatched Images",
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        self.info_label = ttk.Label(title_frame, text="Loading...")
        self.info_label.pack(side="right")
        
        # Create paned window for image grid and metadata
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)
        
        # Left panel - image grid
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Image grid with scrollbar
        grid_frame = ttk.Frame(left_frame)
        grid_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(grid_frame, bg="white")
        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Right panel - metadata and analysis
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # Metadata display
        metadata_label = ttk.Label(right_frame, text="Image Metadata", font=("Arial", 12, "bold"))
        metadata_label.pack(anchor="w", pady=(0, 5))
        
        self.metadata_text = scrolledtext.ScrolledText(
            right_frame,
            height=15,
            width=40,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.metadata_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # Analysis section
        analysis_label = ttk.Label(right_frame, text="Common Terms", font=("Arial", 12, "bold"))
        analysis_label.pack(anchor="w", pady=(0, 5))
        
        self.analysis_text = scrolledtext.ScrolledText(
            right_frame,
            height=8,
            width=40,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.analysis_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # Action buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(
            btn_frame,
            text="Analyze Terms",
            command=self.analyze_common_terms
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="Open Term Manager",
            command=self.open_term_manager
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="Refresh",
            command=self.refresh_images
        ).pack(side="right")
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(bottom_frame, text="Close", command=self.destroy).pack(side="right")
    
    def setup_modal_behavior(self):
        """Set up modal dialog behavior."""
        self.transient(self.parent)
        
        # Center on parent
        self.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def load_unmatched_images(self):
        """Load images from the unmatched folder."""
        unmatched_folder = self.config_manager.sorted_folders.get('unmatched')
        if not unmatched_folder or not os.path.exists(unmatched_folder):
            self.info_label.config(text="No unmatched folder found")
            self.metadata_text.insert("1.0", "No unmatched folder found. Make sure auto-sort has been run with 'move_to_unmatched' option enabled.")
            return
        
        # Find all image files in unmatched folder
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.unmatched_images = []
        
        for filename in os.listdir(unmatched_folder):
            if os.path.splitext(filename.lower())[1] in image_extensions:
                full_path = os.path.join(unmatched_folder, filename)
                self.unmatched_images.append(full_path)
        
        if not self.unmatched_images:
            self.info_label.config(text="No unmatched images found")
            self.metadata_text.insert("1.0", "No images found in unmatched folder. This means either:\n\n1. All images have been successfully categorized\n2. Auto-sort hasn't been run yet\n3. 'No Matches' setting is set to 'leave_in_place'")
            return
        
        self.info_label.config(text=f"Found {len(self.unmatched_images)} unmatched images")
        
        # Start loading thumbnails in background
        threading.Thread(target=self.load_thumbnails_async, daemon=True).start()
    
    def load_thumbnails_async(self):
        """Load image thumbnails in background thread."""
        for i, image_path in enumerate(self.unmatched_images):
            try:
                # Load and resize image
                with Image.open(image_path) as img:
                    img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    self.thumbnails[image_path] = photo
                
                # Update UI in main thread
                self.after(0, self.add_thumbnail_to_grid, image_path, i)
                
            except Exception as e:
                print(f"Error loading thumbnail for {image_path}: {e}")
        
        # Update grid layout after all thumbnails loaded
        self.after(0, self.update_grid_layout)
    
    def add_thumbnail_to_grid(self, image_path, index):
        """Add a thumbnail to the grid display."""
        if image_path not in self.thumbnails:
            return
        
        # Calculate grid position
        cols = 4  # Number of columns
        row = index // cols
        col = index % cols
        
        # Create frame for this thumbnail
        thumb_frame = ttk.Frame(self.scrollable_frame)
        thumb_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Add thumbnail button
        photo = self.thumbnails[image_path]
        btn = tk.Button(
            thumb_frame,
            image=photo,
            command=lambda path=image_path: self.select_image(path),
            relief="raised",
            bd=2
        )
        btn.pack()
        
        # Add filename label
        filename = os.path.basename(image_path)
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        ttk.Label(
            thumb_frame,
            text=filename,
            font=("Arial", 8),
            anchor="center"
        ).pack()
    
    def update_grid_layout(self):
        """Update the scrollable region after loading thumbnails."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def select_image(self, image_path):
        """Handle image selection and display metadata."""
        self.current_selection = image_path
        
        # Clear metadata display
        self.metadata_text.delete("1.0", tk.END)
        self.metadata_text.insert("1.0", "Loading metadata...")
        
        # Load metadata in background
        threading.Thread(
            target=self.load_metadata_async,
            args=(image_path,),
            daemon=True
        ).start()
    
    def load_metadata_async(self, image_path):
        """Load image metadata in background thread."""
        try:
            # Extract metadata
            metadata = self.metadata_parser.extract_metadata(image_path)
            self.metadata_cache[image_path] = metadata
            
            # Update UI in main thread
            self.after(0, self.display_metadata, image_path, metadata)
            
        except Exception as e:
            error_msg = f"Error loading metadata: {str(e)}"
            self.after(0, self.display_metadata, image_path, None, error_msg)
    
    def display_metadata(self, image_path, metadata, error=None):
        """Display metadata for selected image."""
        if self.current_selection != image_path:
            return  # Selection changed while loading
        
        self.metadata_text.delete("1.0", tk.END)
        
        if error:
            self.metadata_text.insert("1.0", error)
            return
        
        if not metadata:
            self.metadata_text.insert("1.0", "No metadata found for this image.\n\nThis could mean:\n- Image has no embedded parameters\n- No companion .txt file found\n- Metadata extraction failed")
            return
        
        # Display formatted metadata
        filename = os.path.basename(image_path)
        output = f"File: {filename}\n\n"
        
        for key, value in metadata.items():
            if isinstance(value, str) and value.strip():
                output += f"{key.upper()}:\n{value}\n\n"
            elif value:
                output += f"{key.upper()}: {value}\n\n"
        
        self.metadata_text.insert("1.0", output)
    
    def analyze_common_terms(self):
        """Analyze all unmatched images to find common terms."""
        self.analysis_text.delete("1.0", tk.END)
        self.analysis_text.insert("1.0", "Analyzing metadata...")
        
        # Run analysis in background
        threading.Thread(target=self.analyze_terms_async, daemon=True).start()
    
    def analyze_terms_async(self):
        """Analyze metadata for common terms in background thread."""
        try:
            all_words = []
            processed_count = 0
            
            for image_path in self.unmatched_images:
                # Use cached metadata if available
                if image_path in self.metadata_cache:
                    metadata = self.metadata_cache[image_path]
                else:
                    metadata = self.metadata_parser.extract_metadata(image_path)
                    self.metadata_cache[image_path] = metadata
                
                if metadata:
                    # Extract words from all text fields
                    for key, value in metadata.items():
                        if isinstance(value, str):
                            # Split on common delimiters and clean words
                            words = re.findall(r'\b[a-zA-Z]{3,}\b', value.lower())
                            all_words.extend(words)
                
                processed_count += 1
                
                # Update progress occasionally
                if processed_count % 10 == 0:
                    progress_text = f"Analyzing... {processed_count}/{len(self.unmatched_images)}"
                    self.after(0, self.update_analysis_text, progress_text)
            
            # Count word frequencies
            word_counts = Counter(all_words)
            
            # Filter out common/stop words
            stop_words = {
                'the', 'and', 'with', 'for', 'are', 'this', 'that', 'have', 'from',
                'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time',
                'very', 'when', 'come', 'here', 'how', 'just', 'like', 'long',
                'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well',
                'were', 'will', 'about', 'can', 'could', 'get', 'has', 'him',
                'his', 'her', 'into', 'its', 'may', 'new', 'now', 'old', 'see',
                'two', 'who', 'boy', 'did', 'down', 'each', 'end', 'few', 'got',
                'had', 'has', 'her', 'him', 'his', 'how', 'man', 'new', 'now',
                'old', 'put', 'say', 'she', 'too', 'use', 'was', 'way', 'who',
                'you', 'all', 'any', 'but', 'day', 'get', 'her', 'him', 'his',
                'how', 'its', 'let', 'may', 'new', 'not', 'now', 'old', 'our',
                'out', 'say', 'she', 'too', 'two', 'use', 'was', 'way', 'who',
                'win', 'yes', 'yet', 'you', 'big', 'box', 'can', 'car', 'cut',
                'dog', 'eat', 'end', 'far', 'fly', 'fun', 'got', 'gun', 'hat',
                'hit', 'job', 'key', 'leg', 'let', 'map', 'men', 'mix', 'net',
                'oil', 'own', 'pay', 'put', 'red', 'run', 'sat', 'six', 'sit',
                'ten', 'top', 'try', 'win', 'yes'
            }
            
            # Get most common words (excluding stop words)
            common_words = [
                (word, count) for word, count in word_counts.most_common(50)
                if word not in stop_words and len(word) >= 3
            ]
            
            # Update UI with results
            self.after(0, self.display_analysis_results, common_words, processed_count)
            
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            self.after(0, self.update_analysis_text, error_msg)
    
    def update_analysis_text(self, text):
        """Update analysis text display."""
        self.analysis_text.delete("1.0", tk.END)
        self.analysis_text.insert("1.0", text)
    
    def display_analysis_results(self, common_words, processed_count):
        """Display the results of term analysis."""
        self.analysis_text.delete("1.0", tk.END)
        
        if not common_words:
            self.analysis_text.insert("1.0", f"Analyzed {processed_count} images.\n\nNo significant terms found. This could mean:\n- Images have very little metadata\n- Terms are too varied to show patterns\n- All meaningful terms are already configured")
            return
        
        output = f"Analyzed {processed_count} images\n\n"
        output += "Most Common Terms:\n"
        output += "-" * 20 + "\n"
        
        for word, count in common_words[:25]:
            percentage = (count / processed_count) * 100
            output += f"{word:<15} {count:>3} ({percentage:4.1f}%)\n"
        
        output += "\n" + "=" * 30 + "\n"
        output += "Suggested Actions:\n"
        output += "- Review terms with high frequency\n"
        output += "- Consider adding promising terms\n"
        output += "- Use 'Open Term Manager' to add terms\n"
        output += "- Re-run auto-sort after adding terms"
        
        self.analysis_text.insert("1.0", output)
    
    def open_term_manager(self):
        """Open the Term Manager dialog."""
        try:
            # Import and create Term Manager dialog
            from term_manager import TermManagerDialog
            dialog = TermManagerDialog(self.parent, self.config_manager)
            dialog.wait_window()
            
            # After term manager closes, offer to refresh this view
            if messagebox.askyesno(
                "Refresh",
                "Term Manager closed. Would you like to refresh the unmatched images view?",
                parent=self
            ):
                self.refresh_images()
                
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not open Term Manager: {str(e)}",
                parent=self
            )
    
    def refresh_images(self):
        """Refresh the unmatched images display."""
        # Clear current data
        self.unmatched_images = []
        self.thumbnails = {}
        self.metadata_cache = {}
        self.current_selection = None
        
        # Clear UI
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.metadata_text.delete("1.0", tk.END)
        self.analysis_text.delete("1.0", tk.END)
        
        # Reload
        self.load_unmatched_images()


def show_unmatched_viewer(parent, config_manager):
    """Show the unmatched images viewer dialog."""
    dialog = UnmatchedViewerDialog(parent, config_manager)
    return dialog