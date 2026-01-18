"""
Toast Notification Manager for Image Toolkit Hub

Provides non-blocking toast notifications that appear in the bottom-right
corner of the screen. Toasts auto-dismiss after a configurable timeout
and stack vertically when multiple notifications are active.

Usage:
    from toast_manager import ToastManager

    # Initialize once with your root window
    toast = ToastManager(root)

    # Show notifications
    toast.show_success("Auto-sort complete", "847 images sorted to 12 folders")
    toast.show_error("Export failed", "Insufficient disk space")
    toast.show_info("Processing", "Tag embedding in progress...")

Author: Claude Code Implementation
Version: 1.0
"""

import tkinter as tk
from typing import Optional, Literal
from ui_theme import Theme


ToastType = Literal["success", "error", "warning", "info"]


class Toast:
    """Individual toast notification window."""

    # Toast dimensions
    WIDTH = 320
    HEIGHT = 80
    PADDING = 12
    MARGIN = 10  # Space between stacked toasts

    def __init__(
        self,
        manager: "ToastManager",
        title: str,
        message: str,
        toast_type: ToastType = "info",
        duration: int = 5000,
        position_index: int = 0
    ):
        self.manager = manager
        self.duration = duration
        self.position_index = position_index
        self.dismissed = False

        # Create borderless window
        self.window = tk.Toplevel(manager.root)
        self.window.withdraw()  # Hide initially
        self.window.overrideredirect(True)  # No window decorations
        self.window.attributes("-topmost", True)  # Stay on top

        # Set window transparency (Windows)
        try:
            self.window.attributes("-alpha", 0.95)
        except tk.TclError:
            pass  # Alpha not supported on this platform

        # Configure window
        self.window.configure(bg=Theme.BG_CARD)

        # Create main frame with border effect
        self.frame = tk.Frame(
            self.window,
            bg=Theme.BG_CARD,
            highlightbackground=self._get_accent_color(toast_type),
            highlightthickness=2
        )
        self.frame.pack(fill="both", expand=True)

        # Inner padding frame
        inner = tk.Frame(self.frame, bg=Theme.BG_CARD)
        inner.pack(fill="both", expand=True, padx=self.PADDING, pady=self.PADDING)

        # Header row (icon + title + close button)
        header = tk.Frame(inner, bg=Theme.BG_CARD)
        header.pack(fill="x")

        # Type icon
        icon = self._get_icon(toast_type)
        icon_label = tk.Label(
            header,
            text=icon,
            font=("Segoe UI", 14),
            fg=self._get_accent_color(toast_type),
            bg=Theme.BG_CARD
        )
        icon_label.pack(side="left", padx=(0, 8))

        # Title
        title_label = tk.Label(
            header,
            text=title,
            font=Theme.FONT_HEADING,
            fg=Theme.TEXT,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)

        # Close button
        close_btn = tk.Label(
            header,
            text="✕",
            font=("Segoe UI", 10),
            fg=Theme.TEXT_DIM,
            bg=Theme.BG_CARD,
            cursor="hand2"
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.dismiss())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=Theme.TEXT))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=Theme.TEXT_DIM))

        # Message
        if message:
            msg_label = tk.Label(
                inner,
                text=message,
                font=Theme.FONT_BODY,
                fg=Theme.TEXT_DIM,
                bg=Theme.BG_CARD,
                anchor="w",
                wraplength=self.WIDTH - (self.PADDING * 2) - 20
            )
            msg_label.pack(fill="x", pady=(6, 0))

        # Click anywhere to dismiss
        for widget in [self.frame, inner, header, title_label]:
            widget.bind("<Button-1>", lambda e: self.dismiss())

        # Position and show
        self._position()
        self.window.deiconify()

        # Schedule auto-dismiss
        if duration > 0:
            self.window.after(duration, self.dismiss)

    def _get_accent_color(self, toast_type: ToastType) -> str:
        """Get the accent color for the toast type."""
        colors = {
            "success": Theme.SUCCESS,
            "error": Theme.ERROR,
            "warning": Theme.WARNING,
            "info": Theme.ACCENT
        }
        return colors.get(toast_type, Theme.ACCENT)

    def _get_icon(self, toast_type: ToastType) -> str:
        """Get the icon character for the toast type."""
        icons = {
            "success": "✓",
            "error": "✕",
            "warning": "⚠",
            "info": "ℹ"
        }
        return icons.get(toast_type, "ℹ")

    def _position(self):
        """Position the toast in the bottom-right corner."""
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Calculate position (bottom-right with margin)
        x = screen_width - self.WIDTH - 20
        y = screen_height - self.HEIGHT - 60 - (self.position_index * (self.HEIGHT + self.MARGIN))

        self.window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def update_position(self, new_index: int):
        """Update toast position when stack changes."""
        self.position_index = new_index
        if not self.dismissed:
            self._position()

    def dismiss(self):
        """Dismiss the toast."""
        if self.dismissed:
            return
        self.dismissed = True

        try:
            self.window.destroy()
        except tk.TclError:
            pass  # Window already destroyed

        self.manager._on_toast_dismissed(self)


class ToastManager:
    """
    Manages toast notifications for the application.

    Create one instance per application, passing the root window.
    Then use show_success(), show_error(), show_warning(), show_info()
    to display notifications.
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the toast manager.

        Args:
            root: The main Tk window (needed to create Toplevel windows)
        """
        self.root = root
        self.active_toasts: list[Toast] = []

    def show(
        self,
        title: str,
        message: str = "",
        toast_type: ToastType = "info",
        duration: int = 5000
    ) -> Toast:
        """
        Show a toast notification.

        Args:
            title: The toast title (bold text)
            message: Optional secondary message
            toast_type: Type of toast (success, error, warning, info)
            duration: Auto-dismiss time in ms (0 = no auto-dismiss)

        Returns:
            The Toast instance
        """
        position = len(self.active_toasts)
        toast = Toast(
            self,
            title=title,
            message=message,
            toast_type=toast_type,
            duration=duration,
            position_index=position
        )
        self.active_toasts.append(toast)
        return toast

    def show_success(self, title: str, message: str = "", duration: int = 5000) -> Toast:
        """Show a success toast (green accent)."""
        return self.show(title, message, "success", duration)

    def show_error(self, title: str, message: str = "", duration: int = 8000) -> Toast:
        """Show an error toast (red accent, longer duration)."""
        return self.show(title, message, "error", duration)

    def show_warning(self, title: str, message: str = "", duration: int = 6000) -> Toast:
        """Show a warning toast (amber accent)."""
        return self.show(title, message, "warning", duration)

    def show_info(self, title: str, message: str = "", duration: int = 5000) -> Toast:
        """Show an info toast (blue accent)."""
        return self.show(title, message, "info", duration)

    def dismiss_all(self):
        """Dismiss all active toasts."""
        for toast in self.active_toasts[:]:  # Copy list to avoid modification during iteration
            toast.dismiss()

    def _on_toast_dismissed(self, toast: Toast):
        """Called when a toast is dismissed. Reposition remaining toasts."""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)

        # Reposition remaining toasts
        for i, remaining_toast in enumerate(self.active_toasts):
            remaining_toast.update_position(i)


# Singleton instance for convenience (optional pattern)
_global_manager: Optional[ToastManager] = None


def init(root: tk.Tk) -> ToastManager:
    """Initialize the global toast manager."""
    global _global_manager
    _global_manager = ToastManager(root)
    return _global_manager


def get_manager() -> Optional[ToastManager]:
    """Get the global toast manager instance."""
    return _global_manager


def show_success(title: str, message: str = "") -> Optional[Toast]:
    """Show a success toast using the global manager."""
    if _global_manager:
        return _global_manager.show_success(title, message)
    return None


def show_error(title: str, message: str = "") -> Optional[Toast]:
    """Show an error toast using the global manager."""
    if _global_manager:
        return _global_manager.show_error(title, message)
    return None


def show_warning(title: str, message: str = "") -> Optional[Toast]:
    """Show a warning toast using the global manager."""
    if _global_manager:
        return _global_manager.show_warning(title, message)
    return None


def show_info(title: str, message: str = "") -> Optional[Toast]:
    """Show an info toast using the global manager."""
    if _global_manager:
        return _global_manager.show_info(title, message)
    return None
