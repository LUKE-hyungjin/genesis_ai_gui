"""
System bootstrap and shutdown for Genesis Interactive GUI.

This module handles initialization and teardown of the entire application,
including IPC setup, thread creation, and resource cleanup.

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import threading
import time
import platform
from typing import Optional, Dict

from src.core.ipc import CommandQueue, EventQueue, FrameBuffer, PlotBuffer
from src.core.commands import ShutdownCommand
from src.core.sim_loop import start_mock_sim_thread
from src.infra.metrics import TimedLock, MetricsCollector
from src.ui.main import initialize_dpg, destroy_dpg, create_main_window, run_gui_loop


# ============================================================================
# Backend Selection (Phase 2: T037-T039)
# ============================================================================

def select_genesis_backend() -> str:
    """
    Select appropriate Genesis/Taichi backend based on operating system.

    Constitutional Compliance:
    - Must run on main thread before any Genesis contexts created (Principle I)

    Backend Selection Matrix:
    - macOS: Metal (primary) → Vulkan (fallback)
    - Linux: CUDA (primary) → Vulkan (fallback)
    - Windows: CUDA (primary) → Vulkan (fallback)

    Returns:
        Backend name string ("metal", "cuda", or "vulkan")

    Raises:
        RuntimeError: If platform unsupported or all backends fail
    """
    import genesis as gs

    system = platform.system()
    print(f"[SYSTEM] Detecting platform: {system}")

    if system == "Darwin":  # macOS
        print("[SYSTEM] macOS detected, trying Metal backend...")
        try:
            gs.init(backend=gs.metal)
            print("[SYSTEM] ✓ Metal backend initialized successfully")
            return "metal"
        except Exception as e:
            print(f"[SYSTEM] ✗ Metal init failed: {e}")
            print("[SYSTEM] Falling back to Vulkan...")
            try:
                gs.init(backend=gs.vulkan)
                print("[SYSTEM] ✓ Vulkan backend initialized successfully")
                return "vulkan"
            except Exception as e2:
                raise RuntimeError(f"All backends failed on macOS. Metal: {e}, Vulkan: {e2}")

    elif system == "Linux":
        print("[SYSTEM] Linux detected, trying CUDA backend...")
        try:
            gs.init(backend=gs.cuda)
            print("[SYSTEM] ✓ CUDA backend initialized successfully")
            return "cuda"
        except Exception as e:
            print(f"[SYSTEM] ✗ CUDA init failed: {e}")
            print("[SYSTEM] Falling back to Vulkan...")
            try:
                gs.init(backend=gs.vulkan)
                print("[SYSTEM] ✓ Vulkan backend initialized successfully")
                return "vulkan"
            except Exception as e2:
                raise RuntimeError(f"All backends failed on Linux. CUDA: {e}, Vulkan: {e2}")

    elif system == "Windows":
        print("[SYSTEM] Windows detected, trying CUDA backend...")
        try:
            gs.init(backend=gs.cuda)
            print("[SYSTEM] ✓ CUDA backend initialized successfully")
            return "cuda"
        except Exception as e:
            print(f"[SYSTEM] ✗ CUDA init failed: {e}")
            print("[SYSTEM] Falling back to Vulkan...")
            try:
                gs.init(backend=gs.vulkan)
                print("[SYSTEM] ✓ Vulkan backend initialized successfully")
                return "vulkan"
            except Exception as e2:
                raise RuntimeError(f"All backends failed on Windows. CUDA: {e}, Vulkan: {e2}")

    else:
        raise RuntimeError(f"Unsupported platform: {system}")


# ============================================================================
# System State Container
# ============================================================================

class SystemState:
    """
    Container for all system components.

    This class holds references to all IPC primitives, threads, and metrics
    for coordinated shutdown.
    """

    def __init__(self):
        """Initialize empty system state."""
        # IPC primitives
        self.command_queue: Optional[CommandQueue] = None
        self.event_queue: Optional[EventQueue] = None
        self.frame_buffer: Optional[FrameBuffer] = None
        self.plot_buffers: Optional[Dict[str, PlotBuffer]] = None

        # Thread management
        self.sim_thread: Optional[threading.Thread] = None
        self.shutdown_event: Optional[threading.Event] = None

        # Metrics
        self.frame_lock: Optional[TimedLock] = None
        self.scene_lock: Optional[threading.Lock] = None
        self.metrics_collector: Optional[MetricsCollector] = None

        # GUI
        self.widget_tags: Dict[str, str] = {}

        # Genesis (Phase 2+)
        self.genesis_scene = None
        self.genesis_camera = None
        self.backend: Optional[str] = None

        print("[SYSTEM] SystemState initialized")


# ============================================================================
# Mock System Initialization (Phase 1)
# ============================================================================

def initialize_mock_system(
    viewport_width: int = 1280,
    viewport_height: int = 720,
    sim_hz: float = 1000.0,
) -> SystemState:
    """
    Initialize mock system for Phase 1 validation.

    This function:
    1. Creates IPC primitives (queues, buffers)
    2. Initializes metrics infrastructure
    3. Starts mock simulation thread
    4. Initializes DPG GUI on main thread
    5. Creates main window with controls

    Constitutional Compliance:
    - Main thread creates all contexts (Principle I)
    - Simulation runs on background thread (Principle I)

    Args:
        viewport_width: Viewport width in pixels (default 1280)
        viewport_height: Viewport height in pixels (default 720)
        sim_hz: Simulation loop target frequency (default 1000 Hz)

    Returns:
        SystemState with all initialized components
    """
    state = SystemState()

    print("[SYSTEM] Initializing mock system...")
    print(f"[SYSTEM] Viewport: {viewport_width}x{viewport_height}")
    print(f"[SYSTEM] Sim target: {sim_hz} Hz")

    # ========================================================================
    # 1. Initialize Metrics Infrastructure (before IPC so TimedLock can be shared)
    # ========================================================================

    state.frame_lock = TimedLock(threading.Lock(), window_size=1000)
    state.scene_lock = threading.Lock()
    state.metrics_collector = MetricsCollector()

    print("[SYSTEM] Metrics infrastructure initialized")

    # ========================================================================
    # 2. Create IPC Primitives (FrameBuffer uses shared TimedLock)
    # ========================================================================

    state.command_queue = CommandQueue(maxsize=1000)
    state.event_queue = EventQueue(maxsize=1000)
    state.frame_buffer = FrameBuffer(width=viewport_width, height=viewport_height, lock=state.frame_lock)
    state.plot_buffers = {
        "kinetic_energy": PlotBuffer(maxlen=10000),
        "sim_fps": PlotBuffer(maxlen=10000),
    }

    print("[SYSTEM] IPC primitives created")

    # ========================================================================
    # 3. Start Mock Simulation Thread
    # ========================================================================

    state.sim_thread, state.shutdown_event = start_mock_sim_thread(
        command_queue=state.command_queue,
        event_queue=state.event_queue,
        frame_buffer=state.frame_buffer,
        plot_buffers=state.plot_buffers,
        fps_counter=state.metrics_collector.sim_fps_counter,
        target_hz=sim_hz,
    )

    print("[SYSTEM] Mock simulation thread started")

    # ========================================================================
    # 4. Initialize DPG GUI (Main Thread)
    # ========================================================================

    initialize_dpg(width=1280, height=720)

    print("[SYSTEM] DPG initialized")

    # ========================================================================
    # 5. Create Main Window
    # ========================================================================

    def on_shutdown():
        """Shutdown callback from GUI exit button."""
        print("[SYSTEM] Shutdown requested from GUI")
        # Signal shutdown via command
        state.command_queue.put(ShutdownCommand())

    state.widget_tags = create_main_window(
        command_queue=state.command_queue,
        frame_buffer=state.frame_buffer,
        metrics_collector=state.metrics_collector,
        on_shutdown=on_shutdown,
        scene_lock=state.scene_lock,
    )

    print("[SYSTEM] Main window created")
    print("[SYSTEM] Mock system initialization complete")

    return state


# ============================================================================
# Genesis System Initialization (Phase 2)
# ============================================================================

def initialize_genesis_system(
    viewport_width: int = 1280,
    viewport_height: int = 720,
) -> SystemState:
    """
    Initialize Genesis system for Phase 2 validation.

    This function (Phase 2 - Single-threaded Genesis integration):
    1. Selects and initializes Genesis backend (Metal/CUDA/Vulkan)
    2. Creates Genesis scene and test objects
    3. Creates Genesis camera
    4. Creates IPC primitives (queues, buffers)
    5. Initializes metrics infrastructure
    6. Initializes DPG GUI on main thread
    7. Creates main window with controls

    Constitutional Compliance:
    - ALL Genesis/Taichi contexts created on main thread (Principle I)
    - No background thread yet in Phase 2 (single-threaded validation first)
    - Phase 3 will add background thread

    Args:
        viewport_width: Viewport width in pixels (default 1280)
        viewport_height: Viewport height in pixels (default 720)

    Returns:
        SystemState with all initialized components
    """
    import genesis as gs
    from src.core.scene_setup import create_test_scene, create_camera

    state = SystemState()

    print("[SYSTEM] Initializing Genesis system (Phase 2)...")
    print(f"[SYSTEM] Viewport: {viewport_width}x{viewport_height}")

    # ========================================================================
    # 1. Select and Initialize Genesis Backend (T037-T039)
    # ========================================================================

    state.backend = select_genesis_backend()
    print(f"[SYSTEM] Backend selected: {state.backend}")

    # ========================================================================
    # 2. Create Genesis Scene (T040-T041)
    # ========================================================================

    print("[SYSTEM] Creating Genesis scene...")
    state.genesis_scene = gs.Scene(show_viewer=False)
    create_test_scene(state.genesis_scene)
    print("[SYSTEM] Genesis scene created")

    # ========================================================================
    # 3. Create Genesis Camera (T041)
    # ========================================================================

    state.genesis_camera = create_camera(
        state.genesis_scene,
        width=viewport_width,
        height=viewport_height
    )

    # ========================================================================
    # 4. Build Scene (required before rendering)
    # ========================================================================

    print("[SYSTEM] Building Genesis scene...")
    state.genesis_scene.build()
    print("[SYSTEM] Genesis scene built successfully")

    # ========================================================================
    # 5. Initialize Metrics Infrastructure (before IPC so TimedLock can be shared)
    # ========================================================================

    state.frame_lock = TimedLock(threading.Lock(), window_size=1000)
    state.scene_lock = threading.Lock()
    state.metrics_collector = MetricsCollector()

    print("[SYSTEM] Metrics infrastructure initialized")

    # ========================================================================
    # 6. Create IPC Primitives (FrameBuffer uses shared TimedLock)
    # ========================================================================

    state.command_queue = CommandQueue(maxsize=1000)
    state.event_queue = EventQueue(maxsize=1000)
    state.frame_buffer = FrameBuffer(width=viewport_width, height=viewport_height, lock=state.frame_lock)
    state.plot_buffers = {
        "kinetic_energy": PlotBuffer(maxlen=10000),
        "sim_fps": PlotBuffer(maxlen=10000),
    }

    print("[SYSTEM] IPC primitives created")

    # ========================================================================
    # 7. Initialize DPG GUI (Main Thread)
    # ========================================================================

    initialize_dpg(width=1280, height=720)

    print("[SYSTEM] DPG initialized")

    # ========================================================================
    # 8. Create Main Window
    # ========================================================================

    def on_shutdown():
        """Shutdown callback from GUI exit button."""
        print("[SYSTEM] Shutdown requested from GUI")
        # For Phase 2, we don't have a simulation thread yet
        # Just stop DPG
        import dearpygui.dearpygui as dpg
        dpg.stop_dearpygui()

    state.widget_tags = create_main_window(
        command_queue=state.command_queue,
        frame_buffer=state.frame_buffer,
        metrics_collector=state.metrics_collector,
        on_shutdown=on_shutdown,
        scene_lock=state.scene_lock,
    )

    print("[SYSTEM] Main window created")
    print("[SYSTEM] Genesis system initialization complete")
    print("[SYSTEM] NOTE: Phase 2 single-threaded mode - no background simulation thread")

    return state


# ============================================================================
# Genesis System Initialization with Threading (Phase 3: T059-T063)
# ============================================================================

def initialize_genesis_system_threaded(
    viewport_width: int = 1280,
    viewport_height: int = 720,
    sim_hz: float = 1000.0,
) -> SystemState:
    """
    Initialize Genesis system with background simulation thread (Phase 3).

    This function (Phase 3 - Threaded Genesis):
    1. Selects and initializes Genesis backend (Metal/CUDA/Vulkan) ON MAIN THREAD
    2. Creates Genesis scene and test objects ON MAIN THREAD
    3. Creates Genesis camera ON MAIN THREAD
    4. Builds scene ON MAIN THREAD (required before rendering)
    5. Creates IPC primitives
    6. Initializes metrics infrastructure
    7. Starts Genesis simulation thread (AFTER all contexts created)
    8. Initializes DPG GUI on main thread
    9. Creates main window with controls

    Constitutional Compliance:
    - ALL Genesis/Taichi contexts created on main thread BEFORE thread start (Principle I)
    - Simulation runs on background thread (Principle II)
    - Threading.Event for coordinated shutdown (Principle VIII)

    Args:
        viewport_width: Viewport width in pixels (default 1280)
        viewport_height: Viewport height in pixels (default 720)
        sim_hz: Simulation loop target frequency (default 1000 Hz)

    Returns:
        SystemState with all initialized components including background thread
    """
    import genesis as gs
    from src.core.scene_setup import create_test_scene, create_camera
    from src.core.sim_loop import start_genesis_sim_thread

    state = SystemState()

    print("=" * 70)
    print("Genesis Interactive GUI - Phase 3: Dual-Loop Architecture")
    print("=" * 70)
    print("[SYSTEM] Initializing Genesis system (Phase 3 - Threaded)...")
    print(f"[SYSTEM] Viewport: {viewport_width}x{viewport_height}")
    print(f"[SYSTEM] Sim target: {sim_hz} Hz")

    # ========================================================================
    # 1. Select and Initialize Genesis Backend ON MAIN THREAD (T063)
    # ========================================================================

    state.backend = select_genesis_backend()
    print(f"[SYSTEM] Backend selected: {state.backend}")

    # ========================================================================
    # 2. Create Genesis Scene ON MAIN THREAD (T063)
    # ========================================================================

    print("[SYSTEM] Creating Genesis scene...")
    state.genesis_scene = gs.Scene(show_viewer=False)
    create_test_scene(state.genesis_scene)
    print("[SYSTEM] Genesis scene created")

    # ========================================================================
    # 3. Create Genesis Camera ON MAIN THREAD (T063)
    # ========================================================================

    state.genesis_camera = create_camera(
        state.genesis_scene,
        width=viewport_width,
        height=viewport_height
    )

    # ========================================================================
    # 4. Build Scene ON MAIN THREAD (T063)
    # ========================================================================

    print("[SYSTEM] Building Genesis scene...")
    state.genesis_scene.build()
    print("[SYSTEM] Genesis scene built successfully")
    print("[SYSTEM] ✓ All Genesis/Taichi contexts created on main thread")

    # ========================================================================
    # 5. Initialize Metrics Infrastructure (before IPC so TimedLock can be shared)
    # ========================================================================

    state.frame_lock = TimedLock(threading.Lock(), window_size=1000)
    state.scene_lock = threading.Lock()
    state.metrics_collector = MetricsCollector()

    print("[SYSTEM] Metrics infrastructure initialized")

    # ========================================================================
    # 6. Create IPC Primitives (FrameBuffer uses shared TimedLock) (T060)
    # ========================================================================

    state.command_queue = CommandQueue(maxsize=1000)
    state.event_queue = EventQueue(maxsize=1000)
    state.frame_buffer = FrameBuffer(width=viewport_width, height=viewport_height, lock=state.frame_lock)
    state.plot_buffers = {
        "kinetic_energy": PlotBuffer(maxlen=10000),
        "sim_fps": PlotBuffer(maxlen=10000),
    }

    print("[SYSTEM] IPC primitives created")

    # ========================================================================
    # 7. Start Genesis Simulation Thread (T059, T060, T061)
    # ========================================================================

    print("[SYSTEM] Starting Genesis simulation thread...")
    state.sim_thread, state.shutdown_event = start_genesis_sim_thread(
        scene=state.genesis_scene,
        camera=state.genesis_camera,
        command_queue=state.command_queue,
        event_queue=state.event_queue,
        frame_buffer=state.frame_buffer,
        plot_buffers=state.plot_buffers,
        fps_counter=state.metrics_collector.sim_fps_counter,
        scene_lock=state.scene_lock,
        target_hz=sim_hz,
    )

    print("[SYSTEM] ✓ Genesis simulation thread started")

    # ========================================================================
    # 8. Initialize DPG GUI (Main Thread)
    # ========================================================================

    initialize_dpg(width=1280, height=720)

    print("[SYSTEM] DPG initialized")

    # ========================================================================
    # 9. Create Main Window
    # ========================================================================

    def on_shutdown():
        """Shutdown callback from GUI exit button."""
        print("[SYSTEM] Shutdown requested from GUI")
        # Signal shutdown via event
        state.shutdown_event.set()
        # Also send shutdown command
        state.command_queue.put(ShutdownCommand())

    state.widget_tags = create_main_window(
        command_queue=state.command_queue,
        frame_buffer=state.frame_buffer,
        metrics_collector=state.metrics_collector,
        event_queue=state.event_queue,
        genesis_scene=state.genesis_scene,
        on_shutdown=on_shutdown,
        scene_lock=state.scene_lock,
        plot_buffers=state.plot_buffers,
    )

    # Phase 6: Store camera and scene references for gizmo/picking
    state.widget_tags["_camera_ref"] = state.genesis_camera
    state.widget_tags["_genesis_scene_ref"] = state.genesis_scene

    print("[SYSTEM] Main window created")
    print("[SYSTEM] Genesis system initialization complete (Phase 6)")
    print("[SYSTEM] Background thread running - GUI and Sim loops now independent")
    print("=" * 70)

    return state


# ============================================================================
# System Shutdown
# ============================================================================

def shutdown_system(state: SystemState, timeout: float = 2.0):
    """
    Shutdown system and cleanup resources.

    This function:
    1. Sends ShutdownCommand to simulation thread
    2. Waits for simulation thread to exit (with timeout)
    3. Destroys DPG context
    4. Cleans up resources

    Constitutional Compliance:
    - Clean shutdown sequence (Principle I)

    Args:
        state: SystemState to shutdown
        timeout: Max time to wait for thread join (seconds)
    """
    print("[SYSTEM] Starting shutdown sequence...")

    # ========================================================================
    # 1. Signal Simulation Thread to Stop
    # ========================================================================

    if state.command_queue and state.shutdown_event:
        print("[SYSTEM] Sending ShutdownCommand")
        try:
            state.command_queue.put(ShutdownCommand(), timeout=1.0)
        except Exception as e:
            print(f"[SYSTEM] Warning: Failed to send ShutdownCommand: {e}")

        # Also set event as backup
        state.shutdown_event.set()

    # ========================================================================
    # 2. Wait for Simulation Thread
    # ========================================================================

    if state.sim_thread:
        print(f"[SYSTEM] Waiting for simulation thread (timeout: {timeout}s)")
        state.sim_thread.join(timeout=timeout)

        if state.sim_thread.is_alive():
            print("[SYSTEM] Warning: Simulation thread did not exit cleanly")
        else:
            print("[SYSTEM] Simulation thread exited")

    # ========================================================================
    # 3. Destroy DPG Context
    # ========================================================================

    destroy_dpg()

    # ========================================================================
    # 4. Cleanup
    # ========================================================================

    print("[SYSTEM] Shutdown complete")


# ============================================================================
# DPG Exit Handler
# ============================================================================

def create_exit_handler(state: SystemState):
    """
    Create DPG exit handler callback.

    This is registered with DPG to handle window close events.

    Args:
        state: SystemState for shutdown

    Returns:
        Exit handler function
    """
    def exit_handler():
        """Handle DPG exit event."""
        print("[SYSTEM] DPG exit event received")
        shutdown_system(state)

    return exit_handler
