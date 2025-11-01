# Command Contracts

**Purpose**: Define all command types for GUI → Simulation thread communication.

**Usage**: Commands are immutable dataclasses passed via `queue.Queue`.

---

## Base Command

```python
from dataclasses import dataclass
from typing import Any
import time

@dataclass(frozen=True)
class BaseCommand:
    """Base class for all commands."""
    timestamp: float = time.time()
```

---

## Playback Control Commands

### PlayCommand

**Purpose**: Start continuous simulation.

**Fields**:
```python
@dataclass(frozen=True)
class PlayCommand(BaseCommand):
    """Start continuous simulation playback."""
    pass  # No additional fields
```

**Example**:
```python
cmd = PlayCommand()
command_queue.put(cmd)
```

---

### PauseCommand

**Purpose**: Pause simulation (freeze current state).

**Fields**:
```python
@dataclass(frozen=True)
class PauseCommand(BaseCommand):
    """Pause simulation playback."""
    pass  # No additional fields
```

**Example**:
```python
cmd = PauseCommand()
command_queue.put(cmd)
```

---

### StepCommand

**Purpose**: Advance simulation by N timesteps.

**Fields**:
```python
@dataclass(frozen=True)
class StepCommand(BaseCommand):
    """Step simulation forward."""
    steps: int = 1  # Number of timesteps (default 1)

    def __post_init__(self):
        assert self.steps > 0, "steps must be positive"
```

**Example**:
```python
# Single step
cmd = StepCommand(steps=1)

# Multi-step
cmd = StepCommand(steps=10)

command_queue.put(cmd)
```

---

## Property Edit Commands

### PreviewPropertyCommand

**Purpose**: Temporary property update during drag (no Undo stack modification).

**Fields**:
```python
@dataclass(frozen=True)
class PreviewPropertyCommand(BaseCommand):
    """Preview property change (no Undo)."""
    entity_id: int
    property_path: str
    value: Any

    def __post_init__(self):
        assert isinstance(self.entity_id, int), "entity_id must be int"
        assert isinstance(self.property_path, str), "property_path must be str"
```

**Example**:
```python
# Slider drag (continuous preview)
cmd = PreviewPropertyCommand(
    entity_id=42,
    property_path="position.x",
    value=3.5
)
command_queue.put(cmd)
```

**Constitutional Compliance**: ✅ Principle VI (Optimistic UI - preview only)

---

### UpdatePropertyCommand

**Purpose**: Committed property update with Undo/Redo support.

**Fields**:
```python
@dataclass(frozen=True)
class UpdatePropertyCommand(BaseCommand):
    """Commit property change (adds to Undo stack)."""
    entity_id: int
    property_path: str
    old_value: Any
    new_value: Any

    def __post_init__(self):
        assert isinstance(self.entity_id, int), "entity_id must be int"
        assert isinstance(self.property_path, str), "property_path must be str"
        assert self.old_value != self.new_value, "old/new must differ"
```

**Example**:
```python
# Slider release (commit)
cmd = UpdatePropertyCommand(
    entity_id=42,
    property_path="position.x",
    old_value=2.0,
    new_value=3.5
)
command_queue.put(cmd)
```

**Constitutional Compliance**: ✅ Principle VI (Commit on Release - single Undo entry)

---

## Undo/Redo Commands

### UndoCommand

**Purpose**: Revert last committed property change.

**Fields**:
```python
@dataclass(frozen=True)
class UndoCommand(BaseCommand):
    """Undo last committed change."""
    pass  # No additional fields
```

**Example**:
```python
cmd = UndoCommand()
command_queue.put(cmd)
```

**Processing**:
```python
def handle_undo(undo_stack):
    cmd = undo_stack.undo()  # Returns UpdatePropertyCommand
    if cmd:
        set_property(cmd.entity_id, cmd.property_path, cmd.old_value)
```

---

### RedoCommand

**Purpose**: Re-apply last undone change.

**Fields**:
```python
@dataclass(frozen=True)
class RedoCommand(BaseCommand):
    """Redo last undone change."""
    pass  # No additional fields
```

**Example**:
```python
cmd = RedoCommand()
command_queue.put(cmd)
```

**Processing**:
```python
def handle_redo(undo_stack):
    cmd = undo_stack.redo()  # Returns UpdatePropertyCommand
    if cmd:
        set_property(cmd.entity_id, cmd.property_path, cmd.new_value)
```

---

## Selection Commands

### RayCastCommand

**Purpose**: Perform viewport raycast for entity selection (Phase 5).

**Fields**:
```python
@dataclass(frozen=True)
class RayCastCommand(BaseCommand):
    """Raycast from viewport for entity selection."""
    x_norm: float  # Normalized screen X [0..1]
    y_norm: float  # Normalized screen Y [0..1]

    def __post_init__(self):
        assert 0.0 <= self.x_norm <= 1.0, "x_norm must be in [0..1]"
        assert 0.0 <= self.y_norm <= 1.0, "y_norm must be in [0..1]"
```

**Example**:
```python
# User clicks at screen position (640, 480) in 1280x960 viewport
cmd = RayCastCommand(
    x_norm=640 / 1280,  # 0.5
    y_norm=480 / 960    # 0.5
)
command_queue.put(cmd)
```

**Processing**:
```python
def handle_raycast(scene, camera, cmd):
    # Convert normalized coords to world ray
    ray = camera.screen_to_ray(cmd.x_norm, cmd.y_norm)

    # Raycast against scene
    hit = scene.raycast(ray.origin, ray.direction)

    if hit:
        # Emit EntitySelectedEvent
        event_queue.put(EntitySelectedEvent(entity_id=hit.entity_id))
```

---

## Shutdown Commands

### ShutdownCommand

**Purpose**: Signal simulation thread to exit gracefully.

**Fields**:
```python
@dataclass(frozen=True)
class ShutdownCommand(BaseCommand):
    """Shutdown simulation thread."""
    pass  # No additional fields
```

**Example**:
```python
# User closes window
cmd = ShutdownCommand()
command_queue.put(cmd)
```

**Processing**:
```python
def sim_loop(command_queue, shutdown_flag):
    while not shutdown_flag.is_set():
        cmd = command_queue.get(timeout=0.01)

        if isinstance(cmd, ShutdownCommand):
            shutdown_flag.set()
            break  # Exit loop
```

**Constitutional Compliance**: ✅ Principle VIII (Shutdown Sequence Safety)

---

## Command Summary Table

| Command | Purpose | Undo Support | Phase |
|---------|---------|--------------|-------|
| `PlayCommand` | Start sim | No | 1 |
| `PauseCommand` | Pause sim | No | 1 |
| `StepCommand` | Step N times | No | 1 |
| `PreviewPropertyCommand` | Drag preview | **No** (preview only) | 4 |
| `UpdatePropertyCommand` | Commit edit | **Yes** (Undo/Redo) | 4 |
| `UndoCommand` | Revert last edit | N/A | 4 |
| `RedoCommand` | Re-apply edit | N/A | 4 |
| `RayCastCommand` | Viewport selection | No | 5 |
| `ShutdownCommand` | Exit sim thread | No | 1 |

---

## Usage Patterns

### Playback Control Flow

```python
# GUI button callbacks
def on_play_clicked():
    command_queue.put(PlayCommand())

def on_pause_clicked():
    command_queue.put(PauseCommand())

def on_step_clicked():
    command_queue.put(StepCommand(steps=1))
```

### Property Edit Flow (Optimistic UI)

```python
# Inspector slider callbacks
def on_slider_drag(entity_id, property_path, value):
    # Preview during drag (no Undo)
    command_queue.put(PreviewPropertyCommand(
        entity_id=entity_id,
        property_path=property_path,
        value=value
    ))

def on_slider_release(entity_id, property_path, old_value, new_value):
    # Commit on release (add to Undo)
    command_queue.put(UpdatePropertyCommand(
        entity_id=entity_id,
        property_path=property_path,
        old_value=old_value,
        new_value=new_value
    ))
```

### Undo/Redo Flow

```python
# GUI keyboard shortcuts
def on_ctrl_z():
    if undo_stack.can_undo():
        command_queue.put(UndoCommand())

def on_ctrl_shift_z():
    if undo_stack.can_redo():
        command_queue.put(RedoCommand())
```

---

## Validation & Error Handling

### Command Validation

All commands validate on construction:

```python
try:
    cmd = StepCommand(steps=-1)
except AssertionError as e:
    logging.error(f"Invalid command: {e}")
```

### Queue Full Handling

```python
try:
    command_queue.put(cmd, timeout=0.1)
except queue.Full:
    logging.warning("Command queue full, dropping command")
```

---

## Extension Points

To add new commands:

1. Define dataclass inheriting `BaseCommand`
2. Add `__post_init__` validation
3. Document in this file
4. Implement handler in `src/core/sim_loop.py`
5. Add to command type registry

**Example**:
```python
@dataclass(frozen=True)
class ResetSceneCommand(BaseCommand):
    """Reset scene to initial state."""
    scene_name: str = "default"
```
