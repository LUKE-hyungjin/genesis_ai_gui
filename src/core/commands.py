"""
Command and Event dataclasses for GUI <-> Simulation thread communication.

This module defines all command types (GUI → Sim) and event types (Sim → GUI)
following the constitutional data pathway segregation principle.

All commands and events are immutable (frozen=True) and serializable.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple
from enum import Enum
import time


# ============================================================================
# Base Classes
# ============================================================================

@dataclass(frozen=True)
class BaseCommand:
    """Base class for all commands (GUI → Simulation)."""
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class BaseEvent:
    """Base class for all events (Simulation → GUI)."""
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Playback Control Commands
# ============================================================================

@dataclass(frozen=True)
class PlayCommand(BaseCommand):
    """Start continuous simulation playback."""
    pass  # No additional fields


@dataclass(frozen=True)
class PauseCommand(BaseCommand):
    """Pause simulation playback."""
    pass  # No additional fields


@dataclass(frozen=True)
class StepCommand(BaseCommand):
    """Step simulation forward by N timesteps."""
    steps: int = 1  # Number of timesteps (default 1)

    def __post_init__(self):
        if self.steps <= 0:
            raise ValueError("steps must be positive")


# ============================================================================
# Property Edit Commands
# ============================================================================

@dataclass(frozen=True)
class PreviewPropertyCommand(BaseCommand):
    """
    Temporary property update during drag (no Undo stack modification).

    Constitutional Compliance: Principle VI (Optimistic UI - preview only)
    """
    entity_id: int = field(default=None)
    property_path: str = field(default=None)
    value: Any = field(default=None)

    def __post_init__(self):
        if self.entity_id is None or not isinstance(self.entity_id, int):
            raise TypeError("entity_id must be int")
        if self.property_path is None or not isinstance(self.property_path, str):
            raise TypeError("property_path must be str")


@dataclass(frozen=True)
class UpdatePropertyCommand(BaseCommand):
    """
    Committed property update with Undo/Redo support.

    Constitutional Compliance: Principle VI (Commit on Release - single Undo entry)
    """
    entity_id: int = field(default=None)
    property_path: str = field(default=None)
    old_value: Any = field(default=None)
    new_value: Any = field(default=None)

    def __post_init__(self):
        if self.entity_id is None or not isinstance(self.entity_id, int):
            raise TypeError("entity_id must be int")
        if self.property_path is None or not isinstance(self.property_path, str):
            raise TypeError("property_path must be str")
        if self.old_value == self.new_value:
            raise ValueError("old_value and new_value must differ")


# ============================================================================
# Undo/Redo Commands
# ============================================================================

@dataclass(frozen=True)
class UndoCommand(BaseCommand):
    """Undo last committed change."""
    pass  # No additional fields


@dataclass(frozen=True)
class RedoCommand(BaseCommand):
    """Redo last undone change."""
    pass  # No additional fields


# ============================================================================
# Selection Commands
# ============================================================================

@dataclass(frozen=True)
class RayCastCommand(BaseCommand):
    """
    Perform viewport raycast for entity selection (Phase 5).

    Coordinates are normalized [0..1] screen space.
    """
    x_norm: float = field(default=None)  # Normalized screen X [0..1]
    y_norm: float = field(default=None)  # Normalized screen Y [0..1]

    def __post_init__(self):
        if self.x_norm is None or not (0.0 <= self.x_norm <= 1.0):
            raise ValueError("x_norm must be in [0..1]")
        if self.y_norm is None or not (0.0 <= self.y_norm <= 1.0):
            raise ValueError("y_norm must be in [0..1]")


# ============================================================================
# Shutdown Commands
# ============================================================================

@dataclass(frozen=True)
class ShutdownCommand(BaseCommand):
    """
    Signal simulation thread to exit gracefully.

    Constitutional Compliance: Principle VIII (Shutdown Sequence Safety)
    """
    pass  # No additional fields


# ============================================================================
# Events (Simulation → GUI)
# ============================================================================

@dataclass(frozen=True)
class EntitySelectedEvent(BaseEvent):
    """
    Entity selection changed.

    entity_id=None indicates deselection.
    """
    entity_id: Optional[int] = field(default=None)

    def __post_init__(self):
        if self.entity_id is not None:
            if not isinstance(self.entity_id, int):
                raise TypeError("entity_id must be int or None")
            if self.entity_id < 0:
                raise ValueError("entity_id must be non-negative")


@dataclass(frozen=True)
class WidgetUpdateEvent(BaseEvent):
    """
    Update a specific DPG widget value from simulation thread.

    Used for FPS counters, timestep displays, status indicators.
    """
    widget_tag: str = field(default=None)  # DPG widget tag/ID
    value: Any = field(default=None)       # New value (must be JSON-serializable)

    def __post_init__(self):
        if self.widget_tag is None or not isinstance(self.widget_tag, str):
            raise TypeError("widget_tag must be str")
        if len(self.widget_tag) == 0:
            raise ValueError("widget_tag cannot be empty")


@dataclass(frozen=True)
class CollisionEvent(BaseEvent):
    """
    Physics collision detected (Phase 5).

    Used for logging, debugging, or visualization.
    """
    entity_a_id: int = field(default=None)
    entity_b_id: int = field(default=None)
    impulse_magnitude: float = field(default=None)  # Collision force magnitude
    contact_point: Tuple[float, float, float] = field(default=None)  # (x, y, z)

    def __post_init__(self):
        if self.entity_a_id is None or not isinstance(self.entity_a_id, int):
            raise TypeError("entity_a_id must be int")
        if self.entity_b_id is None or not isinstance(self.entity_b_id, int):
            raise TypeError("entity_b_id must be int")
        if self.impulse_magnitude is None or self.impulse_magnitude < 0.0:
            raise ValueError("impulse must be non-negative")
        if self.contact_point is None or len(self.contact_point) != 3:
            raise ValueError("contact_point must be (x, y, z)")


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class LogEvent(BaseEvent):
    """
    Logging message from simulation thread.

    Safer than direct logging from background thread.
    """
    level: LogLevel = field(default=None)
    message: str = field(default=None)
    source: str = "sim"  # Source module/component

    def __post_init__(self):
        if self.level is None or not isinstance(self.level, LogLevel):
            raise TypeError("level must be LogLevel enum")
        if self.message is None or not isinstance(self.message, str):
            raise TypeError("message must be str")
        if len(self.message) == 0:
            raise ValueError("message cannot be empty")


@dataclass(frozen=True)
class PlotDataEvent(BaseEvent):
    """
    Time-series plot data point.

    Alternative to direct buffer access for plot updates.
    """
    plot_id: str = field(default=None)    # Plot buffer identifier (e.g., "kinetic_energy")
    time: float = field(default=None)     # X-axis value (simulation time or wallclock time)
    value: float = field(default=None)    # Y-axis value

    def __post_init__(self):
        if self.plot_id is None or not isinstance(self.plot_id, str):
            raise TypeError("plot_id must be str")
        if not isinstance(self.time, (int, float)):
            raise TypeError("time must be numeric")
        if not isinstance(self.value, (int, float)):
            raise TypeError("value must be numeric")


@dataclass(frozen=True)
class PropertyChangedEvent(BaseEvent):
    """
    Entity property changed in simulation (not user edit).

    Used to reflect simulation-driven changes in inspector.
    """
    entity_id: int = field(default=None)
    property_path: str = field(default=None)
    new_value: Any = field(default=None)

    def __post_init__(self):
        if self.entity_id is None or not isinstance(self.entity_id, int):
            raise TypeError("entity_id must be int")
        if self.property_path is None or not isinstance(self.property_path, str):
            raise TypeError("property_path must be str")
