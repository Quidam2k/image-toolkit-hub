"""
Shared UI Theme for Image Toolkit Hub

Single source of truth for colors, fonts, and styling across all dialogs.
Uses a modern charcoal/off-white dark theme with blue accent.

Author: Claude Code Implementation
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk


class Theme:
    """
    Modern dark theme with charcoal backgrounds and off-white text.

    Follows 60-30-10 rule:
    - 60% dominant: BG_PRIMARY (main background)
    - 30% secondary: BG_CARD (panels, cards)
    - 10% accent: ACCENT (buttons, highlights)
    """

    # === BACKGROUNDS (Charcoal grays, not navy) ===
    BG_PRIMARY = "#1a1a1a"      # Main background - true charcoal
    BG_CARD = "#252525"         # Cards, panels - slightly lighter
    BG_HOVER = "#333333"        # Hover states
    BG_INPUT = "#1f1f1f"        # Input fields - darker
    BG_ELEVATED = "#2d2d2d"     # Elevated elements (tooltips, dropdowns)

    # === ACCENT (Single blue accent - professional, not gaming) ===
    ACCENT = "#3b82f6"          # Primary blue
    ACCENT_HOVER = "#60a5fa"    # Lighter blue for hover
    ACCENT_DIM = "#1e40af"      # Darker blue for pressed states
    ACCENT_SUBTLE = "#1e3a5f"   # Very subtle blue for backgrounds

    # === TEXT (Off-white spectrum) ===
    TEXT = "#f5f5f5"            # Primary text - off-white
    TEXT_DIM = "#a3a3a3"        # Secondary text - dimmed
    TEXT_MUTED = "#737373"      # Muted text - hints, placeholders
    TEXT_DISABLED = "#525252"   # Disabled text

    # === SEMANTIC COLORS ===
    SUCCESS = "#22c55e"         # Green - success states
    WARNING = "#f59e0b"         # Amber - warnings
    ERROR = "#ef4444"           # Red - errors
    INFO = "#3b82f6"            # Blue - info (same as accent)

    # === BORDERS ===
    BORDER = "#404040"          # Standard border
    BORDER_LIGHT = "#525252"    # Lighter border for contrast
    BORDER_FOCUS = "#3b82f6"    # Focus ring (accent)

    # === FONTS ===
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"

    # Font tuples for Tkinter
    FONT_TITLE = ("Segoe UI", 18, "bold")
    FONT_HEADING = ("Segoe UI", 12, "bold")
    FONT_SUBHEADING = ("Segoe UI", 11, "bold")
    FONT_BODY = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_TINY = ("Segoe UI", 8)
    FONT_MONO_NORMAL = ("Consolas", 10)
    FONT_MONO_SMALL = ("Consolas", 9)

    # Stats-specific fonts (for ranker)
    FONT_STATS = ("Consolas", 10)
    FONT_STATS_LARGE = ("Consolas", 14, "bold")

    # Legacy font names for compatibility
    FONT_ICON = ("Segoe UI", 20)

    # === LEGACY ALIASES ===
    # For backwards compatibility with existing code
    BG_DARK = BG_PRIMARY

    @classmethod
    def apply(cls, root):
        """
        Apply theme to all ttk widgets in a window.

        Call this once when creating a new Toplevel or Tk root.
        """
        style = ttk.Style(root)
        style.theme_use("clam")

        # === BASE STYLES ===
        style.configure(".",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT,
            font=cls.FONT_BODY,
            borderwidth=0,
            focuscolor=cls.ACCENT
        )

        # === FRAMES ===
        style.configure("TFrame", background=cls.BG_PRIMARY)
        style.configure("Card.TFrame", background=cls.BG_CARD)
        style.configure("Dark.TFrame", background=cls.BG_PRIMARY)

        # === LABELS ===
        style.configure("TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT
        )
        style.configure("Card.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT
        )
        style.configure("Title.TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT,
            font=cls.FONT_TITLE
        )
        style.configure("Heading.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            font=cls.FONT_HEADING
        )
        style.configure("Dim.TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT_DIM
        )
        style.configure("Muted.TLabel",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT_MUTED
        )
        style.configure("Body.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT_DIM,
            font=cls.FONT_BODY
        )
        style.configure("Icon.TLabel",
            background=cls.BG_CARD,
            foreground=cls.ACCENT,
            font=cls.FONT_ICON
        )
        # Stats labels for ranker
        style.configure("Stats.TLabel",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            font=cls.FONT_STATS
        )
        style.configure("StatsLarge.TLabel",
            background=cls.BG_CARD,
            foreground=cls.ACCENT,
            font=cls.FONT_STATS_LARGE
        )
        style.configure("Success.TLabel",
            background=cls.BG_CARD,
            foreground=cls.SUCCESS,
            font=cls.FONT_STATS
        )
        style.configure("Warning.TLabel",
            background=cls.BG_CARD,
            foreground=cls.WARNING,
            font=cls.FONT_STATS
        )

        # === BUTTONS ===
        style.configure("TButton",
            background=cls.ACCENT,
            foreground=cls.TEXT,
            padding=(12, 6),
            font=cls.FONT_BODY
        )
        style.map("TButton",
            background=[
                ("active", cls.ACCENT_HOVER),
                ("disabled", cls.BG_CARD)
            ],
            foreground=[
                ("disabled", cls.TEXT_DISABLED)
            ]
        )

        style.configure("Secondary.TButton",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            padding=(12, 6)
        )
        style.map("Secondary.TButton",
            background=[
                ("active", cls.BG_HOVER),
                ("disabled", cls.BG_PRIMARY)
            ]
        )

        style.configure("Accent.TButton",
            background=cls.ACCENT,
            foreground=cls.TEXT,
            font=cls.FONT_BODY,
            padding=(20, 10)
        )
        style.map("Accent.TButton",
            background=[("active", cls.ACCENT_HOVER)]
        )

        style.configure("Winner.TButton",
            background=cls.SUCCESS,
            foreground=cls.TEXT,
            padding=(8, 4)
        )
        style.map("Winner.TButton",
            background=[("active", "#16a34a")]
        )

        # === CHECKBUTTONS ===
        style.configure("TCheckbutton",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            indicatorbackground=cls.BG_PRIMARY,
            indicatorforeground=cls.SUCCESS
        )
        style.map("TCheckbutton",
            background=[("active", cls.BG_HOVER)],
            indicatorcolor=[
                ("selected", cls.SUCCESS),
                ("!selected", cls.BG_PRIMARY)
            ]
        )

        # === ENTRY ===
        style.configure("TEntry",
            fieldbackground=cls.BG_INPUT,
            foreground=cls.TEXT,
            insertcolor=cls.TEXT,
            padding=(8, 6)
        )
        style.map("TEntry",
            fieldbackground=[("focus", cls.BG_INPUT)],
            bordercolor=[("focus", cls.ACCENT)]
        )

        # === SPINBOX ===
        style.configure("TSpinbox",
            background=cls.BG_INPUT,
            foreground=cls.TEXT,
            fieldbackground=cls.BG_INPUT,
            arrowcolor=cls.TEXT
        )

        # === LABELFRAME ===
        style.configure("TLabelframe",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            bordercolor=cls.BORDER
        )
        style.configure("TLabelframe.Label",
            background=cls.BG_CARD,
            foreground=cls.ACCENT,
            font=cls.FONT_HEADING
        )
        style.configure("Card.TLabelframe",
            background=cls.BG_CARD,
            foreground=cls.TEXT
        )
        style.configure("Card.TLabelframe.Label",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            font=cls.FONT_HEADING
        )

        # === SCROLLBAR ===
        style.configure("Vertical.TScrollbar",
            background=cls.BG_CARD,
            troughcolor=cls.BG_PRIMARY,
            arrowcolor=cls.TEXT
        )
        style.configure("Horizontal.TScrollbar",
            background=cls.BG_CARD,
            troughcolor=cls.BG_PRIMARY,
            arrowcolor=cls.TEXT
        )

        # === PROGRESSBAR ===
        style.configure("TProgressbar",
            background=cls.ACCENT,
            troughcolor=cls.BG_PRIMARY
        )
        style.configure("Green.Horizontal.TProgressbar",
            background=cls.SUCCESS,
            troughcolor=cls.BG_PRIMARY
        )

        # === TREEVIEW ===
        style.configure("Treeview",
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            fieldbackground=cls.BG_CARD,
            rowheight=28,
            font=cls.FONT_BODY
        )
        style.configure("Treeview.Heading",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT,
            font=cls.FONT_HEADING
        )
        style.map("Treeview",
            background=[("selected", cls.ACCENT)],
            foreground=[("selected", cls.TEXT)]
        )

        # === NOTEBOOK (Tabs) ===
        style.configure("TNotebook",
            background=cls.BG_PRIMARY,
            borderwidth=0
        )
        style.configure("TNotebook.Tab",
            background=cls.BG_CARD,
            foreground=cls.TEXT_DIM,
            padding=(16, 8)
        )
        style.map("TNotebook.Tab",
            background=[
                ("selected", cls.BG_PRIMARY),
                ("active", cls.BG_HOVER)
            ],
            foreground=[
                ("selected", cls.TEXT)
            ]
        )

        # === PANEDWINDOW ===
        style.configure("TPanedwindow",
            background=cls.BG_PRIMARY
        )

        # === COMBOBOX ===
        style.configure("TCombobox",
            fieldbackground=cls.BG_INPUT,
            background=cls.BG_CARD,
            foreground=cls.TEXT,
            arrowcolor=cls.TEXT
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", cls.BG_INPUT)],
            selectbackground=[("readonly", cls.ACCENT)]
        )

    @classmethod
    def configure_root(cls, root: tk.Tk | tk.Toplevel):
        """
        Configure a Tk or Toplevel window with theme colors.

        Args:
            root: The window to configure
        """
        root.configure(bg=cls.BG_PRIMARY)
        cls.apply(root)

    @classmethod
    def create_tooltip(cls, widget, text: str):
        """
        Create a themed tooltip for a widget.

        Args:
            widget: The widget to attach the tooltip to
            text: The tooltip text
        """
        tooltip = None

        def show(event):
            nonlocal tooltip
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = tk.Label(
                tooltip,
                text=text,
                font=cls.FONT_SMALL,
                fg=cls.TEXT,
                bg=cls.BG_ELEVATED,
                padx=8,
                pady=4,
                relief="solid",
                borderwidth=1
            )
            label.pack()

        def hide(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)


# Alias for backwards compatibility
ModernStyle = Theme
