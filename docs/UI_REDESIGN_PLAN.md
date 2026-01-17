# UI Redesign Plan - Image Toolkit Hub

**Created:** January 8, 2026
**Status:** Phase 1 Complete
**Triggered by:** User feedback that the current UI has "weird purple colors" and a clunky "two-layer" design

## Implementation Progress

### Phase 1: Theme Consolidation - COMPLETE
- Created `ui_theme.py` with charcoal/off-white color scheme (no more purple!)
- Updated all 5 dialog files to use shared theme:
  - `setup_dialog.py`
  - `image_ranker_dialog.py`
  - `rankings_view_dialog.py`
  - `app_hub.py`
  - `background_sort_dialog.py`
- New colors: Charcoal backgrounds (#1a1a1a, #252525) + Off-white text (#f5f5f5) + Blue accent (#3b82f6)

---

## Research Summary: 2025/2026 UX Best Practices

### The 60-30-10 Rule
- **60%** dominant color (background) - sets the tone, provides consistent backdrop
- **30%** secondary color (navigation, headers, cards) - adds variety
- **10%** accent color (CTAs, highlights) - draws attention to important elements

### Color Harmony Principles
- **Monochromatic schemes** (shades of a single color) create clean, elegant, professional look
- **Complementary colors** (opposites on color wheel) make elements pop - use sparingly for CTAs
- Avoid using similar saturation for all elements - creates visual competition

### Accessibility Requirements
- Color contrast should pass **4.5:1 to 7.0:1** ratio (AA to AAA)
- Never use low contrast between text and background
- Avoid complementary colors for text/background at similar brightness
- Black and dark gray are easiest to read on light backgrounds

### 2025 UI Design Principles
1. **Clarity Over Cleverness** - Users should instantly understand navigation
2. **Consistency** - Uniform design elements (buttons, fonts, colors) across app
3. **Single accent color** for CTAs to train users where to click
4. **Design in grayscale first** - forces focus on layout and spacing
5. **Limited palette** - "If your color scheme looks like a unicorn exploded, dial it back"

### Sources
- [UI Color Palette 2025 Best Practices - IxDF](https://www.interaction-design.org/literature/article/ui-color-palette)
- [11 UI Design Best Practices for UX Designers (2026 Guide)](https://uxplaybook.org/articles/ui-fundamentals-best-practices-for-ux-designers)
- [Colour Theory for UI Design - Full Clarity](https://fullclarity.co.uk/insights/ui-colour-best-practice/)
- [Color Psychology in UI Design 2025 - MockFlow](https://mockflow.com/blog/color-psychology-in-ui-design)

---

## Current UI Problems

### Problem 1: Color Scheme ("Weird Purple")

**Current ModernStyle colors** (found in `setup_dialog.py` and `image_ranker_dialog.py`):
```python
BG_DARK = "#1a1a2e"      # Dark navy blue
BG_CARD = "#16213e"      # Slightly lighter navy
BG_HOVER = "#1f3460"     # Blue hover
BG_INPUT = "#0f172a"     # Very dark blue
ACCENT = "#7c3aed"       # Bright purple
ACCENT_HOVER = "#8b5cf6" # Lighter purple
TEXT = "#e2e8f0"         # Light gray text
TEXT_DIM = "#94a3b8"     # Dimmer text
TEXT_MUTED = "#64748b"   # Muted text
```

**Issues:**
1. Dark navy + bright purple = "Discord/gaming" aesthetic, not professional
2. Violates 60-30-10 rule - too many competing dark blues
3. Purple accent is too saturated and eye-catching
4. Overall feels dated (2018-2020 dark mode trend)

### Problem 2: Duplicated Style Definitions

Both `setup_dialog.py` and `image_ranker_dialog.py` define their own `ModernStyle` class with identical colors. This:
- Creates code duplication
- Risks divergence if one is updated and not the other
- Makes global theme changes tedious

### Problem 3: Two-Layer UI Architecture

**Current navigation flow:**
```
Main App (image_sorter_enhanced.py)
    ├── Opens SetupDialog (modal) → setup_dialog.py
    │       ├── Opens TermManager (another modal)
    │       ├── Opens BatchExport (another modal)
    │       └── Opens TagDatabase rebuild (another modal)
    │
    ├── Opens ImageRanker (modal) → image_ranker_dialog.py
    │       └── Opens RankingsView (another modal)
    │
    └── Opens various other dialogs...
```

**Issues:**
1. User bounces between multiple windows
2. Settings in SetupDialog are duplicated conceptually with what you'd need in ImageRanker
3. Modal-on-modal is poor UX - feels cluttered
4. No unified "hub" feeling - just a collection of popups

---

## Proposed Solutions

### Solution A: New Color Scheme

**Light theme option (professional, clean):**
```python
class Theme:
    # Backgrounds - neutral grays
    BG_PRIMARY = "#f8fafc"     # Main background - very light gray
    BG_SECONDARY = "#f1f5f9"   # Cards, panels - slightly darker
    BG_TERTIARY = "#e2e8f0"    # Borders, dividers
    BG_INPUT = "#ffffff"       # Input fields - white

    # Single accent color - clean blue
    ACCENT = "#2563eb"         # Primary actions
    ACCENT_HOVER = "#1d4ed8"   # Hover state
    ACCENT_LIGHT = "#dbeafe"   # Light accent background

    # Text - high contrast
    TEXT_PRIMARY = "#0f172a"   # Main text - near black
    TEXT_SECONDARY = "#475569" # Secondary text
    TEXT_MUTED = "#94a3b8"     # Hints, placeholders

    # Semantic colors
    SUCCESS = "#16a34a"
    WARNING = "#d97706"
    ERROR = "#dc2626"

    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_HEADING = ("Segoe UI", 12, "bold")
    FONT_BODY = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_MONO = ("Consolas", 10)
```

**Dark theme option (if preferred, but refined):**
```python
class ThemeDark:
    # Backgrounds - true dark, not navy
    BG_PRIMARY = "#0f0f0f"     # True dark
    BG_SECONDARY = "#1a1a1a"   # Cards
    BG_TERTIARY = "#262626"    # Elevated elements
    BG_INPUT = "#171717"       # Input fields

    # Single accent - NOT purple, use blue or teal
    ACCENT = "#3b82f6"         # Blue
    ACCENT_HOVER = "#60a5fa"

    # Text
    TEXT_PRIMARY = "#fafafa"
    TEXT_SECONDARY = "#a1a1aa"
    TEXT_MUTED = "#71717a"
```

### Solution B: Shared Theme Module

Create `ui_theme.py` that all UI files import:

```python
# ui_theme.py
"""
Shared UI theme for Image Toolkit Hub.
Single source of truth for colors, fonts, and styling.
"""

class Theme:
    """Application theme - light mode."""
    # ... colors as above ...

    @classmethod
    def apply_to_ttk(cls, root):
        """Apply theme to ttk widgets."""
        style = ttk.Style(root)
        style.theme_use("clam")
        # ... configure all styles ...

# Usage in other files:
# from ui_theme import Theme
# Theme.apply_to_ttk(self)
```

### Solution C: Single-Window Architecture

Instead of modal dialogs, use a **tabbed or sidebar navigation**:

```
┌──────────────────────────────────────────────────────────────────┐
│  Image Toolkit Hub                                    [_][□][X]  │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                       │
│  [Sort]  │   (Content area changes based on selected mode)       │
│          │                                                       │
│  [Rank]  │   Currently showing: Manual Sort                      │
│          │   ┌─────┬─────┬─────┬─────┐                          │
│  [Auto]  │   │ img │ img │ img │ img │                          │
│          │   ├─────┼─────┼─────┼─────┤                          │
│ [Export] │   │ img │ img │ img │ img │                          │
│          │   └─────┴─────┴─────┴─────┘                          │
│ [Config] │                                                       │
│          │   Stats: 1,234 images | Page 1/50                     │
└──────────┴───────────────────────────────────────────────────────┘
```

**Benefits:**
- Single window to manage
- No modal confusion
- Shared status bar, shared folder selection
- Feels like a cohesive tool, not separate utilities

**Implementation approach:**
1. Main window has sidebar navigation (or top tabs)
2. Each "mode" (Sort, Rank, Export, Config) is a Frame that gets shown/hidden
3. Shared state (current folders, settings) accessible to all modes
4. Keyboard shortcuts work globally

---

## Implementation Plan

### Phase 1: Theme Consolidation
1. Create `ui_theme.py` with new color scheme
2. Update `image_ranker_dialog.py` to use shared theme
3. Update `setup_dialog.py` to use shared theme
4. Update `rankings_view_dialog.py` to use shared theme
5. Test visual consistency

### Phase 2: Image Ranker Polish
1. Apply new theme to ranker
2. Consider whether ranker should remain a dialog or become a "mode"
3. If staying as dialog: at least make it feel part of the same app

### Phase 3: Architecture Refactor (Optional, Larger Scope)
1. Refactor main app to use sidebar/tab navigation
2. Convert dialogs to switchable panels
3. Unify state management

---

## Questions for User

1. **Light or dark theme preference?** Light is more professional/modern, dark is easier on eyes for long sessions
2. **Keep dialogs or move to single-window?** Dialogs are easier to implement, single-window is better UX
3. **What accent color?** Blue is safe/professional, could also use teal, green, or a muted orange

---

## Files That Need Changes

- `ui_theme.py` (NEW) - shared theme definitions
- `image_ranker_dialog.py` - remove local ModernStyle, import theme
- `setup_dialog.py` - remove local ModernStyle, import theme
- `rankings_view_dialog.py` - update styling
- `image_sorter_enhanced.py` - potentially major refactor for single-window
- `term_manager.py` - update styling
- `auto_sort_progress.py` - update styling
- `batch_export_dialog.py` - update styling
