"""
Live signal plotting panel with LTTB downsampling.

This module implements a DPG plot widget that displays real-time
simulation signals (kinetic energy, sim FPS) with efficient downsampling.

Constitutional Compliance:
- Principle III (Explicit Main-Thread Ops): All DPG operations on main thread
- Principle IV (Data Pathway Segregation): Reads from PlotBuffer (deque)
- Principle VII (Performance Targets): Downsample < 2ms for 10k samples
"""

import numpy as np
from typing import Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from src.core.ipc import PlotBuffer

# Try to import tsdownsample for LTTB; fall back to simple stride-based downsampling
try:
    from tsdownsample import LTTBDownsampler
    _HAS_LTTB = True
except ImportError:
    _HAS_LTTB = False


# ============================================================================
# Signal Registry
# ============================================================================

SIGNAL_REGISTRY = {
    "kinetic_energy": {
        "label": "Kinetic Energy",
        "color": (220, 60, 60, 255),   # Red
        "y_label": "Energy (J)",
    },
    "sim_fps": {
        "label": "Sim FPS",
        "color": (60, 200, 60, 255),   # Green
        "y_label": "FPS",
    },
}

MAX_DISPLAY_POINTS = 500


# ============================================================================
# Downsampling (T128-T130)
# ============================================================================

def downsample_plot_data(
    timestamps: np.ndarray,
    values: np.ndarray,
    max_points: int = MAX_DISPLAY_POINTS,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Downsample time-series data for efficient plotting.

    Uses LTTB (Largest-Triangle-Three-Buckets) when tsdownsample is available,
    otherwise falls back to uniform stride-based downsampling.

    Performance Target: < 2ms for 10k samples (Principle VII).

    Args:
        timestamps: 1D array of timestamps
        values: 1D array of signal values
        max_points: Maximum number of output points (default 500)

    Returns:
        (downsampled_timestamps, downsampled_values)
    """
    n = len(timestamps)
    if n <= max_points:
        return timestamps, values

    if _HAS_LTTB:
        # LTTB downsampling (preserves visual shape)
        downsampler = LTTBDownsampler()
        indices = downsampler.downsample(values.astype(np.float64), n_out=max_points)
        return timestamps[indices], values[indices]
    else:
        # Fallback: uniform stride
        step = max(1, n // max_points)
        return timestamps[::step], values[::step]


# ============================================================================
# Plot Panel Widget (T120-T122, T126)
# ============================================================================

class PlotPanelWidget:
    """
    Live signal plotting panel below the viewport.

    Features:
    - Combo box to select active signal (kinetic_energy, sim_fps)
    - DPG line plot with auto-fitting axes
    - LTTB downsampling for efficient rendering at 60 FPS
    - Color-coded signals from registry

    Constitutional Compliance:
    - All DPG operations on main thread (Principle III)
    - Reads PlotBuffer.get_all() each frame (Principle IV)
    - Downsample budget < 2ms (Principle VII)
    """

    def __init__(
        self,
        parent_tag: str,
        plot_buffers: Dict[str, PlotBuffer],
        width: int = -1,
        height: int = 250,
    ):
        """
        Initialize plot panel.

        Args:
            parent_tag: DPG parent widget tag
            plot_buffers: Dict of PlotBuffer instances keyed by signal name
            width: Panel width (-1 for auto)
            height: Panel height in pixels
        """
        self.parent_tag = parent_tag
        self.plot_buffers = plot_buffers
        self.width = width
        self.height = height

        # Signal names from buffers
        self.signal_names = list(plot_buffers.keys())
        self.active_signal = self.signal_names[0] if self.signal_names else ""

        # DPG tags
        self.combo_tag = f"{parent_tag}_plot_combo"
        self.plot_tag = f"{parent_tag}_plot"
        self.x_axis_tag = f"{parent_tag}_plot_xaxis"
        self.y_axis_tag = f"{parent_tag}_plot_yaxis"
        self.series_tag = f"{parent_tag}_plot_series"

        self._create_panel()

    def _create_panel(self):
        """Create DPG plot panel widgets."""
        with dpg.group(parent=self.parent_tag):
            dpg.add_separator()
            dpg.add_text("Signal Plot", color=(255, 255, 0))

            # Signal selector combo
            combo_labels = [
                SIGNAL_REGISTRY.get(name, {}).get("label", name)
                for name in self.signal_names
            ]
            default_label = combo_labels[0] if combo_labels else ""

            dpg.add_combo(
                items=combo_labels,
                default_value=default_label,
                tag=self.combo_tag,
                callback=self._on_signal_changed,
                width=self.width if self.width > 0 else -1,
            )

            # DPG plot widget
            with dpg.plot(
                tag=self.plot_tag,
                width=self.width,
                height=self.height,
                no_mouse_pos=True,
            ):
                # X axis (time)
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    label="Time (s)",
                    tag=self.x_axis_tag,
                )

                # Y axis (signal value)
                y_label = SIGNAL_REGISTRY.get(self.active_signal, {}).get("y_label", "Value")
                dpg.add_plot_axis(
                    dpg.mvYAxis,
                    label=y_label,
                    tag=self.y_axis_tag,
                )

                # Line series (initially empty)
                color = SIGNAL_REGISTRY.get(self.active_signal, {}).get("color", (200, 200, 200, 255))
                dpg.add_line_series(
                    [],
                    [],
                    label=self.active_signal,
                    parent=self.y_axis_tag,
                    tag=self.series_tag,
                )

            # Apply theme color to series
            self._apply_series_color(color)

    def _apply_series_color(self, color):
        """Apply color theme to the line series."""
        theme_tag = f"{self.series_tag}_theme"
        if dpg.does_item_exist(theme_tag):
            dpg.delete_item(theme_tag)

        with dpg.theme(tag=theme_tag):
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots)

        dpg.bind_item_theme(self.series_tag, theme_tag)

    def _on_signal_changed(self, sender, app_data, user_data=None):
        """Handle signal combo selection change."""
        # Map label back to signal name
        for name in self.signal_names:
            label = SIGNAL_REGISTRY.get(name, {}).get("label", name)
            if label == app_data:
                self.active_signal = name
                break

        # Update Y axis label
        y_label = SIGNAL_REGISTRY.get(self.active_signal, {}).get("y_label", "Value")
        dpg.set_item_label(self.y_axis_tag, y_label)

        # Update series color
        color = SIGNAL_REGISTRY.get(self.active_signal, {}).get("color", (200, 200, 200, 255))
        self._apply_series_color(color)

    def update(self):
        """
        Update plot with latest data from active PlotBuffer.

        Called once per GUI frame (~60 Hz). Gets all data from buffer,
        downsamples via LTTB, and updates DPG line series.

        Performance Target: < 2ms total (Principle VII).
        """
        if not self.active_signal or self.active_signal not in self.plot_buffers:
            return

        buf = self.plot_buffers[self.active_signal]
        timestamps, values = buf.get_all()

        if len(timestamps) == 0:
            return

        # Downsample for efficient rendering
        t_ds, v_ds = downsample_plot_data(timestamps, values)

        # Update line series data
        dpg.set_value(self.series_tag, [t_ds.tolist(), v_ds.tolist()])

        # Auto-fit axes to show all data
        dpg.fit_axis_data(self.x_axis_tag)
        dpg.fit_axis_data(self.y_axis_tag)
