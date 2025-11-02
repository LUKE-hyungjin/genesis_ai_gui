"""
Application entry point for Genesis Interactive GUI.

Run with: python -m src

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import sys
import signal

from src.infra.bootstrap import (
    initialize_mock_system,
    initialize_genesis_system,
    initialize_genesis_system_threaded,
    shutdown_system
)
from src.ui.main import run_gui_loop, run_genesis_gui_loop


def main_phase1():
    """
    Main application entry point.

    This function:
    1. Initializes the mock system (Phase 1)
    2. Sets up signal handlers for clean shutdown
    3. Runs the GUI render loop on main thread
    4. Performs cleanup on exit
    """
    print("=" * 70)
    print("Genesis Interactive GUI - Phase 1: Mock Threading")
    print("=" * 70)

    # ========================================================================
    # 1. Initialize System
    # ========================================================================

    state = initialize_mock_system(
        viewport_width=1280,
        viewport_height=720,
        sim_hz=1000.0,
    )

    # ========================================================================
    # 2. Setup Signal Handlers
    # ========================================================================

    def signal_handler(sig, frame):
        """Handle SIGINT (Ctrl+C) gracefully."""
        print("\n[MAIN] SIGINT received, shutting down...")
        shutdown_system(state)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # ========================================================================
    # 3. Run GUI Loop (Main Thread)
    # ========================================================================

    try:
        run_gui_loop(
            command_queue=state.command_queue,
            event_queue=state.event_queue,
            frame_buffer=state.frame_buffer,
            plot_buffer=state.plot_buffer,
            metrics_collector=state.metrics_collector,
            frame_lock=state.frame_lock,
            widget_tags=state.widget_tags,
        )
    except KeyboardInterrupt:
        print("\n[MAIN] KeyboardInterrupt, shutting down...")
    except Exception as e:
        print(f"[MAIN] Error in GUI loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ====================================================================
        # 4. Cleanup
        # ====================================================================
        shutdown_system(state)

    print("=" * 70)
    print("Genesis Interactive GUI - Exited")
    print("=" * 70)


def main_phase2():
    """
    Main application entry point for Phase 2 (Genesis Integration).

    This function:
    1. Initializes Genesis system (single-threaded)
    2. Sets up signal handlers for clean shutdown
    3. Runs the GUI render loop with Genesis rendering on main thread
    4. Performs cleanup on exit

    Phase 2 Note:
    - Single-threaded mode (no background simulation thread yet)
    - Genesis rendering happens in GUI loop (main thread)
    - Phase 3 will add background thread
    """
    print("=" * 70)
    print("Genesis Interactive GUI - Phase 2: Genesis Integration")
    print("=" * 70)

    # ========================================================================
    # 1. Initialize Genesis System
    # ========================================================================

    state = initialize_genesis_system(
        viewport_width=1280,
        viewport_height=720,
    )

    # ========================================================================
    # 2. Setup Signal Handlers
    # ========================================================================

    def signal_handler(sig, frame):
        """Handle SIGINT (Ctrl+C) gracefully."""
        print("\n[MAIN] SIGINT received, shutting down...")
        # For Phase 2, just destroy DPG (no sim thread to join)
        from src.ui.main import destroy_dpg
        destroy_dpg()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # ========================================================================
    # 3. Run GUI Loop with Genesis Rendering (Main Thread)
    # ========================================================================

    try:
        run_genesis_gui_loop(
            scene=state.genesis_scene,
            camera=state.genesis_camera,
            command_queue=state.command_queue,
            event_queue=state.event_queue,
            frame_buffer=state.frame_buffer,
            plot_buffer=state.plot_buffer,
            metrics_collector=state.metrics_collector,
            frame_lock=state.frame_lock,
            widget_tags=state.widget_tags,
        )
    except KeyboardInterrupt:
        print("\n[MAIN] KeyboardInterrupt, shutting down...")
    except Exception as e:
        print(f"[MAIN] Error in GUI loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ====================================================================
        # 4. Cleanup
        # ====================================================================
        from src.ui.main import destroy_dpg
        destroy_dpg()

    print("=" * 70)
    print("Genesis Interactive GUI - Exited")
    print("=" * 70)


def main_phase3():
    """
    Main application entry point for Phase 3 (Dual-Loop Architecture).

    This function:
    1. Initializes Genesis system with background simulation thread
    2. Sets up signal handlers for clean shutdown
    3. Runs the GUI render loop on main thread (independent from sim)
    4. Performs cleanup on exit

    Phase 3 Features:
    - Dual-loop architecture: GUI (60 FPS) + Sim (max FPS) independent
    - Background simulation thread with Genesis
    - Playback control via commands (Play/Pause/Step)
    - Clean shutdown with thread coordination

    Constitutional Compliance:
    - All Genesis/Taichi contexts initialized on main thread BEFORE thread start
    - Simulation runs on background thread
    - GUI runs on main thread
    """
    # No header print here - initialize_genesis_system_threaded() prints it

    # ========================================================================
    # 1. Initialize Genesis System with Background Thread
    # ========================================================================

    state = initialize_genesis_system_threaded(
        viewport_width=1280,
        viewport_height=720,
        sim_hz=1000.0,
    )

    # ========================================================================
    # 2. Setup Signal Handlers
    # ========================================================================

    def signal_handler(sig, frame):
        """Handle SIGINT (Ctrl+C) gracefully."""
        print("\n[MAIN] SIGINT received, shutting down...")
        shutdown_system(state)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # ========================================================================
    # 3. Run GUI Loop (Main Thread) - Sim runs independently on background
    # ========================================================================

    try:
        run_gui_loop(
            command_queue=state.command_queue,
            event_queue=state.event_queue,
            frame_buffer=state.frame_buffer,
            plot_buffer=state.plot_buffer,
            metrics_collector=state.metrics_collector,
            frame_lock=state.frame_lock,
            widget_tags=state.widget_tags,
        )
    except KeyboardInterrupt:
        print("\n[MAIN] KeyboardInterrupt, shutting down...")
    except Exception as e:
        print(f"[MAIN] Error in GUI loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ====================================================================
        # 4. Cleanup
        # ====================================================================
        shutdown_system(state)

    print("=" * 70)
    print("Genesis Interactive GUI - Exited")
    print("=" * 70)


if __name__ == "__main__":
    # Phase 3: Dual-Loop Architecture (threaded Genesis)
    main_phase3()

    # Phase 2: Genesis Integration (single-threaded)
    # main_phase2()

    # Phase 1: Mock Threading
    # main_phase1()
