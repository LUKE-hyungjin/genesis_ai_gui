# Quickstart Guide: Genesis Interactive GUI

**Date**: 2025-11-01
**Purpose**: Get started with development, validate phase checkpoints, and troubleshoot common issues
**Audience**: Developers implementing the Genesis Interactive GUI

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Phase Validation Checklists](#phase-validation-checklists)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Performance Profiling](#performance-profiling)
5. [References](#references)

---

## Development Setup

### Prerequisites

**Required Software**:
- Python 3.11+ (3.11.0 or later)
- pip 23.0+ (for package management)
- Git (for version control)

**Hardware Requirements**:
- GPU with Vulkan/Metal/CUDA support (see [Backend Selection](#backend-selection))
- 8 GB RAM minimum (16 GB recommended for complex scenes)
- 1920x1080 display minimum

**Operating Systems**:
- macOS 14+ (Sonoma or later) - Metal backend
- Linux (Ubuntu 22.04+, other distros with Vulkan/CUDA) - CUDA/Vulkan backend
- Windows 10/11 - CUDA/Vulkan backend

---

### Backend Selection

Genesis requires a Taichi GPU backend. The backend is selected automatically based on your system:

| OS | Primary Backend | Fallback Backend | Requirements |
|----|-----------------|------------------|--------------|
| **macOS** | Metal | Vulkan | macOS 14+, Apple Silicon or Intel with Metal support |
| **Linux** | CUDA (NVIDIA) | Vulkan | NVIDIA GPU with CUDA 11.0+ OR Vulkan 1.2+ |
| **Windows** | CUDA (NVIDIA) | Vulkan | NVIDIA GPU with CUDA 11.0+ OR Vulkan 1.2+ |

**To check available backends**:
```bash
python -c "import taichi as ti; print(ti.get_available_backends())"
```

---

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd genesis_ai_gui
```

---

### Step 2: Create Virtual Environment

**Using venv (recommended)**:
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows
```

**Using conda (alternative)**:
```bash
conda create -n genesis-gui python=3.11
conda activate genesis-gui
```

---

### Step 3: Install Dependencies

**Core Dependencies**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Install Genesis (includes Taichi)
pip install genesis-world

# Install Dear PyGui
pip install dearpygui

# Install downsampling library
pip install tsdownsample

# Install NumPy (if not already installed by Genesis)
pip install numpy>=1.24.0
```

**Development Dependencies** (optional):
```bash
# Testing
pip install pytest pytest-cov

# Linting/formatting
pip install black ruff mypy

# Profiling
pip install py-spy memray
```

**Verify Installation**:
```bash
python -c "import genesis as gs; import dearpygui.dearpygui as dpg; import tsdownsample; print('All imports successful!')"
```

---

### Step 4: Verify GPU Backend

Run the backend detection script:

```python
# save as test_backend.py
import platform
import genesis as gs

def test_backend_init():
    """Test Genesis backend initialization."""
    system = platform.system()
    print(f"Operating System: {system}")

    try:
        if system == "Darwin":  # macOS
            print("Attempting Metal backend...")
            gs.init(backend=gs.metal)
            print("✅ Metal backend initialized successfully")
        else:
            print("Attempting CUDA backend...")
            gs.init(backend=gs.cuda)
            print("✅ CUDA backend initialized successfully")
    except Exception as e:
        print(f"⚠️  Primary backend failed: {e}")
        print("Attempting Vulkan fallback...")
        try:
            gs.init(backend=gs.vulkan)
            print("✅ Vulkan backend initialized successfully")
        except Exception as e2:
            print(f"❌ All backends failed: {e2}")
            print("Check GPU drivers and Taichi installation")
            return False

    return True

if __name__ == "__main__":
    success = test_backend_init()
    exit(0 if success else 1)
```

**Run**:
```bash
python test_backend.py
```

**Expected Output**:
```
Operating System: Darwin
Attempting Metal backend...
✅ Metal backend initialized successfully
```

---

### Step 5: Project Structure Setup

Create the recommended directory structure:

```bash
mkdir -p src/core src/ui src/infra tests docs
```

**Resulting structure**:
```
genesis_ai_gui/
├── src/
│   ├── core/           # Simulation thread logic
│   │   ├── sim_loop.py
│   │   ├── ipc.py
│   │   └── commands.py
│   ├── ui/             # GUI thread logic
│   │   ├── main.py
│   │   ├── viewport.py
│   │   ├── inspector.py
│   │   ├── plots.py
│   │   └── gizmo.py
│   └── infra/          # Shared infrastructure
│       ├── bootstrap.py
│       ├── metrics.py
│       └── config.py
├── tests/              # Unit tests
├── specs/              # Specifications
└── .venv/              # Virtual environment
```

---

## Phase Validation Checklists

Use these checklists to manually validate each phase's Definition of Done (DoD) locally before proceeding to the next phase.

---

### Phase 1: Mock Thread + GUI Wiring

**Objective**: Validate threading architecture with mock simulation loop.

**Setup**:
1. Implement `src/core/sim_loop.py` with mock loop (no Genesis yet)
2. Implement `src/ui/main.py` with DPG window and Play/Pause/Step buttons
3. Implement `src/core/ipc.py` with command/event queues
4. Implement `src/ui/viewport.py` with raw texture placeholder

**Manual Validation Steps**:

```bash
# Run the application
python src/ui/main.py
```

**Checklist**:

- [ ] **Window Launch**
  - DPG window appears at 1280x720 resolution
  - Window title is "Genesis Interactive GUI - Phase 1"
  - No crashes during startup

- [ ] **Mock Viewport**
  - Viewport panel shows 640x480 colored rectangle (test pattern)
  - Color cycles slowly (e.g., red → green → blue over 5 seconds)
  - Texture updates smoothly at ~60 FPS

- [ ] **Playback Controls**
  - "Play" button starts mock simulation loop
  - "Pause" button pauses mock loop
  - "Step" button advances 1 timestep when paused
  - Button states update correctly (Play ↔ Pause)

- [ ] **FPS Display**
  - GUI FPS counter shows ~60 FPS (stable)
  - Sim FPS counter shows 500+ FPS (mock loop is fast)
  - FPS updates every second

- [ ] **Threading Validation**
  - Open Activity Monitor/Task Manager: 2 Python threads visible
  - GUI remains responsive while simulation runs (try dragging window)
  - No "Application Not Responding" warnings

- [ ] **Shutdown**
  - Close window with X button: application exits cleanly within 1 second
  - No zombie threads remain (check Activity Monitor)
  - No segmentation faults or Python tracebacks

**Common Issues**:
- If GUI freezes: Simulation loop is blocking main thread (check threading setup)
- If mock texture is black: DPG texture format is wrong (see [Troubleshooting](#green-or-noisy-texture))
- If window doesn't appear: DPG context not created on main thread (see [Context Init Failures](#context-initialization-failures))

**Success Criteria**: All checkboxes ✅ → Proceed to Phase 2

---

### Phase 2: Genesis Renderer Integration

**Objective**: Replace mock texture with real Genesis camera output.

**Setup**:
1. Update `src/core/sim_loop.py` to initialize Genesis scene with camera
2. Implement frame conversion pipeline (Genesis → DPG texture format)
3. Update frame buffer to handle real frames

**Manual Validation Steps**:

```bash
# Run with Genesis backend
python src/ui/main.py
```

**Checklist**:

- [ ] **Backend Initialization**
  - Terminal shows backend selection log (Metal/CUDA/Vulkan)
  - No Taichi/Genesis initialization errors
  - Backend init completes within 5 seconds

- [ ] **Scene Rendering**
  - Viewport shows rendered 3D scene (simple cube/sphere + ground plane)
  - Camera view is correct (entities visible, not clipped)
  - Colors are accurate (no green tint, no noise)

- [ ] **Texture Update**
  - Scene renders at 60 FPS in viewport
  - No flickering or tearing
  - Frame updates are smooth (no stuttering)

- [ ] **Playback Controls**
  - "Play" starts continuous physics simulation
  - "Pause" freezes scene (entities stop moving)
  - "Step" advances 1 physics timestep (entities move slightly)

- [ ] **Frame Format Validation**
  - Run validation script:
    ```python
    import numpy as np
    # After rendering one frame
    assert frame_buffer.data.dtype == np.float32
    assert frame_buffer.data.ndim == 1
    assert len(frame_buffer.data) % 4 == 0
    assert frame_buffer.data.min() >= 0.0
    assert frame_buffer.data.max() <= 1.0
    print("✅ Frame format valid")
    ```
  - No assertion errors

- [ ] **Performance**
  - GUI FPS: 60 FPS (stable)
  - Sim FPS: 500+ FPS (simple scene)
  - Frame conversion overhead: < 3ms (measure with `time.perf_counter()`)

- [ ] **Memory Leaks**
  - Run for 60 seconds continuously
  - Memory usage remains stable (< 500 MB growth)
  - No Python garbage collection warnings

**Common Issues**:
- Green tint: Texture format wrong (see [Troubleshooting](#green-or-noisy-texture))
- Black screen: Camera not positioned correctly or no entities in scene
- Crash on init: Backend/GPU issue (see [Context Init Failures](#context-initialization-failures))

**Success Criteria**: All checkboxes ✅ → Proceed to Phase 3

---

### Phase 3: Dual Loop Optimization + Inspector Panel

**Objective**: Optimize frame pipeline and add basic inspector UI.

**Setup**:
1. Implement frame skipping logic (render every Nth simulation step)
2. Implement `src/ui/inspector.py` with property display (read-only)
3. Add plot panel with 1 metric (e.g., kinetic energy)

**Manual Validation Steps**:

```bash
python src/ui/main.py
```

**Checklist**:

- [ ] **Frame Skipping**
  - Set simulation to 1000 Hz, rendering to 60 Hz
  - Sim FPS: 1000+ FPS
  - GUI FPS: 60 FPS (stable)
  - Viewport updates at 60 FPS (smooth, no stuttering)

- [ ] **Inspector Panel**
  - Right panel shows "Inspector" title
  - When no entity selected: Shows "No Selection"
  - Hardcode selection of entity 0 (for testing):
    - Shows "Entity 0"
    - Displays properties: position (x, y, z), velocity (x, y, z), mass
    - Values update in real-time during simulation

- [ ] **Plot Panel**
  - Bottom panel shows plot titled "Kinetic Energy"
  - Plot updates in real-time during simulation (smooth line)
  - X-axis: simulation time, Y-axis: energy value
  - No lag or stuttering in plot updates

- [ ] **Performance Targets**
  - GUI FPS: 60 FPS (stable)
  - Sim FPS: 1000+ FPS (complex scene)
  - Frame latency: < 16.7ms p95 (measure with logging)
  - Plot downsampling: 10,000 samples → 1,000 rendered (via LTTB)

- [ ] **Stress Test**
  - Run for 5 minutes continuously
  - All FPS counters remain stable
  - No memory leaks (< 1 GB growth)
  - No GUI stuttering

**Common Issues**:
- Sim FPS drops below 1000: Frame skipping not working or lock contention
- Inspector not updating: Event queue not being processed
- Plot stutters: Downsampling not enabled or plot buffer too large

**Success Criteria**: All checkboxes ✅ → Proceed to Phase 4 (optional)

---

### Phase 4: Property Editing + Undo/Redo

**Objective**: Enable live property editing with Undo/Redo support.

**Setup**:
1. Update `src/ui/inspector.py` with editable sliders/inputs
2. Implement `PreviewPropertyCommand` for drag preview
3. Implement `UpdatePropertyCommand` for commit
4. Implement `UndoCommand`/`RedoCommand` and undo stack
5. Add keyboard shortcuts (Ctrl+Z, Ctrl+Shift+Z)

**Manual Validation Steps**:

```bash
python src/ui/main.py
```

**Checklist**:

- [ ] **Inspector Editing**
  - Select entity (hardcoded for Phase 4 testing)
  - Inspector shows editable sliders for position.x (range: -10 to 10)
  - Drag slider: Entity position updates in real-time (preview)
  - Release slider: Single Undo entry created

- [ ] **Preview Behavior**
  - While dragging slider:
    - Entity position updates smoothly
    - No Undo stack growth (check via debug print)
  - After release:
    - Undo stack has 1 new entry (old_value → new_value)

- [ ] **Undo Functionality**
  - Make 3 edits (change position.x three times)
  - Press Ctrl+Z: Last edit reverts
  - Press Ctrl+Z again: Second-to-last edit reverts
  - Press Ctrl+Z again: Third-to-last edit reverts
  - Press Ctrl+Z again: Nothing happens (undo stack empty)

- [ ] **Redo Functionality**
  - After undoing 3 edits:
    - Press Ctrl+Shift+Z: First edit re-applies
    - Press Ctrl+Shift+Z again: Second edit re-applies
    - Press Ctrl+Shift+Z again: Third edit re-applies
  - Make new edit: Redo stack clears (verify via debug print)

- [ ] **Edge Cases**
  - Undo while simulation running: Works correctly
  - Undo while dragging slider: Slider updates to undone value
  - Undo stack max size: After 100 edits, oldest entry is discarded

- [ ] **Performance**
  - Preview updates: < 1ms per command (measure with logging)
  - Commit latency: < 10ms (slider release → entity update)
  - Undo/Redo latency: < 5ms

**Common Issues**:
- Multiple Undo entries per drag: `PreviewPropertyCommand` being added to stack (bug)
- Undo doesn't work: Command not being processed or property not reverting
- Slider doesn't update after Undo: Inspector not listening to property change events

**Success Criteria**: All checkboxes ✅ → Proceed to Phase 5 (optional)

---

### Phase 5: Raycasting + Gizmo Manipulation

**Objective**: Add entity selection via raycasting and 3D gizmo manipulation.

**Setup**:
1. Implement viewport click → raycast command flow
2. Implement raycast in simulation thread
3. Implement selection feedback (highlight, outline)
4. Add 3D gizmo widget (translate/rotate/scale)

**Manual Validation Steps**:

```bash
python src/ui/main.py
```

**Checklist**:

- [ ] **Entity Selection**
  - Click on entity in viewport: Entity becomes selected
  - Inspector updates to show selected entity properties
  - Click on empty space: Selection clears (inspector shows "No Selection")

- [ ] **Selection Feedback**
  - Selected entity has visual highlight (e.g., outline, bounding box)
  - Highlight updates immediately after click (< 100ms latency)

- [ ] **Gizmo Manipulation**
  - When entity selected: 3D gizmo appears at entity origin
  - Gizmo has 3 axes (X=red, Y=green, Z=blue)
  - Drag X-axis arrow: Entity moves along X only
  - Drag Y-axis arrow: Entity moves along Y only
  - Drag Z-axis arrow: Entity moves along Z only

- [ ] **Gizmo Modes**
  - Press "W" key: Translate mode (arrows)
  - Press "E" key: Rotate mode (circles)
  - Press "R" key: Scale mode (boxes)
  - Each mode works correctly

- [ ] **Undo Integration**
  - Drag gizmo to move entity: Single Undo entry created
  - Undo: Entity returns to original position
  - Redo: Entity returns to moved position

- [ ] **Edge Cases**
  - Raycast miss (click on sky): No crash, no selection change (or deselect)
  - Raycast multiple entities (overlapping): Closest entity selected
  - Gizmo manipulation while simulation running: Works correctly

- [ ] **Performance**
  - Raycast latency: < 100ms (click → selection)
  - Gizmo update latency: < 16ms (drag → visual feedback)

**Common Issues**:
- Raycast always misses: Camera/ray calculation is wrong
- Gizmo doesn't appear: Gizmo rendering not implemented or wrong position
- Gizmo manipulation doesn't commit: `UpdatePropertyCommand` not being sent

**Success Criteria**: All checkboxes ✅ → All phases complete!

---

## Troubleshooting Guide

### Context Initialization Failures

**Symptom**:
- Segmentation fault on startup
- Error: "Cannot initialize Taichi context from non-main thread"
- DPG window doesn't appear

**Cause**: Graphics contexts (Taichi, DPG) created in background thread instead of main thread.

**Solution**:

1. **Verify initialization order** in `main.py`:
   ```python
   def main():
       # STEP 1: Initialize Genesis (MAIN THREAD ONLY)
       backend = select_backend()
       gs.init(backend=backend)

       # STEP 2: Create Genesis scene (MAIN THREAD ONLY)
       scene = gs.Scene(...)

       # STEP 3: Initialize DPG (MAIN THREAD ONLY)
       dpg.create_context()
       dpg.setup_dearpygui()

       # STEP 4: Start background thread AFTER all contexts ready
       sim_thread = threading.Thread(target=sim_loop, args=(scene, ...))
       sim_thread.start()

       # STEP 5: Run DPG render loop (MAIN THREAD)
       while dpg.is_dearpygui_running():
           dpg.render_dearpygui_frame()
   ```

2. **Check thread creation**:
   - All `gs.init()`, `gs.Scene()`, `dpg.create_context()` calls must be in `main()` function
   - Background thread must be started AFTER all contexts are ready
   - Never call `gs.init()` inside `sim_loop()` function

3. **Validate with logging**:
   ```python
   import threading

   def main():
       print(f"Main thread ID: {threading.current_thread().ident}")
       gs.init(backend=gs.metal)  # Should print same thread ID
       scene = gs.Scene(...)       # Should print same thread ID

       def sim_loop():
           print(f"Sim thread ID: {threading.current_thread().ident}")  # Different ID!
           # Do NOT initialize anything here

       sim_thread = threading.Thread(target=sim_loop)
       sim_thread.start()
   ```

**Verify Fix**:
- Application launches without crashes
- DPG window appears
- Terminal shows: "Main thread ID: XXXX" and "Sim thread ID: YYYY" (different values)

---

### Green or Noisy Texture

**Symptom**:
- Viewport shows solid green color
- Viewport shows random noise/static
- Viewport shows incorrect colors (inverted, oversaturated)

**Cause**: DPG texture format mismatch or incorrect data range.

**Root Causes & Solutions**:

#### Issue 1: Wrong Data Type

**Check**:
```python
print(f"Frame dtype: {frame_buffer.data.dtype}")  # Must be float32
```

**Fix**:
```python
# Convert to float32
frame = genesis_frame.astype(np.float32)

# If Genesis outputs uint8 [0..255], normalize:
if genesis_frame.dtype == np.uint8:
    frame = genesis_frame.astype(np.float32) / 255.0
```

#### Issue 2: Out-of-Range Values

**Check**:
```python
print(f"Frame range: [{frame.min()}, {frame.max()}]")  # Must be [0.0, 1.0]
```

**Fix**:
```python
# Clamp to [0.0, 1.0]
frame = np.clip(frame, 0.0, 1.0)
```

#### Issue 3: Missing Alpha Channel

**Check**:
```python
print(f"Frame shape: {frame.shape}")  # Must be (H, W, 4) or (H*W*4,)
```

**Fix**:
```python
# Add alpha channel if RGB (3 channels)
if frame.shape[-1] == 3:
    h, w, _ = frame.shape
    alpha = np.ones((h, w, 1), dtype=np.float32)
    frame = np.concatenate([frame, alpha], axis=-1)
```

#### Issue 4: Not Flattened

**Check**:
```python
print(f"Frame ndim: {frame.ndim}")  # Must be 1
```

**Fix**:
```python
# Flatten to 1D
frame_flat = frame.ravel()  # Use ravel() for view (faster than flatten())
```

#### Issue 5: Wrong DPG Format Constant

**Check**:
```python
# When creating texture
dpg.add_raw_texture(..., format=???)
```

**Fix**:
```python
# Must use mvFormat_Float_rgba for float32 RGBA
import dearpygui.dearpygui as dpg

dpg.add_raw_texture(
    width=width,
    height=height,
    default_value=frame_flat,
    format=dpg.mvFormat_Float_rgba,  # CRITICAL!
    tag="viewport_texture"
)
```

**Complete Validation Script**:

```python
import numpy as np

def validate_frame_for_dpg(frame):
    """Validate frame meets DPG requirements."""
    # Check dtype
    if frame.dtype != np.float32:
        raise ValueError(f"Wrong dtype: {frame.dtype}, must be float32")

    # Check ndim
    if frame.ndim != 1:
        raise ValueError(f"Wrong ndim: {frame.ndim}, must be 1 (flattened)")

    # Check length (must be multiple of 4 for RGBA)
    if len(frame) % 4 != 0:
        raise ValueError(f"Length {len(frame)} not multiple of 4 (RGBA)")

    # Check range
    if frame.min() < 0.0 or frame.max() > 1.0:
        raise ValueError(f"Values out of range: [{frame.min()}, {frame.max()}], must be [0.0, 1.0]")

    print("✅ Frame format valid for DPG")
    return True

# Usage
validate_frame_for_dpg(frame_buffer.data)
```

**Verify Fix**:
- Viewport shows correct rendered scene
- Colors are accurate (not green, not noisy)
- Scene is sharp (not blurry)

---

### GUI Stuttering or Low FPS

**Symptom**:
- GUI FPS drops below 60 FPS
- Viewport updates are stuttery/janky
- Mouse input is laggy

**Cause**: Lock contention, slow frame conversion, or GIL blocking.

**Diagnosis**:

1. **Measure lock hold time**:
   ```python
   import time

   class FrameBuffer:
       def write(self, frame):
           start = time.perf_counter()
           with self.lock:
               self.data[:] = frame
           elapsed = (time.perf_counter() - start) * 1000  # ms

           if elapsed > 5.0:
               logging.warning(f"Lock held for {elapsed:.2f}ms (target < 1ms)")
   ```

2. **Profile frame conversion**:
   ```python
   def genesis_frame_to_dpg_texture(genesis_frame):
       start = time.perf_counter()

       # Conversion steps...

       elapsed = (time.perf_counter() - start) * 1000  # ms
       if elapsed > 3.0:
           logging.warning(f"Frame conversion took {elapsed:.2f}ms (target < 3ms)")
   ```

3. **Check GIL release**:
   ```python
   # Run for 10 seconds and check FPS
   # Expected: Sim FPS 500-1000+, GUI FPS ~60
   # If Sim FPS < 100: GIL contention issue
   ```

**Solutions**:

#### Solution 1: Reduce Lock Scope

**Before** (slow):
```python
def sim_loop(frame_buffer):
    with frame_buffer.lock:  # ❌ Lock held too long
        frame = camera.render()  # 5-10ms
        frame_flat = convert(frame)  # 2-3ms
        frame_buffer.data[:] = frame_flat
```

**After** (fast):
```python
def sim_loop(frame_buffer):
    # Heavy work outside lock
    frame = camera.render()  # No lock
    frame_flat = convert(frame)  # No lock

    # Quick copy inside lock
    with frame_buffer.lock:  # ✅ Lock held < 1ms
        frame_buffer.data[:] = frame_flat
```

#### Solution 2: Pre-allocate Buffers

**Before** (slow):
```python
def convert(frame):
    alpha = np.ones((h, w, 1), dtype=np.float32)  # ❌ Allocation every frame
    frame_rgba = np.concatenate([frame, alpha], axis=-1)
    return frame_rgba.ravel()
```

**After** (fast):
```python
# Pre-allocate once
alpha_channel = np.ones((height, width, 1), dtype=np.float32)
output_buffer = np.zeros(height * width * 4, dtype=np.float32)

def convert(frame):
    frame_rgba = np.concatenate([frame, alpha_channel], axis=-1)  # ✅ Reuse alpha
    np.copyto(output_buffer, frame_rgba.ravel())  # ✅ Reuse buffer
    return output_buffer
```

#### Solution 3: Skip Unnecessary Conversions

```python
# If Genesis outputs RGBA float32 natively, skip conversion entirely
frame_flat = genesis_frame.ravel()  # Direct view, no copy
```

**Verify Fix**:
- GUI FPS returns to 60 FPS (stable)
- Lock hold time p95 < 1ms
- Frame conversion < 3ms

---

### Simulation Thread Won't Exit

**Symptom**:
- Close window, but Python process remains running
- Activity Monitor shows zombie thread
- Must force-quit application

**Cause**: Simulation loop not checking shutdown flag.

**Solution**:

1. **Implement shutdown flag**:
   ```python
   import threading

   shutdown_flag = threading.Event()

   def sim_loop(shutdown_flag):
       while not shutdown_flag.is_set():
           # Simulation step...

           # Check flag frequently (every iteration)
           if shutdown_flag.is_set():
               break

       print("Simulation thread exiting cleanly")
   ```

2. **Send shutdown signal on window close**:
   ```python
   import dearpygui.dearpygui as dpg

   def on_close():
       print("Shutting down simulation thread...")
       shutdown_flag.set()  # Signal thread to exit

       # Wait for thread to exit (with timeout)
       sim_thread.join(timeout=2.0)

       if sim_thread.is_alive():
           logging.error("Simulation thread did not exit cleanly!")
       else:
           print("✅ Simulation thread exited")

   dpg.set_exit_callback(on_close)
   ```

3. **Use non-blocking queue operations**:
   ```python
   def sim_loop(command_queue, shutdown_flag):
       while not shutdown_flag.is_set():
           try:
               # Use timeout to check shutdown flag periodically
               cmd = command_queue.get(timeout=0.01)  # 10ms timeout
               process_command(cmd)
           except queue.Empty:
               continue  # No command, check shutdown flag again
   ```

**Verify Fix**:
- Close window: Application exits within 1 second
- Terminal shows: "Simulation thread exiting cleanly" and "✅ Simulation thread exited"
- Activity Monitor: No zombie Python processes

---

### High Memory Usage or Leaks

**Symptom**:
- Memory usage grows continuously over time
- Application uses > 2 GB RAM after 10 minutes
- System runs out of memory and crashes

**Diagnosis**:

1. **Profile with memray** (recommended):
   ```bash
   pip install memray
   memray run src/ui/main.py
   memray flamegraph memray-*.bin
   # Open generated HTML file in browser
   ```

2. **Manual tracking**:
   ```python
   import psutil
   import os

   def log_memory_usage():
       process = psutil.Process(os.getpid())
       mem_mb = process.memory_info().rss / 1024 / 1024
       print(f"Memory usage: {mem_mb:.2f} MB")

   # Call every 10 seconds
   ```

**Common Causes & Solutions**:

#### Cause 1: Frame Buffer Not Reused

**Before** (leak):
```python
def sim_loop():
    while True:
        frame = camera.render()  # New allocation every frame! ❌
```

**After** (fixed):
```python
# Reuse shared buffer
def sim_loop(frame_buffer):
    while True:
        camera.render_to_buffer(frame_buffer.data)  # Reuse existing buffer ✅
```

#### Cause 2: Plot Buffer Unbounded

**Before** (leak):
```python
plot_buffer = []  # No size limit! ❌

def sim_loop():
    plot_buffer.append((time, value))  # Grows forever
```

**After** (fixed):
```python
from collections import deque

plot_buffer = deque(maxlen=10000)  # Bounded ✅

def sim_loop():
    plot_buffer.append((time, value))  # Oldest dropped automatically
```

#### Cause 3: Event Queue Backlog

**Before** (leak):
```python
# Events emitted faster than consumed
event_queue = queue.Queue(maxsize=0)  # Unbounded! ❌
```

**After** (fixed):
```python
# Bounded queue with overflow handling
event_queue = queue.Queue(maxsize=1000)  # Bounded ✅

def emit_event(event):
    try:
        event_queue.put(event, timeout=0.01)
    except queue.Full:
        logging.warning("Event queue full, dropping event")
```

**Verify Fix**:
- Run for 10 minutes: Memory usage remains stable (< 500 MB growth)
- No Python warnings about garbage collection
- memray flamegraph shows no runaway allocations

---

## Performance Profiling

### CPU Profiling with py-spy

**Install**:
```bash
pip install py-spy
```

**Profile application**:
```bash
# Record for 60 seconds
sudo py-spy record -o profile.svg --duration 60 -- python src/ui/main.py

# Open profile.svg in browser to see flamegraph
```

**What to look for**:
- Hot spots in simulation loop (> 10% CPU)
- Lock contention (time spent waiting for locks)
- Unnecessary allocations (numpy array creation in hot path)

---

### GPU Profiling

**macOS Metal** (Xcode Instruments):
1. Open Xcode
2. Xcode → Open Developer Tool → Instruments
3. Select "Metal System Trace" template
4. Target: Python process
5. Record for 30 seconds while running simulation
6. Look for:
   - GPU idle time (should be minimal)
   - Command buffer submission rate (should match simulation FPS)

**Linux/Windows CUDA** (NVIDIA Nsight Systems):
```bash
nsys profile --trace=cuda,nvtx python src/ui/main.py
```

---

### Frame Latency Measurement

```python
import time
import collections

class LatencyTracker:
    def __init__(self, window_size=100):
        self.samples = collections.deque(maxlen=window_size)

    def record(self, latency_ms):
        self.samples.append(latency_ms)

    def get_p95(self):
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[idx]

# Usage in sim loop
latency_tracker = LatencyTracker()

def sim_loop():
    while True:
        start = time.perf_counter()

        # Render frame
        camera.render_to_buffer(frame_buffer.data)

        elapsed_ms = (time.perf_counter() - start) * 1000
        latency_tracker.record(elapsed_ms)

        # Log every 60 frames
        if frame_count % 60 == 0:
            p95 = latency_tracker.get_p95()
            print(f"Frame latency p95: {p95:.2f}ms (target < 16.7ms)")
```

---

## References

### Documentation

- **Genesis Documentation**: https://genesis-world.readthedocs.io/
- **Dear PyGui Documentation**: https://dearpygui.readthedocs.io/
- **Taichi Documentation**: https://docs.taichi-lang.org/
- **tsdownsample**: https://github.com/predict-idlab/tsdownsample

### Internal Specifications

- [Feature Specification](./spec.md) - Full feature requirements
- [Implementation Plan](./plan.md) - Phase-by-phase implementation guide
- [Research Findings](./research.md) - Backend selection, threading patterns
- [Data Model](./data-model.md) - Command/event contracts, buffer specs
- [Command Contracts](./contracts/commands.md) - Detailed command schemas
- [Event Contracts](./contracts/events.md) - Detailed event schemas

### External Resources

- **Python Threading**: https://docs.python.org/3/library/threading.html
- **NumPy Array Interface**: https://numpy.org/doc/stable/user/basics.html
- **Queue Module**: https://docs.python.org/3/library/queue.html
- **Profiling Python**: https://docs.python.org/3/library/profile.html

---

## Getting Help

### Debugging Tips

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Add thread ID to logs**:
   ```python
   import threading
   logging.basicConfig(
       format='[%(asctime)s] [%(levelname)s] [Thread-%(thread)d] %(message)s'
   )
   ```

3. **Validate frame buffer every N frames**:
   ```python
   if frame_count % 60 == 0:
       validate_frame_for_dpg(frame_buffer.data)
   ```

4. **Monitor queue depths**:
   ```python
   if frame_count % 60 == 0:
       cmd_depth = command_queue.qsize()
       evt_depth = event_queue.qsize()
       print(f"Queue depths: Cmd={cmd_depth}, Evt={evt_depth}")
       if cmd_depth > 100 or evt_depth > 100:
           logging.warning("Queue backlog detected!")
   ```

### Common Patterns

**Pattern: Safe Shutdown**
```python
def main():
    shutdown_flag = threading.Event()

    try:
        # Start sim thread
        sim_thread = threading.Thread(target=sim_loop, args=(shutdown_flag,))
        sim_thread.start()

        # Run GUI
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

    finally:
        # Always clean up on exit
        print("Shutting down...")
        shutdown_flag.set()
        sim_thread.join(timeout=2.0)
        dpg.destroy_context()
```

**Pattern: Frame Buffer Access**
```python
# Write (sim thread)
with frame_buffer.lock:
    frame_buffer.data[:] = new_frame

# Read (GUI thread)
with frame_buffer.lock:
    dpg.set_value("viewport_texture", frame_buffer.data)
```

---

**Next Steps**: After completing Phase 1 validation, proceed to [Implementation Plan](./plan.md) for detailed phase-by-phase guidance.
