"""
Main GUI module for DearPyGui interface.

This module implements the GUI thread initialization, main window layout,
playback controls, and render loop.

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import dearpygui.dearpygui as dpg
import time
import queue
from typing import Optional, Callable, Dict

from src.core.commands import (
    PlayCommand,
    PauseCommand,
    StepCommand,
    ShutdownCommand,
    UndoCommand,
    RedoCommand,
    EntitySelectedEvent,
    WidgetUpdateEvent,
    LogEvent,
    PropertyChangedEvent,
    LogLevel,
)
from src.core.ipc import CommandQueue, EventQueue, FrameBuffer, PlotBuffer
from src.infra.metrics import FPSCounter, MetricsCollector
from src.ui.viewport import create_viewport, update_viewport
from src.ui.scene_tree import create_scene_tree
from src.ui.inspector import create_property_inspector


# ============================================================================
# DPG Context Initialization
# ============================================================================

def initialize_dpg(width: int = 1280, height: int = 720):
    """
    Initialize DearPyGui context and main window.

    Constitutional Compliance:
    - Must run on main thread (Principle I)

    Args:
        width: Window width in pixels (default 1280)
        height: Window height in pixels (default 720)
    """
    dpg.create_context()

    # Configure viewport
    dpg.create_viewport(
        title="Genesis Interactive GUI",
        width=width,
        height=height,
        resizable=True,
    )

    dpg.setup_dearpygui()
    dpg.show_viewport()

    print(f"[GUI] DearPyGui initialized ({width}x{height})")


def destroy_dpg():
    """
    Destroy DearPyGui context and cleanup.

    Constitutional Compliance:
    - Must run on main thread (Principle I)
    """
    dpg.destroy_context()
    print("[GUI] DearPyGui destroyed")


# ============================================================================
# Main Window Layout
# ============================================================================

def create_main_window(
    command_queue: CommandQueue,
    frame_buffer: FrameBuffer,
    metrics_collector: MetricsCollector,
    event_queue: Optional[EventQueue] = None,
    genesis_scene=None,
    on_shutdown: Optional[Callable] = None,
    scene_lock=None,
) -> Dict[str, str]:
    """
    Create main window with viewport, controls, metrics, and Phase 4 widgets.

    Layout (Phase 4 enabled if event_queue provided):
    - Left: Scene Tree (300px width) - Phase 4 only
    - Center: 3D Viewport (fills remaining space)
    - Right: Control panel (300px width) with playback controls, metrics, inspector

    Layout (Phase 3 fallback if event_queue is None):
    - Left: 3D Viewport (1280x720)
    - Right: Control panel (300px width) with playback controls and metrics

    Args:
        command_queue: Command queue for sending commands to sim thread
        frame_buffer: Frame buffer for viewport updates
        metrics_collector: Metrics collector for dashboard
        event_queue: Event queue for Phase 4 entity selection events (None = Phase 3 mode)
        genesis_scene: Genesis scene reference for Phase 4 scene tree
        on_shutdown: Callback to trigger on exit button
        scene_lock: Lock for thread-safe scene state reads in inspector

    Returns:
        Dictionary with widget tags for later access
    """
    tags = {}

    # Determine if Phase 4 is enabled
    phase4_enabled = event_queue is not None

    with dpg.window(
        label="Genesis Interactive GUI - Phase 4" if phase4_enabled else "Genesis Interactive GUI - Phase 3",
        tag="main_window",
        width=1280,
        height=720,
        no_close=True,
        no_collapse=True,
    ):
        with dpg.group(horizontal=True):
            # ================================================================
            # Phase 4: Three-panel layout (Scene Tree | Viewport | Controls)
            # Phase 3: Single viewport (full width)
            # ================================================================

            if phase4_enabled:
                # ============================================================
                # Left Panel: Scene Tree (300px)
                # ============================================================
                with dpg.child_window(
                    width=300,
                    height=-1,
                    tag="scene_tree_panel",
                    border=True,
                ):
                    dpg.add_text("Scene Tree", color=(255, 255, 0))
                    dpg.add_separator()

                    # Create scene tree widget (callback wired after inspector creation)
                    scene_tree_widget = create_scene_tree(
                        parent_tag="scene_tree_panel",
                        width=280,
                        height=600,
                    )

                    # Populate scene tree if genesis_scene provided
                    if genesis_scene is not None:
                        scene_tree_widget.populate_from_scene(genesis_scene)

                    tags["scene_tree_widget"] = scene_tree_widget

            # ================================================================
            # Center Panel: Viewport
            # ================================================================

            # Viewport configuration
            viewport_texture_width = 1280
            viewport_texture_height = 720

            if phase4_enabled:
                # Phase 4: Viewport fills remaining space between left and right panels
                # Available: 1280 - 300 (left) - 300 (right) = 680px
                viewport_panel_width = 680
                viewport_image_width = 680
                viewport_image_height = 382  # 680 / (16/9) ≈ 382

                # Wrap viewport in a child_window to properly participate in horizontal layout
                with dpg.child_window(
                    width=viewport_panel_width,  # Fixed width to match available space
                    height=-1,
                    tag="viewport_panel",
                    border=False,
                ):
                    viewport_tag = create_viewport(
                        width=viewport_texture_width,
                        height=viewport_texture_height,
                        parent="viewport_panel",
                        tag="main_viewport",
                        display_width=viewport_image_width,
                        display_height=viewport_image_height,
                    )
                    tags["viewport"] = viewport_tag
            else:
                # Phase 3: Full-width viewport (no side panels)
                viewport_tag = create_viewport(
                    width=viewport_texture_width,
                    height=viewport_texture_height,
                    parent="main_window",
                    tag="main_viewport",
                )
                tags["viewport"] = viewport_tag

            # ================================================================
            # Right Panel: Control Panel (Phase 3 & 4)
            # ================================================================

            with dpg.child_window(
                width=300,
                height=-1,
                tag="control_panel",
                border=True,
            ):
                # ============================================================
                # Playback Controls
                # ============================================================

                dpg.add_text("Playback Controls", color=(255, 255, 0))
                dpg.add_separator()

                # Play button
                def on_play():
                    command_queue.put(PlayCommand())
                    print("[GUI] Sent PlayCommand")

                dpg.add_button(
                    label="Play",
                    callback=on_play,
                    width=-1,
                    tag="play_button",
                )

                # Pause button
                def on_pause():
                    command_queue.put(PauseCommand())
                    print("[GUI] Sent PauseCommand")

                dpg.add_button(
                    label="Pause",
                    callback=on_pause,
                    width=-1,
                    tag="pause_button",
                )

                # Step button
                def on_step():
                    command_queue.put(StepCommand())
                    print("[GUI] Sent StepCommand")

                dpg.add_button(
                    label="Step",
                    callback=on_step,
                    width=-1,
                    tag="step_button",
                )

                dpg.add_separator()

                # ============================================================
                # Metrics Dashboard
                # ============================================================

                dpg.add_text("Performance Metrics", color=(255, 255, 0))
                dpg.add_separator()

                # GUI FPS
                dpg.add_text("GUI FPS: 0.0", tag="gui_fps_label")
                tags["gui_fps_label"] = "gui_fps_label"

                # Sim FPS
                dpg.add_text("Sim FPS: 0.0", tag="sim_fps_label")
                tags["sim_fps_label"] = "sim_fps_label"

                # Frame p95
                dpg.add_text("Frame p95: 0.00ms", tag="frame_p95_label")
                tags["frame_p95_label"] = "frame_p95_label"

                # Lock p95
                dpg.add_text("Lock p95: 0.00ms", tag="lock_p95_label")
                tags["lock_p95_label"] = "lock_p95_label"

                # Command queue depth
                dpg.add_text("Cmd Queue: 0", tag="cmd_queue_label")
                tags["cmd_queue_label"] = "cmd_queue_label"

                # Event queue depth
                dpg.add_text("Evt Queue: 0", tag="evt_queue_label")
                tags["evt_queue_label"] = "evt_queue_label"

                # Plot buffer utilization
                dpg.add_text("Plot Buffer: 0.0%", tag="plot_buffer_label")
                tags["plot_buffer_label"] = "plot_buffer_label"

                dpg.add_separator()

                # ============================================================
                # Property Inspector (Phase 4 only)
                # ============================================================

                if phase4_enabled:
                    dpg.add_text("Property Inspector", color=(255, 255, 0))
                    dpg.add_separator()

                    # Create property inspector widget
                    inspector_widget = create_property_inspector(
                        parent_tag="control_panel",
                        command_queue=command_queue,
                        width=280,
                        height=200,
                        scene_lock=scene_lock,
                    )

                    # Set scene reference if available
                    if genesis_scene is not None:
                        inspector_widget.set_scene_reference(genesis_scene)

                    tags["inspector_widget"] = inspector_widget

                    dpg.add_separator()

                # ============================================================
                # Exit Button
                # ============================================================

                def on_exit():
                    print("[GUI] Exit button pressed")
                    if on_shutdown:
                        on_shutdown()
                    # Stop DPG render loop to trigger clean shutdown
                    dpg.stop_dearpygui()

                dpg.add_button(
                    label="Exit",
                    callback=on_exit,
                    width=-1,
                    tag="exit_button",
                )

    # ====================================================================
    # Wire Scene Tree → Inspector (direct callback, no event queue)
    # ====================================================================

    if phase4_enabled:
        _scene_tree = tags.get("scene_tree_widget")
        _inspector = tags.get("inspector_widget")

        if _scene_tree is not None and _inspector is not None:
            def _on_entity_selected(entity_id):
                if entity_id is not None:
                    _inspector.populate_inspector(entity_id)
                else:
                    _inspector.clear()

            _scene_tree.set_on_select(_on_entity_selected)

    dpg.set_primary_window("main_window", True)
    tags["main_window"] = "main_window"

    phase_str = "Phase 4" if phase4_enabled else "Phase 3"
    print(f"[GUI] Main window created ({phase_str})")
    return tags


# ============================================================================
# GUI Render Loop
# ============================================================================

def run_gui_loop(
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    metrics_collector: MetricsCollector,
    frame_lock,  # TimedLock instance
    widget_tags: Dict[str, str],
):
    """
    Main GUI render loop (runs on main thread).

    This function:
    1. Processes events from simulation thread
    2. Updates viewport texture from frame buffer
    3. Updates metrics dashboard
    4. Renders DPG frame

    Constitutional Compliance:
    - Runs on main thread (Principle I)
    - Processes events from queue.Queue (Principle IV)
    - Reads from shared FrameBuffer with Lock (Principle IV)

    Performance Target:
    - 60 FPS GUI (16.7ms frame budget)

    Args:
        command_queue: Command queue (for metrics)
        event_queue: Event queue from sim thread
        frame_buffer: Frame buffer for viewport
        plot_buffer: Plot buffer for metrics
        metrics_collector: Metrics collector
        frame_lock: TimedLock for frame buffer access timing
        widget_tags: Widget tags from create_main_window
    """
    gui_fps_counter = metrics_collector.gui_fps_counter

    # Setup keyboard shortcuts (Phase 4)
    setup_keyboard_shortcuts(command_queue)

    # Get Phase 4 widgets if present
    scene_tree_widget = widget_tags.get("scene_tree_widget")
    inspector_widget = widget_tags.get("inspector_widget")

    print("[GUI] Starting render loop")

    while dpg.is_dearpygui_running():
        gui_fps_counter.tick()

        # ====================================================================
        # 1. Process Events from Simulation Thread
        # ====================================================================

        # Process all pending events (non-blocking)
        # Phase 4: Use process_event_queue helper (T111)
        process_event_queue(event_queue, scene_tree_widget, inspector_widget)

        # ====================================================================
        # 2. Update Viewport from Frame Buffer
        # ====================================================================

        # FrameBuffer.read() uses its internal lock (shared TimedLock)
        # so no external lock wrapping needed here
        update_viewport(widget_tags["viewport"], frame_buffer)

        # ====================================================================
        # 3. Refresh Property Inspector (Phase 4)
        # ====================================================================

        # Update inspector property values to reflect current scene state
        if inspector_widget is not None:
            inspector_widget.refresh()

        # ====================================================================
        # 4. Update Metrics Dashboard
        # ====================================================================

        # Collect metrics
        metrics = metrics_collector.collect(
            command_queue=command_queue,
            event_queue=event_queue,
            frame_lock=frame_lock,
            plot_buffer=plot_buffer,
        )

        # Update labels
        dpg.set_value(widget_tags["gui_fps_label"], f"GUI FPS: {metrics['gui_fps']:.1f}")
        dpg.set_value(widget_tags["sim_fps_label"], f"Sim FPS: {metrics['sim_fps']:.1f}")
        dpg.set_value(widget_tags["frame_p95_label"], f"Frame p95: {metrics['gui_frame_p95_ms']:.2f}ms")
        dpg.set_value(widget_tags["lock_p95_label"], f"Lock p95: {metrics['frame_lock_p95_ms']:.2f}ms")
        dpg.set_value(widget_tags["cmd_queue_label"], f"Cmd Queue: {metrics['command_queue_depth']}")
        dpg.set_value(widget_tags["evt_queue_label"], f"Evt Queue: {metrics['event_queue_depth']}")
        dpg.set_value(widget_tags["plot_buffer_label"], f"Plot Buffer: {metrics['plot_buffer_util']*100:.1f}%")

        # ====================================================================
        # 5. Render DPG Frame
        # ====================================================================

        dpg.render_dearpygui_frame()

    print("[GUI] Render loop exited")


# ============================================================================
# Genesis GUI Render Loop (Phase 2)
# ============================================================================

def run_genesis_gui_loop(
    scene,  # Genesis Scene instance
    camera,  # Genesis Camera instance
    command_queue: CommandQueue,
    event_queue: EventQueue,
    frame_buffer: FrameBuffer,
    plot_buffer: PlotBuffer,
    metrics_collector: MetricsCollector,
    frame_lock,  # TimedLock instance
    widget_tags: Dict[str, str],
):
    """
    Genesis GUI render loop for Phase 2 (single-threaded mode).

    This function runs on the main thread and:
    1. Steps Genesis simulation (if playing)
    2. Renders Genesis frame and writes to frame buffer
    3. Updates viewport texture from frame buffer
    4. Updates metrics dashboard
    5. Renders DPG frame

    Constitutional Compliance:
    - Runs on main thread (Principle I)
    - All Genesis operations on main thread (Phase 2 requirement)
    - Reads/writes shared FrameBuffer with Lock (Principle IV)

    Performance Target:
    - 60 FPS GUI (16.7ms frame budget)

    Args:
        scene: Genesis Scene instance
        camera: Genesis Camera instance
        command_queue: Command queue (for future playback controls)
        event_queue: Event queue (for future events)
        frame_buffer: Frame buffer for viewport
        plot_buffer: Plot buffer for metrics
        metrics_collector: Metrics collector
        frame_lock: TimedLock for frame buffer access timing
        widget_tags: Widget tags from create_main_window
    """
    from src.core.sim_loop import render_genesis_frame

    gui_fps_counter = metrics_collector.gui_fps_counter

    print("[GUI] Starting Genesis render loop (Phase 2 single-threaded)")

    frame_count = 0

    while dpg.is_dearpygui_running():
        gui_fps_counter.tick()

        # ====================================================================
        # 1. Step Genesis Simulation (every frame for now)
        # ====================================================================

        # For Phase 2, we step the simulation every GUI frame
        # Phase 3 will move this to background thread
        scene.step()

        # ====================================================================
        # 2. Render Genesis Frame and Update Frame Buffer
        # ====================================================================

        # FrameBuffer.write() uses its internal lock (shared TimedLock)
        render_genesis_frame(scene, camera, frame_buffer)

        # ====================================================================
        # 3. Update Viewport from Frame Buffer
        # ====================================================================

        # FrameBuffer.read() uses its internal lock (shared TimedLock)
        update_viewport(widget_tags["viewport"], frame_buffer)

        # ====================================================================
        # 4. Update Metrics Dashboard
        # ====================================================================

        # Collect metrics (sim FPS will be ~60 since we step every GUI frame)
        metrics = metrics_collector.collect(
            command_queue=command_queue,
            event_queue=event_queue,
            frame_lock=frame_lock,
            plot_buffer=plot_buffer,
        )

        # Update labels
        dpg.set_value(widget_tags["gui_fps_label"], f"GUI FPS: {metrics['gui_fps']:.1f}")
        dpg.set_value(widget_tags["sim_fps_label"], f"Sim FPS: {metrics['sim_fps']:.1f} (Phase 2: locked to GUI)")
        dpg.set_value(widget_tags["frame_p95_label"], f"Frame p95: {metrics['gui_frame_p95_ms']:.2f}ms")
        dpg.set_value(widget_tags["lock_p95_label"], f"Lock p95: {metrics['frame_lock_p95_ms']:.2f}ms")
        dpg.set_value(widget_tags["cmd_queue_label"], f"Cmd Queue: {metrics['command_queue_depth']}")
        dpg.set_value(widget_tags["evt_queue_label"], f"Evt Queue: {metrics['event_queue_depth']}")
        dpg.set_value(widget_tags["plot_buffer_label"], f"Plot Buffer: {metrics['plot_buffer_util']*100:.1f}%")

        # ====================================================================
        # 5. Render DPG Frame
        # ====================================================================

        dpg.render_dearpygui_frame()

        frame_count += 1

        # Log every 60 frames (~1 second)
        if frame_count % 60 == 0:
            print(f"[GUI] Frame {frame_count}: GUI FPS={metrics['gui_fps']:.1f}, Lock p95={metrics['frame_lock_p95_ms']:.2f}ms")

    print("[GUI] Genesis render loop exited")


# ============================================================================
# Phase 4: Event Processing & Keyboard Shortcuts
# ============================================================================

def process_event_queue(event_queue: EventQueue, scene_tree_widget=None, inspector_widget=None):
    """
    Process events from simulation thread.

    Constitutional Compliance: T111-T114
    - WidgetUpdateEvent: Update DPG widget values
    - LogEvent: Append to console log
    - PropertyChangedEvent: Update inspector display
    - EntitySelectedEvent: Handled by scene tree widget

    Args:
        event_queue: Event queue from simulation thread
        scene_tree_widget: Scene tree widget (optional, Phase 4)
        inspector_widget: Property inspector widget (optional, Phase 4)
    """
    events_processed = 0

    while events_processed < 100:  # Limit to prevent infinite loop
        try:
            event = event_queue.get_nowait()
            events_processed += 1

            # WidgetUpdateEvent (T112)
            if isinstance(event, WidgetUpdateEvent):
                if dpg.does_item_exist(event.widget_tag):
                    dpg.set_value(event.widget_tag, event.value)

            # LogEvent (T113)
            elif isinstance(event, LogEvent):
                color = {
                    LogLevel.DEBUG: (150, 150, 150),
                    LogLevel.INFO: (200, 200, 200),
                    LogLevel.WARNING: (255, 200, 0),
                    LogLevel.ERROR: (255, 100, 100),
                }.get(event.level, (200, 200, 200))

                # TODO: Add console window widget in Phase 4+
                print(f"[{event.level.value}] {event.message}")

            # PropertyChangedEvent (T114)
            elif isinstance(event, PropertyChangedEvent):
                if inspector_widget is not None:
                    inspector_widget.update_property_display(
                        event.property_path,
                        event.new_value
                    )

            # EntitySelectedEvent (handled by scene tree, but also update inspector)
            elif isinstance(event, EntitySelectedEvent):
                if inspector_widget is not None:
                    if event.entity_id is not None:
                        inspector_widget.populate_inspector(event.entity_id)
                    else:
                        inspector_widget.clear()

        except queue.Empty:
            break


def setup_keyboard_shortcuts(command_queue: CommandQueue):
    """
    Setup keyboard shortcuts for Undo/Redo.

    Constitutional Compliance: T109
    - Ctrl+Z: Undo
    - Ctrl+Shift+Z: Redo

    Args:
        command_queue: Command queue for sending commands
    """
    with dpg.handler_registry(tag="keyboard_handler"):
        # Undo/Redo commands
        def on_undo():
            command_queue.put(UndoCommand())
            print("[GUI] Sent UndoCommand (Ctrl+Z)")

        def on_redo():
            command_queue.put(RedoCommand())
            print("[GUI] Sent RedoCommand")

        # Ctrl+Z = Undo, Ctrl+Shift+Z = Redo
        def on_z_release():
            ctrl = dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)
            if not ctrl:
                return
            shift = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)
            if shift:
                on_redo()
            else:
                on_undo()

        dpg.add_key_release_handler(
            key=dpg.mvKey_Z,
            callback=lambda: on_z_release(),
        )

        # Ctrl+Y = Redo (alternative shortcut)
        dpg.add_key_release_handler(
            key=dpg.mvKey_Y,
            callback=lambda: on_redo() if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl) else None,
        )

    print("[GUI] Keyboard shortcuts registered (Ctrl+Z=Undo, Ctrl+Shift+Z/Ctrl+Y=Redo)")
