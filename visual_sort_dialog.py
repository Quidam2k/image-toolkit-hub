"""
Visual Sort Dialog for Image Grid Sorter

Provides a comprehensive UI for visual classification sorting:
- Sort by shot type (portrait, upper_body, cowboy_shot, full_body, wide_shot)
- Sort by person count (solo, duo, group)
- Sort by NSFW rating (general, sensitive, questionable, explicit)
- LoRA profile filtering
- Preview/scan functionality before sorting

Author: Claude Code Implementation
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
import time
import json

from visual_classifier import (
    VisualClassifier, ShotType, PersonCount, NSFWRating,
    LoRASortingProfile, EXAMPLE_PROFILES
)


class VisualSortDialog(tk.Toplevel):
    """Dialog for visual classification sorting operations."""

    def __init__(self, parent, config_manager, image_files=None):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.image_files = image_files or []
        self.result = None
        self.classifier = None
        self.preview_results = None
        self.custom_profiles = self._load_custom_profiles()

        self.setup_ui()
        self.setup_modal()

    def _load_custom_profiles(self):
        """Load custom LoRA profiles from config."""
        try:
            profiles_path = os.path.join(
                os.path.dirname(__file__), 'data', 'lora_profiles.json'
            )
            if os.path.exists(profiles_path):
                with open(profiles_path, 'r') as f:
                    data = json.load(f)
                    return {
                        name: LoRASortingProfile.from_dict(p)
                        for name, p in data.items()
                    }
        except Exception:
            pass
        return {}

    def _save_custom_profiles(self):
        """Save custom LoRA profiles to config."""
        try:
            profiles_path = os.path.join(
                os.path.dirname(__file__), 'data', 'lora_profiles.json'
            )
            os.makedirs(os.path.dirname(profiles_path), exist_ok=True)
            data = {name: p.to_dict() for name, p in self.custom_profiles.items()}
            with open(profiles_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving profiles: {e}")

    def setup_ui(self):
        """Create the dialog UI."""
        self.title("Visual Sort - LoRA Workflow Helper")
        self.geometry("700x650")
        self.resizable(True, True)

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Sort by Classification
        self.sort_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.sort_tab, text="Sort by Classification")
        self._setup_sort_tab()

        # Tab 2: LoRA Profiles
        self.profile_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.profile_tab, text="LoRA Profiles")
        self._setup_profile_tab()

        # Tab 3: Preview/Scan
        self.preview_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.preview_tab, text="Preview & Scan")
        self._setup_preview_tab()

        # Bottom frame with common controls
        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(fill="x")

        # Image count label
        self.image_count_label = ttk.Label(
            bottom_frame,
            text=f"Images loaded: {len(self.image_files)}"
        )
        self.image_count_label.pack(side="left")

        # Close button
        ttk.Button(
            bottom_frame, text="Close", command=self.destroy
        ).pack(side="right", padx=5)

    def _setup_sort_tab(self):
        """Set up the Sort by Classification tab."""
        # Description
        desc = ttk.Label(
            self.sort_tab,
            text="Sort images into folders based on visual properties detected by WD14.\n"
                 "This is useful for organizing images for different LoRA workflows.",
            wraplength=600,
            justify="left"
        )
        desc.pack(anchor="w", pady=(0, 15))

        # Sort mode selection
        mode_frame = ttk.LabelFrame(self.sort_tab, text="Sort By", padding=10)
        mode_frame.pack(fill="x", pady=(0, 15))

        self.sort_mode = tk.StringVar(value="shot_type")

        modes = [
            ("Shot Type", "shot_type",
             "portrait, upper_body, cowboy_shot, full_body, wide_shot"),
            ("Person Count", "person_count",
             "solo, duo, group"),
            ("NSFW Rating", "nsfw_rating",
             "general, sensitive, questionable, explicit"),
        ]

        for label, value, desc in modes:
            frame = ttk.Frame(mode_frame)
            frame.pack(fill="x", pady=2)

            rb = ttk.Radiobutton(
                frame, text=label, variable=self.sort_mode, value=value
            )
            rb.pack(side="left")

            ttk.Label(
                frame, text=f"  ({desc})",
                foreground="gray", font=("Arial", 9)
            ).pack(side="left")

        # Options
        options_frame = ttk.LabelFrame(self.sort_tab, text="Options", padding=10)
        options_frame.pack(fill="x", pady=(0, 15))

        self.copy_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Copy files (keep originals in place)",
            variable=self.copy_mode_var
        ).pack(anchor="w")

        self.use_yolo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Use YOLO for person detection (more accurate, requires ultralytics)",
            variable=self.use_yolo_var
        ).pack(anchor="w")

        # Output info
        output_frame = ttk.LabelFrame(self.sort_tab, text="Output", padding=10)
        output_frame.pack(fill="x", pady=(0, 15))

        auto_sorted = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
        ttk.Label(
            output_frame,
            text=f"Images will be sorted to: {auto_sorted}/visual_<mode>/<category>/",
            wraplength=600
        ).pack(anchor="w")

        # Start button
        btn_frame = ttk.Frame(self.sort_tab)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(
            btn_frame,
            text="Start Visual Sort",
            command=self._start_visual_sort
        ).pack(side="right")

        ttk.Button(
            btn_frame,
            text="Preview First",
            command=lambda: self.notebook.select(2)  # Switch to preview tab
        ).pack(side="right", padx=5)

    def _setup_profile_tab(self):
        """Set up the LoRA Profiles tab."""
        # Description
        desc = ttk.Label(
            self.profile_tab,
            text="LoRA profiles define which images are suitable for specific LoRAs.\n"
                 "Select a profile to filter images that match its criteria.",
            wraplength=600,
            justify="left"
        )
        desc.pack(anchor="w", pady=(0, 15))

        # Profile list
        list_frame = ttk.LabelFrame(self.profile_tab, text="Available Profiles", padding=10)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Treeview for profiles
        columns = ("name", "shot_types", "person_count", "rating")
        self.profile_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=8
        )

        self.profile_tree.heading("name", text="Profile Name")
        self.profile_tree.heading("shot_types", text="Shot Types")
        self.profile_tree.heading("person_count", text="Person Count")
        self.profile_tree.heading("rating", text="Rating")

        self.profile_tree.column("name", width=120)
        self.profile_tree.column("shot_types", width=200)
        self.profile_tree.column("person_count", width=100)
        self.profile_tree.column("rating", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                   command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=scrollbar.set)

        self.profile_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate profiles
        self._refresh_profile_list()

        # Profile actions
        action_frame = ttk.Frame(self.profile_tab)
        action_frame.pack(fill="x", pady=10)

        ttk.Button(
            action_frame, text="New Profile...",
            command=self._new_profile
        ).pack(side="left", padx=2)

        ttk.Button(
            action_frame, text="Edit Profile...",
            command=self._edit_profile
        ).pack(side="left", padx=2)

        ttk.Button(
            action_frame, text="Delete Profile",
            command=self._delete_profile
        ).pack(side="left", padx=2)

        ttk.Button(
            action_frame, text="Sort by Selected Profile",
            command=self._sort_by_profile
        ).pack(side="right", padx=2)

    def _setup_preview_tab(self):
        """Set up the Preview & Scan tab."""
        # Description
        desc = ttk.Label(
            self.preview_tab,
            text="Scan images to see how they would be classified before sorting.\n"
                 "This helps you understand your collection's composition.",
            wraplength=600,
            justify="left"
        )
        desc.pack(anchor="w", pady=(0, 15))

        # Scan controls
        scan_frame = ttk.LabelFrame(self.preview_tab, text="Scan Options", padding=10)
        scan_frame.pack(fill="x", pady=(0, 15))

        limit_frame = ttk.Frame(scan_frame)
        limit_frame.pack(fill="x", pady=5)

        ttk.Label(limit_frame, text="Sample size:").pack(side="left")
        self.sample_size = tk.StringVar(value="100")
        sample_combo = ttk.Combobox(
            limit_frame, textvariable=self.sample_size,
            values=["50", "100", "250", "500", "All"], width=10
        )
        sample_combo.pack(side="left", padx=5)

        ttk.Button(
            scan_frame, text="Scan Images",
            command=self._start_preview_scan
        ).pack(anchor="w", pady=5)

        # Results display
        results_frame = ttk.LabelFrame(self.preview_tab, text="Classification Results", padding=10)
        results_frame.pack(fill="both", expand=True)

        # Create three columns for results
        cols_frame = ttk.Frame(results_frame)
        cols_frame.pack(fill="both", expand=True)

        # Shot type column
        shot_frame = ttk.LabelFrame(cols_frame, text="Shot Types", padding=5)
        shot_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.shot_results = tk.Text(shot_frame, width=20, height=10, state="disabled")
        self.shot_results.pack(fill="both", expand=True)

        # Person count column
        person_frame = ttk.LabelFrame(cols_frame, text="Person Count", padding=5)
        person_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.person_results = tk.Text(person_frame, width=20, height=10, state="disabled")
        self.person_results.pack(fill="both", expand=True)

        # NSFW rating column
        rating_frame = ttk.LabelFrame(cols_frame, text="NSFW Rating", padding=5)
        rating_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.rating_results = tk.Text(rating_frame, width=20, height=10, state="disabled")
        self.rating_results.pack(fill="both", expand=True)

        # Progress
        self.preview_progress = ttk.Progressbar(
            results_frame, mode="determinate", length=400
        )
        self.preview_progress.pack(fill="x", pady=10)

        self.preview_status = ttk.Label(results_frame, text="Ready to scan")
        self.preview_status.pack()

    def _refresh_profile_list(self):
        """Refresh the profile list in the treeview."""
        self.profile_tree.delete(*self.profile_tree.get_children())

        # Add example profiles
        all_profiles = {**EXAMPLE_PROFILES, **self.custom_profiles}

        for name, profile in all_profiles.items():
            d = profile.to_dict()
            shots = ", ".join(d['shot_types']) if d['shot_types'] else "any"
            persons = ", ".join(d['person_counts']) if d['person_counts'] else "any"
            ratings = ", ".join(d['nsfw_ratings']) if d['nsfw_ratings'] else "any"

            self.profile_tree.insert("", "end", values=(name, shots, persons, ratings))

    def _new_profile(self):
        """Create a new LoRA profile."""
        dialog = ProfileEditDialog(self, None)
        self.wait_window(dialog)

        if dialog.result:
            profile = dialog.result
            self.custom_profiles[profile.name] = profile
            self._save_custom_profiles()
            self._refresh_profile_list()

    def _edit_profile(self):
        """Edit selected profile."""
        selection = self.profile_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a profile to edit.")
            return

        name = self.profile_tree.item(selection[0])['values'][0]

        # Check if it's a built-in profile
        if name in EXAMPLE_PROFILES and name not in self.custom_profiles:
            if messagebox.askyesno(
                "Built-in Profile",
                f"'{name}' is a built-in profile. Create a copy to edit?"
            ):
                profile = EXAMPLE_PROFILES[name]
                dialog = ProfileEditDialog(self, profile, copy_mode=True)
            else:
                return
        else:
            profile = self.custom_profiles.get(name) or EXAMPLE_PROFILES.get(name)
            dialog = ProfileEditDialog(self, profile)

        self.wait_window(dialog)

        if dialog.result:
            new_profile = dialog.result
            # Remove old name if renamed
            if name in self.custom_profiles and name != new_profile.name:
                del self.custom_profiles[name]
            self.custom_profiles[new_profile.name] = new_profile
            self._save_custom_profiles()
            self._refresh_profile_list()

    def _delete_profile(self):
        """Delete selected profile."""
        selection = self.profile_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a profile to delete.")
            return

        name = self.profile_tree.item(selection[0])['values'][0]

        if name in EXAMPLE_PROFILES and name not in self.custom_profiles:
            messagebox.showinfo("Info", "Cannot delete built-in profiles.")
            return

        if messagebox.askyesno("Confirm", f"Delete profile '{name}'?"):
            if name in self.custom_profiles:
                del self.custom_profiles[name]
                self._save_custom_profiles()
                self._refresh_profile_list()

    def _sort_by_profile(self):
        """Sort images using selected profile."""
        selection = self.profile_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a profile first.")
            return

        name = self.profile_tree.item(selection[0])['values'][0]
        profile = self.custom_profiles.get(name) or EXAMPLE_PROFILES.get(name)

        if not profile:
            messagebox.showerror("Error", "Profile not found.")
            return

        if not self.image_files:
            messagebox.showinfo("Info", "No images loaded.")
            return

        self.result = {
            'action': 'profile_sort',
            'profile': profile,
            'use_yolo': self.use_yolo_var.get(),
            'copy_mode': self.copy_mode_var.get()
        }
        self.destroy()

    def _start_visual_sort(self):
        """Start the visual sort operation."""
        if not self.image_files:
            messagebox.showinfo("Info", "No images loaded.")
            return

        self.result = {
            'action': 'visual_sort',
            'sort_by': self.sort_mode.get(),
            'use_yolo': self.use_yolo_var.get(),
            'copy_mode': self.copy_mode_var.get()
        }
        self.destroy()

    def _start_preview_scan(self):
        """Start scanning images for preview."""
        if not self.image_files:
            messagebox.showinfo("Info", "No images loaded.")
            return

        # Get sample size
        sample = self.sample_size.get()
        if sample == "All":
            images = self.image_files
        else:
            limit = int(sample)
            images = self.image_files[:limit]

        # Clear previous results
        for widget in [self.shot_results, self.person_results, self.rating_results]:
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")

        self.preview_progress['value'] = 0
        self.preview_status.config(text="Initializing classifier...")
        self.update_idletasks()

        # Run scan in thread
        def scan_thread():
            try:
                classifier = VisualClassifier(use_yolo=self.use_yolo_var.get())

                if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
                    self.after(0, lambda: messagebox.showerror(
                        "Error", "WD14 tagger not loaded. Check model files."
                    ))
                    return

                shot_counts = {}
                person_counts = {}
                rating_counts = {}
                total = len(images)

                for i, img in enumerate(images):
                    result = classifier.classify_image(img)

                    shot = result.shot_type.value
                    person = result.person_count.value
                    rating = result.nsfw_rating.value

                    shot_counts[shot] = shot_counts.get(shot, 0) + 1
                    person_counts[person] = person_counts.get(person, 0) + 1
                    rating_counts[rating] = rating_counts.get(rating, 0) + 1

                    # Update progress
                    progress = (i + 1) / total * 100
                    self.after(0, lambda p=progress, c=i+1, t=total: self._update_scan_progress(p, c, t))

                # Update results
                self.after(0, lambda: self._display_scan_results(
                    shot_counts, person_counts, rating_counts, total
                ))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _update_scan_progress(self, progress, current, total):
        """Update scan progress display."""
        self.preview_progress['value'] = progress
        self.preview_status.config(text=f"Scanning: {current}/{total}")

    def _display_scan_results(self, shot_counts, person_counts, rating_counts, total):
        """Display scan results in the preview tab."""
        self.preview_status.config(text=f"Scan complete: {total} images")

        # Shot types
        self.shot_results.config(state="normal")
        self.shot_results.delete("1.0", "end")
        for shot, count in sorted(shot_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            self.shot_results.insert("end", f"{shot}: {count} ({pct:.1f}%)\n")
        self.shot_results.config(state="disabled")

        # Person counts
        self.person_results.config(state="normal")
        self.person_results.delete("1.0", "end")
        for person, count in sorted(person_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            self.person_results.insert("end", f"{person}: {count} ({pct:.1f}%)\n")
        self.person_results.config(state="disabled")

        # Ratings
        self.rating_results.config(state="normal")
        self.rating_results.delete("1.0", "end")
        for rating, count in sorted(rating_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            self.rating_results.insert("end", f"{rating}: {count} ({pct:.1f}%)\n")
        self.rating_results.config(state="disabled")

    def setup_modal(self):
        """Set up modal dialog behavior."""
        self.transient(self.parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


class ProfileEditDialog(tk.Toplevel):
    """Dialog for editing LoRA sorting profiles."""

    def __init__(self, parent, profile=None, copy_mode=False):
        super().__init__(parent)
        self.parent = parent
        self.profile = profile
        self.copy_mode = copy_mode
        self.result = None

        self.setup_ui()
        self.setup_modal()

        if profile:
            self._load_profile(profile)

    def setup_ui(self):
        """Create the profile edit UI."""
        self.title("Edit LoRA Profile" if self.profile and not self.copy_mode else "New LoRA Profile")
        self.geometry("500x550")
        self.resizable(False, False)

        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)

        # Profile name
        name_frame = ttk.LabelFrame(main, text="Profile Name", padding=10)
        name_frame.pack(fill="x", pady=(0, 10))

        self.name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.name_var, width=40).pack(fill="x")

        # Shot types
        shot_frame = ttk.LabelFrame(main, text="Shot Types (check to require)", padding=10)
        shot_frame.pack(fill="x", pady=(0, 10))

        self.shot_vars = {}
        shot_types = ["extreme_closeup", "portrait", "upper_body", "cowboy_shot", "full_body", "wide_shot"]
        for st in shot_types:
            var = tk.BooleanVar()
            self.shot_vars[st] = var
            ttk.Checkbutton(shot_frame, text=st, variable=var).pack(anchor="w")

        # Person counts
        person_frame = ttk.LabelFrame(main, text="Person Count (check to require)", padding=10)
        person_frame.pack(fill="x", pady=(0, 10))

        self.person_vars = {}
        person_types = ["solo", "duo", "group"]
        for pt in person_types:
            var = tk.BooleanVar()
            self.person_vars[pt] = var
            ttk.Checkbutton(person_frame, text=pt, variable=var).pack(anchor="w")

        # NSFW ratings
        rating_frame = ttk.LabelFrame(main, text="NSFW Rating (check to allow)", padding=10)
        rating_frame.pack(fill="x", pady=(0, 10))

        self.rating_vars = {}
        rating_types = ["general", "sensitive", "questionable", "explicit"]
        for rt in rating_types:
            var = tk.BooleanVar()
            self.rating_vars[rt] = var
            ttk.Checkbutton(rating_frame, text=rt, variable=var).pack(anchor="w")

        # Tags
        tags_frame = ttk.LabelFrame(main, text="Tag Filters (comma-separated)", padding=10)
        tags_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(tags_frame, text="Required tags:").pack(anchor="w")
        self.required_tags_var = tk.StringVar()
        ttk.Entry(tags_frame, textvariable=self.required_tags_var, width=50).pack(fill="x", pady=(0, 5))

        ttk.Label(tags_frame, text="Excluded tags:").pack(anchor="w")
        self.excluded_tags_var = tk.StringVar()
        ttk.Entry(tags_frame, textvariable=self.excluded_tags_var, width=50).pack(fill="x")

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(15, 0))

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

    def _load_profile(self, profile):
        """Load profile data into the form."""
        if self.copy_mode:
            self.name_var.set(f"{profile.name}_copy")
        else:
            self.name_var.set(profile.name)

        if profile.shot_types:
            for st in profile.shot_types:
                if st.value in self.shot_vars:
                    self.shot_vars[st.value].set(True)

        if profile.person_counts:
            for pc in profile.person_counts:
                if pc.value in self.person_vars:
                    self.person_vars[pc.value].set(True)

        if profile.nsfw_ratings:
            for nr in profile.nsfw_ratings:
                if nr.value in self.rating_vars:
                    self.rating_vars[nr.value].set(True)

        if profile.required_tags:
            self.required_tags_var.set(", ".join(profile.required_tags))

        if profile.excluded_tags:
            self.excluded_tags_var.set(", ".join(profile.excluded_tags))

    def _save(self):
        """Save the profile."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name is required.")
            return

        # Collect shot types
        shot_types = None
        selected_shots = [st for st, var in self.shot_vars.items() if var.get()]
        if selected_shots:
            shot_types = [ShotType(st) for st in selected_shots]

        # Collect person counts
        person_counts = None
        selected_persons = [pc for pc, var in self.person_vars.items() if var.get()]
        if selected_persons:
            person_counts = [PersonCount(pc) for pc in selected_persons]

        # Collect ratings
        nsfw_ratings = None
        selected_ratings = [nr for nr, var in self.rating_vars.items() if var.get()]
        if selected_ratings:
            nsfw_ratings = [NSFWRating(nr) for nr in selected_ratings]

        # Collect tags
        required_tags = []
        if self.required_tags_var.get().strip():
            required_tags = [t.strip() for t in self.required_tags_var.get().split(",")]

        excluded_tags = []
        if self.excluded_tags_var.get().strip():
            excluded_tags = [t.strip() for t in self.excluded_tags_var.get().split(",")]

        self.result = LoRASortingProfile(
            name=name,
            shot_types=shot_types,
            person_counts=person_counts,
            nsfw_ratings=nsfw_ratings,
            required_tags=required_tags,
            excluded_tags=excluded_tags
        )
        self.destroy()

    def setup_modal(self):
        """Set up modal dialog behavior."""
        self.transient(self.parent)
        self.grab_set()

        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


def show_visual_sort_dialog(parent, config_manager, image_files=None):
    """Show the visual sort dialog and return the result."""
    dialog = VisualSortDialog(parent, config_manager, image_files)
    parent.wait_window(dialog)
    return dialog.result
