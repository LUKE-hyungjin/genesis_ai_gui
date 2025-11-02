"""
Undo/Redo stack implementation for property editing.

This module implements a stack-based Undo/Redo system that stores
UpdatePropertyCommand history for property edits.

Constitutional Compliance:
- Principle VI: Optimistic UI (only UpdatePropertyCommand on stack, not PreviewPropertyCommand)
- Stack-based history with bounded capacity
- Thread-safe operations (used from simulation thread)

Phase: 4 (Property Editing & Undo)
Tasks: T106-T110
"""

from typing import List, Optional
from dataclasses import dataclass
from src.core.commands import UpdatePropertyCommand


# ============================================================================
# Undo Stack
# ============================================================================

class UndoStack:
    """
    Stack-based Undo/Redo system for property edits.

    Constitutional Compliance: T106
    - Stores only UpdatePropertyCommand (not PreviewPropertyCommand)
    - Bounded capacity to prevent unbounded memory growth
    - Redo stack cleared on new edit (standard Undo/Redo behavior)
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize undo stack.

        Args:
            max_size: Maximum number of undo entries (default 100)
        """
        self.max_size = max_size

        # Undo stack (newest at end)
        self.undo_stack: List[UpdatePropertyCommand] = []

        # Redo stack (newest at end)
        self.redo_stack: List[UpdatePropertyCommand] = []

    def push(self, command: UpdatePropertyCommand):
        """
        Push command onto undo stack.

        Args:
            command: UpdatePropertyCommand to store

        Constitutional Compliance: T110
        - Only UpdatePropertyCommand is pushed (not PreviewPropertyCommand)
        - Clears redo stack (new edit invalidates redo history)
        - Enforces max_size limit (drops oldest if full)
        """
        if not isinstance(command, UpdatePropertyCommand):
            raise TypeError("Only UpdatePropertyCommand can be pushed to undo stack")

        # Clear redo stack (new edit invalidates redo)
        self.redo_stack.clear()

        # Push to undo stack
        self.undo_stack.append(command)

        # Enforce max size (drop oldest)
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)

        print(f"[UNDO_STACK] Pushed: {command.property_path} {command.old_value} → {command.new_value}")
        print(f"[UNDO_STACK] Undo depth: {len(self.undo_stack)}, Redo depth: {len(self.redo_stack)}")

    def undo(self) -> Optional[UpdatePropertyCommand]:
        """
        Pop command from undo stack and move to redo stack.

        Returns:
            UpdatePropertyCommand to undo, or None if stack empty

        Constitutional Compliance: T107
        - Pops from undo stack
        - Pushes to redo stack
        - Returns command for applying old_value
        """
        if not self.can_undo():
            print("[UNDO_STACK] Cannot undo: stack empty")
            return None

        # Pop from undo stack
        command = self.undo_stack.pop()

        # Push to redo stack
        self.redo_stack.append(command)

        print(f"[UNDO_STACK] Undo: {command.property_path} {command.new_value} → {command.old_value}")
        print(f"[UNDO_STACK] Undo depth: {len(self.undo_stack)}, Redo depth: {len(self.redo_stack)}")

        return command

    def redo(self) -> Optional[UpdatePropertyCommand]:
        """
        Pop command from redo stack and move to undo stack.

        Returns:
            UpdatePropertyCommand to redo, or None if stack empty

        Constitutional Compliance: T108
        - Pops from redo stack
        - Pushes to undo stack
        - Returns command for applying new_value
        """
        if not self.can_redo():
            print("[UNDO_STACK] Cannot redo: stack empty")
            return None

        # Pop from redo stack
        command = self.redo_stack.pop()

        # Push back to undo stack
        self.undo_stack.append(command)

        print(f"[UNDO_STACK] Redo: {command.property_path} {command.old_value} → {command.new_value}")
        print(f"[UNDO_STACK] Undo depth: {len(self.undo_stack)}, Redo depth: {len(self.redo_stack)}")

        return command

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return len(self.redo_stack) > 0

    def clear(self):
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        print("[UNDO_STACK] Cleared all stacks")

    def get_undo_depth(self) -> int:
        """Get undo stack depth."""
        return len(self.undo_stack)

    def get_redo_depth(self) -> int:
        """Get redo stack depth."""
        return len(self.redo_stack)

    def peek_undo(self) -> Optional[UpdatePropertyCommand]:
        """
        Peek at top of undo stack without popping.

        Returns:
            Top UpdatePropertyCommand or None if empty
        """
        if self.can_undo():
            return self.undo_stack[-1]
        return None

    def peek_redo(self) -> Optional[UpdatePropertyCommand]:
        """
        Peek at top of redo stack without popping.

        Returns:
            Top UpdatePropertyCommand or None if empty
        """
        if self.can_redo():
            return self.redo_stack[-1]
        return None
