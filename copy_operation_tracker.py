"""
Copy Operation Tracker

Tracks long-running copy operations and enables resume after interruption.
Saves state to a JSON file that persists between sessions.

Author: Claude Code Implementation
Version: 1.0
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)

# State file location
STATE_FILE = Path(__file__).parent / "data" / "pending_copy_operation.json"


class CopyOperationTracker:
    """
    Tracks copy operations and enables resume after interruption.

    Usage:
        tracker = CopyOperationTracker()

        # Check for interrupted operation on startup
        if tracker.has_pending_operation():
            info = tracker.get_pending_info()
            # Show dialog to user asking if they want to resume

        # Start a new operation
        tracker.start_operation(source_files, output_folder, operation_type="tshirt_copy")

        # Mark files as copied
        for file in files:
            shutil.copy2(file, dest)
            tracker.mark_copied(file)

        # Complete operation
        tracker.complete_operation()
    """

    def __init__(self):
        self.state = None
        self._load_state()

    def _load_state(self):
        """Load existing state from disk."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded pending copy operation state: {self.state.get('operation_type', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load copy operation state: {e}")
                self.state = None
        else:
            self.state = None

    def _save_state(self):
        """Save current state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save copy operation state: {e}")

    def _clear_state(self):
        """Clear state from disk."""
        self.state = None
        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
                logger.info("Cleared copy operation state file")
            except Exception as e:
                logger.warning(f"Failed to delete state file: {e}")

    def has_pending_operation(self) -> bool:
        """Check if there's a pending (interrupted) copy operation."""
        if not self.state:
            return False

        # Check if operation was actually interrupted (not completed)
        if self.state.get('completed', False):
            self._clear_state()
            return False

        # Verify destination folder still exists
        output_folder = self.state.get('output_folder')
        if output_folder and not os.path.exists(output_folder):
            logger.info(f"Pending operation's output folder no longer exists: {output_folder}")
            self._clear_state()
            return False

        return True

    def get_pending_info(self) -> Optional[Dict]:
        """Get information about the pending operation."""
        if not self.has_pending_operation():
            return None

        copied_files = set(self.state.get('copied_files', []))
        all_files = self.state.get('source_files', [])
        remaining = [f for f in all_files if f not in copied_files]

        # Verify remaining files still exist
        remaining_valid = [f for f in remaining if os.path.exists(f)]

        return {
            'operation_type': self.state.get('operation_type', 'copy'),
            'output_folder': self.state.get('output_folder'),
            'started_at': self.state.get('started_at'),
            'total_files': len(all_files),
            'copied_count': len(copied_files),
            'remaining_count': len(remaining_valid),
            'remaining_files': remaining_valid
        }

    def start_operation(self, source_files: List[str], output_folder: str,
                        operation_type: str = "copy") -> None:
        """
        Start tracking a new copy operation.

        Args:
            source_files: List of source file paths to copy
            output_folder: Destination folder
            operation_type: Type identifier (e.g., "tshirt_copy", "batch_export")
        """
        self.state = {
            'operation_type': operation_type,
            'source_files': source_files,
            'output_folder': output_folder,
            'copied_files': [],
            'started_at': datetime.now().isoformat(),
            'completed': False
        }
        self._save_state()
        logger.info(f"Started tracking copy operation: {operation_type}, {len(source_files)} files")

    def mark_copied(self, file_path: str) -> None:
        """Mark a file as successfully copied."""
        if not self.state:
            return

        if file_path not in self.state['copied_files']:
            self.state['copied_files'].append(file_path)

            # Save every 10 files to reduce I/O while maintaining reasonable checkpoints
            if len(self.state['copied_files']) % 10 == 0:
                self._save_state()

    def complete_operation(self) -> None:
        """Mark operation as completed and clear state."""
        if self.state:
            self.state['completed'] = True
            self.state['completed_at'] = datetime.now().isoformat()
            logger.info(f"Copy operation completed: {len(self.state.get('copied_files', []))} files")
        self._clear_state()

    def cancel_operation(self) -> None:
        """Cancel and clear the current operation without marking complete."""
        logger.info("Copy operation cancelled by user")
        self._clear_state()

    def resume_operation(self, progress_callback: Optional[Callable] = None,
                         cancel_check: Optional[Callable] = None) -> Dict:
        """
        Resume a pending copy operation.

        Args:
            progress_callback: Optional callback(current, total, filename)
            cancel_check: Optional callable that returns True if should cancel

        Returns:
            Dict with copy statistics
        """
        if not self.has_pending_operation():
            return {'error': 'No pending operation to resume'}

        info = self.get_pending_info()
        remaining_files = info['remaining_files']
        output_folder = info['output_folder']

        if not remaining_files:
            self.complete_operation()
            return {
                'output_folder': output_folder,
                'total_found': info['total_files'],
                'copied': info['copied_count'],
                'failed': 0,
                'failed_files': [],
                'resumed': True
            }

        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        copied = 0
        failed = []
        total = len(remaining_files)

        for i, src_path in enumerate(remaining_files):
            # Check for cancellation
            if cancel_check and cancel_check():
                logger.info("Resume operation cancelled by user")
                self._save_state()  # Save progress
                break

            try:
                src = Path(src_path)
                dst = output_path / src.name

                # Handle duplicate filenames
                if dst.exists():
                    stem = src.stem
                    suffix = src.suffix
                    counter = 1
                    while dst.exists():
                        dst = output_path / f"{stem}_{counter}{suffix}"
                        counter += 1

                shutil.copy2(src, dst)
                self.mark_copied(src_path)
                copied += 1

            except Exception as e:
                logger.error(f"Failed to copy {src_path}: {e}")
                failed.append((src_path, str(e)))

            if progress_callback:
                progress_callback(i + 1, total, os.path.basename(src_path))

        # Check if all files processed
        new_info = self.get_pending_info()
        if new_info and new_info['remaining_count'] == 0:
            self.complete_operation()
        else:
            self._save_state()  # Ensure final state is saved

        return {
            'output_folder': output_folder,
            'total_found': info['total_files'],
            'copied': info['copied_count'] + copied,
            'resumed_copied': copied,
            'failed': len(failed),
            'failed_files': failed,
            'resumed': True
        }


# Global tracker instance
_tracker = None

def get_tracker() -> CopyOperationTracker:
    """Get or create the global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = CopyOperationTracker()
    return _tracker


def check_for_interrupted_copy() -> Optional[Dict]:
    """
    Check for interrupted copy operation.

    Returns:
        Dict with pending operation info, or None if no pending operation
    """
    tracker = get_tracker()
    if tracker.has_pending_operation():
        return tracker.get_pending_info()
    return None
