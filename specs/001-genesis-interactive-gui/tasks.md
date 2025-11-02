# Tasks: Genesis Interactive GUI

**Input**: Design documents from `/specs/001-genesis-interactive-gui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This project uses manual smoke tests per phase gate. No automated test tasks included.

**Organization**: Tasks are grouped by phase following the constitutional phase gates. Each phase is independently testable using quickstart.md validation checklists.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5, US6)
- Include exact file paths in descriptions

---

## Phase 1: Setup & Mock Threading

**Purpose**: Project initialization and mock threading validation (Constitutional Phase 1)

**Objective**: Validate data pathway architecture with mock simulation before Genesis integration

**DoD Gate**: Mock threading working at 1000 Hz sim / 60 FPS GUI with no crashes

### Infrastructure Setup

- [X] T001 Create project directory structure (src/core/, src/ui/, src/infra/, tests/smoke/)
- [X] T002 Initialize Python 3.11+ project with requirements.txt (Genesis, DearPyGui, NumPy, tsdownsample)
- [X] T003 [P] Create .gitignore for Python project (.venv/, __pycache__/, *.pyc)
- [X] T004 [P] Create README.md with project overview and setup instructions

### Data Contracts & IPC

- [X] T005 [P] Implement BaseCommand and BaseEvent dataclasses in src/core/commands.py
- [X] T006 [P] Implement all command types in src/core/commands.py (Play, Pause, Step, PreviewProperty, UpdateProperty, Undo, Redo, Shutdown)
- [X] T007 [P] Implement all event types in src/core/commands.py (EntitySelected, WidgetUpdate, Collision, Log, PlotData, PropertyChanged)
- [X] T008 [P] Implement CommandQueue wrapper in src/core/ipc.py
- [X] T009 [P] Implement EventQueue wrapper in src/core/ipc.py
- [X] T010 [P] Implement FrameBuffer class with threading.Lock in src/core/ipc.py
- [X] T011 [P] Implement PlotBuffer class with collections.deque in src/core/ipc.py

### Mock Simulation Thread

- [X] T012 Implement mock_sim_loop function in src/core/sim_loop.py (generates random frames at 1000 Hz)
- [X] T013 Add command processing stub in mock_sim_loop (Play/Pause/Step commands)
- [X] T014 Add frame buffer write logic in mock_sim_loop (random RGBA float32 [0..1] data)
- [X] T015 Add plot buffer write logic in mock_sim_loop (random time-series data)
- [X] T016 [P] Implement FPSCounter class in src/infra/metrics.py for simulation FPS tracking
- [X] T017 [P] Implement TimedLock wrapper in src/infra/metrics.py for lock timing

### DPG GUI Thread

- [X] T018 Implement DPG context initialization in src/ui/main.py
- [X] T019 Implement main GUI window layout in src/ui/main.py (viewport, controls, metrics)
- [X] T020 [P] Implement create_viewport function in src/ui/viewport.py (add_raw_texture with mvFormat_Float_rgba)
- [X] T021 [P] Implement update_viewport function in src/ui/viewport.py (set_value from frame buffer)
- [X] T022 [P] Create playback control buttons in src/ui/main.py (Play, Pause, Step)
- [X] T023 [P] Wire playback buttons to CommandQueue in src/ui/main.py
- [X] T024 Implement GUI render loop in src/ui/main.py (process events, update viewport, render frame)
- [X] T025 [P] Implement FPSCounter display in src/infra/metrics.py (GUI FPS label)
- [X] T026 [P] Implement metrics dashboard window in src/infra/metrics.py (FPS, lock time, queue depths)

### Bootstrap & Shutdown

- [X] T027 Implement initialize_mock_system function in src/infra/bootstrap.py (create IPC, start thread)
- [X] T028 Implement shutdown_system function in src/infra/bootstrap.py (signal stop, join thread, destroy DPG)
- [X] T029 Implement application entry point in src/__main__.py (call bootstrap, run GUI loop)
- [X] T030 Add ShutdownCommand handling in mock_sim_loop
- [X] T031 Add DPG exit callback in src/ui/main.py to trigger shutdown sequence

### Validation

- [ ] T032 Run Phase 1 validation checklist from specs/001-genesis-interactive-gui/quickstart.md
- [ ] T033 Verify mock viewport shows cycling colors at 60 FPS
- [ ] T034 Verify GUI FPS stable at ~60 FPS, Sim FPS at 500+ FPS (mock is fast)
- [ ] T035 Verify shutdown completes cleanly within 1 second
- [ ] T036 Run 5-minute stress test with no crashes or memory leaks

**Checkpoint**: Phase 1 complete - threading architecture validated with mock data

---

## Phase 2: Genesis Integration & Texture Validation

**Purpose**: Replace mock simulation with real Genesis renderer (Constitutional Phase 2)

**Objective**: Prove Genesis-to-DPG rendering path correctness in single-threaded mode first

**DoD Gate**: Genesis scene renders correctly in DPG viewport, all texture format requirements met

### Backend Selection

- [X] T037 Implement backend selection logic in src/infra/bootstrap.py (Metal/CUDA/Vulkan per research.md)
- [X] T038 Add fallback backend logic in src/infra/bootstrap.py (try primary, fall back to Vulkan)
- [X] T039 Add startup logging for backend selection in src/infra/bootstrap.py

### Single-Thread Genesis Integration

- [X] T040 Implement genesis_init function in src/infra/bootstrap.py (gs.init, gs.Scene on main thread)
- [X] T041 Create simple test scene in src/core/scene_setup.py (cube, sphere, ground plane, camera)
- [X] T042 [P] Implement frame format validation function in src/core/ipc.py (dtype, shape, range checks)
- [X] T043 [P] Implement genesis_frame_to_dpg_texture conversion in src/core/ipc.py (ensure float32 RGBA [0..1] flatten)

### Single-Thread Test Harness

- [ ] T044 Create phase2_single_thread_test.py in tests/smoke/ (initialize Genesis + DPG on main thread only)
- [ ] T045 Add Genesis camera.render() call in test harness
- [ ] T046 Add frame format validation in test harness (assert dtype, channels, range)
- [ ] T047 Add visual inspection loop in test harness (render for 60 frames, 1 second)
- [ ] T048 Run Phase 2 validation checklist from quickstart.md

### Genesis Simulation Loop (No Threading Yet)

- [X] T049 Replace mock_sim_loop with genesis_sim_loop in src/core/sim_loop.py (but still call from main thread)
- [X] T050 Add Genesis scene.step() call in genesis_sim_loop
- [X] T051 Add Genesis camera.render() call in genesis_sim_loop
- [X] T052 Add frame conversion and buffer write in genesis_sim_loop (convert → flatten → write to frame buffer)
- [X] T053 Update src/__main__.py to use genesis_sim_loop (single-threaded mode for Phase 2)

### Validation

- [X] T054 Run application in single-threaded mode and verify Genesis scene renders
- [X] T055 Verify no green tint, noise, or visual artifacts in viewport
- [X] T056 Verify backend initialization logs show correct backend (Metal/CUDA/Vulkan)
- [X] T057 Verify no context errors or crashes during initialization
- [X] T058 Run texture format validation and confirm all assertions pass

**Checkpoint**: Phase 2 complete - Genesis rendering works correctly in single-threaded mode

**GATE**: Phase 3 (multi-threading) MUST NOT begin until Phase 2 visual rendering confirmed working

---

## Phase 3: Dual-Loop Separation (User Story 1 & 2)

**Purpose**: Implement full Init-Main, Run-Threaded architecture (Constitutional Phase 3)

**Objective**: Independent GUI (60 FPS) and Sim (max FPS) loops with no context errors

**DoD Gate**: 10-minute continuous run with GUI 60 FPS, Sim 500+ FPS, no crashes

**User Stories Covered**: US1 (Playback Control), US2 (Real-time Viewport)

### Thread Migration

- [X] T059 Update src/infra/bootstrap.py to start genesis_sim_loop in background thread (threading.Thread)
- [X] T060 Pass all IPC objects to background thread (command_queue, event_queue, frame_buffer, plot_buffer, locks)
- [X] T061 Add threading.Event shutdown_flag to coordinate graceful shutdown
- [X] T062 Update genesis_sim_loop to check shutdown_flag and command_queue.get(timeout=0.01)
- [X] T063 Verify all Genesis/Taichi contexts still created on main thread BEFORE thread start

### User Story 1: Playback Control (P1)

**Goal**: Start, pause, and step through simulations for behavior observation and debugging

**Independent Test**: Click Play/Pause/Step buttons and verify simulation state changes correctly

- [X] T064 [US1] Implement Play command processing in genesis_sim_loop (set running flag)
- [X] T065 [US1] Implement Pause command processing in genesis_sim_loop (clear running flag)
- [X] T066 [US1] Implement Step command processing in genesis_sim_loop (step N times when paused)
- [X] T067 [US1] Wire Play button callback in src/ui/main.py to emit PlayCommand
- [X] T068 [US1] Wire Pause button callback in src/ui/main.py to emit PauseCommand
- [X] T069 [US1] Wire Step button callback in src/ui/main.py to emit StepCommand(steps=1)
- [X] T070 [US1] Update playback button states in src/ui/main.py (Play ↔ Pause toggle)
- [ ] T071 [US1] Test User Story 1 acceptance scenarios from spec.md (Play → continuous, Pause → freeze, Step → advance 1)

### User Story 2: Real-time 3D Viewport (P1)

**Goal**: Continuously updating 3D viewport showing simulation state at 60 FPS

**Independent Test**: Run simulation at 1000+ FPS and verify viewport displays smooth 60 FPS updates

- [X] T072 [US2] Verify frame buffer read in GUI loop uses lock correctly in src/ui/main.py
- [X] T073 [US2] Verify frame buffer write in sim loop uses lock correctly in src/core/sim_loop.py
- [X] T074 [US2] Minimize lock scope in sim loop (convert frame outside lock, only copy inside)
- [X] T075 [US2] Add frame skip logic in sim loop (render every Nth step if sim FPS >> 60)
- [X] T076 [US2] Optimize frame conversion pipeline to < 3ms per frame
- [ ] T077 [US2] Test User Story 2 acceptance scenarios from spec.md (moving bodies at 60 FPS, sim FPS 1000+, frame time p95 ≤ 16.7ms)

### Metrics & Observability

- [X] T078 [P] Add queue depth monitoring to metrics dashboard in src/infra/metrics.py
- [X] T079 [P] Add lock hold time p95 display to metrics dashboard in src/infra/metrics.py
- [X] T080 [P] Add memory usage tracking to metrics dashboard in src/infra/metrics.py
- [X] T081 [P] Implement periodic metrics logging (every 60 frames) in src/core/sim_loop.py

### Shutdown Sequence

- [X] T082 Update shutdown sequence in src/infra/bootstrap.py (set flag → put ShutdownCommand → join with timeout)
- [X] T083 Add timeout handling in shutdown (log warning if thread doesn't exit)
- [X] T084 Update ShutdownCommand processing in genesis_sim_loop (break loop, exit cleanly)
- [X] T085 Verify DPG exit callback triggers shutdown sequence correctly

### Validation

- [ ] T086 Run Phase 3 validation checklist from quickstart.md
- [ ] T087 Verify independent FPS counters (GUI ~60 FPS, Sim 500-1000+ FPS)
- [ ] T088 Verify GUI remains responsive while simulation runs (drag window, click buttons)
- [ ] T089 Run 10-minute stability test with no crashes, deadlocks, or memory leaks
- [ ] T090 Verify shutdown completes within 5 seconds from window close
- [ ] T091 Verify metrics dashboard shows stable performance (lock hold < 1ms p95, queue depth < 100)

**Checkpoint**: Phase 3 complete - User Story 1 (Playback) and User Story 2 (Viewport) fully functional

**GATE**: Phase 4 (bidirectional communication) MUST NOT begin until Phase 3 stability proven

---

## Phase 4: Property Editing & Undo (User Story 3)

**Purpose**: Interactive property editing with Undo/Redo (Constitutional Phase 4)

**Objective**: Optimistic UI + Commit on Release pattern working correctly

**DoD Gate**: Slider drag → preview only, release → single Undo entry, Undo/Redo works

**User Stories Covered**: US3 (Entity Selection and Property Editing)

### User Story 3: Entity Selection and Property Editing (P2)

**Goal**: Select entities, view properties, modify with immediate feedback, Undo/Redo support

**Independent Test**: Select entity, drag slider, observe preview, release, verify single Undo entry

### Scene Tree Widget

- [ ] T092 [P] [US3] Implement scene tree widget in src/ui/scene_tree.py (DPG tree node structure)
- [ ] T093 [P] [US3] Populate scene tree from Genesis scene entities in src/ui/scene_tree.py
- [ ] T094 [P] [US3] Add selection callback to scene tree in src/ui/scene_tree.py (emit EntitySelectedEvent)
- [ ] T095 [P] [US3] Add EntitySelectedEvent processing in src/ui/main.py (update inspector)

### Property Inspector Widget

- [ ] T096 [P] [US3] Implement Inspector class in src/ui/inspector.py with widget registry
- [ ] T097 [P] [US3] Add widget registry entries in src/ui/inspector.py (float→slider, vec3→input_floatx, bool→checkbox, enum→combo)
- [ ] T098 [P] [US3] Implement populate_inspector function in src/ui/inspector.py (query entity properties from scene)
- [ ] T099 [US3] Implement on_preview callback in src/ui/inspector.py (emit PreviewPropertyCommand during drag)
- [ ] T100 [US3] Implement on_commit callback in src/ui/inspector.py (emit UpdatePropertyCommand on release)
- [ ] T101 [US3] Store original value at drag start in src/ui/inspector.py (for UpdatePropertyCommand.old_value)

### Property Command Processing

- [ ] T102 [US3] Implement PreviewPropertyCommand handler in src/core/sim_loop.py (apply temporary change, no Undo)
- [ ] T103 [US3] Implement UpdatePropertyCommand handler in src/core/sim_loop.py (apply change, push to Undo stack)
- [ ] T104 [P] [US3] Implement property path resolver in src/core/sim_loop.py (parse "position.x" → nested getattr/setattr)
- [ ] T105 [P] [US3] Add property change validation in src/core/sim_loop.py (min/max clamp, type check)

### Undo/Redo System

- [ ] T106 [P] [US3] Implement UndoStack class in src/core/undo_stack.py (push, undo, redo, can_undo, can_redo)
- [ ] T107 [US3] Implement UndoCommand handler in src/core/sim_loop.py (pop from undo_stack, apply old_value)
- [ ] T108 [US3] Implement RedoCommand handler in src/core/sim_loop.py (pop from redo_stack, apply new_value)
- [ ] T109 [P] [US3] Add keyboard shortcuts in src/ui/main.py (Ctrl+Z → UndoCommand, Ctrl+Shift+Z → RedoCommand)
- [ ] T110 [US3] Verify redo_stack clears on new UpdatePropertyCommand (not on PreviewPropertyCommand)

### Event Processing

- [ ] T111 [US3] Implement event loop processing in src/ui/main.py (process event_queue every frame)
- [ ] T112 [P] [US3] Add WidgetUpdateEvent handler in src/ui/main.py (dpg.set_value for metrics)
- [ ] T113 [P] [US3] Add LogEvent handler in src/ui/main.py (append to console window with color)
- [ ] T114 [P] [US3] Add PropertyChangedEvent handler in src/ui/main.py (update inspector if selected)

### Validation

- [ ] T115 [US3] Run Phase 4 validation checklist from quickstart.md
- [ ] T116 [US3] Test User Story 3 acceptance scenarios from spec.md:
  - [ ] T116a Scene tree selection → inspector populates
  - [ ] T116b Drag slider → entity moves in real-time (preview)
  - [ ] T116c Release slider → single Undo entry created
  - [ ] T116d Undo → property reverts to pre-drag value (not intermediate)
  - [ ] T116e Inspector widget type matches property type (slider for bounded float, etc.)
- [ ] T117 [US3] Verify Undo stack contains only UpdatePropertyCommand, not PreviewPropertyCommand
- [ ] T118 [US3] Verify command queue depth stays < 100 during rapid slider dragging
- [ ] T119 [US3] Make 3 edits, Undo 3 times, Redo 3 times, make new edit → verify Redo stack clears

**Checkpoint**: Phase 4 complete - User Story 3 (Property Editing + Undo) fully functional

**GATE**: Phase 5 (advanced features) is OPTIONAL - can stop here for MVP

---

## Phase 5: Live Plotting (User Story 4)

**Purpose**: Real-time signal plotting with downsampling (Constitutional Phase 5)

**Objective**: Plot 1000+ Hz data at 60 FPS GUI using LTTB downsampling

**DoD Gate**: Plots update smoothly with 10k samples, no GUI stuttering

**User Stories Covered**: US4 (Live Signal Plotting)

### User Story 4: Live Signal Plotting (P2)

**Goal**: Monitor simulation signals (forces, velocities, energies) in real-time plots

**Independent Test**: Select signal, run simulation at 1000+ FPS, verify plot updates at 60 FPS smoothly

### Plot Widget Infrastructure

- [ ] T120 [P] [US4] Create plot panel layout in src/ui/plots.py (DPG plot widget)
- [ ] T121 [P] [US4] Implement create_plot function in src/ui/plots.py (add_plot with x/y series)
- [ ] T122 [P] [US4] Add signal selection dropdown in src/ui/plots.py (kinetic energy, potential energy, custom)
- [ ] T123 [P] [US4] Create plot_buffers dictionary in src/ui/main.py (one PlotBuffer per signal)

### Plot Data Collection

- [ ] T124 [US4] Emit PlotDataEvent from sim loop in src/core/sim_loop.py (kinetic energy every timestep)
- [ ] T125 [P] [US4] Add scene.get_metric helper in src/core/scene_setup.py (calculate kinetic/potential energy)
- [ ] T126 [US4] Process PlotDataEvent in GUI loop in src/ui/main.py (append to plot_buffer)
- [ ] T127 [P] [US4] Verify plot_buffer circular behavior (oldest dropped when full)

### Downsampling Integration

- [ ] T128 [P] [US4] Implement downsample_plot_data function in src/ui/plots.py using tsdownsample.lttb
- [ ] T129 [US4] Add downsample call in update_plot function (10k → 1k points before rendering)
- [ ] T130 [P] [US4] Add downsampling algorithm selection in src/ui/plots.py (LTTB vs MinMax)
- [ ] T131 [US4] Optimize plot update to run only at 60 FPS (not every sim step)

### Validation

- [ ] T132 [US4] Run Phase 5 plot validation from quickstart.md
- [ ] T133 [US4] Test User Story 4 acceptance scenarios from spec.md:
  - [ ] T133a Select signal → plot displays updating smoothly
  - [ ] T133b Sim at 1000 Hz → plot downsamples and updates at 60 FPS
  - [ ] T133c Plot with 10k points → GUI maintains 60 FPS
  - [ ] T133d Buffer reaches max → oldest samples removed
- [ ] T134 [US4] Verify plot trends preserved after downsampling (visual inspection)
- [ ] T135 [US4] Run simulation for 5 minutes with plots enabled, verify no stuttering or memory leaks

**Checkpoint**: Phase 5 Plotting complete - User Story 4 (Live Plots) fully functional

---

## Phase 6: Raycasting & Gizmo (User Story 5 & 6) [OPTIONAL]

**Purpose**: Advanced viewport interaction (Constitutional Phase 5 continued)

**Objective**: Raycast selection and DPG drawlist gizmo overlay

**DoD Gate**: Click entity to select, drag gizmo to move, single Undo entry on release

**User Stories Covered**: US5 (Viewport Raycasting), US6 (Transform Gizmo)

### User Story 5: Viewport Entity Selection via Raycasting (P3)

**Goal**: Click entities in viewport to select them (instead of scene tree only)

**Independent Test**: Click visible object in viewport, verify selection in scene tree and inspector

- [ ] T136 [P] [US5] Implement viewport click handler in src/ui/viewport.py (capture mouse coords)
- [ ] T137 [P] [US5] Convert screen coords to normalized [0..1] in src/ui/viewport.py
- [ ] T138 [US5] Emit RayCastCommand from viewport click in src/ui/viewport.py
- [ ] T139 [US5] Implement RayCastCommand handler in src/core/sim_loop.py (camera.screen_to_ray)
- [ ] T140 [US5] Perform scene raycast in src/core/sim_loop.py (find nearest intersected entity)
- [ ] T141 [US5] Emit EntitySelectedEvent from raycast hit in src/core/sim_loop.py
- [ ] T142 [US5] Test User Story 5 acceptance scenarios from spec.md:
  - [ ] T142a Click entity → selected in scene tree + inspector
  - [ ] T142b Click empty space → selection clears
  - [ ] T142c Multiple overlapping entities → nearest selected

### User Story 6: Transform Gizmo Overlay (P3)

**Goal**: Visual gizmo for direct manipulation of entity position/rotation in viewport

**Independent Test**: Select entity, see gizmo, drag axis, entity moves, single Undo entry on release

- [ ] T143 [P] [US6] Implement TransformGizmo class in src/ui/gizmo.py (DPG drawlist-based)
- [ ] T144 [P] [US6] Implement project_to_screen helper in src/ui/gizmo.py (3D entity position → 2D screen)
- [ ] T145 [US6] Render gizmo axes in src/ui/gizmo.py (X=red, Y=green, Z=blue lines using dpg.draw_line)
- [ ] T146 [US6] Add gizmo mouse drag detection in src/ui/gizmo.py (check if dragging on axis)
- [ ] T147 [US6] Emit PreviewPropertyCommand during gizmo drag in src/ui/gizmo.py (update position)
- [ ] T148 [US6] Emit UpdatePropertyCommand on gizmo release in src/ui/gizmo.py (commit to Undo)
- [ ] T149 [US6] Integrate gizmo rendering into viewport update loop in src/ui/viewport.py
- [ ] T150 [US6] Test User Story 6 acceptance scenarios from spec.md:
  - [ ] T150a Entity selected → gizmo appears
  - [ ] T150b Drag X/Y/Z axis → entity moves along that axis only
  - [ ] T150c Gizmo release → single Undo entry created
  - [ ] T150d Gizmo uses DPG drawlist (no ImGuizmo dependency)

### Validation

- [ ] T151 Run Phase 5 advanced features validation from quickstart.md
- [ ] T152 Verify raycasting latency < 100ms (click → selection)
- [ ] T153 Verify gizmo render overhead < 1ms (profiling)
- [ ] T154 Verify Undo/Redo integration with gizmo (same as inspector sliders)

**Checkpoint**: Phase 6 complete - All user stories implemented (US1-US6 complete)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple components

- [ ] T155 [P] Add comprehensive logging throughout application (info, warning, error levels)
- [ ] T156 [P] Add error handling for common failures (GPU init, file I/O, invalid commands)
- [ ] T157 [P] Add configuration file support in src/infra/config.py (window size, backend override, buffer sizes)
- [ ] T158 [P] Update README.md with usage instructions and screenshots
- [ ] T159 [P] Create user guide in docs/user_guide.md (how to use all features)
- [ ] T160 [P] Add performance profiling helpers in src/infra/metrics.py (optional py-spy integration)
- [ ] T161 Code review and refactoring pass (remove duplicates, improve naming)
- [ ] T162 Security review (no obvious vulnerabilities, proper input validation)
- [ ] T163 Run all phase validation checklists from quickstart.md end-to-end
- [ ] T164 Performance optimization pass (profile hot spots, optimize if needed)
- [ ] T165 Memory leak audit (run for 30 minutes, check memory usage)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup & Mock)**: No dependencies - can start immediately
- **Phase 2 (Genesis Integration)**: Depends on Phase 1 completion
- **Phase 3 (Dual-Loop + US1/US2)**: Depends on Phase 2 completion - **BLOCKS all remaining user stories**
- **Phase 4 (US3)**: Depends on Phase 3 completion
- **Phase 5 (US4)**: Depends on Phase 3 completion (can run in parallel with Phase 4)
- **Phase 6 (US5/US6)**: Depends on Phase 4 completion (needs inspector/Undo)
- **Phase 7 (Polish)**: Depends on all desired user story phases being complete

### User Story Dependencies

- **US1 (Playback) & US2 (Viewport)**: Foundational - implemented together in Phase 3
- **US3 (Property Editing)**: Depends on US1/US2 (Phase 3 complete)
- **US4 (Plotting)**: Depends on US1/US2 (Phase 3 complete) - **Can run in parallel with US3**
- **US5 (Raycasting)**: Depends on US3 (needs inspector integration)
- **US6 (Gizmo)**: Depends on US3 (needs Undo/Redo system) - **Can run in parallel with US5**

### Within Each Phase

**Phase 1**:
- Infrastructure → Data Contracts → Mock Sim → GUI → Bootstrap (generally sequential)
- [P] tasks within each group can run in parallel

**Phase 2**:
- Backend selection → Single-thread test → Genesis integration (sequential)
- [P] validation tasks can run in parallel

**Phase 3**:
- Thread migration → US1 implementation → US2 optimization (sequential for correctness)
- [P] metrics tasks can run in parallel with core work

**Phase 4**:
- Scene tree → Inspector → Property commands → Undo/Redo (sequential dependencies)
- [P] event processing tasks can run in parallel

**Phase 5**:
- Plot infrastructure → Data collection → Downsampling (sequential)
- [P] plot widget and algorithm selection can be prototyped in parallel

**Phase 6**:
- US5 (Raycasting) and US6 (Gizmo) can run in parallel after US3 complete

### Parallel Opportunities

**Phase 1 Parallelization**:
```bash
# Data contracts (all independent):
Task T005-T007: Command/Event dataclasses
Task T008-T011: IPC classes (CommandQueue, EventQueue, FrameBuffer, PlotBuffer)

# Infrastructure (all independent):
Task T016-T017: Metrics classes
Task T020-T026: UI widgets and controls
```

**Phase 3 Parallelization** (after thread migration):
```bash
# US1 and US2 core work sequential, but metrics parallel:
Task T064-T071: US1 Playback (sequential)
Task T072-T077: US2 Viewport (sequential)
Task T078-T081: Metrics (parallel with above)
```

**Phase 4 Parallelization**:
```bash
# Scene tree, Inspector widget registry, Undo stack independent:
Task T092-T095: Scene tree widget
Task T096-T098: Inspector widget registry
Task T106: UndoStack class
Task T109: Keyboard shortcuts

# Can work in parallel, then integrate
```

**Phase 5 Parallelization**:
```bash
# Plot infrastructure independent of data collection:
Task T120-T123: Plot widget infrastructure
Task T124-T127: Plot data collection
Task T128-T131: Downsampling (depends on T120-T123)
```

**Phase 6 Parallelization**:
```bash
# US5 and US6 fully independent:
Task T136-T142: US5 Raycasting (parallel branch 1)
Task T143-T150: US6 Gizmo (parallel branch 2)
```

**Phase 7 Parallelization**:
```bash
# All polish tasks independent:
Task T155-T165: All can run in parallel
```

---

## Parallel Example: Phase 1

```bash
# After project structure created (T001-T004):

# Launch data contracts group (parallel):
Task T005: "Implement BaseCommand and BaseEvent dataclasses in src/core/commands.py"
Task T006: "Implement all command types in src/core/commands.py"
Task T007: "Implement all event types in src/core/commands.py"
Task T008: "Implement CommandQueue wrapper in src/core/ipc.py"
Task T009: "Implement EventQueue wrapper in src/core/ipc.py"
Task T010: "Implement FrameBuffer class in src/core/ipc.py"
Task T011: "Implement PlotBuffer class in src/core/ipc.py"

# Launch infrastructure group (parallel with above):
Task T016: "Implement FPSCounter class in src/infra/metrics.py"
Task T017: "Implement TimedLock wrapper in src/infra/metrics.py"

# Launch UI group (parallel with above):
Task T020: "Implement create_viewport function in src/ui/viewport.py"
Task T021: "Implement update_viewport function in src/ui/viewport.py"
Task T022: "Create playback control buttons in src/ui/main.py"
Task T025: "Implement FPSCounter display in src/infra/metrics.py"
Task T026: "Implement metrics dashboard window in src/infra/metrics.py"
```

---

## Implementation Strategy

### MVP First (Phase 1-4: US1, US2, US3)

This delivers a fully functional interactive GUI with playback, viewport, and property editing:

1. **Phase 1** (2 weeks): Setup + Mock Threading → Validates architecture
2. **Phase 2** (1 week): Genesis Integration → Validates rendering pipeline
3. **Phase 3** (2 weeks): Dual-Loop + US1/US2 → Delivers playback + viewport (core value)
4. **Phase 4** (2 weeks): US3 → Adds property editing + Undo (interactive tuning)

**STOP and DEPLOY**: This is a complete, valuable MVP (7 weeks)

### Incremental Delivery Beyond MVP

5. **Phase 5** (2 weeks): US4 → Adds live plotting (quantitative analysis)
6. **Phase 6** (2 weeks): US5/US6 → Adds raycasting + gizmo (UX polish)
7. **Phase 7** (1 week): Polish → Final improvements

**Full Feature Set**: 12 weeks total

### Parallel Team Strategy

With 2 developers after Phase 3 complete:

- **Developer A**: Phase 4 (US3 - Property Editing)
- **Developer B**: Phase 5 (US4 - Plotting)

With 3 developers after Phase 4 complete:

- **Developer A**: Phase 6 US5 (Raycasting)
- **Developer B**: Phase 6 US6 (Gizmo)
- **Developer C**: Phase 7 (Polish)

---

## Summary

- **Total Tasks**: 165 tasks
- **Phases**: 7 phases (Phase 1-4 = MVP, Phase 5-7 = optional enhancements)
- **User Stories**:
  - US1 (Playback Control): Phase 3, 8 tasks
  - US2 (Real-time Viewport): Phase 3, 6 tasks
  - US3 (Property Editing): Phase 4, 28 tasks
  - US4 (Live Plotting): Phase 5, 16 tasks
  - US5 (Raycasting): Phase 6, 7 tasks
  - US6 (Gizmo): Phase 6, 8 tasks
- **Parallel Opportunities**: 60+ tasks marked [P] for parallel execution
- **Independent Testing**: Each phase has validation checklist in quickstart.md
- **MVP Scope**: Phases 1-4 (US1, US2, US3) = 7 weeks
- **Full Scope**: Phases 1-7 (all 6 user stories) = 12 weeks

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label (US1-US6) maps task to specific user story for traceability
- Constitutional compliance enforced through phase gates (see plan.md)
- Tests are manual smoke tests per phase (quickstart.md checklists)
- Each phase checkpoint allows independent validation before proceeding
- Stop at Phase 4 for MVP or continue to Phase 7 for full feature set
- Commit after each task or logical group for incremental progress
