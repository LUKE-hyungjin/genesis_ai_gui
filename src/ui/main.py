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

from src.core.commands import PlayCommand, PauseCommand, StepCommand, ShutdownCommand
from src.core.ipc import CommandQueue, EventQueue, FrameBuffer, PlotBuffer
from src.infra.metrics import FPSCounter, MetricsCollector
from src.ui.viewport import create_viewport, update_viewport


# ============================================================================
# DPG Context Initialization
# ============================================================================

def initialize_dpg(width: int = 1600, height: int = 900):
    """
    Initialize DearPyGui context and main window.

    Constitutional Compliance:
    - Must run on main thread (Principle I)

    Args:
        width: Window width in pixels (default 1600)
        height: Window height in pixels (default 900)
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
    on_shutdown: Optional[Callable] = None,
) -> Dict[str, str]:
    """
    Create main window with viewport, controls, and metrics.

    Layout:
    - Left: 3D Viewport (1280x720)
    - Right: Control panel (playback controls + metrics dashboard)

    Args:
        command_queue: Command queue for sending commands to sim thread
        frame_buffer: Frame buffer for viewport updates
        metrics_collector: Metrics collector for dashboard
        on_shutdown: Callback to trigger on exit button

    Returns:
        Dictionary with widget tags for later access
    """
    tags = {}

    with dpg.window(
        label="Genesis Interactive GUI",
        tag="main_window",
        width=1600,
        height=900,
        no_close=True,
        no_collapse=True,
    ):
        with dpg.group(horizontal=True):
            # ================================================================
            # Left: Viewport
            # ================================================================

            with dpg.child_window(
                width=1280,
                height=720,
                tag="viewport_container",
            ):
                viewport_tag = create_viewport(
                    width=1280,
                    height=720,
                    parent="viewport_container",
                    tag="main_viewport",
                )
                tags["viewport"] = viewport_tag

            # ================================================================
            # Right: Control Panel
            # ================================================================

            with dpg.child_window(
                width=300,
                height=720,
                tag="control_panel",
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

    dpg.set_primary_window("main_window", True)
    tags["main_window"] = "main_window"

    print("[GUI] Main window created")
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

    print("[GUI] Starting render loop")

    while dpg.is_dearpygui_running():
        gui_fps_counter.tick()

        # ====================================================================
        # 1. Process Events from Simulation Thread
        # ====================================================================

        # Process all pending events (non-blocking)
        try:
            while True:
                event = event_queue.get_nowait()
                # For Phase 1 mock, we don't emit events
                # Future phases will handle EntitySelectedEvent, LogEvent, etc.
        except queue.Empty:
            pass

        # ====================================================================
        # 2. Update Viewport from Frame Buffer
        # ====================================================================

        with frame_lock:
            update_viewport(widget_tags["viewport"], frame_buffer)

        # ====================================================================
        # 3. Update Metrics Dashboard
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
        # 4. Render DPG Frame
        # ====================================================================

        dpg.render_dearpygui_frame()

    print("[GUI] Render loop exited")
