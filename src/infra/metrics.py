"""
Performance metrics and observability infrastructure.

This module implements FPS counters, lock timing, and metrics dashboard
for monitoring system performance.

Constitutional Compliance: Principle VII (Performance & Stability Targets)
"""

import time
import threading
import numpy as np
from collections import deque
from typing import Optional


# ============================================================================
# FPS Counter
# ============================================================================

class FPSCounter:
    """
    Frame-per-second counter for measuring loop performance.

    Tracks frame times over a sliding window and calculates FPS and p95 latency.
    """

    def __init__(self, window_size: int = 100):
        """
        Initialize FPS counter.

        Args:
            window_size: Number of frames to average over (default 100)
        """
        self.frame_times = deque(maxlen=window_size)
        self.last_tick: Optional[float] = None
        self.window_size = window_size

    def tick(self):
        """Record a frame/tick event."""
        now = time.perf_counter()
        if self.last_tick is not None:
            frame_time = now - self.last_tick
            self.frame_times.append(frame_time)
        self.last_tick = now

    def get_fps(self) -> float:
        """
        Get current FPS.

        Returns:
            Frames per second (0 if insufficient data)
        """
        if not self.frame_times:
            return 0.0
        avg_frame_time = np.mean(self.frame_times)
        if avg_frame_time == 0:
            return 0.0
        return 1.0 / avg_frame_time

    def get_p95_ms(self) -> float:
        """
        Get p95 frame time in milliseconds.

        Returns:
            95th percentile frame time in ms (0 if insufficient data)
        """
        if not self.frame_times:
            return 0.0
        return np.percentile(self.frame_times, 95) * 1000  # Convert to ms

    def get_avg_ms(self) -> float:
        """
        Get average frame time in milliseconds.

        Returns:
            Average frame time in ms (0 if insufficient data)
        """
        if not self.frame_times:
            return 0.0
        return np.mean(self.frame_times) * 1000  # Convert to ms

    def reset(self):
        """Clear all frame time history."""
        self.frame_times.clear()
        self.last_tick = None


# ============================================================================
# Timed Lock (for measuring lock hold time)
# ============================================================================

class TimedLock:
    """
    Thread lock wrapper that measures hold time.

    Constitutional Compliance:
    - Lock hold time target: p95 ≤ 1ms (Principle VII)

    Usage:
        lock = TimedLock(threading.Lock())
        with lock:
            # Critical section
            pass
        print(f"Lock p95: {lock.get_p95_ms():.2f}ms")
    """

    def __init__(self, lock: threading.Lock, window_size: int = 1000):
        """
        Initialize timed lock wrapper.

        Args:
            lock: Underlying threading.Lock instance
            window_size: Number of acquisitions to track (default 1000)
        """
        self.lock = lock
        self.hold_times = deque(maxlen=window_size)
        self.acquire_time: Optional[float] = None
        self.window_size = window_size

    def __enter__(self):
        """Acquire lock and start timing."""
        self.acquire_time = time.perf_counter()
        self.lock.acquire()
        return self

    def __exit__(self, *args):
        """Release lock and record hold time."""
        if self.acquire_time is not None:
            hold_time = time.perf_counter() - self.acquire_time
            self.hold_times.append(hold_time)
            self.acquire_time = None
        self.lock.release()

    def get_p95_ms(self) -> float:
        """
        Get p95 lock hold time in milliseconds.

        Returns:
            95th percentile hold time in ms (0 if insufficient data)
        """
        if not self.hold_times:
            return 0.0
        return np.percentile(self.hold_times, 95) * 1000  # Convert to ms

    def get_avg_ms(self) -> float:
        """
        Get average lock hold time in milliseconds.

        Returns:
            Average hold time in ms (0 if insufficient data)
        """
        if not self.hold_times:
            return 0.0
        return np.mean(self.hold_times) * 1000  # Convert to ms

    def get_max_ms(self) -> float:
        """
        Get maximum lock hold time in milliseconds.

        Returns:
            Maximum hold time in ms (0 if insufficient data)
        """
        if not self.hold_times:
            return 0.0
        return np.max(self.hold_times) * 1000  # Convert to ms

    def reset(self):
        """Clear all hold time history."""
        self.hold_times.clear()


# ============================================================================
# Metrics Dashboard (DPG window with metrics display)
# ============================================================================

class MetricsCollector:
    """
    Centralized metrics collection and reporting.

    Aggregates metrics from various sources (FPS counters, locks, queues)
    and provides a unified interface for metrics dashboards.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.gui_fps_counter = FPSCounter(window_size=100)
        self.sim_fps_counter = FPSCounter(window_size=100)

    def collect(self, command_queue, event_queue, frame_lock, plot_buffers=None) -> dict:
        """
        Collect all metrics.

        Args:
            command_queue: CommandQueue instance
            event_queue: EventQueue instance
            frame_lock: TimedLock instance for frame buffer
            plot_buffers: Dict[str, PlotBuffer] or single PlotBuffer (backward compat)

        Returns:
            Dictionary with all metrics
        """
        # Plot buffer utilization (max across all buffers)
        plot_util = 0.0
        if plot_buffers is not None:
            if isinstance(plot_buffers, dict):
                if plot_buffers:
                    plot_util = max(b.utilization() for b in plot_buffers.values())
            else:
                # Backward compat: single PlotBuffer
                plot_util = plot_buffers.utilization()

        return {
            "gui_fps": self.gui_fps_counter.get_fps(),
            "gui_frame_p95_ms": self.gui_fps_counter.get_p95_ms(),
            "sim_fps": self.sim_fps_counter.get_fps(),
            "command_queue_depth": command_queue.qsize(),
            "event_queue_depth": event_queue.qsize(),
            "frame_lock_p95_ms": frame_lock.get_p95_ms(),
            "plot_buffer_util": plot_util,
        }

    def format_metrics(self, metrics: dict) -> str:
        """
        Format metrics as human-readable string.

        Args:
            metrics: Dictionary from collect()

        Returns:
            Formatted metrics string
        """
        lines = [
            f"GUI FPS: {metrics['gui_fps']:.1f}",
            f"Sim FPS: {metrics['sim_fps']:.1f}",
            f"Frame p95: {metrics['gui_frame_p95_ms']:.2f}ms",
            f"Lock p95: {metrics['frame_lock_p95_ms']:.2f}ms",
            f"Cmd Queue: {metrics['command_queue_depth']}",
            f"Evt Queue: {metrics['event_queue_depth']}",
            f"Plot Buffer: {metrics['plot_buffer_util']*100:.1f}%",
        ]
        return "\n".join(lines)
