# Data Model: Genesis Interactive GUI

**Date**: 2025-11-01
**Phase**: Phase 1 Design
**Status**: Canonical specification

This document defines the canonical data contracts for inter-thread communication and shared data structures.

## Command/Event Architecture

### Overview

Commands flow from GUI thread → Simulation thread (user actions).
Events flow from Simulation thread → GUI thread (state notifications).

**Constitutional Compliance**: Principle IV (Data Pathway Segregation)
- Commands/Events: `queue.Queue` (serializable objects)
- Frames: Shared `numpy.ndarray` + `threading.Lock`
- Plots: `collections.deque` (circular buffer)

---

## Command Contracts

All commands MUST be Python dataclasses with these properties:
- Immutable (frozen=True)
- Serializable (no complex objects)
- Include timestamp for debugging

### Base Command

```python
from dataclasses import dataclass
from typing import Any
import time

@dataclass(frozen=True)
class BaseCommand:
    """Base class for all commands."""
    timestamp: float = time.time()
```

### Command Types

See [contracts/commands.md](./contracts/commands.md) for detailed schemas.

**Summary**:
- `PlayCommand`: Start continuous simulation
- `PauseCommand`: Pause simulation
- `StepCommand`: Advance N timesteps
- `PreviewPropertyCommand`: Temporary property update (no Undo)
- `UpdatePropertyCommand`: Committed property update (adds to Undo)
- `UndoCommand`: Revert last committed change
- `RedoCommand`: Re-apply last undone change
- `RayCastCommand`: Perform viewport raycast for selection

---

## Event Contracts

All events MUST be Python dataclasses following the same structure as commands.

### Base Event

```python
@dataclass(frozen=True)
class BaseEvent:
    """Base class for all events."""
    timestamp: float = time.time()
```

### Event Types

See [contracts/events.md](./contracts/events.md) for detailed schemas.

**Summary**:
- `EntitySelectedEvent`: Entity selection changed
- `WidgetUpdateEvent`: GUI widget should update
- `CollisionEvent`: Physics collision detected
- `LogEvent`: Logging message from simulation

---

## Shared Buffer Specifications

### Frame Buffer

**Purpose**: Transfer rendered frames from simulation thread to GUI thread.

**Specification**:
```python
import numpy as np
import threading

class FrameBuffer:
    """Shared frame buffer with thread-safe access."""

    def __init__(self, width: int, height: int):
        """
        Initialize frame buffer.

        Args:
            width: Viewport width in pixels
            height: Viewport height in pixels
        """
        self.width = width
        self.height = height
        self.size = width * height * 4  # RGBA

        # Shared array (float32 RGBA [0..1] flattened)
        self.data = np.zeros(self.size, dtype=np.float32)

        # Thread synchronization
        self.lock = threading.Lock()

    def write(self, frame: np.ndarray):
        """
        Write frame from simulation thread.

        Args:
            frame: (H, W, 4) float32 RGBA array or (H*W*4,) flat array
        """
        frame_flat = frame.ravel() if frame.ndim > 1 else frame

        assert frame_flat.dtype == np.float32, "Must be float32"
        assert len(frame_flat) == self.size, f"Size mismatch: {len(frame_flat)} != {self.size}"

        with self.lock:
            self.data[:] = frame_flat

    def read(self) -> np.ndarray:
        """
        Read frame from GUI thread.

        Returns:
            Copy of frame data (H*W*4,) flat array
        """
        with self.lock:
            return self.data.copy()

    def read_no_copy(self) -> np.ndarray:
        """
        Read frame without copying (UNSAFE: caller must hold lock).

        Returns:
            View of frame data (not thread-safe)
        """
        return self.data
```

**Constitutional Compliance**:
- ✅ float32 dtype (Principle V)
- ✅ RGBA 4 channels (Principle V)
- ✅ [0..1] range (enforced by conversion layer)
- ✅ 1D flattened (Principle V)
- ✅ Shared memory + Lock (Principle IV)

**Performance Targets**:
- Lock hold time: < 1ms p95
- Copy time (read): ~0.5ms @ 1080p

### Plot Buffer

**Purpose**: Store time-series data for live plotting.

**Specification**:
```python
from collections import deque
from typing import Tuple
import numpy as np

class PlotBuffer:
    """Circular buffer for time-series plot data."""

    def __init__(self, maxlen: int = 10000):
        """
        Initialize plot buffer.

        Args:
            maxlen: Maximum number of samples (oldest dropped when full)
        """
        self.buffer = deque(maxlen=maxlen)
        self.maxlen = maxlen

    def append(self, timestamp: float, value: float):
        """
        Append sample from simulation thread.

        Args:
            timestamp: Simulation time or wall-clock time
            value: Scalar metric value
        """
        self.buffer.append((timestamp, value))

    def get_all(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get all samples (GUI thread).

        Returns:
            (timestamps, values) as numpy arrays
        """
        if not self.buffer:
            return np.array([]), np.array([])

        data = list(self.buffer)
        t = np.array([d[0] for d in data])
        v = np.array([d[1] for d in data])
        return t, v

    def clear(self):
        """Clear all samples."""
        self.buffer.clear()

    def utilization(self) -> float:
        """
        Get buffer utilization percentage.

        Returns:
            0.0 - 1.0 (1.0 = full)
        """
        return len(self.buffer) / self.maxlen
```

**Constitutional Compliance**:
- ✅ deque with maxlen (Principle IV)
- ✅ (timestamp, value) tuple schema (Principle IV)
- ✅ Thread-safe (deque append is atomic)

**Performance Targets**:
- Append latency: < 0.01ms
- Read all: < 1ms for 10k samples

---

## Undo/Redo Model

### Stack Semantics

**Undo Stack**:
- Stores committed `UpdatePropertyCommand` instances
- LIFO (last-in, first-out)
- Maximum size: 100 entries (configurable)
- Grows on each committed edit

**Redo Stack**:
- Stores undone commands
- LIFO
- Cleared when new action committed
- Grows on Undo, shrinks on Redo

### State Transitions

```
Initial State:
  Undo: []
  Redo: []

User drags slider (preview):
  → PreviewPropertyCommand sent
  → Undo: [] (unchanged)
  → Redo: [] (unchanged)

User releases slider (commit):
  → UpdatePropertyCommand(old=5, new=10) sent
  → Undo: [cmd1]
  → Redo: []

User clicks Undo:
  → Apply cmd1.old_value (revert to 5)
  → Undo: []
  → Redo: [cmd1]

User clicks Redo:
  → Apply cmd1.new_value (restore to 10)
  → Undo: [cmd1]
  → Redo: []

User makes new edit:
  → UpdatePropertyCommand(old=10, new=15) sent
  → Undo: [cmd1, cmd2]
  → Redo: [] (cleared!)
```

### Implementation

```python
from typing import List, Optional

class UndoStack:
    """Undo/Redo stack manager."""

    def __init__(self, max_size: int = 100):
        """
        Initialize undo stack.

        Args:
            max_size: Maximum number of undo entries
        """
        self.undo_stack: List[UpdatePropertyCommand] = []
        self.redo_stack: List[UpdatePropertyCommand] = []
        self.max_size = max_size

    def push(self, command: 'UpdatePropertyCommand'):
        """
        Push committed command to undo stack.

        Args:
            command: UpdatePropertyCommand with old/new values
        """
        self.undo_stack.append(command)
        self.redo_stack.clear()  # Clear redo on new action

        # Enforce max size
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)  # Remove oldest

    def undo(self) -> Optional['UpdatePropertyCommand']:
        """
        Pop command from undo stack and push to redo stack.

        Returns:
            Command to revert (or None if empty)
        """
        if not self.undo_stack:
            return None

        command = self.undo_stack.pop()
        self.redo_stack.append(command)
        return command

    def redo(self) -> Optional['UpdatePropertyCommand']:
        """
        Pop command from redo stack and push to undo stack.

        Returns:
            Command to re-apply (or None if empty)
        """
        if not self.redo_stack:
            return None

        command = self.redo_stack.pop()
        self.undo_stack.append(command)
        return command

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def clear(self):
        """Clear both stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
```

**Constitutional Compliance**:
- ✅ Preview commands NOT in stack (Principle VI)
- ✅ Only committed UpdatePropertyCommands in stack (Principle VI)
- ✅ Single commit on release (Principle VI)

### Memory Considerations

| Stack Size | Memory Usage | Notes |
|------------|--------------|-------|
| 10 entries | ~1 KB | Minimal (each command ~100 bytes) |
| 100 entries | ~10 KB | Default (recommended) |
| 1000 entries | ~100 KB | Large (may impact performance) |

**Recommendation**: Cap at 100 entries; sufficient for typical editing sessions.

---

## Entity Property Schema

### Property Types

Properties exposed in inspector are typed and validated:

| Python Type | DPG Widget | Validation |
|-------------|------------|------------|
| `float` | `slider_float` (if bounded) or `input_float` | min/max clamp |
| `Vec3` | `input_floatx(3)` | Per-component min/max |
| `bool` | `checkbox` | None |
| `Enum` | `combo` | Must be valid enum value |
| `str` | `input_text` | Optional regex pattern |

### Property Path Notation

Properties referenced by dot-notation paths:

```python
"position.x"       # Entity position X component
"velocity.z"       # Entity velocity Z component
"mass"             # Scalar property
"material.color"   # Nested property
```

**Parsing**:
```python
def get_nested_property(entity, path: str):
    """Get property value by path."""
    parts = path.split(".")
    obj = entity
    for part in parts:
        obj = getattr(obj, part)
    return obj

def set_nested_property(entity, path: str, value):
    """Set property value by path."""
    parts = path.split(".")
    obj = entity
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)
```

---

## Queue Contracts

### Command Queue

```python
import queue

command_queue = queue.Queue(maxsize=1000)  # Bounded queue

# Producer (GUI thread)
command_queue.put(PlayCommand())

# Consumer (Sim thread)
try:
    cmd = command_queue.get(timeout=0.01)
    process_command(cmd)
except queue.Empty:
    pass  # No commands pending
```

**Characteristics**:
- FIFO (first-in, first-out) strict ordering
- Thread-safe (built-in locks)
- Bounded (maxsize=1000) to prevent memory exhaustion
- Non-blocking get with timeout

### Event Queue

```python
event_queue = queue.Queue(maxsize=1000)  # Bounded queue

# Producer (Sim thread)
event_queue.put(EntitySelectedEvent(entity_id=123))

# Consumer (GUI thread)
while not event_queue.empty():
    event = event_queue.get_nowait()
    handle_event(event)
```

**Characteristics**:
- FIFO (first-in, first-out)
- Thread-safe
- Bounded (maxsize=1000)
- Non-blocking get (get_nowait)

---

## Validation & Observability

### Contract Validation

All commands/events MUST validate on construction:

```python
@dataclass(frozen=True)
class UpdatePropertyCommand(BaseCommand):
    entity_id: int
    property_path: str
    old_value: Any
    new_value: Any

    def __post_init__(self):
        """Validate command fields."""
        assert isinstance(self.entity_id, int), "entity_id must be int"
        assert isinstance(self.property_path, str), "property_path must be str"
        assert self.old_value != self.new_value, "old/new must differ"
```

### Metrics Collection

Monitor queue depths and buffer utilization:

```python
class MetricsCollector:
    def collect(self):
        return {
            "command_queue_depth": command_queue.qsize(),
            "event_queue_depth": event_queue.qsize(),
            "plot_buffer_util": plot_buffer.utilization(),
            "frame_buffer_lock_p95": frame_lock.get_p95_ms()
        }
```

---

## Summary

| Data Structure | Purpose | Thread Safety | Size Limit |
|----------------|---------|---------------|------------|
| **Command Queue** | GUI → Sim actions | queue.Queue (built-in) | 1000 items |
| **Event Queue** | Sim → GUI notifications | queue.Queue (built-in) | 1000 items |
| **Frame Buffer** | Sim → GUI rendered frames | threading.Lock | H×W×4 floats |
| **Plot Buffer** | Sim → GUI time-series | deque (atomic append) | 10,000 samples |
| **Undo Stack** | GUI → Sim reversible edits | Single-threaded (GUI only) | 100 entries |

**Constitutional Compliance**: ✅ All data pathways follow Principle IV (Data Pathway Segregation).

---

## References

- Detailed command schemas: [contracts/commands.md](./contracts/commands.md)
- Detailed event schemas: [contracts/events.md](./contracts/events.md)
- Threading patterns: [research.md](./research.md#threading-pitfalls--mitigations)
