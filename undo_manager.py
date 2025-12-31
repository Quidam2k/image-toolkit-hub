"""
Undo/Redo Manager for Image Grid Sorter

Provides comprehensive undo/redo functionality for auto-sort and other
file operations. Maintains operation history with full replayability.

Author: Claude Code Implementation
Version: 1.0
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class UndoManager:
    """Manage undo/redo operations for file manipulation tasks."""

    def __init__(self, max_history: int = 50):
        """
        Initialize the undo manager.

        Args:
            max_history: Maximum number of operations to keep in history
        """
        self.logger = logging.getLogger(__name__)
        self.undo_stack: List[Dict] = []
        self.redo_stack: List[Dict] = []
        self.max_history = max_history

    def record_operation(
        self,
        movements: List[Dict],
        operation_name: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Record an operation for undo capability.

        Args:
            movements: List of file movements (move/copy operations)
            operation_name: Human-readable name of operation
            metadata: Optional metadata about the operation
        """
        if not movements:
            return

        operation = {
            'name': operation_name,
            'timestamp': datetime.now().isoformat(),
            'movements': movements,
            'metadata': metadata or {},
            'status': 'recorded'
        }

        self.undo_stack.append(operation)

        # Limit history size
        if len(self.undo_stack) > self.max_history:
            removed = self.undo_stack.pop(0)
            self.logger.debug(f"Removed oldest operation from history: {removed['name']}")

        # Clear redo stack when new operation recorded
        self.redo_stack.clear()

        self.logger.info(f"Operation recorded: {operation_name} ({len(movements)} movements)")

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of operation that would be undone."""
        if not self.can_undo():
            return None
        return self.undo_stack[-1]['name']

    def get_redo_description(self) -> Optional[str]:
        """Get description of operation that would be redone."""
        if not self.can_redo():
            return None
        return self.redo_stack[-1]['name']

    def undo_last_operation(self) -> Tuple[bool, str]:
        """
        Reverse the last recorded operation.

        Returns:
            (success, message) tuple
        """
        if not self.can_undo():
            return False, "Nothing to undo"

        try:
            operation = self.undo_stack.pop()
            self.logger.info(f"Undoing: {operation['name']}")

            # Reverse movements in reverse order
            errors = []
            for movement in reversed(operation['movements']):
                try:
                    if movement['operation'] == 'move':
                        # Reverse: move from destination back to source
                        os.makedirs(os.path.dirname(movement['source']), exist_ok=True)
                        shutil.move(movement['destination'], movement['source'])

                    elif movement['operation'] == 'copy':
                        # Reverse: delete the copy
                        if os.path.exists(movement['destination']):
                            os.remove(movement['destination'])

                except Exception as e:
                    error_msg = f"Failed to reverse {movement['operation']}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

            # Move operation to redo stack
            self.redo_stack.append(operation)

            if errors:
                error_str = "; ".join(errors)
                return False, f"Partial undo completed with errors: {error_str}"

            success_msg = f"Undone: {operation['name']} ({len(operation['movements'])} files)"
            self.logger.info(success_msg)
            return True, success_msg

        except Exception as e:
            error_msg = f"Error during undo: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def redo_operation(self) -> Tuple[bool, str]:
        """
        Replay the last undone operation.

        Returns:
            (success, message) tuple
        """
        if not self.can_redo():
            return False, "Nothing to redo"

        try:
            operation = self.redo_stack.pop()
            self.logger.info(f"Redoing: {operation['name']}")

            # Replay movements in original order
            errors = []
            for movement in operation['movements']:
                try:
                    if movement['operation'] == 'move':
                        # Redo: move from source to destination
                        os.makedirs(os.path.dirname(movement['destination']), exist_ok=True)
                        shutil.move(movement['source'], movement['destination'])

                    elif movement['operation'] == 'copy':
                        # Redo: copy from source to destination
                        os.makedirs(os.path.dirname(movement['destination']), exist_ok=True)
                        shutil.copy2(movement['source'], movement['destination'])

                except Exception as e:
                    error_msg = f"Failed to redo {movement['operation']}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

            # Move operation back to undo stack
            self.undo_stack.append(operation)

            if errors:
                error_str = "; ".join(errors)
                return False, f"Partial redo completed with errors: {error_str}"

            success_msg = f"Redone: {operation['name']} ({len(operation['movements'])} files)"
            self.logger.info(success_msg)
            return True, success_msg

        except Exception as e:
            error_msg = f"Error during redo: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def clear_history(self) -> None:
        """Clear all undo and redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.logger.info("Undo/redo history cleared")

    def get_history_stats(self) -> Dict:
        """Get statistics about undo/redo history."""
        return {
            'undo_count': len(self.undo_stack),
            'redo_count': len(self.redo_stack),
            'max_history': self.max_history,
            'undo_operations': [op['name'] for op in self.undo_stack[-10:]],
            'redo_operations': [op['name'] for op in self.redo_stack[-10:]]
        }
