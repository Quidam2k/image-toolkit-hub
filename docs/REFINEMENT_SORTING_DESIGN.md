# Refinement Sorting & Custom Category Names

**Created:** 2026-03-04
**Status:** Design / Not Yet Implemented

---

## Problem Statement

When re-sorting an already-sorted collection (e.g., refining the best images from `sorted_MJ2025/1/`), the current workflow has friction:

1. **Workaround required:** User must manually add an output subfolder as a new source folder, which creates confusingly-named destinations (e.g., source `sorted_MJ2025/1` produces `sorted_1/` because only the basename is used).
2. **No custom category names:** Destination folders are always `1/`, `2/`, `3/`. When doing themed sorts (e.g., "T-Shirt" vs "Jacket"), there's no way to name the buckets meaningfully.
3. **Copy mode gotcha:** If the user forgets to enable copy mode, images are moved out of the source — destructive when the source is itself a curated output folder.

---

## Feature 1: Custom Category Names (Renameable Destination Folders)

### Concept

Allow users to give meaningful names to the three sort categories, persisted per sorting session or globally.

### Proposed UX

In the setup dialog (or a new lightweight popup), each category slot gets an editable label:

| Slot | Default Name | Example Custom Name |
|------|-------------|-------------------|
| 1 (left-click) | `1` | `T-Shirt` |
| 2 (mouse4) | `2` | `Jacket` |
| 3 (mouse5) | `3` | `Reject` |

The category name is shown:
- In the status bar / HUD overlay so the user remembers what each button does
- As the actual destination folder name (instead of `1/`, `2/`, `3/`)

### Config Changes

```json
{
  "output_folders": {
    "1": "T-Shirt",
    "2": "Jacket",
    "3": "Reject",
    "removed": "removed",
    "auto_sorted": "auto_sorted",
    "unmatched": "unmatched"
  }
}
```

The `output_folders` dict already exists and maps slot keys to folder names. Currently hardcoded to `"1": "1"` etc. Making these user-editable is the natural extension.

### Implementation Notes

- **Config:** Already structured correctly — just need UI to edit the values.
- **UI:** Add editable fields in setup dialog for category 1/2/3 folder names.
- **HUD:** Show category labels on the grid view so user knows what each click does. Could be a small legend in the corner: `LClick: T-Shirt | M4: Jacket | M5: Reject`
- **Validation:** Sanitize folder names (no special characters, reasonable length).

### Effort: Low-Medium

The config structure already supports this. Main work is the UI for editing names and displaying the legend.

---

## Feature 2: Refinement Sorting Mode

### Concept

A streamlined way to re-sort an existing output folder without the manual workaround of adding it as a source. Essentially: "I've already done a first pass — now I want to make a second pass within these results."

### Proposed Workflow

1. User right-clicks a source folder in the setup dialog (or uses a menu option) and selects "Refine this folder"
2. App sets:
   - Source = the selected folder
   - Destination = subfolder within it (or sibling folder) with a user-chosen name scheme
   - Copy mode = ON by default (safe — don't destroy the curated collection)
3. User optionally renames the category slots for this refinement pass
4. Sort proceeds as normal

### Key Design Decisions

**Where do refined results go?**

Option A: **Subfolder within the source** (e.g., `sorted_MJ2025/1/refined_TShirt/`)
- Pro: Results are clearly nested under their parent sort
- Con: Source scanning with `include_subfolders` would pick up the refined results too

Option B: **Sibling folder with prefix** (e.g., `sorted_MJ2025/1_refined/TShirt/`)
- Pro: Clean separation from source, no subfolder scanning issues
- Con: Naming could get long for deep refinements

Option C: **Standard sorted_ output** but with a user-chosen session name (e.g., `sorted_MJ2025_refine_clothing/TShirt/`)
- Pro: Consistent with existing pattern, clear naming
- Con: User needs to pick a name

**Recommendation:** Option C — it's the most consistent with existing behavior and gives the user full control over naming. The setup dialog would just have a "Session name" or "Output folder name" field when in refinement mode.

**Should copy mode be forced on?**

Recommendation: Default to ON with a warning if user turns it off ("Source is a curated collection — moving files will remove them from the original sort results"). Don't force it, but make the safe choice obvious.

### Implementation Sketch

1. Add "Refine..." button/option next to source folders in setup dialog
2. When activated:
   - Pre-fill source with the selected folder
   - Show session name field (default: `{source_name}_refined`)
   - Show category name fields (default: `1`, `2`, `3`)
   - Auto-enable copy mode with advisory note
3. Config temporarily overrides `output_folders` and `destination_location` for the session
4. Sorting proceeds normally with the custom names

### Effort: Medium

Requires setup dialog changes, temporary config override logic, and the category naming feature (Feature 1).

---

## Bonus: Better Destination Naming for Subfolder Sources

### Current Bug/Annoyance

When source is `sorted_MJ2025/1`, `os.path.basename()` returns `1`, creating `sorted_1/` as the destination — confusing and potentially conflicting with other sources.

### Fix

Use more path context when generating the destination name. For example:
- `sorted_MJ2025/1` → `sorted_MJ2025_1` (use last two path components)
- Or: detect when basename is a single digit/generic name and include the parent

### Implementation

In `config_manager.py` `get_destination_folder_for_source()` and `setup_folders()`:

```python
def get_smart_source_name(self, source_folder):
    """Generate a meaningful destination name from a source path."""
    basename = os.path.basename(source_folder)
    # If basename is generic (single digit, single char), include parent
    if len(basename) <= 2 or basename.isdigit():
        parent = os.path.basename(os.path.dirname(source_folder))
        return self.sanitize_folder_name(f"{parent}_{basename}")
    return self.sanitize_folder_name(basename)
```

### Effort: Low

---

## Implementation Priority

1. **Destination naming fix** (Low effort, prevents confusion) — do first
2. **Custom category names** (Low-Medium, enables meaningful sorting) — do second
3. **Refinement mode** (Medium, builds on category names) — do third

Each builds on the previous, and they can be shipped incrementally.
