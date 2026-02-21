"""
Smoke test: Verify all modules import correctly.

This test validates that the Phase 1 codebase has no import errors
or syntax issues.
"""

def test_core_commands():
    """Test that core commands module imports."""
    from src.core.commands import (
        PlayCommand,
        PauseCommand,
        StepCommand,
        PreviewPropertyCommand,
        UpdatePropertyCommand,
        UndoCommand,
        RedoCommand,
        RayCastCommand,
        ShutdownCommand,
        EntitySelectedEvent,
        WidgetUpdateEvent,
        CollisionEvent,
        LogEvent,
        LogLevel,
        PlotDataEvent,
        PropertyChangedEvent,
    )
    print("✓ src.core.commands imports successfully")


def test_core_ipc():
    """Test that core IPC module imports."""
    from src.core.ipc import (
        CommandQueue,
        EventQueue,
        FrameBuffer,
        PlotBuffer,
    )
    print("✓ src.core.ipc imports successfully")


def test_core_sim_loop():
    """Test that simulation loop module imports."""
    from src.core.sim_loop import (
        MockSimulationState,
        mock_sim_loop,
        start_mock_sim_thread,
    )
    print("✓ src.core.sim_loop imports successfully")


def test_infra_metrics():
    """Test that metrics module imports."""
    from src.infra.metrics import (
        FPSCounter,
        TimedLock,
        MetricsCollector,
    )
    print("✓ src.infra.metrics imports successfully")


def test_ui_viewport():
    """Test that viewport module imports."""
    from src.ui.viewport import (
        create_viewport,
        update_viewport,
        get_viewport_size,
    )
    print("✓ src.ui.viewport imports successfully")


def test_ui_main():
    """Test that main UI module imports."""
    from src.ui.main import (
        initialize_dpg,
        destroy_dpg,
        create_main_window,
        run_gui_loop,
    )
    print("✓ src.ui.main imports successfully")


def test_ui_plots():
    """Test that plots module imports (Phase 5)."""
    from src.ui.plots import (
        PlotPanelWidget,
        downsample_plot_data,
        SIGNAL_REGISTRY,
    )
    print("✓ src.ui.plots imports successfully")


def test_core_picking():
    """Test that picking module imports (Phase 6)."""
    from src.core.picking import (
        build_view_matrix,
        build_projection_matrix,
        project_to_screen,
        pick_nearest_entity,
    )
    print("✓ src.core.picking imports successfully")


def test_ui_gizmo():
    """Test that gizmo module imports (Phase 6)."""
    from src.ui.gizmo import (
        TransformGizmo,
        AXIS_COLORS,
        AXIS_DIRECTIONS,
    )
    print("✓ src.ui.gizmo imports successfully")


def test_infra_bootstrap():
    """Test that bootstrap module imports."""
    from src.infra.bootstrap import (
        SystemState,
        initialize_mock_system,
        shutdown_system,
        create_exit_handler,
    )
    print("✓ src.infra.bootstrap imports successfully")


def test_main_entry_point():
    """Test that main entry point imports."""
    import src.__main__
    print("✓ src.__main__ imports successfully")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 1 Import Smoke Tests")
    print("=" * 70)

    tests = [
        test_core_commands,
        test_core_ipc,
        test_core_sim_loop,
        test_core_picking,
        test_infra_metrics,
        test_ui_viewport,
        test_ui_main,
        test_ui_plots,
        test_ui_gizmo,
        test_infra_bootstrap,
        test_main_entry_point,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    exit(0 if failed == 0 else 1)
