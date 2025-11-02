"""
Mock simulation loop for Phase 1 threading validation.

This module implements a mock simulation thread that generates random frames
and plot data to validate the threading architecture before Genesis integration.

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import time
import queue
import threading
import numpy as np
from typing import Optional, Tuple

from src.core.commands import (
    BaseCommand,
    PlayCommand,
    PauseCommand,
    StepCommand,
    ShutdownCommand,
    PreviewPropertyCommand,
    UpdatePropertyCommand,
    UndoCommand,
    RedoCommand,
)
from src.core.ipc import CommandQueue, EventQueue, FrameBuffer, PlotBuffer
from src.core.undo_stack import UndoStack


# ============================================================================
# Mock Simulation Loop
# ============================================================================

class MockSimulationState:
    """
    State machine for mock simulation playback control.

    States:
    - PAUSED: Not advancing simulation
    - PLAYING: Continuously advancing simulation
    - STEP: Advance one frame then return to PAUSED
    """

    def __init__(self):
        """Initialize simulation state."""
        self.is_playing = False
        self.step_requested = False
        self.sim_time = 0.0  # Simulation time in seconds
        self.frame_count = 0

    def handle_command(self, command: BaseCommand):
        """
        Process playback control command.

        Args:
            command: Command to process
        """
        if isinstance(command, PlayCommand):
            self.is_playing = True
            self.step_requested = False
        elif isinstance(command, PauseCommand):
            self.is_playing = False
            self.step_requested = False
        elif isinstance(command, StepCommand):
            self.is_playing = False
            self.step_requested = True

    def should_advance(self) -> bool:
        """
        Check if simulation should advance this frame.

        Returns:
            True if should advance (playing or step requested)
        """
        if self.step_requested:
            self.step_requested = False
            return True
        return self.is_playing

    def advance(self, dt: float):
        """
        Advance simulation state.

        Args:
            dt: Time step in seconds (typically 0.001 = 1ms @ 1000 Hz)
        """
        self.sim_time += dt
        self.frame_count += 1


def mock_sim_loop(
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    fps_counter,  # FPSCounter instance
    target_hz: float = 1000.0,
    shutdown_event: Optional[threading.Event] = None,
):
    """
    Mock simulation loop running at ~1000 Hz.

    This function runs in a background thread and:
    1. Processes commands from GUI (Play/Pause/Step/Shutdown)
    2. Generates random RGBA float32 [0..1] frames
    3. Writes frames to shared FrameBuffer
    4. Generates random time-series data for PlotBuffer
    5. Emits events back to GUI

    Constitutional Compliance:
    - Runs on background thread (Principle I)
    - Uses queue.Queue for commands (Principle IV)
    - Writes to shared numpy.ndarray + Lock for frames (Principle IV)
    - Uses collections.deque for plots (Principle IV)

    Args:
        command_queue: Commands from GUI thread
        event_queue: Events to GUI thread
        frame_buffer: Shared frame buffer for rendered frames
        plot_buffer: Circular buffer for time-series data
        target_hz: Target loop frequency (default 1000 Hz)
        shutdown_event: Optional event to signal shutdown
    """
    state = MockSimulationState()
    dt = 1.0 / target_hz  # Time step per frame

    print(f"[SIM] Mock simulation loop starting (target: {target_hz} Hz)")

    while True:
        loop_start = time.perf_counter()

        # Track FPS
        fps_counter.tick()

        # ====================================================================
        # 1. Command Processing
        # ====================================================================

        # Process all pending commands (non-blocking)
        try:
            while True:
                command = command_queue.get_nowait()

                # Handle shutdown
                if isinstance(command, ShutdownCommand):
                    print("[SIM] Received ShutdownCommand, exiting loop")
                    return

                # Handle playback control
                state.handle_command(command)

        except queue.Empty:
            pass

        # Check shutdown event if provided
        if shutdown_event is not None and shutdown_event.is_set():
            print("[SIM] Shutdown event set, exiting loop")
            return

        # ====================================================================
        # 2. Simulation Step (if playing or step requested)
        # ====================================================================

        if state.should_advance():
            state.advance(dt)

        # ====================================================================
        # 3. Frame Buffer Write (random RGBA data)
        # ====================================================================

        # Generate random frame: RGBA float32 [0..1]
        # Use simulation time to create animated patterns
        width = frame_buffer.width
        height = frame_buffer.height

        # Create animated gradient based on sim time
        x = np.linspace(0, 1, width, dtype=np.float32)
        y = np.linspace(0, 1, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # Animated color channels
        phase = state.sim_time * 2.0  # Animation speed
        r = 0.5 + 0.5 * np.sin(xx * 4 + phase)
        g = 0.5 + 0.5 * np.sin(yy * 4 + phase)
        b = 0.5 + 0.5 * np.sin((xx + yy) * 4 + phase)
        a = np.ones((height, width), dtype=np.float32)  # Full opacity

        # Stack into RGBA (H, W, 4)
        frame = np.stack([r, g, b, a], axis=-1).astype(np.float32)

        # Write to shared frame buffer
        frame_buffer.write(frame)

        # ====================================================================
        # 4. Plot Buffer Write (random time-series data)
        # ====================================================================

        # Generate random metric value (simulated FPS or other metric)
        # Use sine wave + noise for realistic-looking data
        base_value = 60.0 + 10.0 * np.sin(state.sim_time * 0.5)
        noise = np.random.normal(0, 2.0)
        metric_value = base_value + noise

        plot_buffer.append(timestamp=state.sim_time, value=metric_value)

        # ====================================================================
        # 5. Event Emission (periodic status events)
        # ====================================================================

        # Emit status event every 60 frames (~60ms @ 1000 Hz)
        if state.frame_count % 60 == 0:
            # Could emit custom events here, but for Phase 1 mock we skip
            # to keep things simple
            pass

        # ====================================================================
        # 6. Rate Limiting (sleep to maintain target Hz)
        # ====================================================================

        loop_duration = time.perf_counter() - loop_start
        sleep_time = dt - loop_duration

        if sleep_time > 0:
            time.sleep(sleep_time)
        # If we're running slow, don't sleep (best-effort timing)


def start_mock_sim_thread(
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    fps_counter,  # FPSCounter instance
    target_hz: float = 1000.0,
) -> Tuple[threading.Thread, threading.Event]:
    """
    Start mock simulation thread.

    Args:
        command_queue: Commands from GUI thread
        event_queue: Events to GUI thread
        frame_buffer: Shared frame buffer
        plot_buffer: Plot data buffer
        fps_counter: FPSCounter for simulation FPS tracking
        target_hz: Target loop frequency (default 1000 Hz)

    Returns:
        (thread, shutdown_event) tuple
    """
    shutdown_event = threading.Event()

    thread = threading.Thread(
        target=mock_sim_loop,
        args=(command_queue, event_queue, frame_buffer, plot_buffer, fps_counter, target_hz, shutdown_event),
        name="MockSimThread",
        daemon=True,
    )

    thread.start()
    print(f"[MAIN] Mock simulation thread started: {thread.name}")

    return thread, shutdown_event


# ============================================================================
# Genesis Simulation Functions (Phase 2)
# ============================================================================

def render_genesis_frame(scene, camera, frame_buffer):
    """
    Render single Genesis frame and write to frame buffer.

    This function:
    1. Calls camera.render() to get Genesis frame
    2. Converts to DPG texture format (float32 RGBA [0..1] flattened)
    3. Writes to shared frame buffer

    Constitutional Compliance:
    - Reads/writes shared FrameBuffer with lock (Principle IV)
    - Output format: float32 RGBA [0..1] flattened (Principle V)

    Args:
        scene: Genesis scene instance
        camera: Genesis camera instance
        frame_buffer: FrameBuffer instance for output

    Returns:
        Genesis frame in native format (for debugging/validation)
    """
    from src.core.ipc import genesis_frame_to_dpg_texture

    # Render frame from Genesis camera
    # Genesis camera.render() returns tuple of (rgb, depth, segmentation, normal)
    # We only need the RGB image (first element)
    render_output = camera.render()

    # Extract RGB frame (first element of tuple)
    if isinstance(render_output, tuple):
        genesis_frame = render_output[0]  # RGB image
    else:
        genesis_frame = render_output

    # Convert to DPG texture format
    dpg_frame = genesis_frame_to_dpg_texture(genesis_frame)

    # Write to shared frame buffer (with lock)
    frame_buffer.write(dpg_frame)

    return genesis_frame


# ============================================================================
# Genesis Simulation Loop (Phase 3: T059-T063)
# ============================================================================

class GenesisSimulationState:
    """
    State machine for Genesis simulation playback control.

    States:
    - PAUSED: Not advancing simulation
    - PLAYING: Continuously advancing simulation
    - STEP: Advance one frame then return to PAUSED

    Constitutional Compliance:
    - Principle I (Init-Main, Run-Threaded)
    - Principle VI (Optimistic UI + Commit on Release)

    Phase 4 Extensions: Property editing with Undo/Redo (T102-T110)
    """

    def __init__(self, scene):
        """
        Initialize simulation state.

        Args:
            scene: Genesis scene object
        """
        # Playback state
        self.is_playing = True  # Start playing by default
        self.step_requested = False
        self.sim_time = 0.0  # Simulation time in seconds
        self.frame_count = 0

        # Property editing state (Phase 4)
        self.scene = scene
        self.undo_stack = UndoStack(max_size=100)

    def handle_command(self, command: BaseCommand):
        """
        Process simulation command.

        Args:
            command: Command to process

        Constitutional Compliance: T102-T103, T107-T108
        - PlayCommand/PauseCommand/StepCommand: Playback control
        - PreviewPropertyCommand: Temporary edit (no Undo)
        - UpdatePropertyCommand: Committed edit (push to Undo stack)
        - UndoCommand/RedoCommand: Undo/Redo operations
        """
        # Playback commands
        if isinstance(command, PlayCommand):
            self.is_playing = True
            self.step_requested = False
            print(f"[SIM] Play command received")
        elif isinstance(command, PauseCommand):
            self.is_playing = False
            self.step_requested = False
            print(f"[SIM] Pause command received")
        elif isinstance(command, StepCommand):
            self.is_playing = False
            self.step_requested = True
            print(f"[SIM] Step command received")

        # Property editing commands (Phase 4)
        elif isinstance(command, PreviewPropertyCommand):
            self._handle_preview_property(command)
        elif isinstance(command, UpdatePropertyCommand):
            self._handle_update_property(command)

        # Undo/Redo commands (Phase 4)
        elif isinstance(command, UndoCommand):
            self._handle_undo()
        elif isinstance(command, RedoCommand):
            self._handle_redo()

    def _handle_preview_property(self, command: PreviewPropertyCommand):
        """
        Handle property preview (no Undo).

        Args:
            command: PreviewPropertyCommand

        Constitutional Compliance: T102
        - Applies temporary property change
        - Does NOT push to Undo stack
        - Provides immediate visual feedback
        """
        try:
            self._set_property_value(command.entity_id, command.property_path, command.value)
            # Note: No Undo stack modification (preview only)
        except Exception as e:
            print(f"[SIM] Preview property failed: {e}")

    def _handle_update_property(self, command: UpdatePropertyCommand):
        """
        Handle property update (with Undo).

        Args:
            command: UpdatePropertyCommand

        Constitutional Compliance: T103, T110
        - Applies committed property change
        - Pushes to Undo stack
        - Clears Redo stack (new edit invalidates redo)
        """
        try:
            # Apply property change
            self._set_property_value(command.entity_id, command.property_path, command.new_value)

            # Push to Undo stack
            self.undo_stack.push(command)

        except Exception as e:
            print(f"[SIM] Update property failed: {e}")

    def _handle_undo(self):
        """
        Handle undo operation.

        Constitutional Compliance: T107
        - Pops from Undo stack
        - Applies old_value
        - Moves command to Redo stack
        """
        command = self.undo_stack.undo()
        if command is None:
            return

        try:
            # Apply old value
            self._set_property_value(command.entity_id, command.property_path, command.old_value)
            print(f"[SIM] Undo: {command.property_path} → {command.old_value}")
        except Exception as e:
            print(f"[SIM] Undo failed: {e}")

    def _handle_redo(self):
        """
        Handle redo operation.

        Constitutional Compliance: T108
        - Pops from Redo stack
        - Applies new_value
        - Moves command back to Undo stack
        """
        command = self.undo_stack.redo()
        if command is None:
            return

        try:
            # Apply new value
            self._set_property_value(command.entity_id, command.property_path, command.new_value)
            print(f"[SIM] Redo: {command.property_path} → {command.new_value}")
        except Exception as e:
            print(f"[SIM] Redo failed: {e}")

    def _set_property_value(self, entity_id: int, property_path: str, value):
        """
        Set entity property value.

        Args:
            entity_id: Entity ID
            property_path: Property path (e.g., "position.x", "position.y", "position.z")
            value: New value

        Constitutional Compliance: T104
        - Property path resolver (nested getattr/setattr)
        - Supports dot-separated paths like "position.x"
        """
        try:
            # Get entity from scene
            # Genesis scene stores entities in a list accessible via scene.entities
            if not hasattr(self.scene, 'entities') or entity_id >= len(self.scene.entities):
                print(f"[SIM] Invalid entity_id: {entity_id}")
                return

            entity = self.scene.entities[entity_id]

            # Parse property path
            path_parts = property_path.split('.')

            if path_parts[0] == 'position':
                # Handle position properties (special case for set_pos)
                # Get current position
                current_pos = entity.get_pos()

                # Convert to list for modification
                if hasattr(current_pos, 'tolist'):
                    pos_list = current_pos.tolist()
                else:
                    pos_list = list(current_pos)

                # Modify specific axis
                if len(path_parts) == 2:
                    axis = path_parts[1].lower()
                    if axis == 'x':
                        pos_list[0] = float(value)
                    elif axis == 'y':
                        pos_list[1] = float(value)
                    elif axis == 'z':
                        pos_list[2] = float(value)
                    else:
                        print(f"[SIM] Unknown axis: {axis}")
                        return

                    # Set new position
                    entity.set_pos(tuple(pos_list))
                    print(f"[SIM] Set entity {entity_id} position: {pos_list}")
                else:
                    print(f"[SIM] Invalid position path: {property_path}")
            else:
                # Generic property path resolver (for future properties)
                obj = entity
                for part in path_parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, path_parts[-1], value)
                print(f"[SIM] Set property: entity={entity_id}, path={property_path}, value={value}")

        except Exception as e:
            print(f"[SIM] Failed to set property: entity={entity_id}, path={property_path}, value={value}, error={e}")
            import traceback
            traceback.print_exc()

    def should_advance(self) -> bool:
        """
        Check if simulation should advance this frame.

        Returns:
            True if should advance (playing or step requested)
        """
        if self.step_requested:
            self.step_requested = False
            return True
        return self.is_playing

    def advance(self, dt: float):
        """
        Advance simulation state.

        Args:
            dt: Time step in seconds (typically 0.001 = 1ms @ 1000 Hz)
        """
        self.sim_time += dt
        self.frame_count += 1


def genesis_sim_loop(
    scene,
    camera,
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    fps_counter,  # FPSCounter instance
    shutdown_event: threading.Event,
    target_hz: float = 1000.0,
):
    """
    Genesis simulation loop running at max FPS on background thread.

    This function runs in a background thread and:
    1. Processes commands from GUI (Play/Pause/Step/Shutdown)
    2. Steps Genesis simulation (scene.step())
    3. Renders camera frames via camera.render()
    4. Converts frames to DPG texture format
    5. Writes frames to shared FrameBuffer
    6. Emits events back to GUI

    Constitutional Compliance:
    - Runs on background thread (Principle I, II)
    - Uses queue.Queue for commands (Principle IV)
    - Writes to shared numpy.ndarray + Lock for frames (Principle IV)
    - Genesis/Taichi contexts created on main thread before thread start (Principle I)

    Args:
        scene: Genesis scene instance (created on main thread)
        camera: Genesis camera instance (created on main thread)
        command_queue: Commands from GUI thread
        event_queue: Events to GUI thread
        frame_buffer: Shared frame buffer for rendered frames
        plot_buffer: Circular buffer for time-series data
        fps_counter: FPSCounter instance for performance tracking
        shutdown_event: Event to signal shutdown
        target_hz: Target loop frequency (default 1000 Hz, but may run slower)
    """
    state = GenesisSimulationState(scene)
    dt = 1.0 / target_hz  # Time step per frame (typically 0.001s = 1ms)

    print(f"[SIM] Genesis simulation loop starting (target: {target_hz} Hz)")

    while True:
        loop_start = time.perf_counter()

        # Track FPS
        fps_counter.tick()

        # ====================================================================
        # 1. Check Shutdown Event (T062)
        # ====================================================================

        if shutdown_event.is_set():
            print("[SIM] Shutdown event detected, exiting loop")
            break

        # ====================================================================
        # 2. Command Processing (T062)
        # ====================================================================

        # Process all pending commands with timeout (non-blocking)
        try:
            command = command_queue.get(timeout=0.01)  # 10ms timeout

            # Handle shutdown
            if isinstance(command, ShutdownCommand):
                print("[SIM] Received ShutdownCommand, exiting loop")
                break

            # Handle playback control
            state.handle_command(command)

        except queue.Empty:
            pass

        # ====================================================================
        # 3. Simulation Step (if playing/stepping)
        # ====================================================================

        if state.should_advance():
            # Step Genesis simulation
            scene.step()

            # Render frame and write to buffer (T075: Frame skip logic)
            # Render every frame for now - GUI reads latest frame at 60 FPS
            # If sim FPS >> 60, GUI will naturally skip intermediate frames
            # Future optimization: render every Nth frame based on FPS ratio
            render_genesis_frame(scene, camera, frame_buffer)

            # Advance state
            state.advance(dt)

        # ====================================================================
        # 4. Rate Limiting (optional - let sim run at max FPS)
        # ====================================================================

        # No sleep - let simulation run at maximum speed
        # GUI will read latest frame at its own 60 FPS rate
        # This creates natural frame skipping when sim FPS >> GUI FPS

    print("[SIM] Genesis simulation loop exited")


def start_genesis_sim_thread(
    scene,
    camera,
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    fps_counter,  # FPSCounter instance
    target_hz: float = 1000.0,
) -> Tuple[threading.Thread, threading.Event]:
    """
    Start Genesis simulation loop in background thread.

    Constitutional Compliance:
    - Genesis/Taichi contexts MUST be created on main thread BEFORE calling this (Principle I)
    - Thread is daemon=True to allow clean shutdown
    - Returns shutdown_event for coordinated shutdown (Principle VIII)

    Args:
        scene: Genesis scene instance (created on main thread)
        camera: Genesis camera instance (created on main thread)
        command_queue: CommandQueue instance
        event_queue: EventQueue instance
        frame_buffer: FrameBuffer instance
        plot_buffer: PlotBuffer instance
        fps_counter: FPSCounter instance
        target_hz: Target loop frequency (default 1000 Hz)

    Returns:
        Tuple of (thread, shutdown_event)
    """
    shutdown_event = threading.Event()

    thread = threading.Thread(
        target=genesis_sim_loop,
        args=(scene, camera, command_queue, event_queue, frame_buffer, plot_buffer, fps_counter, shutdown_event, target_hz),
        name="GenesisSimThread",
        daemon=True,
    )

    thread.start()
    print(f"[MAIN] Genesis simulation thread started: {thread.name}")

    return thread, shutdown_event
