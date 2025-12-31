import tkinter as tk
from tkinter import ttk
import os

class AutoSortConfirmDialog:
    """Enhanced confirmation dialog for auto-sort operations."""
    
    def __init__(self, parent, config_manager, image_count, terms):
        self.parent = parent
        self.config_manager = config_manager
        self.image_count = image_count
        self.terms = terms
        self.result = None  # None = cancelled, 'move' = move mode, 'copy' = copy mode
        
        self.window = tk.Toplevel(parent)
        self.setup_ui()
        self.setup_modal_behavior()
    
    def setup_ui(self):
        """Create the confirmation dialog UI."""
        self.window.title("Auto-Sort Confirmation")
        # Start with base size, will resize after UI is built
        self.window.geometry("600x400")
        self.window.resizable(True, True)
        
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Auto-Sort Images",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Summary info
        summary_frame = ttk.LabelFrame(main_frame, text="Summary", padding="15")
        summary_frame.pack(fill="x", pady=(0, 15))
        
        enabled_terms = [t for t in self.terms if t.get('enabled', True)]
        
        ttk.Label(summary_frame, text=f"Images to process: {self.image_count}", 
                 font=("Arial", 11, "bold")).pack(anchor="w")
        ttk.Label(summary_frame, text=f"Active terms: {len(enabled_terms)}", 
                 font=("Arial", 11, "bold")).pack(anchor="w")
        
        # Get current settings
        auto_settings = self.config_manager.get_auto_sort_settings()
        
        # Mode info
        mode_frame = ttk.LabelFrame(main_frame, text="Operation Mode", padding="15")
        mode_frame.pack(fill="x", pady=(0, 15))
        
        # Current mode from settings
        current_mode = "COPY" if auto_settings.get('copy_instead_of_move', False) else "MOVE"
        mode_color = "#2196F3" if current_mode == "COPY" else "#FF9800"
        
        # Mode description
        mode_desc = {
            "MOVE": "Images will be moved to destination folders (originals removed from source)",
            "COPY": "Images will be copied to destination folders (originals remain in source)"
        }
        
        ttk.Label(mode_frame, text=f"Current mode: {current_mode}", 
                 font=("Arial", 11, "bold")).pack(anchor="w")
        ttk.Label(mode_frame, text=mode_desc[current_mode], 
                 font=("Arial", 9), foreground="gray").pack(anchor="w", pady=(5, 0))
        
        # Destination info
        dest_frame = ttk.LabelFrame(main_frame, text="Destinations", padding="15")
        dest_frame.pack(fill="x", pady=(0, 15))
        
        # Auto-sorted folder path
        auto_folder = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
        ttk.Label(dest_frame, text=f"Base folder: {auto_folder}/", 
                 font=("Arial", 10)).pack(anchor="w")
        
        # Show sample destinations
        sample_terms = [t['folder_name'] for t in enabled_terms[:3]]
        if sample_terms:
            sample_text = "Subfolders: " + ", ".join(f"{auto_folder}/{term}/" for term in sample_terms)
            if len(enabled_terms) > 3:
                sample_text += f" (+{len(enabled_terms)-3} more)"
            ttk.Label(dest_frame, text=sample_text, 
                     font=("Arial", 9), foreground="gray").pack(anchor="w", pady=(5, 0))
        
        # Handling rules
        rules_frame = ttk.LabelFrame(main_frame, text="Handling Rules", padding="15")
        rules_frame.pack(fill="x", pady=(0, 15))
        
        multiple_rule = auto_settings.get('handle_multiple_matches', 'first_match')
        no_match_rule = auto_settings.get('handle_no_matches', 'leave_in_place')
        
        ttk.Label(rules_frame, text=f"Multiple matches: {multiple_rule.replace('_', ' ').title()}", 
                 font=("Arial", 10)).pack(anchor="w")
        ttk.Label(rules_frame, text=f"No matches: {no_match_rule.replace('_', ' ').title()}", 
                 font=("Arial", 10)).pack(anchor="w")
        
        # Terms list
        terms_frame = ttk.LabelFrame(main_frame, text="Active Terms (by priority)", padding="15")
        terms_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Calculate terms display height
        terms_display_height = max(3, min(len(enabled_terms), 8))  # 3-8 lines
        
        # Create scrollable terms list
        terms_text = tk.Text(terms_frame, height=terms_display_height, font=("Arial", 9), 
                            wrap=tk.WORD, state=tk.DISABLED)
        terms_scroll = ttk.Scrollbar(terms_frame, orient="vertical", command=terms_text.yview)
        terms_text.configure(yscrollcommand=terms_scroll.set)
        
        terms_text.pack(side="left", fill="both", expand=True)
        terms_scroll.pack(side="right", fill="y")
        
        # Populate terms
        terms_text.config(state=tk.NORMAL)
        sorted_terms = sorted(enabled_terms, key=lambda x: x.get('priority', 999))
        for i, term in enumerate(sorted_terms, 1):
            match_type = term.get('match_type', 'word_boundary').replace('_', ' ')
            folder = term.get('folder_name', term['term'])
            terms_text.insert(tk.END, f"{i:2d}. {term['term']} → {folder}/ ({match_type})\n")
        terms_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Action buttons
        ttk.Button(button_frame, text="Cancel", 
                  command=self.cancel).pack(side="right", padx=(10, 0))
        
        # Mode-specific buttons
        copy_btn = ttk.Button(button_frame, text="📋 Copy Mode", 
                             command=self.copy_mode)
        copy_btn.pack(side="right", padx=(5, 0))
        
        move_btn = ttk.Button(button_frame, text="📁 Move Mode", 
                             command=self.move_mode)
        move_btn.pack(side="right")
        
        # Info label
        info_text = "Choose 'Move Mode' to relocate images or 'Copy Mode' to keep originals in place"
        ttk.Label(button_frame, text=info_text, 
                 font=("Arial", 8), foreground="gray").pack(side="left")
        
        # Auto-resize window to fit content
        self.auto_resize_window()
    
    def auto_resize_window(self):
        """Automatically resize window to fit all content."""
        self.window.update_idletasks()
        
        # Get the required size for all content
        req_width = self.window.winfo_reqwidth()
        req_height = self.window.winfo_reqheight()
        
        # Add some padding
        final_width = max(600, req_width + 40)
        final_height = max(400, req_height + 40)
        
        # Limit maximum size to screen size
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        final_width = min(final_width, int(screen_width * 0.8))
        final_height = min(final_height, int(screen_height * 0.8))
        
        self.window.geometry(f"{final_width}x{final_height}")
    
    def setup_modal_behavior(self):
        """Set up modal behavior."""
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Bind Escape key to cancel
        self.window.bind('<Escape>', lambda e: self.cancel())
        
        # Center on parent
        self.window.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.window.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
    
    def move_mode(self):
        """User chose move mode."""
        self.result = 'move'
        self.window.destroy()
    
    def copy_mode(self):
        """User chose copy mode."""
        self.result = 'copy'
        self.window.destroy()
    
    def cancel(self):
        """User cancelled."""
        self.result = None
        self.window.destroy()
    
    def show(self):
        """Show the dialog and return the result."""
        self.window.wait_window()
        return self.result

def show_auto_sort_confirm(parent, config_manager, image_count, terms):
    """Show the auto-sort confirmation dialog."""
    dialog = AutoSortConfirmDialog(parent, config_manager, image_count, terms)
    return dialog.show()