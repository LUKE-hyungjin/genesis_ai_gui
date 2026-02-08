"""
Inter-Process Communication (IPC) primitives for thread-safe data sharing.

This module implements the constitutional data pathway segregation:
- CommandQueue: GUI → Sim (queue.Queue)
- EventQueue: Sim → GUI (queue.Queue)
- FrameBuffer: Sim → GUI (shared numpy.ndarray + threading.Lock)
- PlotBuffer: Sim → GUI (collections.deque)

Constitutional Compliance: Principle IV (Data Pathway Segregation)
"""

import queue
import threading
import numpy as np
from collections import deque
from typing import Optional, Tuple


# ============================================================================
# Command Queue (GUI → Simulation)
# ============================================================================

class CommandQueue:
    """
    Thread-safe queue for commands from GUI to simulation thread.

    Constitutional Compliance:
    - Commands via queue.Queue (Principle IV)
    - Bounded queue (maxsize) to prevent memory exhaustion
    """

    def __init__(self, maxsize: int = 1000):
        """
        Initialize command queue.

        Args:
            maxsize: Maximum number of commands (default 1000)
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize

    def put(self, command, block: bool = True, timeout: Optional[float] = None):
        """
        Put command into queue.

        Args:
            command: Command instance (subclass of BaseCommand)
            block: Block if queue is full (default True)
            timeout: Timeout in seconds (default None = wait forever)

        Raises:
            queue.Full: If queue is full and block=False or timeout expires
        """
        self._queue.put(command, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None):
        """
        Get command from queue.

        Args:
            block: Block if queue is empty (default True)
            timeout: Timeout in seconds (default None = wait forever)

        Returns:
            Command instance

        Raises:
            queue.Empty: If queue is empty and block=False or timeout expires
        """
        return self._queue.get(block=block, timeout=timeout)

    def get_nowait(self):
        """Get command without blocking (raises queue.Empty if empty)."""
        return self._queue.get_nowait()

    def put_nowait(self, command):
        """Put command without blocking (raises queue.Full if full)."""
        self._queue.put_nowait(command)

    def qsize(self) -> int:
        """Return approximate queue depth."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if queue is empty."""
        return self._queue.empty()


# ============================================================================
# Event Queue (Simulation → GUI)
# ============================================================================

class EventQueue:
    """
    Thread-safe queue for events from simulation to GUI thread.

    Constitutional Compliance:
    - Events via queue.Queue (Principle IV)
    - Bounded queue (maxsize) to prevent memory exhaustion
    """

    def __init__(self, maxsize: int = 1000):
        """
        Initialize event queue.

        Args:
            maxsize: Maximum number of events (default 1000)
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize

    def put(self, event, block: bool = True, timeout: Optional[float] = None):
        """
        Put event into queue.

        Args:
            event: Event instance (subclass of BaseEvent)
            block: Block if queue is full (default True)
            timeout: Timeout in seconds (default None = wait forever)

        Raises:
            queue.Full: If queue is full and block=False or timeout expires
        """
        self._queue.put(event, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None):
        """
        Get event from queue.

        Args:
            block: Block if queue is empty (default True)
            timeout: Timeout in seconds (default None = wait forever)

        Returns:
            Event instance

        Raises:
            queue.Empty: If queue is empty and block=False or timeout expires
        """
        return self._queue.get(block=block, timeout=timeout)

    def get_nowait(self):
        """Get event without blocking (raises queue.Empty if empty)."""
        return self._queue.get_nowait()

    def put_nowait(self, event):
        """Put event without blocking (raises queue.Full if full)."""
        self._queue.put_nowait(event)

    def qsize(self) -> int:
        """Return approximate queue depth."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if queue is empty."""
        return self._queue.empty()


# ============================================================================
# Frame Buffer (Simulation → GUI, shared memory)
# ============================================================================

class FrameBuffer:
    """
    Shared frame buffer with thread-safe access for rendered frames.

    Constitutional Compliance:
    - Shared numpy.ndarray + threading.Lock (Principle IV)
    - float32 RGBA [0..1] flattened (Principle V)

    Performance Targets:
    - Lock hold time < 1ms p95
    - Copy time ~0.5ms @ 1080p
    """

    def __init__(self, width: int, height: int, lock: Optional[threading.Lock] = None):
        """
        Initialize frame buffer.

        Args:
            width: Viewport width in pixels
            height: Viewport height in pixels
            lock: Optional external lock (e.g., TimedLock) for synchronized access.
                  If None, creates an internal threading.Lock.
        """
        self.width = width
        self.height = height
        self.size = width * height * 4  # RGBA

        # Shared array (float32 RGBA [0..1] flattened)
        self.data = np.zeros(self.size, dtype=np.float32)

        # Thread synchronization (use external lock if provided)
        self.lock = lock if lock is not None else threading.Lock()

    def write(self, frame: np.ndarray):
        """
        Write frame from simulation thread.

        Args:
            frame: (H, W, 4) float32 RGBA array or (H*W*4,) flat array

        Raises:
            AssertionError: If frame format doesn't match requirements
        """
        frame_flat = frame.ravel() if frame.ndim > 1 else frame

        assert frame_flat.dtype == np.float32, "Must be float32"
        assert len(frame_flat) == self.size, f"Size mismatch: {len(frame_flat)} != {self.size}"

        with self.lock:
            self.data[:] = frame_flat

    def read(self) -> np.ndarray:
        """
        Read frame from GUI thread.

        Returns:
            Copy of frame data (H*W*4,) flat array
        """
        with self.lock:
            return self.data.copy()

    def read_no_copy(self) -> np.ndarray:
        """
        Read frame without copying (UNSAFE: caller must hold lock).

        Returns:
            View of frame data (not thread-safe)
        """
        return self.data


# ============================================================================
# Plot Buffer (Simulation → GUI, circular buffer)
# ============================================================================

class PlotBuffer:
    """
    Circular buffer for time-series plot data.

    Constitutional Compliance:
    - collections.deque with maxlen (Principle IV)
    - (timestamp, value) tuple schema

    Performance Targets:
    - Append latency < 0.01ms
    - Read all < 1ms for 10k samples
    """

    def __init__(self, maxlen: int = 10000):
        """
        Initialize plot buffer.

        Args:
            maxlen: Maximum number of samples (oldest dropped when full)
        """
        self.buffer = deque(maxlen=maxlen)
        self.maxlen = maxlen

    def append(self, timestamp: float, value: float):
        """
        Append sample from simulation thread.

        Args:
            timestamp: Simulation time or wall-clock time
            value: Scalar metric value
        """
        self.buffer.append((timestamp, value))

    def get_all(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get all samples (GUI thread).

        Returns:
            (timestamps, values) as numpy arrays
        """
        if not self.buffer:
            return np.array([]), np.array([])

        data = list(self.buffer)
        t = np.array([d[0] for d in data])
        v = np.array([d[1] for d in data])
        return t, v

    def clear(self):
        """Clear all samples."""
        self.buffer.clear()

    def utilization(self) -> float:
        """
        Get buffer utilization percentage.

        Returns:
            0.0 - 1.0 (1.0 = full)
        """
        return len(self.buffer) / self.maxlen

    def __len__(self) -> int:
        """Return number of samples in buffer."""
        return len(self.buffer)


# ============================================================================
# Frame Format Conversion (Phase 2: T042-T043)
# ============================================================================

def validate_frame_format(frame: np.ndarray) -> bool:
    """
    Validate that frame meets DPG texture format requirements.

    Constitutional Compliance:
    - float32 RGBA [0..1] flattened (Principle V)

    Args:
        frame: Frame array to validate (can be 1D or 3D)

    Returns:
        True if valid

    Raises:
        AssertionError: If validation fails with specific error message
    """
    # Check dtype
    assert frame.dtype == np.float32, f"Frame dtype must be float32, got {frame.dtype}"

    # Check dimensionality (either 1D flat or 3D (H, W, 4))
    if frame.ndim == 1:
        assert len(frame) % 4 == 0, f"1D frame length must be multiple of 4 (RGBA), got {len(frame)}"
    elif frame.ndim == 3:
        assert frame.shape[2] == 4, f"Frame must have 4 channels (RGBA), got {frame.shape[2]}"
    else:
        raise AssertionError(f"Frame must be 1D or 3D, got {frame.ndim}D")

    # Check value range
    min_val = frame.min()
    max_val = frame.max()
    assert min_val >= 0.0, f"Frame values must be >= 0.0, got min={min_val}"
    assert max_val <= 1.0, f"Frame values must be <= 1.0, got max={max_val}"

    return True


def genesis_frame_to_dpg_texture(genesis_frame: np.ndarray) -> np.ndarray:
    """
    Convert Genesis camera output to DPG-compatible texture format.

    This function handles all necessary conversions:
    1. Type conversion to float32
    2. Value range normalization to [0..1]
    3. Alpha channel addition if RGB (3 channels)
    4. Flattening to 1D array

    Constitutional Compliance:
    - Outputs float32 RGBA [0..1] flattened (Principle V)

    Performance Target:
    - < 3ms @ 1080p (within 16.7ms GUI frame budget)

    Args:
        genesis_frame: NumPy array from camera.render()
            Can be:
            - (H, W, 3) uint8 RGB [0..255]
            - (H, W, 3) float32 RGB [0..1]
            - (H, W, 4) uint8 RGBA [0..255]
            - (H, W, 4) float32 RGBA [0..1]

    Returns:
        1D float32 RGBA array in [0..1] range suitable for dpg.set_value()

    Raises:
        AssertionError: If input format is invalid
    """
    # Assumption: Genesis outputs (H, W, C) where C = 3 (RGB) or 4 (RGBA)
    assert genesis_frame.ndim == 3, f"Expected 3D array (H, W, C), got {genesis_frame.ndim}D"
    assert genesis_frame.shape[2] in [3, 4], f"Expected 3 or 4 channels, got {genesis_frame.shape[2]}"

    frame = genesis_frame.copy()

    # Step 1: Convert to float32 if needed
    if frame.dtype != np.float32:
        if frame.dtype == np.uint8:
            frame = frame.astype(np.float32) / 255.0  # [0..255] → [0..1]
        else:
            frame = frame.astype(np.float32)

    # Step 2: Normalize to [0..1] if needed
    min_val = frame.min()
    max_val = frame.max()
    if min_val < 0.0 or max_val > 1.0:
        # Clamp to [0..1]
        frame = np.clip(frame, 0.0, 1.0)
        print(f"[FRAME] Warning: Frame values outside [0..1] range (min={min_val}, max={max_val}), clamped")

    # Step 3: Add alpha channel if RGB (3 channels)
    if frame.shape[-1] == 3:
        h, w, _ = frame.shape
        alpha = np.ones((h, w, 1), dtype=np.float32)
        frame = np.concatenate([frame, alpha], axis=-1)

    # Step 4: Flatten to 1D
    frame_flat = frame.ravel()  # Use ravel() for contiguous view (faster than flatten())

    # Validate output format
    validate_frame_format(frame_flat)

    return frame_flat
