"""
File Operations Utility Module

Centralized file handling for image operations, including:
- Moving/copying images with companion files (.txt, .json, etc.)
- File naming conflict resolution
- Disk space validation

This module consolidates file operation logic that was previously duplicated
across auto_sorter.py, batch_exporter.py, and tag_embedder.py.

Author: Claude Code Implementation
Version: 1.0
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Companion file extensions to handle alongside images
COMPANION_EXTENSIONS = ['.txt', '.json', '.yaml', '.yml']


def get_companion_files(image_path: str) -> List[str]:
    """
    Find all companion files for an image (e.g., .txt tag files).

    Args:
        image_path: Path to the image file

    Returns:
        List of paths to companion files that exist
    """
    companions = []
    for ext in COMPANION_EXTENSIONS:
        companion_path = image_path + ext
        if os.path.exists(companion_path):
            companions.append(companion_path)
    return companions


def handle_naming_conflict(dest_path: str) -> str:
    """
    Handle file naming conflicts by adding numeric suffix.

    Args:
        dest_path: Proposed destination path

    Returns:
        Available path (original or with numeric suffix)
    """
    if not os.path.exists(dest_path):
        return dest_path

    base, ext = os.path.splitext(dest_path)
    counter = 1

    while os.path.exists(dest_path):
        dest_path = f"{base}_{counter}{ext}"
        counter += 1

    return dest_path


def move_with_companions(
    source_path: str,
    dest_path: str,
    handle_conflicts: bool = True
) -> List[Tuple[str, str]]:
    """
    Move an image and all its companion files to the destination.

    Args:
        source_path: Source image path
        dest_path: Destination image path
        handle_conflicts: Whether to auto-rename on conflicts

    Returns:
        List of (source, dest) tuples for all files moved
    """
    moved_files = []

    # Handle naming conflicts if requested
    if handle_conflicts:
        dest_path = handle_naming_conflict(dest_path)

    # Move the main image
    shutil.move(source_path, dest_path)
    moved_files.append((source_path, dest_path))

    # Move companion files
    for companion_src in get_companion_files(source_path):
        # Companion files use the same extension pattern: image.png.txt
        ext = os.path.splitext(companion_src)[1]
        companion_dest = dest_path + ext
        if os.path.exists(companion_src):
            shutil.move(companion_src, companion_dest)
            moved_files.append((companion_src, companion_dest))

    return moved_files


def copy_with_companions(
    source_path: str,
    dest_path: str,
    handle_conflicts: bool = True
) -> List[Tuple[str, str]]:
    """
    Copy an image and all its companion files to the destination.

    Args:
        source_path: Source image path
        dest_path: Destination image path
        handle_conflicts: Whether to auto-rename on conflicts

    Returns:
        List of (source, dest) tuples for all files copied
    """
    copied_files = []

    # Handle naming conflicts if requested
    if handle_conflicts:
        dest_path = handle_naming_conflict(dest_path)

    # Copy the main image
    shutil.copy2(source_path, dest_path)
    copied_files.append((source_path, dest_path))

    # Copy companion files
    for companion_src in get_companion_files(source_path):
        ext = os.path.splitext(companion_src)[1]
        companion_dest = dest_path + ext
        if os.path.exists(companion_src):
            shutil.copy2(companion_src, companion_dest)
            copied_files.append((companion_src, companion_dest))

    return copied_files


def check_disk_space(
    files: List[str],
    destination_folder: str,
    safety_margin: float = 1.1
) -> Tuple[bool, Optional[str]]:
    """
    Check if there's enough disk space for an operation.

    Args:
        files: List of file paths to process
        destination_folder: Destination folder path
        safety_margin: Multiplier for required space (1.1 = 10% extra)

    Returns:
        (success, error_message) tuple
    """
    if not destination_folder or not os.path.exists(destination_folder):
        return True, None  # Can't check, assume OK

    try:
        # Calculate total size of files
        total_size = 0
        for file_path in files:
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
                # Include companion files
                for companion in get_companion_files(file_path):
                    total_size += os.path.getsize(companion)

        # Get free space
        free_space = shutil.disk_usage(destination_folder).free

        # Apply safety margin
        required_space = total_size * safety_margin

        if required_space > free_space:
            free_gb = free_space / (1024 ** 3)
            required_gb = required_space / (1024 ** 3)
            error_msg = (
                f"Insufficient disk space: need {required_gb:.2f} GB, "
                f"only {free_gb:.2f} GB available"
            )
            return False, error_msg

        return True, None

    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return True, None  # Log error but allow operation


def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Could not create directory {path}: {e}")
        return False


def format_size(size_bytes: int) -> str:
    """
    Format bytes as human-readable size.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
