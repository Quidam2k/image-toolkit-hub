"""
Term Manager Dialog for Image Grid Sorter

Provides a comprehensive interface for managing auto-sort terms including:
- Term configuration with priority, match types, and search scopes
- Multi-tag settings and combination folder options
- Import/export functionality for term collections
- Real-time validation and testing capabilities

Version: 2.1 (Added all_combinations mode support)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import re

class TermManagerDialog(tk.Toplevel):
    """
    Dialog window for managing auto-sort terms and multi-tag settings.
    
    Provides a user-friendly interface for configuring search terms, their priorities,
    match types, search scopes, and multi-tag behavior. Includes validation, testing,
    and import/export capabilities.
    """
    
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.terms = self.config_manager.get_auto_sort_terms().copy()
        
        self.setup_ui()
        self.setup_modal_behavior()
        self.populate_terms()
    
    def setup_ui(self):
        """Create the term manager interface."""
        self.title("Auto-Sort Term Manager")
        self.geometry("600x500")
        self.resizable(True, True)
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Auto-Sort Terms",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Instructions
        info_label = ttk.Label(
            main_frame,
            text="Configure terms to automatically sort images based on metadata content.",
            wraplength=550
        )
        info_label.pack(pady=(0, 15))
        
        # Terms list frame
        list_frame = ttk.LabelFrame(main_frame, text="Search Terms", padding="10")
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Create treeview for terms
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.terms_tree = ttk.Treeview(
            tree_frame,
            columns=("enabled", "priority", "match_type", "case_sensitive"),
            show="tree headings",
            height=12
        )
        
        # Configure columns
        self.terms_tree.heading("#0", text="Term")
        self.terms_tree.heading("enabled", text="Enabled")
        self.terms_tree.heading("priority", text="Priority")
        self.terms_tree.heading("match_type", text="Match Type")
        self.terms_tree.heading("case_sensitive", text="Case Sensitive")
        
        self.terms_tree.column("#0", width=200)
        self.terms_tree.column("enabled", width=70)
        self.terms_tree.column("priority", width=70)
        self.terms_tree.column("match_type", width=100)
        self.terms_tree.column("case_sensitive", width=100)
        
        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.terms_tree.yview)
        self.terms_tree.configure(yscrollcommand=scrollbar.set)
        
        self.terms_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Term control buttons
        term_btn_frame = ttk.Frame(list_frame)
        term_btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(term_btn_frame, text="Add Term", command=self.add_term).pack(side="left", padx=(0, 5))
        ttk.Button(term_btn_frame, text="Edit Term", command=self.edit_term).pack(side="left", padx=(0, 5))
        ttk.Button(term_btn_frame, text="Remove", command=self.remove_term).pack(side="left", padx=(0, 5))
        ttk.Button(term_btn_frame, text="Move Up", command=self.move_term_up).pack(side="left", padx=(0, 15))
        ttk.Button(term_btn_frame, text="Move Down", command=self.move_term_down).pack(side="left", padx=(0, 15))
        ttk.Button(term_btn_frame, text="Test Terms", command=self.test_terms).pack(side="right")
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Auto-Sort Settings", padding="10")
        settings_frame.pack(fill="x", pady=(0, 15))
        
        # Get current settings
        self.settings = self.config_manager.get_auto_sort_settings()
        
        # Settings grid
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill="x")
        
        # Multi-tag mode
        ttk.Label(settings_grid, text="Multi-Tag Mode:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.multi_tag_mode_var = tk.StringVar(value=self.settings.get('multi_tag_mode', 'single_folder'))
        multi_tag_combo = ttk.Combobox(
            settings_grid,
            textvariable=self.multi_tag_mode_var,
            values=['single_folder', 'multi_folder', 'smart_combination', 'all_combinations'],
            state="readonly",
            width=15
        )
        multi_tag_combo.grid(row=0, column=1, sticky="w", padx=(0, 20))
        multi_tag_combo.bind('<<ComboboxSelected>>', self.on_multi_tag_mode_changed)
        
        # Max folders (for multi-folder mode)
        ttk.Label(settings_grid, text="Max Folders:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.max_folders_var = tk.StringVar(value=str(self.settings.get('multi_tag_max_folders', 5)))
        max_folders_entry = ttk.Entry(settings_grid, textvariable=self.max_folders_var, width=5)
        max_folders_entry.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        # Second row - legacy compatibility settings
        ttk.Label(settings_grid, text="Single-Tag Fallback:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(5, 0))
        self.multiple_matches_var = tk.StringVar(value=self.settings.get('handle_multiple_matches', 'first_match'))
        multiple_combo = ttk.Combobox(
            settings_grid,
            textvariable=self.multiple_matches_var,
            values=['first_match', 'most_specific', 'skip'],
            state="readonly",
            width=15
        )
        multiple_combo.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(5, 0))
        
        # No matches handling
        ttk.Label(settings_grid, text="No Matches:").grid(row=1, column=2, sticky="w", padx=(0, 10), pady=(5, 0))
        self.no_matches_var = tk.StringVar(value=self.settings.get('handle_no_matches', 'leave_in_place'))
        no_matches_combo = ttk.Combobox(
            settings_grid,
            textvariable=self.no_matches_var,
            values=['leave_in_place', 'move_to_unmatched'],
            state="readonly",
            width=15
        )
        no_matches_combo.grid(row=1, column=3, sticky="w", pady=(5, 0))
        
        # Combination folder settings
        combo_frame = ttk.Frame(settings_frame)
        combo_frame.pack(fill="x", pady=(10, 0))
        
        self.create_combination_folders_var = tk.BooleanVar(value=self.settings.get('create_combination_folders', False))
        ttk.Checkbutton(
            combo_frame,
            text="Create combination folders",
            variable=self.create_combination_folders_var
        ).pack(side="left", padx=(0, 15))
        
        ttk.Label(combo_frame, text="Separator:").pack(side="left", padx=(0, 5))
        self.combination_separator_var = tk.StringVar(value=self.settings.get('combination_separator', '_'))
        separator_entry = ttk.Entry(combo_frame, textvariable=self.combination_separator_var, width=3)
        separator_entry.pack(side="left", padx=(0, 15))
        
        ttk.Label(combo_frame, text="Min tags:").pack(side="left", padx=(0, 5))
        self.min_combination_tags_var = tk.StringVar(value=str(self.settings.get('min_tags_for_combination', 2)))
        min_tags_entry = ttk.Entry(combo_frame, textvariable=self.min_combination_tags_var, width=3)
        min_tags_entry.pack(side="left", padx=(0, 15))
        
        ttk.Label(combo_frame, text="Max tags:").pack(side="left", padx=(0, 5))
        self.max_combination_tags_var = tk.StringVar(value=str(self.settings.get('max_tags_for_combination', 3)))
        max_tags_entry = ttk.Entry(combo_frame, textvariable=self.max_combination_tags_var, width=3)
        max_tags_entry.pack(side="left")
        
        # Checkboxes for other settings
        checkboxes_frame = ttk.Frame(settings_frame)
        checkboxes_frame.pack(fill="x", pady=(10, 0))
        
        self.create_subfolders_var = tk.BooleanVar(value=self.settings.get('create_subfolders', True))
        ttk.Checkbutton(
            checkboxes_frame,
            text="Create subfolders for terms",
            variable=self.create_subfolders_var
        ).pack(side="left", padx=(0, 20))
        
        self.log_operations_var = tk.BooleanVar(value=self.settings.get('log_operations', True))
        ttk.Checkbutton(
            checkboxes_frame,
            text="Log auto-sort operations",
            variable=self.log_operations_var
        ).pack(side="left")
        
        # Dialog buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Save", command=self.save_changes).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btn_frame, text="Import", command=self.import_terms).pack(side="left")
        ttk.Button(btn_frame, text="Export", command=self.export_terms).pack(side="left", padx=(5, 0))
        
        # Bind double-click to edit
        self.terms_tree.bind("<Double-1>", lambda e: self.edit_term())
    
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
    
    def populate_terms(self):
        """Populate the terms tree with current terms."""
        # Clear existing items
        for item in self.terms_tree.get_children():
            self.terms_tree.delete(item)
        
        # Sort terms by priority
        sorted_terms = sorted(self.terms, key=lambda x: x.get('priority', 999))
        
        # Add terms to tree
        for term_config in sorted_terms:
            self.terms_tree.insert(
                "",
                "end",
                text=term_config['term'],
                values=(
                    "Yes" if term_config.get('enabled', True) else "No",
                    term_config.get('priority', 1),
                    term_config.get('match_type', 'word_boundary'),
                    "Yes" if term_config.get('case_sensitive', False) else "No"
                )
            )
    
    def add_term(self):
        """Add a new term."""
        dialog = TermEditDialog(self, "Add Term")
        dialog.wait_window()  # Wait for dialog to close
        if dialog.result:
            # Check for duplicates
            existing_terms = [t['term'] for t in self.terms]
            if dialog.result['term'] in existing_terms:
                messagebox.showerror("Error", "Term already exists!")
                return
            
            # Set priority
            dialog.result['priority'] = len(self.terms) + 1
            
            self.terms.append(dialog.result)
            self.populate_terms()
            # Auto-save after adding
            self._auto_save()
    
    def edit_term(self):
        """Edit selected term."""
        selection = self.terms_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a term to edit.")
            return
        
        item = selection[0]
        term_text = self.terms_tree.item(item)['text']
        
        # Find the term config
        term_config = next((t for t in self.terms if t['term'] == term_text), None)
        if not term_config:
            return
        
        dialog = TermEditDialog(self, "Edit Term", term_config)
        dialog.wait_window()  # Wait for dialog to close
        if dialog.result:
            # Update the term
            term_config.update(dialog.result)
            self.populate_terms()
            # Auto-save after editing
            self._auto_save()
    
    def remove_term(self):
        """Remove selected term."""
        selection = self.terms_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a term to remove.")
            return
        
        item = selection[0]
        term_text = self.terms_tree.item(item)['text']
        
        if messagebox.askyesno("Confirm", f"Remove term '{term_text}'?"):
            self.terms = [t for t in self.terms if t['term'] != term_text]
            self.populate_terms()
            # Auto-save after removing
            self._auto_save()
    
    def move_term_up(self):
        """Move selected term up in priority."""
        selection = self.terms_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a term to move.")
            return
        
        item = selection[0]
        term_text = self.terms_tree.item(item)['text']
        
        # Find the term and move it up in the list
        for i, term in enumerate(self.terms):
            if term['term'] == term_text and i > 0:
                # Move term up by swapping positions in list
                self.terms[i], self.terms[i-1] = self.terms[i-1], self.terms[i]
                # Update priorities to match new positions
                self._update_priorities()
                self.populate_terms()
                self._select_term(term_text)
                self._auto_save()
                break
    
    def move_term_down(self):
        """Move selected term down in priority."""
        selection = self.terms_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a term to move.")
            return
        
        item = selection[0]
        term_text = self.terms_tree.item(item)['text']
        
        # Find the term and move it down in the list
        for i, term in enumerate(self.terms):
            if term['term'] == term_text and i < len(self.terms) - 1:
                # Move term down by swapping positions in list
                self.terms[i], self.terms[i+1] = self.terms[i+1], self.terms[i]
                # Update priorities to match new positions
                self._update_priorities()
                self.populate_terms()
                self._select_term(term_text)
                self._auto_save()
                break
    
    def _auto_save(self):
        """Automatically save changes to config."""
        try:
            self.config_manager.config['auto_sort_terms'] = self.terms
            self.config_manager.save_config()
        except Exception as e:
            print(f"Warning: Failed to auto-save terms: {e}")
    
    def _update_priorities(self):
        """Update priorities to match current list order."""
        for i, term in enumerate(self.terms):
            term['priority'] = i + 1
    
    def _select_term(self, term_text):
        """Select the specified term in the tree."""
        for item in self.terms_tree.get_children():
            if self.terms_tree.item(item)['text'] == term_text:
                self.terms_tree.selection_set(item)
                self.terms_tree.focus(item)
                break
    
    def test_terms(self):
        """Open term testing dialog."""
        TermTestDialog(self, self.terms)
    
    def import_terms(self):
        """Import terms from file."""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Import Terms",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.config_manager.import_terms(filename, merge=True)
                self.terms = self.config_manager.get_auto_sort_terms().copy()
                self.populate_terms()
                messagebox.showinfo("Success", "Terms imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import terms: {e}")
    
    def export_terms(self):
        """Export terms to file."""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Export Terms",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Temporarily update config with current terms
                old_terms = self.config_manager.config['auto_sort_terms']
                self.config_manager.config['auto_sort_terms'] = self.terms
                self.config_manager.export_terms(filename)
                self.config_manager.config['auto_sort_terms'] = old_terms
                messagebox.showinfo("Success", "Terms exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export terms: {e}")
    
    def save_changes(self):
        """Save changes to configuration."""
        try:
            # Update terms
            self.config_manager.config['auto_sort_terms'] = self.terms
            
            # Validate numeric inputs
            try:
                max_folders = int(self.max_folders_var.get())
                min_combination_tags = int(self.min_combination_tags_var.get())
                max_combination_tags = int(self.max_combination_tags_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid numeric values in settings.")
                return
            
            # Update settings
            self.config_manager.update_auto_sort_settings(
                # Multi-tag settings
                multi_tag_mode=self.multi_tag_mode_var.get(),
                multi_tag_max_folders=max_folders,
                create_combination_folders=self.create_combination_folders_var.get(),
                combination_separator=self.combination_separator_var.get(),
                min_tags_for_combination=min_combination_tags,
                max_tags_for_combination=max_combination_tags,
                # Legacy settings
                handle_multiple_matches=self.multiple_matches_var.get(),
                handle_no_matches=self.no_matches_var.get(),
                create_subfolders=self.create_subfolders_var.get(),
                log_operations=self.log_operations_var.get()
            )
            
            # Recreate folders if needed
            self.config_manager.setup_auto_sort_folders()
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def on_multi_tag_mode_changed(self, event=None):
        """Handle multi-tag mode selection change."""
        mode = self.multi_tag_mode_var.get()
        # Could add mode-specific UI updates here if needed
        # For example, enable/disable certain controls based on mode
        pass


class TermEditDialog(tk.Toplevel):
    """Dialog for editing individual terms."""
    
    def __init__(self, parent, title, term_config=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.setup_ui(title, term_config)
        self.setup_modal_behavior()
    
    def setup_ui(self, title, term_config):
        """Create the term edit interface."""
        self.title(title)
        self.geometry("450x400")
        self.resizable(True, True)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # Term input
        ttk.Label(main_frame, text="Search Term:").pack(anchor="w")
        self.term_var = tk.StringVar(value=term_config['term'] if term_config else "")
        term_entry = ttk.Entry(main_frame, textvariable=self.term_var, width=50)
        term_entry.pack(fill="x", pady=(5, 15))
        term_entry.focus()
        
        # Bind Enter key to submit
        term_entry.bind('<Return>', lambda e: self.ok_clicked())
        
        # Match type
        ttk.Label(main_frame, text="Match Type:").pack(anchor="w")
        self.match_type_var = tk.StringVar(value=term_config.get('match_type', 'word_boundary') if term_config else 'word_boundary')
        match_combo = ttk.Combobox(
            main_frame,
            textvariable=self.match_type_var,
            values=['word_boundary', 'contains', 'exact', 'regex'],
            state="readonly"
        )
        match_combo.pack(fill="x", pady=(5, 15))
        
        # Search scope
        ttk.Label(main_frame, text="Search Scope:").pack(anchor="w")
        self.search_scope_var = tk.StringVar(value=term_config.get('search_scope', 'either') if term_config else 'either')
        scope_combo = ttk.Combobox(
            main_frame,
            textvariable=self.search_scope_var,
            values=['prompt_only', 'tags_only', 'either', 'both'],
            state="readonly"
        )
        scope_combo.pack(fill="x", pady=(5, 10))
        
        # Search scope explanation
        scope_help = ttk.Label(
            main_frame,
            text="• Prompt Only: Search only in positive prompts\n"
                 "• Tags Only: Search only in tag files/embedded tags\n"
                 "• Either: Match if found in prompts OR tags\n"
                 "• Both: Match only if found in prompts AND tags",
            font=("Arial", 8),
            foreground="gray",
            justify="left"
        )
        scope_help.pack(anchor="w", pady=(0, 15))
        
        # Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill="x", pady=(0, 15))
        
        self.enabled_var = tk.BooleanVar(value=term_config.get('enabled', True) if term_config else True)
        ttk.Checkbutton(options_frame, text="Enabled", variable=self.enabled_var).pack(anchor="w")
        
        self.case_sensitive_var = tk.BooleanVar(value=term_config.get('case_sensitive', False) if term_config else False)
        ttk.Checkbutton(options_frame, text="Case Sensitive", variable=self.case_sensitive_var).pack(anchor="w")
        
        self.allow_multi_copy_var = tk.BooleanVar(value=term_config.get('allow_multi_copy', True) if term_config else True)
        ttk.Checkbutton(options_frame, text="Allow Multi-Folder Copy", variable=self.allow_multi_copy_var).pack(anchor="w")
        
        self.include_negative_var = tk.BooleanVar(value=term_config.get('include_negative_prompt', False) if term_config else False)
        ttk.Checkbutton(options_frame, text="Include Negative Prompt in Search", variable=self.include_negative_var).pack(anchor="w")
        
        # Folder name
        ttk.Label(main_frame, text="Folder Name (optional):").pack(anchor="w")
        default_folder = term_config.get('folder_name', '') if term_config else ''
        self.folder_var = tk.StringVar(value=default_folder)
        folder_entry = ttk.Entry(main_frame, textvariable=self.folder_var, width=50)
        folder_entry.pack(fill="x", pady=(5, 5))
        
        # Folder default explanation
        folder_help = ttk.Label(
            main_frame,
            text="If empty, will use the search term as folder name",
            font=("Arial", 8),
            foreground="gray"
        )
        folder_help.pack(anchor="w", pady=(0, 15))
        
        # Multi-tag options
        multi_frame = ttk.LabelFrame(main_frame, text="Multi-Tag Options", padding="10")
        multi_frame.pack(fill="x", pady=(0, 15))
        
        # Exclusion terms
        ttk.Label(multi_frame, text="Exclusion Terms (comma-separated):").pack(anchor="w")
        default_exclusions = ', '.join(term_config.get('exclusion_terms', [])) if term_config else ''
        self.exclusion_terms_var = tk.StringVar(value=default_exclusions)
        exclusion_entry = ttk.Entry(multi_frame, textvariable=self.exclusion_terms_var, width=50)
        exclusion_entry.pack(fill="x", pady=(5, 10))
        
        # Combination priority
        combination_frame = ttk.Frame(multi_frame)
        combination_frame.pack(fill="x")
        
        ttk.Label(combination_frame, text="Combination Priority:").pack(side="left")
        self.combination_priority_var = tk.StringVar(value=str(term_config.get('combination_priority', 0)) if term_config else '0')
        priority_entry = ttk.Entry(combination_frame, textvariable=self.combination_priority_var, width=5)
        priority_entry.pack(side="left", padx=(5, 15))
        
        priority_help = ttk.Label(
            combination_frame,
            text="Higher values appear first in combination folder names",
            font=("Arial", 8),
            foreground="gray"
        )
        priority_help.pack(side="left")
        
        # Help text
        help_text = ttk.Label(
            main_frame,
            text="Match Types:\n"
                 "• Word Boundary: Matches whole words only\n"
                 "• Contains: Matches anywhere in text\n"
                 "• Exact: Exact text match\n"
                 "• Regex: Regular expression pattern",
            font=("Arial", 8),
            foreground="gray",
            justify="left"
        )
        help_text.pack(fill="x", pady=(0, 15))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="OK", command=self.ok_clicked).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
    
    def setup_modal_behavior(self):
        """Set up modal behavior."""
        self.transient(self.parent)
        self.grab_set()
        
        # Bind Escape key to cancel
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Center on parent
        self.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def ok_clicked(self):
        """Handle OK button click."""
        term = self.term_var.get().strip()
        if not term:
            messagebox.showerror("Error", "Please enter a search term.")
            return
        
        folder_name = self.folder_var.get().strip()
        if not folder_name:
            # Auto-generate folder name from term
            folder_name = re.sub(r'[<>:"/\\|?*]', '_', term.lower())
        
        # Parse exclusion terms
        exclusion_text = self.exclusion_terms_var.get().strip()
        exclusion_terms = [t.strip() for t in exclusion_text.split(',') if t.strip()] if exclusion_text else []
        
        # Parse combination priority
        try:
            combination_priority = int(self.combination_priority_var.get())
        except ValueError:
            combination_priority = 0
        
        self.result = {
            'term': term,
            'enabled': self.enabled_var.get(),
            'match_type': self.match_type_var.get(),
            'case_sensitive': self.case_sensitive_var.get(),
            'folder_name': folder_name,
            'allow_multi_copy': self.allow_multi_copy_var.get(),
            'exclusion_terms': exclusion_terms,
            'combination_priority': combination_priority,
            'search_scope': self.search_scope_var.get(),
            'include_negative_prompt': self.include_negative_var.get()
        }
        
        self.destroy()


class TermTestDialog(tk.Toplevel):
    """Dialog for testing search terms."""
    
    def __init__(self, parent, terms):
        super().__init__(parent)
        self.parent = parent
        self.terms = terms
        
        self.setup_ui()
        self.setup_modal_behavior()
    
    def setup_ui(self):
        """Create the term testing interface."""
        self.title("Test Search Terms")
        self.geometry("700x500")
        self.resizable(True, True)
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Instructions
        ttk.Label(
            main_frame,
            text="Enter sample text (e.g., image prompt) to test which terms would match:",
            font=("Arial", 10)
        ).pack(pady=(0, 10))
        
        # Sample text input
        ttk.Label(main_frame, text="Test Text:").pack(anchor="w")
        self.test_text = tk.Text(main_frame, height=6, width=70)
        self.test_text.pack(fill="x", pady=(5, 15))
        
        # Add sample text
        sample_text = "masterpiece, detailed face, beautiful woman, portrait, photorealistic, high quality"
        self.test_text.insert("1.0", sample_text)
        
        # Test button
        ttk.Button(
            main_frame,
            text="Test Terms",
            command=self.test_terms
        ).pack(pady=(0, 15))
        
        # Results area
        ttk.Label(main_frame, text="Matching Terms:").pack(anchor="w")
        
        self.results_tree = ttk.Treeview(
            main_frame,
            columns=("match_type", "priority"),
            show="tree headings",
            height=8
        )
        self.results_tree.heading("#0", text="Term")
        self.results_tree.heading("match_type", text="Match Type")
        self.results_tree.heading("priority", text="Priority")
        
        self.results_tree.pack(fill="both", expand=True, pady=(5, 15))
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right")
    
    def setup_modal_behavior(self):
        """Set up modal behavior."""
        self.transient(self.parent)
        self.grab_set()
        
        # Bind Escape key to close
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Center on parent
        self.update_idletasks()
        x = (self.parent.winfo_x() + self.parent.winfo_width() // 2 - 
             self.winfo_width() // 2)
        y = (self.parent.winfo_y() + self.parent.winfo_height() // 2 - 
             self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def test_terms(self):
        """Test terms against the sample text."""
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        test_text = self.test_text.get("1.0", "end-1c")
        if not test_text.strip():
            return
        
        # Create mock metadata for testing
        metadata = {
            'positive_prompt': test_text,
            'negative_prompt': ''
        }
        
        # Import metadata parser for testing
        from metadata_parser import MetadataParser
        parser = MetadataParser()
        
        # Find matches
        matches = parser.search_terms_in_metadata(metadata, self.terms)
        
        # Display results
        if matches:
            for match in matches:
                self.results_tree.insert(
                    "",
                    "end",
                    text=match['term'],
                    values=(
                        match.get('match_type', 'word_boundary'),
                        match.get('priority', 1)
                    )
                )
        else:
            # Show message if no matches
            self.results_tree.insert(
                "",
                "end",
                text="No matches found",
                values=("", "")
            )