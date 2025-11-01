"""
Application entry point for Genesis Interactive GUI.

Run with: python -m src

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import sys
import signal

from src.infra.bootstrap import initialize_mock_system, shutdown_system
from src.ui.main import run_gui_loop


def main():
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


if __name__ == "__main__":
    main()
