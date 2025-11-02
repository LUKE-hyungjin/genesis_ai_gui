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
)
from src.core.ipc import CommandQueue, EventQueue, FrameBuffer, PlotBuffer


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
    genesis_frame = camera.render()

    # Convert to DPG texture format
    dpg_frame = genesis_frame_to_dpg_texture(genesis_frame)

    # Write to shared frame buffer (with lock)
    frame_buffer.write(dpg_frame)

    return genesis_frame
