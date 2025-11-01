# Implementation Plan: Genesis Interactive GUI

**Branch**: `001-genesis-interactive-gui` | **Date**: 2025-11-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-genesis-interactive-gui/spec.md`

**Note**: This plan strictly adheres to the constitutional principles defined in `.specify/memory/constitution.md`.

## Executive Summary

This plan details the implementation of Genesis Interactive GUI, an interactive visualization and control interface for Genesis physics simulations. The system integrates ultra-fast Genesis simulation (1000+ FPS) with a responsive Dear PyGui interface (60 FPS) using the constitutionally-mandated "Init-Main, Run-Threaded" architecture.

**Primary Objective**: Safely resolve dual-loop and dual-context initialization challenges to enable concurrent high-speed simulation and responsive GUI without blocking, context errors, or performance degradation.

**Technical Approach**:
- Threading-based dual loops (main thread: DPG GUI, background thread: Genesis simulation)
- Hybrid inter-thread communication (queues for commands/events, shared memory for frames/plots)
- Constitutional compliance gates at each phase to prevent architectural drift

**Scope**:
- **In Scope**:
  - Playback control (Play/Pause/Step)
  - Real-time 3D viewport rendering (60 FPS)
  - Scene tree and property inspector with Undo/Redo
  - Live signal plotting with downsampling
  - Viewport raycasting and transform gizmo (Phase 5)
  - Full constitutional compliance verification

- **Out of Scope**:
  - asyncio event loop integration
  - Multiprocessing-based concurrency
  - Direct ImGuizmo library integration
  - Frame transfer via queue.Queue
  - Distributed/remote simulation
  - Collaborative multi-user editing
  - Built-in data export/scripting

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Genesis (Taichi backend), Dear PyGui, NumPy, tsdownsample
**Storage**: N/A (in-memory simulation state only)
**Testing**: Manual smoke tests per phase (automated testing deferred to post-MVP)
**Target Platform**: macOS 14+ (primary), Linux (Ubuntu 22.04+), Windows 10+ (secondary)
**Project Type**: Single desktop application
**Performance Goals**: GUI 60 FPS (p95 ≤ 16.7ms), Sim max FPS, lock hold ≤ 1ms p95
**Constraints**: Main-thread-only context init, threading-only concurrency, constitutional compliance
**Scale/Scope**: Up to 1,000 entities, 10 concurrent plots, 10,000 samples/plot

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Checklist

| Constitutional Principle | Plan Compliance | Verification Method |
|-------------------------|-----------------|---------------------|
| **I. Main-Thread Context Init** | ✅ Phase 2 enforces `gs.init()`, `gs.Scene()`, `dpg.create_context()` on main thread | Startup logs + code review |
| **II. Init-Main, Run-Threaded** | ✅ Phase 3 implements main=GUI, background=sim pattern | FPS counters show independence |
| **III. Threading-Only Concurrency** | ✅ No asyncio; `threading` module only | Code audit + dependency check |
| **IV. Data Pathway Segregation** | ✅ Commands/events via queue, plots via deque, frames via shared array+lock | Architecture review + profiling |
| **V. Viewport Pipeline Spec** | ✅ Phase 2 verifies float32 RGBA [0..1] flatten → `add_raw_texture`/`set_value` | Visual inspection + format validation |
| **VI. Optimistic UI + Commit** | ✅ Phase 4 implements preview (no Undo) + release (commit) | Manual Undo stack inspection |
| **VII. Performance Targets** | ✅ 60 FPS GUI, max FPS sim, tsdownsample for plots | Metrics dashboard |
| **VIII. Shutdown Sequence** | ✅ Stop loop → join thread → destroy DPG → exit | Shutdown logging + stress test |

**Gate Status**: ✅ **PASS** - All constitutional principles reflected in plan architecture.

**Violation Procedure**: If any principle must be violated during implementation:
1. Document specific violation with rationale in Complexity Tracking section
2. Assess risk (context errors, performance, maintainability)
3. Propose mitigation or simpler constitutional alternative
4. Request explicit approval before proceeding
5. Add compensating controls if approved

## Project Structure

### Documentation (this feature)

```text
specs/001-genesis-interactive-gui/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data contracts
├── quickstart.md        # Phase 1 developer guide
├── contracts/           # Phase 1 API contracts
│   ├── commands.md      # Command schemas
│   └── events.md        # Event schemas
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT in this command)
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── sim_loop.py          # Simulation thread loop + Genesis integration
│   ├── ipc.py               # Inter-thread communication (queues, buffers, locks)
│   └── commands.py          # Command/Event dataclasses
├── ui/
│   ├── main.py              # DPG main loop + initialization orchestration
│   ├── viewport.py          # Viewport widget + texture management
│   ├── inspector.py         # Property inspector + widget registry
│   ├── scene_tree.py        # Scene hierarchy tree widget
│   ├── plots.py             # Live plotting with downsampling
│   └── gizmo.py             # Transform gizmo (DPG drawlist-based) [Phase 5]
├── infra/
│   ├── bootstrap.py         # Init/shutdown sequencing
│   ├── metrics.py           # FPS counters, lock timing, queue depth
│   └── config.py            # Configuration management
└── __main__.py              # Application entry point

tests/
├── smoke/
│   ├── test_phase1_mock.py     # Phase 1 smoke test
│   ├── test_phase2_texture.py  # Phase 2 texture validation
│   ├── test_phase3_threads.py  # Phase 3 dual-loop validation
│   ├── test_phase4_undo.py     # Phase 4 Undo/Redo validation
│   └── test_phase5_advanced.py # Phase 5 gizmo/plots validation
└── manual/
    └── phase_checklists.md     # Manual validation procedures
```

**Structure Decision**: Single project structure chosen because:
- Desktop application (not web/mobile split)
- All components tightly coupled through constitutional data pathways
- Simpler dependency management for threading-based architecture
- Easier to enforce main-thread initialization constraints

## Architecture Blueprint

### Module Boundaries

**Core Layer** (`src/core/`):
- **sim_loop.py**: Background thread simulation loop
  - Responsibilities: Process command queue, step Genesis scene, render camera, emit events, update frame/plot buffers
  - Dependencies: Genesis, Taichi, NumPy, `ipc.py`, `commands.py`
  - Thread: Background (simulation thread)

- **ipc.py**: Inter-thread communication primitives
  - Responsibilities: Define shared buffers (frame, plot), queues (command, event), locks
  - Exports: `CommandQueue`, `EventQueue`, `PlotBuffer`, `FrameBuffer` classes
  - Thread: Shared between main and background

- **commands.py**: Command and Event dataclasses
  - Responsibilities: Define all command/event types with serialization
  - Examples: `PlayCommand`, `PauseCommand`, `UpdatePropertyCommand`, `EntitySelectedEvent`
  - Thread: Data-only (no thread affinity)

**UI Layer** (`src/ui/`):
- **main.py**: DPG main loop orchestration
  - Responsibilities: Initialize DPG context, create UI layout, run render loop, dispatch events
  - Dependencies: Dear PyGui, `ipc.py`, all UI modules
  - Thread: Main thread only

- **viewport.py**: 3D viewport rendering
  - Responsibilities: Create raw texture, update from frame buffer, handle camera controls
  - API: `create_viewport()`, `update_texture(frame_data)`, `handle_mouse_input()`
  - Thread: Main thread (DPG widgets)

- **inspector.py**: Property editing with widget registry
  - Responsibilities: Display entity properties, generate widgets, emit preview/commit commands
  - Widget Registry: `{float: slider, vec3: input_floatx(3), bool: checkbox, enum: combo}`
  - Thread: Main thread (DPG widgets)

- **scene_tree.py**: Hierarchical entity browser
  - Responsibilities: Display entity tree, handle selection, emit EntitySelectedEvent
  - Thread: Main thread (DPG widgets)

- **plots.py**: Live signal plotting with downsampling
  - Responsibilities: Read plot buffer, downsample via tsdownsample, render line plots
  - Thread: Main thread (DPG widgets)

- **gizmo.py**: Transform gizmo overlay [Phase 5]
  - Responsibilities: Render gizmo via DPG drawlist, handle drag interaction, emit preview/commit
  - Thread: Main thread (DPG drawing)

**Infrastructure Layer** (`src/infra/`):
- **bootstrap.py**: Initialization and shutdown sequencing
  - Responsibilities: Enforce main-thread init order, coordinate startup/shutdown
  - Key Functions: `initialize_all()`, `shutdown_all()`
  - Constitutional Compliance: Enforces Principle I (main-thread context init) and VIII (shutdown sequence)

- **metrics.py**: Performance observability
  - Responsibilities: Measure GUI FPS, sim FPS, lock hold time, queue depths
  - Exports: `MetricsDashboard` class with real-time display
  - Thread: Reads from both threads, displays on main thread

- **config.py**: Configuration management
  - Responsibilities: Load settings (window size, backend selection, buffer sizes)
  - Thread: Read on startup (main thread)

### Sequence Diagrams

#### Initialization Sequence (Phase 2-3)

```
[Main Thread]                    [Background Thread]
     |                                   |
     |-- gs.init(backend=Metal) -------->|
     |-- scene = gs.Scene(...) --------->|
     |-- dpg.create_context() ---------->|
     |-- dpg.setup_dearpygui() --------->|
     |                                   |
     |-- create shared buffers --------->|
     |   (frame_buffer, plot_buffer,     |
     |    command_queue, event_queue)    |
     |                                   |
     |-- thread.start(sim_loop) -------->|
     |                                   |-- while running:
     |                                   |     cmd = command_queue.get()
     |                                   |     process_command(cmd)
     |                                   |     scene.step()
     |                                   |     frame = camera.render()
     |                                   |     with lock: frame_buffer[:] = frame
     |                                   |     emit events to event_queue
     |                                   |
     |-- while dpg.is_dearpygui_running(): |
     |     process event_queue ----------|
     |     with lock: read frame_buffer --|
     |     dpg.set_value(texture, frame)  |
     |     dpg.render_dearpygui_frame()   |
     |                                   |
```

#### Command Flow (GUI → Sim)

```
[User Action]      [UI Layer]           [IPC]              [Sim Loop]
     |                  |                  |                    |
Click Play ---------> PlayCommand ------> command_queue -----> get_nowait()
     |                  |                  |                    |
     |                  |                  |                    process_play()
     |                  |                  |                    set running=True
     |                  |                  |                    |
Drag Slider --------> PreviewProperty --> command_queue -----> apply_preview()
(dragging...)          (continuous)        (no Undo)           (temp state)
     |                  |                  |                    |
Release Slider -----> UpdateProperty ---> command_queue -----> apply_update()
     |                  (with old/new)     (add to Undo)        push_undo_stack()
```

#### Event Flow (Sim → GUI)

```
[Sim Loop]         [IPC]              [UI Layer]         [User Sees]
     |                  |                    |                 |
Collision --------> CollisionEvent ---> event_queue -------> process_events()
detected             (aId, bId)                                log to console
     |                  |                    |                 |
Entity ------------> EntitySelected ---> event_queue -------> update_inspector()
selected              (entityId)                               show properties
     |                  |                    |                 |
```

#### Frame Update Flow (Sim → GUI)

```
[Sim Thread]                 [Shared Memory]           [Main Thread]
     |                              |                        |
camera.render() -------------> with lock: ------------> (blocked)
     |                           frame_buffer[:] = data      |
     |                              |                        |
release lock ----------------------|-----------------------> with lock:
     |                              |                      copy = frame_buffer.copy()
     |                              |                        |
     |                              |                      dpg.set_value(tex, copy)
     |                              |                        |
     |                              |                      dpg.render_dearpygui_frame()
```

### Shutdown Sequence

```
[User Closes Window]
     |
     V
[Main Thread]
     |-- Set shutdown flag (atomic bool)
     |
     |-- command_queue.put(ShutdownCommand)  # Signal sim thread
     |
     |-- thread.join(timeout=5.0)  # Wait for sim thread
     |     |
     |     |-- [Background Thread]
     |     |     |-- Receive ShutdownCommand
     |     |     |-- Exit sim loop
     |     |     |-- Return from thread function
     |     |
     |-- if timeout: force terminate (warning logged)
     |
     |-- dpg.stop_dearpygui()  # Exit render loop
     |
     |-- dpg.destroy_context()  # Release GPU resources
     |
     V
[Process Exit]
```

**Constitutional Compliance**: Follows Principle VIII (Shutdown Sequence Safety)

## Phased Delivery Plan

### Phase 0 – Prerequisites & Research

**Objective**: Resolve technical unknowns and establish development environment.

**Deliverables**:
- `research.md` documenting:
  - Backend selection matrix (Metal/CUDA/Vulkan) per OS
  - DPG texture format constraints and performance characteristics
  - Downsampling library comparison (tsdownsample vs pure NumPy)
  - Known threading pitfalls with Taichi/DPG and mitigation strategies
- Development environment setup validated on target platform (macOS 14+)

**Assumptions**:
- Genesis/Taichi latest stable supports Metal backend on macOS
- DPG latest stable compatible with Python 3.11+
- tsdownsample available via pip

**Risks & Mitigations**:
- **Risk**: Library version incompatibilities
  - **Mitigation**: Document exact working versions in `requirements.txt`
- **Risk**: Metal backend unavailable/unstable on target Mac
  - **Mitigation**: Fall back to Vulkan; document in research.md

**Acceptance Criteria**:
- [ ] All dependencies install cleanly on macOS 14+
- [ ] Backend selection logic implemented and tested
- [ ] Research.md complete with decision rationale

**Parallelization**: [P] All research tasks can proceed in parallel.

---

### Phase 1 – Mock Thread + GUI Wiring

**Objective**: Validate data pathway architecture and GUI responsiveness with mock simulation (no Genesis integration yet).

**System Changes**:

**New Modules**:
- `src/core/ipc.py`: CommandQueue, EventQueue, PlotBuffer, FrameBuffer classes
- `src/core/commands.py`: Command/Event dataclass definitions
- `src/infra/bootstrap.py`: Initialization skeleton (DPG only, no Genesis)
- `src/infra/metrics.py`: FPS counters for GUI and mock sim
- `src/ui/main.py`: DPG main loop with basic window
- `src/ui/viewport.py`: Viewport widget with raw texture (mock random pixels)
- `src/ui/scene_tree.py`: Stub scene tree widget
- `src/ui/inspector.py`: Stub inspector widget
- `tests/smoke/test_phase1_mock.py`: Automated smoke test

**Mock Simulation Thread**:
```python
# Pseudocode
def mock_sim_loop(command_queue, event_queue, frame_buffer, plot_buffer, lock):
    while running:
        # Process commands
        cmd = command_queue.get(timeout=0.01)
        if cmd.type == "Play": running_sim = True

        # Generate mock data at 1000 Hz
        if running_sim:
            # Random frame (640x480 RGBA float32 [0..1] flattened)
            frame = np.random.rand(640 * 480 * 4).astype(np.float32)
            with lock:
                frame_buffer[:] = frame

            # Random plot samples
            plot_buffer.append((time.time(), np.random.randn()))

        time.sleep(0.001)  # ~1000 Hz
```

**GUI Thread**:
```python
# Pseudocode
def gui_loop():
    dpg.create_context()
    create_viewport(640, 480)  # Raw texture widget
    dpg.setup_dearpygui()

    while dpg.is_dearpygui_running():
        # Read mock frame
        with frame_lock:
            frame_copy = frame_buffer.copy()
        dpg.set_value("viewport_texture", frame_copy)

        # Process events
        while not event_queue.empty():
            event = event_queue.get()
            handle_event(event)

        # Measure FPS
        metrics.record_gui_frame()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()
```

**Deliverables**:
- `data-model.md`: Command/Event contracts, buffer specifications
- `contracts/commands.md`: Detailed command schemas
- `contracts/events.md`: Detailed event schemas
- `quickstart.md`: Setup instructions + Phase 1 validation checklist

**Assumptions**:
- DPG `add_raw_texture` works with float32 RGBA format
- 1000 Hz mock data generation achievable on target hardware
- `threading.Lock` sufficient for frame buffer synchronization

**Risks & Mitigations**:
- **Risk**: GUI stutters despite mock data simplicity
  - **Mitigation**: Profile lock contention; reduce lock scope
- **Risk**: Queue.Queue overhead too high
  - **Mitigation**: Benchmark and document; consider lock-free alternatives if needed

**Checkpoints & DoD**:
- [ ] Mock sim thread writes to frame/plot buffers at 1000 Hz
- [ ] GUI reads buffers and renders at stable 60 FPS
- [ ] No deadlocks during 5-minute stress test
- [ ] Metrics dashboard shows independent FPS counters
- [ ] Queue depths remain < 100 items under steady state

**KPI Mapping**:
- GUI FPS: Target 60, measured via `metrics.py`
- Mock Sim FPS: Target 1000, measured via counter
- Lock hold time: Target < 1ms, measured via timing wrapper

**Parallelization Opportunities**:
- [P] IPC module (`ipc.py`) can be developed independently
- [P] Commands dataclasses (`commands.py`) can be defined in parallel
- [P] UI widgets (viewport, scene_tree, inspector stubs) can be built concurrently
- [P] Metrics infrastructure (`metrics.py`) independent of core logic

**Constitution Compliance**:
- ✅ Principle II verified: Main thread runs GUI, background runs mock sim
- ✅ Principle IV verified: Commands via queue, frames via shared array+lock
- ✅ Principle V preparation: Raw texture pipeline scaffolded

---

### Phase 2 – Single-Thread Integration Verification

**Objective**: Prove Genesis-to-DPG rendering path correctness in controlled single-threaded environment before introducing threading complexity.

**System Changes**:

**Modified Modules**:
- `src/infra/bootstrap.py`: Add Genesis initialization (`gs.init()`, `gs.Scene()`)
- `src/ui/viewport.py`: Replace mock frame with Genesis camera output
- `tests/smoke/test_phase2_texture.py`: Texture format validation

**Single-Thread Test Harness**:
```python
# Pseudocode (main thread only, no background thread)
def phase2_validation():
    # Constitutional init sequence
    gs.init(backend="Metal")  # macOS
    scene = gs.Scene(...)
    scene.add_entity(gs.RigidBody(...))  # Simple cube
    camera = scene.add_camera(...)

    dpg.create_context()
    dpg.setup_dearpygui()

    # Render single frame
    frame = camera.render()  # Genesis output

    # Validate format
    assert frame.dtype == np.float32, "Must be float32"
    assert frame.shape[-1] == 4, "Must be RGBA"
    assert frame.min() >= 0.0 and frame.max() <= 1.0, "Must be [0..1]"

    # Flatten and display
    frame_flat = frame.ravel()
    dpg.set_value("viewport_texture", frame_flat)

    # Visual confirmation loop
    for _ in range(60):  # 1 second @ 60 FPS
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
```

**Deliverables**:
- Genesis scene setup scripts (simple test scene)
- Texture format validation utility
- Visual inspection checklist

**Assumptions**:
- Genesis camera.render() returns NumPy array
- Output format is either already float32 RGBA [0..1] or easily convertible
- Single-threaded execution avoids context errors

**Risks & Mitigations**:
- **Risk**: Genesis output format incompatible (e.g., uint8, BGR, different range)
  - **Mitigation**: Add conversion layer; document in data-model.md
- **Risk**: Context initialization fails due to missing GPU drivers
  - **Mitigation**: Add graceful error handling with clear message (per Edge Cases)

**Checkpoints & DoD**:
- [ ] Genesis + DPG initialize without errors on main thread
- [ ] `camera.render()` produces frame matching spec (float32 RGBA [0..1] flatten)
- [ ] DPG viewport displays Genesis-rendered scene correctly
- [ ] No visual artifacts (green screen, noise, incorrect geometry)
- [ ] Startup logs confirm main-thread initialization order

**KPI Mapping**:
- Texture format compliance: 100% (automated validation)
- Visual correctness: Manual inspection passes

**Parallelization**: None (single-threaded validation phase)

**Constitution Compliance**:
- ✅ Principle I enforced: All contexts on main thread
- ✅ Principle V verified: Texture format matches DPG spec exactly

**Phase 2 → Phase 3 Gate**:
**CRITICAL**: Phase 3 threading MUST NOT begin until Phase 2 visual rendering is confirmed working. This gate prevents debugging threading issues mixed with rendering format issues.

---

### Phase 3 – Async Loop Separation (Dual-Loop)

**Objective**: Implement full "Init-Main, Run-Threaded" architecture with independent FPS and no context errors.

**System Changes**:

**Modified Modules**:
- `src/core/sim_loop.py`: Replace mock loop with real Genesis simulation
  ```python
  # Pseudocode
  def sim_loop(scene, camera, command_queue, event_queue, frame_buffer, plot_buffer, lock, shutdown_flag):
      while not shutdown_flag.is_set():
          # Process commands
          try:
              cmd = command_queue.get(timeout=0.01)
              if cmd.type == "Play": running = True
              elif cmd.type == "Pause": running = False
              elif cmd.type == "Step": scene.step(); render_frame()
          except queue.Empty:
              pass

          # Sim loop
          if running:
              scene.step()

              # Render frame
              frame = camera.render()
              frame_flat = frame.ravel()
              with lock:
                  frame_buffer[:] = frame_flat

              # Emit plot samples
              plot_buffer.append((time.time(), scene.get_metric("energy")))

          # Record FPS
          sim_fps_counter.tick()
  ```

- `src/infra/bootstrap.py`: Add thread management
  ```python
  # Pseudocode
  def initialize_all():
      # Main thread: Init all contexts
      gs.init(backend=select_backend())
      scene = create_scene()
      camera = scene.add_camera(...)

      dpg.create_context()
      dpg.setup_dearpygui()

      # Create shared resources
      command_queue = queue.Queue()
      event_queue = queue.Queue()
      frame_buffer = np.zeros(H * W * 4, dtype=np.float32)
      plot_buffer = deque(maxlen=10000)
      lock = threading.Lock()
      shutdown_flag = threading.Event()

      # Start background thread
      sim_thread = threading.Thread(
          target=sim_loop,
          args=(scene, camera, command_queue, event_queue,
                frame_buffer, plot_buffer, lock, shutdown_flag)
      )
      sim_thread.start()

      return sim_thread, shutdown_flag, ...
  ```

**Deliverables**:
- Full dual-loop implementation
- 10-minute stability test script
- FPS measurement dashboard

**Assumptions**:
- Genesis simulation is GIL-releasing (allows true parallelism)
- No new GPU contexts created in background thread (Genesis reuses main-thread context)
- Lock contention remains acceptable (< 1ms p95)

**Risks & Mitigations**:
- **Risk**: Context errors due to background thread GPU access
  - **Mitigation**: Verify Genesis/Taichi doesn't create new contexts; add defensive checks
- **Risk**: Frame buffer lock contention degrades sim FPS
  - **Mitigation**: Minimize lock scope; consider double buffering if needed
- **Risk**: Memory leaks during long runs
  - **Mitigation**: Run memory profiler during 10-minute test

**Checkpoints & DoD**:
- [ ] Init-Main, Run-Threaded pattern fully implemented
- [ ] Sim FPS >> 60 FPS (e.g., 500-1000 FPS on test scene)
- [ ] GUI FPS stable at 60 FPS regardless of sim speed
- [ ] No context errors during 10-minute continuous run
- [ ] No crashes, deadlocks, or memory leaks
- [ ] Shutdown sequence completes cleanly within 5 seconds

**KPI Mapping**:
- GUI FPS: p95 ≤ 16.7ms (60 FPS) → measure via `metrics.py`
- Sim FPS: > 100 FPS → measure via counter
- Lock hold time: p95 ≤ 1ms → measure via timing wrapper
- Memory growth: < 10MB over 10 minutes → measure via `psutil`

**Parallelization**: None (core threading migration is sequential)

**Constitution Compliance**:
- ✅ Principle II enforced: Main=GUI, Background=Sim
- ✅ Principle III enforced: Threading only, no asyncio
- ✅ Principle VII verified: Independent FPS achieved

**Phase 3 → Phase 4 Gate**:
**CRITICAL**: Bi-directional communication (Phase 4) MUST NOT begin until Phase 3 stability is proven. Debugging command/event bugs mixed with threading instability is extremely difficult.

---

### Phase 4 – Bidirectional Binding & Undo

**Objective**: Implement command/event pathways and Optimistic UI + Commit on Release pattern for interactive property editing.

**System Changes**:

**New Modules**:
- `src/ui/inspector.py`: Full implementation with widget registry
  ```python
  # Pseudocode
  class Inspector:
      def __init__(self, command_queue):
          self.command_queue = command_queue
          self.widget_registry = {
              float: self.create_slider,
              Vec3: self.create_vec3_input,
              bool: self.create_checkbox,
              Enum: self.create_combo
          }

      def create_slider(self, property_name, value, min_val, max_val):
          dpg.add_slider_float(
              label=property_name,
              default_value=value,
              min_value=min_val,
              max_value=max_val,
              callback=lambda s, v: self.on_preview(property_name, v),
              callback_on_release=lambda s, v: self.on_commit(property_name, v)
          )

      def on_preview(self, prop_name, new_value):
          # Preview only (no Undo)
          cmd = PreviewPropertyCommand(
              entity_id=self.selected_entity,
              property_path=prop_name,
              value=new_value
          )
          self.command_queue.put(cmd)

      def on_commit(self, prop_name, new_value):
          # Commit to Undo stack
          cmd = UpdatePropertyCommand(
              entity_id=self.selected_entity,
              property_path=prop_name,
              old_value=self.original_value,
              new_value=new_value
          )
          self.command_queue.put(cmd)
  ```

- `src/core/undo_stack.py`: Undo/Redo stack management
  ```python
  # Pseudocode
  class UndoStack:
      def __init__(self):
          self.undo_stack = []
          self.redo_stack = []

      def push(self, command):
          self.undo_stack.append(command)
          self.redo_stack.clear()  # Clear redo on new action

      def undo(self):
          if self.undo_stack:
              cmd = self.undo_stack.pop()
              cmd.revert()  # Apply old_value
              self.redo_stack.append(cmd)

      def redo(self):
          if self.redo_stack:
              cmd = self.redo_stack.pop()
              cmd.apply()  # Apply new_value
              self.undo_stack.append(cmd)
  ```

**Modified Modules**:
- `src/ui/scene_tree.py`: Full implementation with selection handling
- `src/core/sim_loop.py`: Add command processing for UpdateProperty, PreviewProperty, Undo, Redo

**Deliverables**:
- Full inspector with widget registry
- Undo/Redo implementation
- Scene tree selection integration
- Manual Undo stack validation checklist

**Assumptions**:
- DPG `callback` fires during drag, `callback_on_release` fires on mouse up
- Preview commands process fast enough (< 50ms) for smooth visual feedback
- Undo stack size remains reasonable (< 1000 entries under normal use)

**Risks & Mitigations**:
- **Risk**: Preview commands saturate queue during rapid dragging
  - **Mitigation**: Add debouncing/throttling; queue depth monitoring
- **Risk**: Undo stack memory growth with complex edits
  - **Mitigation**: Cap stack size at 100 entries; document in data-model.md

**Checkpoints & DoD**:
- [ ] Selecting entity in scene tree populates inspector
- [ ] Dragging slider shows real-time preview in viewport
- [ ] Releasing slider commits single Undo entry (not dozens)
- [ ] Undo reverts to pre-drag value (not last preview)
- [ ] Redo restores post-drag value
- [ ] Undo stack contains only committed UpdatePropertyCommands
- [ ] Command queue depth remains < 100 during rapid dragging

**KPI Mapping**:
- Inspector population latency: < 100ms → manual timing
- Preview update latency: < 50ms → metrics dashboard
- Queue depth under stress: < 100 items → metrics dashboard

**Parallelization Opportunities**:
- [P] Inspector widget creation can be prototyped separately
- [P] Undo stack logic can be unit tested independently
- [P] Scene tree widget can be developed in parallel with inspector

**Constitution Compliance**:
- ✅ Principle VI enforced: Preview (no Undo) during drag, Commit (Undo) on release

**Phase 4 → Phase 5 Gate**:
Phase 5 is optional enhancement. Can stop here and deliver MVP (Phases 1-4 = fully functional interactive GUI).

---

### Phase 5 – Advanced Features (Gizmos & Plots)

**Objective**: Implement viewport raycasting, DPG drawlist-based transform gizmo, and high-performance live plotting with downsampling.

**System Changes**:

**New Modules**:
- `src/ui/gizmo.py`: Transform gizmo implementation
  ```python
  # Pseudocode
  class TransformGizmo:
      def render(self, entity_position, viewport_drawlist):
          # Project 3D position to 2D screen space
          screen_pos = project_to_screen(entity_position)

          # Draw axes using DPG drawlist
          dpg.draw_line(drawlist, screen_pos, screen_pos + x_axis, color=(1,0,0,1))
          dpg.draw_line(drawlist, screen_pos, screen_pos + y_axis, color=(0,1,0,1))
          dpg.draw_line(drawlist, screen_pos, screen_pos + z_axis, color=(0,0,1,1))

          # Handle mouse drag
          if dragging_x_axis:
              delta = mouse_pos - last_mouse_pos
              self.emit_preview(entity, "position.x", delta)
  ```

**Modified Modules**:
- `src/ui/viewport.py`: Add raycasting for entity selection
  ```python
  # Pseudocode
  def on_viewport_click(mouse_x, mouse_y):
      # Convert screen coords to world ray
      ray = camera.screen_to_ray(mouse_x, mouse_y)

      # Raycast against scene
      cmd = RayCastCommand(ray_origin=ray.origin, ray_direction=ray.direction)
      command_queue.put(cmd)
  ```

- `src/ui/plots.py`: Add tsdownsample integration
  ```python
  # Pseudocode
  def update_plot(plot_buffer, plot_widget):
      # Read all samples
      samples = list(plot_buffer)  # deque -> list

      # Downsample to 1000 points
      if len(samples) > 1000:
          t = np.array([s[0] for s in samples])
          v = np.array([s[1] for s in samples])
          downsampled = tsdownsample.lttb(t, v, n_out=1000)
          t_down, v_down = downsampled[:, 0], downsampled[:, 1]
      else:
          t_down, v_down = t, v

      # Update DPG plot
      dpg.set_value(plot_widget, [t_down.tolist(), v_down.tolist()])
  ```

**Deliverables**:
- Working transform gizmo (translate only, rotation deferred)
- Viewport raycasting entity selection
- Live plots with LTTB downsampling
- Performance validation at 1kHz data rate

**Assumptions**:
- DPG drawlist API sufficient for gizmo rendering (no ImGuizmo needed)
- Raycasting performance acceptable (< 10ms per click)
- tsdownsample LTTB scales to 10k samples without lag

**Risks & Mitigations**:
- **Risk**: Gizmo rendering too slow (drawlist overhead)
  - **Mitigation**: Profile and optimize; consider caching geometry
- **Risk**: Plot downsampling still causes GUI stutter
  - **Mitigation**: Run downsampling in background thread; update plot on main thread

**Checkpoints & DoD**:
- [ ] Clicking viewport entity selects it (raycast works)
- [ ] Gizmo appears on selected entity (drawlist rendering)
- [ ] Dragging gizmo axis moves entity with preview feedback
- [ ] Gizmo release commits single Undo entry
- [ ] Plots display 1kHz data smoothly at 60 FPS
- [ ] Visual inspection confirms downsampling preserves trends

**KPI Mapping**:
- Raycast latency: < 10ms → manual timing
- Gizmo render overhead: < 1ms → profiling
- Plot update with 10k samples: < 16ms → metrics dashboard

**Parallelization Opportunities**:
- [P] Gizmo rendering can be prototyped independently
- [P] Raycasting logic can be unit tested separately
- [P] Plot downsampling can be benchmarked in isolation

**Constitution Compliance**:
- ✅ Principle VII verified: Plots use tsdownsample (high-performance downsampling)
- ✅ No ImGuizmo (prohibited); DPG drawlist used instead

---

## KPIs & Observability

### Performance Metrics

| Metric | Target | Measurement Method | Display |
|--------|--------|-------------------|---------|
| **GUI Frame Time (p95)** | ≤ 16.7ms | `time.perf_counter()` per frame | Metrics dashboard |
| **Sim FPS** | > 100 FPS | Counter in sim loop | Metrics dashboard |
| **Frame Buffer Lock Hold Time (p95)** | ≤ 1ms | Timing wrapper around lock | Metrics dashboard |
| **Command Queue Depth** | < 100 items | `queue.qsize()` | Metrics dashboard |
| **Event Queue Depth** | < 100 items | `queue.qsize()` | Metrics dashboard |
| **Plot Buffer Utilization** | < 100% (no overflow) | `len(deque)` / `maxlen` | Metrics dashboard |
| **Memory Growth** | < 10MB/10min | `psutil.Process().memory_info()` | Background monitor |

### Measurement Plan

**FPS Sampling**:
```python
# Pseudocode
class FPSCounter:
    def __init__(self):
        self.frame_times = deque(maxlen=100)

    def tick(self):
        now = time.perf_counter()
        if self.last_tick:
            self.frame_times.append(now - self.last_tick)
        self.last_tick = now

    def get_fps(self):
        if not self.frame_times:
            return 0
        return 1.0 / np.mean(self.frame_times)

    def get_p95(self):
        return np.percentile(self.frame_times, 95) * 1000  # ms
```

**Lock Timing**:
```python
# Pseudocode
class TimedLock:
    def __init__(self, lock):
        self.lock = lock
        self.hold_times = deque(maxlen=1000)

    def __enter__(self):
        self.acquire_time = time.perf_counter()
        self.lock.acquire()
        return self

    def __exit__(self, *args):
        hold_time = time.perf_counter() - self.acquire_time
        self.hold_times.append(hold_time)
        self.lock.release()

    def get_p95_ms(self):
        return np.percentile(self.hold_times, 95) * 1000
```

**Queue Depth Monitoring**:
```python
# Pseudocode
def monitor_queues():
    while running:
        cmd_depth = command_queue.qsize()
        evt_depth = event_queue.qsize()

        if cmd_depth > 1000 or evt_depth > 1000:
            logging.warning(f"Queue depth high: cmd={cmd_depth}, evt={evt_depth}")

        time.sleep(1.0)  # Check every second
```

### Metrics Dashboard (DPG Window)

```python
# Pseudocode
with dpg.window(label="Metrics", pos=(10, 10)):
    dpg.add_text("GUI FPS:", tag="gui_fps_label")
    dpg.add_text("Sim FPS:", tag="sim_fps_label")
    dpg.add_text("Frame Time p95:", tag="frame_p95_label")
    dpg.add_text("Lock Hold p95:", tag="lock_p95_label")
    dpg.add_text("Cmd Queue:", tag="cmd_queue_label")
    dpg.add_text("Evt Queue:", tag="evt_queue_label")

def update_metrics_dashboard():
    dpg.set_value("gui_fps_label", f"GUI FPS: {gui_fps.get_fps():.1f}")
    dpg.set_value("sim_fps_label", f"Sim FPS: {sim_fps.get_fps():.1f}")
    dpg.set_value("frame_p95_label", f"Frame p95: {gui_fps.get_p95():.2f}ms")
    dpg.set_value("lock_p95_label", f"Lock p95: {frame_lock.get_p95_ms():.2f}ms")
    dpg.set_value("cmd_queue_label", f"Cmd Queue: {command_queue.qsize()}")
    dpg.set_value("evt_queue_label", f"Evt Queue: {event_queue.qsize()}")
```

## Out-of-Scope & Anti-Patterns

### Explicitly Out of Scope

| Item | Reason | Future Consideration |
|------|--------|----------------------|
| **asyncio event loop** | Constitutional prohibition; conflicts with DPG/Taichi | Never (architectural constraint) |
| **Multiprocessing** | Constitutional prohibition; complex IPC, context issues | Post-MVP if distributed sim needed |
| **ImGuizmo integration** | Constitutional prohibition; DPG drawlist sufficient | Never (not needed) |
| **Frame transfer via queue** | Constitutional prohibition; pickle overhead unacceptable | Never (shared memory is correct solution) |
| **Automated testing** | Resource constraint; manual smoke tests sufficient for MVP | Post-MVP via pytest + mocking |
| **Data export/logging** | Not in spec; users handle externally | Post-MVP plugin system |
| **Scripting API** | Not in spec; adds complexity | Post-MVP if user demand exists |
| **Multi-user collaboration** | Not in spec; requires server architecture | Out of scope indefinitely |

### Anti-Patterns to Avoid

**Threading Anti-Patterns**:
- ❌ Creating Taichi/Genesis contexts in background thread → crashes
- ❌ Calling DPG functions from background thread → undefined behavior
- ❌ Sharing mutable state without locks → race conditions
- ✅ Correct: All contexts on main thread, explicit locks for shared data

**Performance Anti-Patterns**:
- ❌ Copying frame buffer every frame without lock → tearing/corruption
- ❌ Transferring large arrays via queue → pickle overhead kills FPS
- ❌ Rendering 10k plot points without downsampling → GUI stutter
- ✅ Correct: Shared memory + lock for frames, downsampling for plots

**Undo/Redo Anti-Patterns**:
- ❌ Adding preview updates to Undo stack → stack pollution
- ❌ Storing entire scene state per Undo entry → memory explosion
- ❌ Not clearing Redo stack on new action → broken Redo chain
- ✅ Correct: Only commit on release, store deltas, clear Redo on new action

**Shutdown Anti-Patterns**:
- ❌ Destroying DPG context before stopping render loop → crash
- ❌ Not joining simulation thread → process hangs
- ❌ No timeout on thread join → indefinite hang
- ✅ Correct: Signal → join (timeout) → destroy DPG → exit

## Complexity Tracking

**No constitutional violations planned.** All design decisions comply with constitutional principles.

If violations become necessary during implementation:
1. Document in this section with justification
2. Assess risk (stability, performance, maintainability)
3. Propose mitigation or simpler constitutional alternative
4. Obtain explicit approval before proceeding

## Next Steps

1. **Immediate**: Run `/speckit.tasks` to generate Phase 1 task breakdown
2. **Phase 0**: Complete research.md (backend selection, library investigation)
3. **Phase 1**: Implement mock threading + GUI wiring
4. **Phase 2 Gate**: Verify Genesis→DPG texture path before Phase 3
5. **Phase 3 Gate**: Verify dual-loop stability before Phase 4
6. **Phase 4 Gate**: Verify Undo/Redo correctness before Phase 5
7. **Phase 5**: Optional advanced features (can stop at Phase 4 for MVP)

**Estimated Timeline** (single developer, part-time):
- Phase 0: 1 week (research + setup)
- Phase 1: 2 weeks (mock threading + GUI)
- Phase 2: 1 week (Genesis integration)
- Phase 3: 2 weeks (dual-loop migration)
- Phase 4: 2 weeks (Undo/Redo)
- Phase 5: 2 weeks (gizmos + plots)
- **Total**: ~10 weeks to MVP (Phase 4), 12 weeks to full feature set

**Risk Buffer**: Add 20% contingency for unexpected issues (final estimate: 12-14 weeks).
