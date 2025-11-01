# Event Contracts

**Purpose**: Define all event types for Simulation thread → GUI thread communication.

**Usage**: Events are immutable dataclasses passed via `queue.Queue`.

---

## Base Event

```python
from dataclasses import dataclass
from typing import Any, Optional
import time

@dataclass(frozen=True)
class BaseEvent:
    """Base class for all events."""
    timestamp: float = time.time()
```

---

## Entity Selection Events

### EntitySelectedEvent

**Purpose**: Notify GUI that an entity has been selected (via raycast or programmatic selection).

**Fields**:
```python
@dataclass(frozen=True)
class EntitySelectedEvent(BaseEvent):
    """Entity selection changed."""
    entity_id: Optional[int]  # None = deselection

    def __post_init__(self):
        if self.entity_id is not None:
            assert isinstance(self.entity_id, int), "entity_id must be int or None"
            assert self.entity_id >= 0, "entity_id must be non-negative"
```

**Example**:
```python
# Entity selected via raycast (Phase 5)
event = EntitySelectedEvent(entity_id=42)
event_queue.put(event)

# Deselection (user clicked empty space)
event = EntitySelectedEvent(entity_id=None)
event_queue.put(event)
```

**Processing**:
```python
def handle_entity_selected(event):
    if event.entity_id is None:
        # Clear inspector panel
        dpg.set_value("inspector_label", "No Selection")
        clear_inspector_widgets()
    else:
        # Populate inspector with entity properties
        entity = scene.get_entity(event.entity_id)
        dpg.set_value("inspector_label", f"Entity {event.entity_id}")
        populate_inspector_widgets(entity)
```

**Constitutional Compliance**: ✅ Principle IV (Event queue for GUI updates)

---

## Widget Update Events

### WidgetUpdateEvent

**Purpose**: Update a specific DPG widget value from simulation thread (e.g., FPS counter, timestep display).

**Fields**:
```python
@dataclass(frozen=True)
class WidgetUpdateEvent(BaseEvent):
    """Update DPG widget value."""
    widget_tag: str  # DPG widget tag/ID
    value: Any       # New value (must be JSON-serializable)

    def __post_init__(self):
        assert isinstance(self.widget_tag, str), "widget_tag must be str"
        assert len(self.widget_tag) > 0, "widget_tag cannot be empty"
```

**Example**:
```python
# Update FPS counter
event = WidgetUpdateEvent(
    widget_tag="fps_label",
    value="Sim FPS: 523"
)
event_queue.put(event)

# Update timestep display
event = WidgetUpdateEvent(
    widget_tag="timestep_label",
    value=f"Step: {current_step}"
)
event_queue.put(event)

# Update playback state button
event = WidgetUpdateEvent(
    widget_tag="play_button_label",
    value="Pause"  # Change button text from "Play" to "Pause"
)
event_queue.put(event)
```

**Processing**:
```python
def handle_widget_update(event):
    try:
        dpg.set_value(event.widget_tag, event.value)
    except Exception as e:
        logging.warning(f"Widget update failed for {event.widget_tag}: {e}")
```

**Common Use Cases**:
- FPS/performance metrics
- Simulation timestep counter
- Playback state indicators
- Status bar messages

**Constitutional Compliance**: ✅ Principle IV (Event queue for GUI updates)

---

## Physics Events

### CollisionEvent

**Purpose**: Notify GUI of collision events for logging, debugging, or visualization (Phase 5).

**Fields**:
```python
@dataclass(frozen=True)
class CollisionEvent(BaseEvent):
    """Physics collision detected."""
    entity_a_id: int
    entity_b_id: int
    impulse_magnitude: float  # Collision force magnitude
    contact_point: tuple[float, float, float]  # (x, y, z)

    def __post_init__(self):
        assert isinstance(self.entity_a_id, int), "entity_a_id must be int"
        assert isinstance(self.entity_b_id, int), "entity_b_id must be int"
        assert self.impulse_magnitude >= 0.0, "impulse must be non-negative"
        assert len(self.contact_point) == 3, "contact_point must be (x, y, z)"
```

**Example**:
```python
# Collision between entities 1 and 2
event = CollisionEvent(
    entity_a_id=1,
    entity_b_id=2,
    impulse_magnitude=125.3,
    contact_point=(1.5, 0.0, 2.3)
)
event_queue.put(event)
```

**Processing**:
```python
def handle_collision(event):
    # Log to console
    msg = f"Collision: Entity {event.entity_a_id} <-> {event.entity_b_id} (force={event.impulse_magnitude:.2f}N)"
    logging.info(msg)

    # Add to collision log widget
    dpg.add_text(msg, parent="collision_log_window")

    # Optionally: Add to plot buffer
    collision_plot_buffer.append(event.timestamp, event.impulse_magnitude)
```

**Constitutional Compliance**: ✅ Principle IV (Event queue for notifications)

**Phase**: 5 (Advanced features - collision visualization)

---

## Logging Events

### LogEvent

**Purpose**: Send log messages from simulation thread to GUI console (safer than direct logging from background thread).

**Fields**:
```python
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass(frozen=True)
class LogEvent(BaseEvent):
    """Logging message from simulation thread."""
    level: LogLevel
    message: str
    source: str = "sim"  # Source module/component

    def __post_init__(self):
        assert isinstance(self.level, LogLevel), "level must be LogLevel enum"
        assert isinstance(self.message, str), "message must be str"
        assert len(self.message) > 0, "message cannot be empty"
```

**Example**:
```python
# Info log
event = LogEvent(
    level=LogLevel.INFO,
    message="Simulation started",
    source="sim_loop"
)
event_queue.put(event)

# Warning log
event = LogEvent(
    level=LogLevel.WARNING,
    message="Frame render took 20ms (slow)",
    source="render"
)
event_queue.put(event)

# Error log
event = LogEvent(
    level=LogLevel.ERROR,
    message="Entity 99 not found",
    source="command_handler"
)
event_queue.put(event)
```

**Processing**:
```python
def handle_log_event(event):
    # Format message with timestamp and source
    timestamp_str = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
    formatted = f"[{timestamp_str}] [{event.level.value}] [{event.source}] {event.message}"

    # Log to Python logging
    if event.level == LogLevel.DEBUG:
        logging.debug(formatted)
    elif event.level == LogLevel.INFO:
        logging.info(formatted)
    elif event.level == LogLevel.WARNING:
        logging.warning(formatted)
    elif event.level == LogLevel.ERROR:
        logging.error(formatted)

    # Add to GUI console window
    color = {
        LogLevel.DEBUG: (0.5, 0.5, 0.5),  # Gray
        LogLevel.INFO: (1.0, 1.0, 1.0),   # White
        LogLevel.WARNING: (1.0, 1.0, 0.0), # Yellow
        LogLevel.ERROR: (1.0, 0.0, 0.0)    # Red
    }[event.level]

    dpg.add_text(formatted, parent="console_window", color=color)
```

**Constitutional Compliance**: ✅ Principle IV (Event queue for cross-thread logging)

**Benefits**:
- Thread-safe logging (avoids GIL contention)
- Unified console (all logs in one GUI window)
- Colored output by severity
- Filterable by level/source

---

## Plot Data Events

### PlotDataEvent

**Purpose**: Send time-series data points from simulation to plot buffers (alternative to direct buffer access).

**Fields**:
```python
@dataclass(frozen=True)
class PlotDataEvent(BaseEvent):
    """Time-series plot data point."""
    plot_id: str    # Plot buffer identifier (e.g., "kinetic_energy")
    time: float     # X-axis value (simulation time or wallclock time)
    value: float    # Y-axis value

    def __post_init__(self):
        assert isinstance(self.plot_id, str), "plot_id must be str"
        assert isinstance(self.time, (int, float)), "time must be numeric"
        assert isinstance(self.value, (int, float)), "value must be numeric"
```

**Example**:
```python
# Kinetic energy plot
event = PlotDataEvent(
    plot_id="kinetic_energy",
    time=sim_time,
    value=total_ke
)
event_queue.put(event)

# Multi-metric example
metrics = {
    "kinetic_energy": total_ke,
    "potential_energy": total_pe,
    "total_energy": total_ke + total_pe
}

for plot_id, value in metrics.items():
    event_queue.put(PlotDataEvent(plot_id=plot_id, time=sim_time, value=value))
```

**Processing**:
```python
# GUI thread maintains plot buffers
plot_buffers = {
    "kinetic_energy": PlotBuffer(maxlen=10000),
    "potential_energy": PlotBuffer(maxlen=10000),
    "total_energy": PlotBuffer(maxlen=10000)
}

def handle_plot_data(event):
    if event.plot_id in plot_buffers:
        plot_buffers[event.plot_id].append(event.time, event.value)
    else:
        logging.warning(f"Unknown plot_id: {event.plot_id}")
```

**Alternative**: Direct buffer access from simulation thread
```python
# Alternative: Simulation thread directly accesses plot buffers
# (valid since deque append is thread-safe)
plot_buffer.append(sim_time, total_ke)
```

**Recommendation**: Use direct buffer access for performance; use events if additional processing needed.

**Constitutional Compliance**: ✅ Principle IV (Event queue or deque for plots)

---

## Property Change Events

### PropertyChangedEvent

**Purpose**: Notify GUI that an entity property has changed (e.g., due to physics simulation, not user edit).

**Fields**:
```python
@dataclass(frozen=True)
class PropertyChangedEvent(BaseEvent):
    """Entity property changed in simulation."""
    entity_id: int
    property_path: str
    new_value: Any

    def __post_init__(self):
        assert isinstance(self.entity_id, int), "entity_id must be int"
        assert isinstance(self.property_path, str), "property_path must be str"
```

**Example**:
```python
# Entity position changed due to physics
event = PropertyChangedEvent(
    entity_id=42,
    property_path="position.x",
    new_value=3.72
)
event_queue.put(event)
```

**Processing**:
```python
def handle_property_changed(event):
    # Update inspector if this entity is currently selected
    if current_selection == event.entity_id:
        widget_tag = f"inspector_{event.property_path}"
        try:
            dpg.set_value(widget_tag, event.new_value)
        except Exception as e:
            logging.debug(f"Widget {widget_tag} not found or update failed: {e}")
```

**Use Case**: Reflect simulation-driven changes in inspector (e.g., physics updates position while paused).

**Constitutional Compliance**: ✅ Principle IV (Event queue for notifications)

**Phase**: 4 (Property editing - optional feature for live inspector updates)

---

## Event Summary Table

| Event | Purpose | Typical Frequency | Phase |
|-------|---------|-------------------|-------|
| `EntitySelectedEvent` | Raycast selection result | On user click | 5 |
| `WidgetUpdateEvent` | Update GUI widget value | Variable (FPS, status) | 1 |
| `CollisionEvent` | Physics collision notification | Variable (0-100 Hz) | 5 |
| `LogEvent` | Cross-thread logging | Low (< 10 Hz) | 1 |
| `PlotDataEvent` | Time-series data point | High (60-1000 Hz) | 3 |
| `PropertyChangedEvent` | Property update notification | Variable (0-60 Hz) | 4 |

---

## Usage Patterns

### Event Loop Processing (GUI Thread)

```python
def process_events(event_queue):
    """Process all pending events in GUI thread."""
    while not event_queue.empty():
        try:
            event = event_queue.get_nowait()

            if isinstance(event, EntitySelectedEvent):
                handle_entity_selected(event)
            elif isinstance(event, WidgetUpdateEvent):
                handle_widget_update(event)
            elif isinstance(event, CollisionEvent):
                handle_collision(event)
            elif isinstance(event, LogEvent):
                handle_log_event(event)
            elif isinstance(event, PlotDataEvent):
                handle_plot_data(event)
            elif isinstance(event, PropertyChangedEvent):
                handle_property_changed(event)
            else:
                logging.warning(f"Unknown event type: {type(event)}")

        except queue.Empty:
            break
        except Exception as e:
            logging.error(f"Event processing error: {e}")
```

### Event Emission (Simulation Thread)

```python
def sim_loop(event_queue, frame_buffer, shutdown_flag):
    """Simulation loop emitting events."""
    step_count = 0

    while not shutdown_flag.is_set():
        # Step simulation
        scene.step()
        step_count += 1

        # Emit FPS update (every 60 frames)
        if step_count % 60 == 0:
            fps = calculate_fps()
            event_queue.put(WidgetUpdateEvent(
                widget_tag="fps_label",
                value=f"Sim FPS: {fps:.0f}"
            ))

        # Emit plot data
        ke = calculate_kinetic_energy()
        event_queue.put(PlotDataEvent(
            plot_id="kinetic_energy",
            time=scene.sim_time,
            value=ke
        ))

        # Emit collision events
        for collision in scene.get_collisions():
            event_queue.put(CollisionEvent(
                entity_a_id=collision.entity_a,
                entity_b_id=collision.entity_b,
                impulse_magnitude=collision.impulse,
                contact_point=collision.point
            ))
```

---

## Validation & Error Handling

### Event Validation

All events validate on construction:

```python
try:
    event = WidgetUpdateEvent(widget_tag="", value=123)
except AssertionError as e:
    logging.error(f"Invalid event: {e}")
```

### Queue Full Handling

```python
try:
    event_queue.put(event, timeout=0.1)
except queue.Full:
    logging.warning("Event queue full, dropping event")
```

### Graceful Degradation

```python
def handle_widget_update(event):
    """Update widget with error recovery."""
    try:
        dpg.set_value(event.widget_tag, event.value)
    except SystemError:
        # DPG widget doesn't exist (common during initialization)
        logging.debug(f"Widget {event.widget_tag} not found, skipping")
    except Exception as e:
        # Unexpected error
        logging.error(f"Widget update failed: {e}")
```

---

## Extension Points

To add new event types:

1. Define dataclass inheriting `BaseEvent`
2. Add `__post_init__` validation
3. Document in this file
4. Implement handler in `src/ui/main.py`
5. Add to event dispatcher switch/dict

**Example**:
```python
@dataclass(frozen=True)
class SceneLoadedEvent(BaseEvent):
    """Scene finished loading."""
    scene_name: str
    entity_count: int

    def __post_init__(self):
        assert isinstance(self.scene_name, str), "scene_name must be str"
        assert self.entity_count >= 0, "entity_count must be non-negative"
```

---

## Performance Considerations

### Event Frequency Guidelines

| Frequency | Recommendation | Example |
|-----------|----------------|---------|
| **< 10 Hz** | Safe for all event types | LogEvent, CollisionEvent (sparse) |
| **10-60 Hz** | Safe for lightweight events | WidgetUpdateEvent (FPS counter) |
| **60-1000 Hz** | Use direct buffer access instead | PlotDataEvent → direct deque append |
| **> 1000 Hz** | Never use event queue | Use shared memory (frames, high-rate plots) |

### Memory Usage

| Queue Size | Memory | Notes |
|------------|--------|-------|
| 100 events | ~10 KB | Small events (WidgetUpdate, Log) |
| 1000 events | ~100 KB | Default queue size (safe) |
| 10000 events | ~1 MB | Large queue (risk of backlog) |

**Recommendation**: Cap event queue at 1000 items; monitor `event_queue.qsize()`.

---

## References

- Detailed command schemas: [commands.md](./commands.md)
- Data model overview: [../data-model.md](../data-model.md)
- Threading patterns: [../research.md](../research.md#threading-pitfalls--mitigations)
