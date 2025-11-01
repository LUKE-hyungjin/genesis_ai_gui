# Feature Specification: Genesis Interactive GUI

**Feature Branch**: `001-genesis-interactive-gui`
**Created**: 2025-11-01
**Status**: Draft
**Input**: Create a full product specification for "Genesis Interactive GUI" - an interactive GUI for Genesis simulation integrating high-speed physics with 60FPS Dear PyGui interface using Init-Main Run-Threaded architecture

## Problem Statement

Robotics and physics simulation researchers and engineers need to run ultra-fast Genesis simulations (CPU/GPU-bound, GIL-releasing) while simultaneously interacting with a responsive 60 FPS graphical interface. Currently, integrating high-speed physics simulations with interactive GUIs presents critical technical challenges:

- **Dual-loop coordination**: Simulation loops and GUI render loops compete for resources and can block each other
- **Context initialization conflicts**: Graphics APIs (CUDA, Vulkan, OpenGL, Metal) and GUI frameworks require careful initialization sequencing to prevent crashes
- **Performance bottlenecks**: Naive integration causes either simulation slowdown or GUI stuttering
- **Data synchronization overhead**: Transferring large frame buffers between threads can consume significant CPU cycles

Without a safe, performant integration architecture, users must choose between running headless simulations with post-hoc visualization OR interactive GUIs with severely degraded simulation performance.

## User Scenarios & Testing

### User Story 1 - Simulation Playback Control (Priority: P1)

As a **simulation engineer**, I need to start, pause, and step through simulations so that I can observe system behavior at critical moments and debug physics interactions.

**Why this priority**: Core functionality required for any interactive simulation - without playback control, users cannot effectively observe or analyze simulation behavior. This is the foundation upon which all other features depend.

**Independent Test**: Can be fully tested by launching the application, clicking Play/Pause/Step buttons, and verifying simulation state changes correctly. Delivers immediate value by enabling basic simulation observation.

**Acceptance Scenarios**:

1. **Given** simulation is paused, **When** user clicks Play button, **Then** simulation advances continuously and viewport updates at 60 FPS
2. **Given** simulation is running, **When** user clicks Pause button, **Then** simulation freezes at current state and viewport shows last rendered frame
3. **Given** simulation is paused, **When** user clicks Step button, **Then** simulation advances exactly one physics timestep and viewport updates to show new state
4. **Given** simulation is running at 500 FPS, **When** user interacts with GUI controls, **Then** GUI remains responsive at 60 FPS without stuttering

---

### User Story 2 - Real-time 3D Viewport (Priority: P1)

As a **graphics engineer**, I need to see a continuously updating 3D viewport showing the simulation state so that I can visually verify physics accuracy and scene composition.

**Why this priority**: Visual feedback is essential for understanding simulation behavior - numerical data alone is insufficient for spatial reasoning. This is a critical MVP component alongside playback control.

**Independent Test**: Can be tested by running a simulation with moving objects and verifying the viewport displays smooth 60 FPS updates while simulation runs at maximum speed independently. Delivers value by providing real-time visual feedback.

**Acceptance Scenarios**:

1. **Given** simulation contains moving rigid bodies, **When** simulation runs, **Then** viewport displays bodies moving smoothly at 60 FPS regardless of simulation speed
2. **Given** simulation FPS is 1000, **When** viewport renders, **Then** viewport maintains 60 FPS without dropping frames
3. **Given** viewport is 1920x1080 resolution, **When** rendering occurs, **Then** frame time p95 remains ≤ 16.7ms
4. **Given** simulation is paused, **When** user rotates camera, **Then** viewport updates immediately showing new view angle

---

### User Story 3 - Entity Selection and Property Editing (Priority: P2)

As a **controls engineer**, I need to select entities from a scene tree, view their properties in an inspector panel, and modify values with immediate visual feedback so that I can tune parameters and observe effects in real-time.

**Why this priority**: Interactive parameter tuning is a key differentiator for an interactive GUI versus batch simulation. Enables rapid experimentation and iteration.

**Independent Test**: Can be tested by selecting an entity (e.g., a cube), dragging a slider to change its position, observing the cube move in the viewport during drag, and verifying only one Undo entry is created on release. Delivers value through interactive parameter exploration.

**Acceptance Scenarios**:

1. **Given** scene tree displays entities, **When** user clicks on an entity, **Then** inspector panel populates with entity's editable properties
2. **Given** user drags a position slider, **When** drag is in progress, **Then** viewport shows entity moving in real-time (preview mode, no Undo entry)
3. **Given** user releases slider after dragging, **When** mouse button is released, **Then** single UpdatePropertyCommand is committed to Undo stack
4. **Given** user edits property value, **When** user clicks Undo, **Then** property reverts to value before the committed change (not intermediate drag values)
5. **Given** inspector displays float property, **When** inspector renders, **Then** appropriate widget appears (slider with min/max for bounded floats, input box otherwise)

---

### User Story 4 - Live Signal Plotting (Priority: P2)

As a **simulation engineer**, I need to see live plots of selected simulation signals (forces, velocities, energies) so that I can monitor system dynamics and detect anomalies in real-time.

**Why this priority**: Quantitative monitoring complements visual observation. Essential for analyzing dynamic behavior and debugging control systems. Lower priority than basic playback and viewport since numerical analysis can be done post-hoc.

**Independent Test**: Can be tested by selecting a signal to plot (e.g., robot joint velocity), running simulation at 1000+ FPS, and verifying plot updates smoothly at 60 FPS without GUI stuttering. Delivers value through real-time quantitative analysis.

**Acceptance Scenarios**:

1. **Given** user selects a signal to plot, **When** simulation runs, **Then** plot displays signal values over time updating smoothly
2. **Given** simulation generates 1000 samples per second, **When** plot updates at 60 FPS, **Then** data is downsampled intelligently (LTTB/MinMax) preserving trends
3. **Given** plot contains 10,000 data points, **When** plot renders, **Then** GUI maintains 60 FPS without stuttering
4. **Given** plot buffer reaches maximum length, **When** new samples arrive, **Then** oldest samples are removed (circular buffer behavior)

---

### User Story 5 - Viewport Entity Selection via Raycasting (Priority: P3)

As a **simulation engineer**, I need to click on entities directly in the 3D viewport to select them so that I can quickly inspect and modify objects without searching the scene tree.

**Why this priority**: Improves workflow efficiency but not essential for core functionality. Users can always select via scene tree. Nice-to-have enhancement for UX.

**Independent Test**: Can be tested by clicking on a visible object in the viewport and verifying it becomes selected in the scene tree and inspector updates. Delivers value through more intuitive interaction.

**Acceptance Scenarios**:

1. **Given** viewport displays multiple entities, **When** user clicks on an entity in viewport, **Then** that entity is selected in scene tree and inspector shows its properties
2. **Given** user clicks on empty space in viewport, **When** click occurs, **Then** current selection is cleared
3. **Given** multiple entities overlap at click position, **When** raycast occurs, **Then** nearest entity is selected

---

### User Story 6 - Transform Gizmo Overlay (Priority: P3)

As a **graphics engineer**, I need a visual transform gizmo overlaid on selected entities so that I can manipulate positions and orientations directly in the viewport using mouse drag operations.

**Why this priority**: Advanced interaction feature that significantly improves UX but is not essential for basic simulation control and observation. Can be implemented using DPG drawlist.

**Independent Test**: Can be tested by selecting an entity, verifying a gizmo (axes/arrows) appears, dragging an axis, and seeing the entity move along that axis with preview feedback. Delivers value through direct manipulation interaction.

**Acceptance Scenarios**:

1. **Given** entity is selected, **When** viewport renders, **Then** transform gizmo (axes overlay) appears at entity's position
2. **Given** user drags gizmo axis, **When** drag is in progress, **Then** entity position/rotation updates in real-time (preview mode)
3. **Given** user releases gizmo after drag, **When** mouse button is released, **Then** single UpdatePropertyCommand is committed to Undo stack
4. **Given** gizmo is rendered, **When** viewport draws, **Then** gizmo uses DPG drawlist (no external ImGuizmo dependency)

---

### Edge Cases

- What happens when **simulation FPS exceeds 10,000** and frame buffer updates saturate lock contention?
  - System must cap frame buffer update rate or implement lock-free double buffering
- How does system handle **startup if graphics context initialization fails** (e.g., no GPU available)?
  - Must display clear error message and fail gracefully without crashing
- What happens when **user drags slider rapidly creating hundreds of preview updates per second**?
  - Preview updates must be throttled or debounced to prevent command queue saturation
- How does system handle **shutdown if simulation thread is blocked in long computation**?
  - Shutdown must set stop flag and wait with timeout, force-terminating if needed
- What happens when **plot buffer memory exceeds available RAM** (e.g., 1 million samples)?
  - Buffer must enforce strict maximum size using circular buffer with automatic pruning

## Requirements

### Functional Requirements

**Concurrency & Threading**:

- **FR-001**: System MUST initialize all graphics and compute contexts (Genesis, Taichi, Dear PyGui) on the main thread before starting any background threads
- **FR-002**: System MUST run Dear PyGui event and render loop on the main thread
- **FR-003**: System MUST run simulation loop (scene.step(), camera.render()) on a dedicated background thread
- **FR-004**: System MUST use Python threading module for concurrency (no asyncio, no multiprocessing)
- **FR-005**: Background simulation thread MUST NOT create any new graphics or compute contexts

**Data Pathways**:

- **FR-006**: Commands from GUI to simulation (Play, Pause, Step, UpdateProperty, etc.) MUST be transmitted via queue.Queue with strict ordering
- **FR-007**: Events from simulation to GUI (EntitySelected, WidgetUpdate, etc.) MUST be transmitted via queue.Queue for low-frequency notifications
- **FR-008**: Plot data from simulation to GUI MUST be stored in collections.deque with configurable maximum length
- **FR-009**: Rendered frames from simulation to GUI MUST use shared numpy.ndarray buffer protected by threading.Lock
- **FR-010**: System MUST NOT transfer large frame arrays via queue.Queue (no pickling/copying of frame buffers)

**Viewport Pipeline**:

- **FR-011**: System MUST create Dear PyGui raw texture once using dpg.add_raw_texture during initialization
- **FR-012**: System MUST update texture every frame using dpg.set_value with frame buffer data
- **FR-013**: Frame buffer MUST use dtype np.float32, range [0.0, 1.0], 4 channels (RGBA), and 1D flattened memory layout
- **FR-014**: System MUST normalize frame data to [0.0, 1.0] range if Genesis outputs different range
- **FR-015**: Texture format MUST use Dear PyGui's mvFormat_Float_rgba

**Playback Control**:

- **FR-016**: Users MUST be able to start simulation playback (continuous stepping)
- **FR-017**: Users MUST be able to pause simulation (freeze current state)
- **FR-018**: Users MUST be able to step simulation forward by configurable number of timesteps
- **FR-019**: Playback commands MUST be queued and processed by simulation thread in order

**Scene Tree & Selection**:

- **FR-020**: System MUST display hierarchical scene tree showing all entities
- **FR-021**: Users MUST be able to select entities by clicking in scene tree
- **FR-022**: Selecting entity MUST emit EntitySelectedEvent from simulation thread to GUI thread
- **FR-023**: System MUST update inspector panel when entity selection changes

**Property Inspector & Editing**:

- **FR-024**: Inspector MUST display editable properties for selected entity using data-driven widget registry
- **FR-025**: Float properties MUST display as sliders (if bounded) or input boxes with min/max validation
- **FR-026**: Vector3 properties MUST display as input_floatx(3) widget
- **FR-027**: Boolean properties MUST display as checkboxes
- **FR-028**: Enum properties MUST display as combo boxes with enum values as items
- **FR-029**: While user drags slider, system MUST send PreviewPropertyCommand (no Undo stack modification)
- **FR-030**: When user releases slider, system MUST send single UpdatePropertyCommand with old and new values (adds to Undo stack)

**Undo/Redo**:

- **FR-031**: System MUST maintain Undo stack of committed UpdatePropertyCommand instances
- **FR-032**: System MUST NOT add preview updates to Undo stack during drag operations
- **FR-033**: Users MUST be able to undo property changes using Undo command
- **FR-034**: Users MUST be able to redo previously undone changes using Redo command

**Live Plotting**:

- **FR-035**: Users MUST be able to select simulation signals (forces, velocities, energies, custom metrics) for plotting
- **FR-036**: Plot MUST display time-series data as line graphs updating in real-time
- **FR-037**: GUI thread MUST downsample plot data using tsdownsample library (LTTB or MinMax algorithm) before rendering
- **FR-038**: Plot downsampling MUST reduce data to 200-1000 points per visible frame to maintain 60 FPS
- **FR-039**: Plot buffer MUST enforce maximum length to prevent unbounded memory growth

**Viewport Interaction** (Phase 5):

- **FR-040**: Users SHOULD be able to click on entities in viewport to select them (raycasting)
- **FR-041**: System SHOULD display transform gizmo overlay using DPG drawlist when entity is selected
- **FR-042**: System MUST NOT use external ImGuizmo library (use DPG drawlist custom implementation)

**Shutdown Sequence**:

- **FR-043**: System MUST signal simulation thread to stop before beginning shutdown
- **FR-044**: System MUST wait for simulation thread to join (with timeout)
- **FR-045**: System MUST exit DPG render loop after simulation thread stops
- **FR-046**: System MUST call dpg.destroy_context() before process exit
- **FR-047**: System MUST follow shutdown sequence: stop render loop → destroy DPG → exit process

### Key Entities

- **Scene**: Top-level container for simulation world, manages entities and physics state
- **Entity**: Individual simulation object (rigid body, constraint, sensor, camera) with unique ID and properties
- **Property**: Named attribute of an entity (position, velocity, mass, material, etc.) with type and value
- **Command**: Serializable message from GUI to simulation (Play, Pause, Step, UpdateProperty, PreviewProperty, Undo, Redo, RayCast)
- **Event**: Serializable message from simulation to GUI (EntitySelected, WidgetUpdate, Collision, Log)
- **PlotSample**: Timestamped value tuple (timestamp: float64, value: float32|64) for time-series data
- **FrameBuffer**: Shared numpy array containing rendered RGBA pixels in [0.0, 1.0] range, flattened to 1D
- **Camera**: Viewpoint for rendering, controlled by user input, produces frame buffers via camera.render()

## Success Criteria

### Measurable Outcomes

**Performance**:

- **SC-001**: GUI renders consistently at 60 FPS (frame time p95 ≤ 16.7ms) at 1920x1080 resolution during active simulation
- **SC-002**: Simulation runs at maximum achievable FPS independently of GUI render rate (demonstrated by FPS counter showing sim >> 60 FPS)
- **SC-003**: Frame buffer lock hold time remains ≤ 1ms at p95 under steady-state operation
- **SC-004**: Real-time plots with 10,000 buffered samples render without causing frame drops below 60 FPS

**Reliability**:

- **SC-005**: System initializes without graphics context errors on supported platforms (macOS Metal, Linux/Windows CUDA/Vulkan)
- **SC-006**: System runs continuously for 30 minutes without crashes, deadlocks, or unbounded memory growth
- **SC-007**: Command and event queue depths remain bounded (< 1000 items) under steady-state operation
- **SC-008**: System shuts down cleanly within 5 seconds without crashes or hangs

**User Experience**:

- **SC-009**: Users can start, pause, and step simulation with immediate feedback (< 100ms response time)
- **SC-010**: Property edits via inspector sliders show real-time preview in viewport during drag
- **SC-011**: Single Undo action correctly reverts property change without reverting intermediate preview states
- **SC-012**: Selected entity in scene tree automatically populates inspector within 100ms

**Architectural Compliance**:

- **SC-013**: All graphics/compute context initialization occurs on main thread (verified by startup logs)
- **SC-014**: No frame arrays are transferred via queue.Queue (verified by profiling - no pickle overhead)
- **SC-015**: Viewport texture updates use only dpg.add_raw_texture + dpg.set_value (verified by code audit)

## Assumptions & Dependencies

### Platform & Environment

- Primary development and testing targets macOS 14+ using Taichi Metal backend
- Linux and Windows support via Taichi CUDA or Vulkan backends (tested on Ubuntu 22.04+, Windows 10+)
- User machine has GPU capable of running Genesis simulation (Metal/CUDA/Vulkan support)
- Display resolution is at least 1920x1080 for optimal viewport experience

### Software Dependencies

- Python 3.11 or later installed and available
- Genesis physics engine with Taichi backend (latest stable release)
- Dear PyGui (latest stable release compatible with Python 3.11+)
- NumPy (latest version compatible with Genesis)
- tsdownsample library (for LTTB/MinMax plot downsampling)
- Standard Python libraries: threading, queue, collections

### Architectural Assumptions

- Genesis simulation is GIL-releasing (allows true concurrent execution in background thread)
- Dear PyGui render loop is compatible with threading-based integration (runs on main thread)
- Frame buffer size (H×W×4 floats) fits comfortably in RAM (< 100MB for 4K resolution)
- Plot buffer maximum size (e.g., 10,000 samples × 16 bytes) is reasonable (< 1MB per signal)
- Command/event queue throughput is sufficient for interactive latency (< 100ms end-to-end)

### User Workflow Assumptions

- Users have basic understanding of 3D viewport navigation (pan, rotate, zoom)
- Users understand simulation playback metaphor (Play/Pause/Step similar to video player)
- Users are familiar with property inspector pattern (common in game engines, CAD tools)
- Users expect immediate visual feedback during parameter tuning (industry standard for interactive tools)

### Out of Scope Assumptions

- No support for distributed/remote simulation (single-machine only)
- No support for collaborative multi-user editing
- No support for scripting or automation beyond command replay
- No built-in support for exporting simulation data (users handle external logging if needed)

## Non-Functional Requirements

### Performance Targets

- **NFR-001**: GUI frame render time p95 ≤ 16.7ms at 1920x1080 viewport resolution
- **NFR-002**: Simulation FPS operates independently from GUI FPS (no artificial throttling)
- **NFR-003**: Frame buffer lock hold time p95 ≤ 1ms
- **NFR-004**: Command queue processing latency p95 ≤ 10ms
- **NFR-005**: Property edit preview latency ≤ 50ms (drag to viewport update)

### Reliability

- **NFR-006**: No CUDA/Vulkan/Metal context errors during initialization on supported platforms
- **NFR-007**: No crashes, deadlocks, or race conditions during 30-minute continuous operation
- **NFR-008**: Command and event queues remain bounded (< 1000 items) under steady-state load
- **NFR-009**: Memory usage remains stable (no leaks) over 30-minute session

### Maintainability

- **NFR-010**: Architecture strictly adheres to constitutional principles (Init-Main, Run-Threaded, etc.)
- **NFR-011**: Code organization separates concerns (GUI layer, simulation layer, data pathways)
- **NFR-012**: Data contracts (Commands, Events) are documented and versioned

### Scalability Limits

- **NFR-013**: System supports scenes with up to 1,000 entities in scene tree without UI degradation
- **NFR-014**: System supports up to 10 concurrent plot signals without frame drops
- **NFR-015**: Plot buffers support up to 10,000 samples per signal before circular buffer pruning

## Phased Delivery Plan

### Phase 1 – Mock Thread + GUI Wiring

**Objective**: Validate data pathway architecture and GUI responsiveness with mock simulation.

**Definition of Done**:
- Mock simulation thread successfully writes to command/event queues, plot buffer, and frame buffer
- GUI loop safely reads from all queues/buffers and renders at stable 60 FPS
- No crashes, race conditions, or deadlocks observed during 5-minute stress test
- Manual testing demonstrates stable mock data flow

**Acceptance**:
- Run mock simulation generating random frame data and plot samples at 1000 Hz
- Verify GUI displays updating viewport and plots at 60 FPS
- Monitor queue depths and lock contention metrics

### Phase 2 – Single-Thread Integration Verification

**Objective**: Prove Genesis-to-DPG rendering path correctness in controlled single-threaded environment.

**Definition of Done**:
- Genesis and DPG initialization succeeds in main thread without context errors
- camera.render() → DPG texture update pipeline produces correct visual output
- Texture format compliance verified (float32/RGBA/[0..1]/flatten)
- Rendered Genesis scene displays correctly in DPG viewport

**Acceptance**:
- Initialize Genesis scene with simple geometry (cube, sphere)
- Render frame using Genesis camera
- Verify frame buffer format matches spec (dtype, range, channels, layout)
- Display frame in DPG viewport and visually confirm correctness

### Phase 3 – Async Loop Separation

**Objective**: Implement full Init-Main, Run-Threaded architecture with independent FPS.

**Definition of Done**:
- "Init-Main, Run-Threaded" pattern fully implemented (contexts on main, loops on separate threads)
- Stable operation with no context errors or crashes during 10-minute continuous run
- Simulation FPS independently accelerates beyond GUI rate (measured via FPS counters)
- GUI maintains stable 60 FPS regardless of simulation speed

**Acceptance**:
- Run simulation with computationally intensive physics (many bodies, contacts)
- Measure simulation FPS (should be >> 60 FPS if compute allows)
- Measure GUI FPS (should be stable at 60 FPS)
- Verify frame buffer updates correctly despite FPS mismatch
- Run for 10 minutes and verify no memory leaks, context errors, or crashes

### Phase 4 – Bidirectional Binding & Undo

**Objective**: Implement command/event pathways and Optimistic UI + Commit on Release pattern.

**Definition of Done**:
- Command pathway (GUI → Sim) functions correctly for all command types
- Event pathway (Sim → GUI) functions correctly for all event types
- Slider drag produces preview updates only (no Undo stack pollution)
- Slider release produces single committed UpdatePropertyCommand
- Undo/Redo correctly restores property state

**Acceptance**:
- Select entity in scene tree and verify inspector populates
- Drag property slider and verify entity updates in real-time (preview mode)
- Release slider and verify single Undo entry created
- Execute Undo and verify property reverts to pre-drag value
- Execute Redo and verify property returns to post-drag value
- Verify Undo stack contains only committed changes, not preview updates

### Phase 5 – Advanced Features (Gizmos & Plots)

**Objective**: Implement viewport raycasting, transform gizmo, and high-performance plotting.

**Definition of Done**:
- DPG drawlist-based transform gizmo overlay renders correctly on selected entity
- Raycasting allows clicking entities in viewport to select them
- High-frequency plot data (> 1kHz) downsampled using tsdownsample before rendering
- Real-time plots display smoothly at 60 FPS without GUI lag

**Acceptance**:
- Select entity and verify gizmo (axes overlay) appears in viewport
- Drag gizmo axis and verify entity moves along that axis with preview feedback
- Release gizmo and verify single Undo entry created
- Click on entity in viewport and verify it becomes selected
- Plot signal at 1000 Hz and verify plot renders smoothly using downsampled data
- Verify GUI maintains 60 FPS while rendering plots with 10,000 buffered samples

## Risks & Mitigations

### Risk: Context Initialization Race Conditions

**Description**: Initializing Genesis/Taichi or DPG contexts in wrong thread or wrong order causes crashes or undefined behavior.

**Likelihood**: High (common mistake in multi-threaded graphics applications)
**Impact**: Critical (application crash, unusable)

**Mitigation**:
- Enforce main-thread-only initialization via architectural principle (Constitution Principle I)
- Implement Phase 2 gate to verify single-threaded integration before Phase 3 multi-threading
- Add startup logging to trace initialization sequence
- Document correct initialization order in code comments

### Risk: GUI Stuttering from Plot Rendering

**Description**: Rendering high-frequency plot data (1000+ samples/sec) without downsampling causes GUI frame drops.

**Likelihood**: High (common performance issue with real-time plotting)
**Impact**: High (poor user experience, defeats purpose of interactive GUI)

**Mitigation**:
- Use tsdownsample library with LTTB or MinMax algorithm for intelligent downsampling
- Downsample to 200-1000 points per visible plot region
- Enforce maximum plot buffer size using circular buffer
- Profile plot rendering and optimize if necessary

### Risk: Frame Buffer Copy Overhead

**Description**: Lock contention or excessive memory copying when transferring frames from simulation to GUI.

**Likelihood**: Medium (depends on resolution and simulation FPS)
**Impact**: Medium (reduced simulation FPS, increased latency)

**Mitigation**:
- Pre-allocate shared frame buffer (no per-frame allocation)
- Minimize lock scope (copy data outside lock if possible)
- Avoid transferring frames via queue.Queue (Constitution Principle IV)
- Consider lock-free double buffering if contention becomes measurable issue

### Risk: Queue Depth Explosion

**Description**: Command or event queues grow unbounded if producer outpaces consumer, leading to memory exhaustion.

**Likelihood**: Low (command rate limited by user input, events are low-frequency)
**Impact**: High (memory exhaustion, application hang)

**Mitigation**:
- Monitor queue depths and log warnings if exceeding threshold (e.g., 1000 items)
- Implement back-pressure mechanism (block producer if queue exceeds limit)
- Design event emission to be low-frequency (avoid per-frame events)
- Add observability metrics for queue depth (Constitution Section 6)

### Risk: Shutdown Hang or Crash

**Description**: Incorrect shutdown sequence causes simulation thread to hang or DPG to crash.

**Likelihood**: Medium (shutdown logic is often overlooked)
**Impact**: Medium (frustrating user experience, potential data loss)

**Mitigation**:
- Follow strict shutdown sequence (Constitution Principle VIII): stop loop → join thread → destroy DPG → exit
- Implement timeout for thread join (force-terminate if exceeds threshold)
- Add shutdown state machine with logging for debugging
- Test shutdown under various states (paused, running, error condition)

## Glossary

**Init-Main, Run-Threaded**: Architectural pattern where all graphics/compute context creation occurs on the main thread during initialization, but long-running loops (GUI render, simulation step) execute on separate threads to avoid blocking.

**Preview vs Commit**: Interaction pattern where user actions (e.g., dragging slider) produce immediate visual feedback (preview updates) without modifying application state or Undo stack, and only on completion (e.g., mouse release) is a single committed state change recorded.

**Optimistic UI**: UI design pattern where user inputs update the display immediately (optimistically) before confirmation, providing responsive feedback. In this spec, applies to property editing where drag updates viewport instantly.

**Undo Stack**: Data structure maintaining history of committed state changes (UpdatePropertyCommands) to enable undo/redo operations. Crucially, does NOT include preview updates.

**Constitution**: Project governance document (.specify/memory/constitution.md) defining architectural invariants, phase gates, and compliance requirements that all implementations must follow.

**Phase Gate**: Checkpoint with Definition of Done criteria that must be satisfied before advancing to next implementation phase. Ensures stable foundation before building dependent features.

**Definition of Done (DoD)**: Explicit, measurable completion criteria for a phase or feature. Prevents premature advancement and ensures quality.

**LTTB (Largest Triangle Three Buckets)**: Time-series downsampling algorithm that preserves visual trends by selecting points that maximize triangle area, implemented in tsdownsample library.

**MinMax Downsampling**: Time-series downsampling algorithm that preserves peaks and troughs by selecting minimum and maximum values within time buckets.

**Frame Buffer**: Shared memory region (numpy array) containing rendered image pixels in RGBA float32 format, protected by threading.Lock for safe concurrent access.

**Plot Buffer**: Circular buffer (collections.deque) storing time-series samples as (timestamp, value) tuples, automatically pruning oldest data when maximum length is reached.

**Command Queue**: Thread-safe queue (queue.Queue) transmitting serialized command objects from GUI thread to simulation thread.

**Event Queue**: Thread-safe queue (queue.Queue) transmitting serialized event objects from simulation thread to GUI thread for low-frequency notifications.

**Entity**: Simulation object with unique identifier and properties (position, velocity, material, etc.). Examples: rigid body, joint constraint, camera, sensor.

**Scene Tree**: Hierarchical view of all entities in the simulation, displayed in GUI for navigation and selection.

**Inspector**: GUI panel displaying editable properties of currently selected entity using data-driven widget registry.

**Widget Registry**: Mapping from property types to Dear PyGui widgets (float → slider, vec3 → input_floatx, bool → checkbox, enum → combo).

**Raycast**: Geometric query shooting a ray from camera through viewport pixel to find intersected entities, enabling viewport-based selection.

**Transform Gizmo**: Visual overlay (axes/arrows) on selected entity allowing direct manipulation of position/rotation via mouse drag.

**DPG (Dear PyGui)**: Python GUI framework used for rendering interface, based on Dear ImGui with Python bindings.

**Genesis**: High-performance physics simulation engine with Taichi backend supporting GPU acceleration.

**Taichi**: Parallel programming language and compiler for high-performance computing, used by Genesis for physics kernels.

**Metal/CUDA/Vulkan**: Graphics/compute APIs for GPU acceleration. Metal (macOS), CUDA (NVIDIA), Vulkan (cross-platform).
