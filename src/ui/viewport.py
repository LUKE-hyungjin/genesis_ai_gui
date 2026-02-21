"""
DearPyGui viewport for displaying simulation frames.

This module handles the 3D viewport rendering using DPG's raw texture API
with the constitutional float32 RGBA [0..1] format.

Constitutional Compliance: Principle V (Viewport Pipeline Spec)
"""

import dearpygui.dearpygui as dpg
import numpy as np
from typing import Optional, Tuple, Union

from src.core.ipc import FrameBuffer, CommandQueue
from src.core.commands import RayCastCommand


# ============================================================================
# Viewport Creation and Update
# ============================================================================

def create_viewport(
    width: int = 1280,
    height: int = 720,
    parent: Optional[Union[int, str]] = None,
    tag: str = "viewport_texture",
    display_width: Optional[int] = None,
    display_height: Optional[int] = None,
) -> str:
    """
    Create DPG viewport texture for displaying simulation frames.

    Constitutional Compliance:
    - Uses mvFormat_Float_rgba (Principle V)
    - float32 RGBA [0..1] format (Principle V)

    Args:
        width: Texture width in pixels (default 1280, must match FrameBuffer)
        height: Texture height in pixels (default 720, must match FrameBuffer)
        parent: Parent DPG container (default None = root)
        tag: Unique tag for texture (default "viewport_texture")
        display_width: Image widget display width (default None = use texture width)
        display_height: Image widget display height (default None = use texture height)

    Returns:
        Texture tag string
    """
    # Handle auto-sizing (-1 means use default 1280x720 for texture)
    texture_width = 1280 if width == -1 else width
    texture_height = 720 if height == -1 else height

    # Create raw texture with float32 RGBA format
    # Note: DPG expects flattened array (W * H * 4,)
    default_data = np.zeros((texture_width * texture_height * 4,), dtype=np.float32)

    with dpg.texture_registry() as texture_registry:
        dpg.add_raw_texture(
            width=texture_width,
            height=texture_height,
            default_value=default_data,
            format=dpg.mvFormat_Float_rgba,
            tag=tag,
        )

    # Use display dimensions or texture dimensions
    if display_width is not None and display_height is not None:
        image_width = display_width
        image_height = display_height
    else:
        image_width = texture_width
        image_height = texture_height

    # Create drawlist as the primary display widget.
    # Using a single drawlist for both the image and gizmo overlay ensures they
    # share the same coordinate space and DPG Z-order (items drawn later appear on top).
    # This avoids the separate-widget stacking problem of using add_image + add_drawlist.
    drawlist_tag = f"{tag}_drawlist"
    dpg.add_drawlist(
        tag=drawlist_tag,
        parent=parent,
        width=image_width,
        height=image_height,
    )

    # Draw the viewport texture as the background layer inside the drawlist.
    # dpg.set_value(tag, data) updates the raw texture referenced here each frame.
    dpg.draw_image(
        texture_tag=tag,
        pmin=(0, 0),
        pmax=(image_width, image_height),
        parent=drawlist_tag,
        tag=f"{tag}_bg",
    )

    return tag


def update_viewport(texture_tag: str, frame_buffer: FrameBuffer):
    """
    Update viewport texture from frame buffer.

    Reads the latest frame from FrameBuffer (with thread-safe lock)
    and updates the DPG texture.

    Constitutional Compliance:
    - Reads from shared numpy.ndarray + Lock (Principle IV)
    - float32 RGBA [0..1] format (Principle V)

    Performance Target:
    - Frame buffer copy: ~0.5ms @ 1080p
    - set_value: ~0.1ms

    Args:
        texture_tag: DPG texture tag to update
        frame_buffer: FrameBuffer instance to read from
    """
    # Read frame (thread-safe copy)
    frame_data = frame_buffer.read()

    # Update DPG texture
    # Note: dpg.set_value expects flat array (W * H * 4,)
    dpg.set_value(texture_tag, frame_data)


def get_viewport_size(texture_tag: str) -> Tuple[int, int]:
    """
    Get current viewport dimensions.

    Args:
        texture_tag: DPG texture tag

    Returns:
        (width, height) in pixels
    """
    # Get texture configuration
    config = dpg.get_item_configuration(texture_tag)
    return config["width"], config["height"]


def resize_viewport(texture_tag: str, width: int, height: int):
    """
    Resize viewport texture.

    Note: This requires recreating the texture in DPG. For Phase 1,
    viewport size is fixed. Dynamic resizing is Phase 3+ feature.

    Args:
        texture_tag: DPG texture tag
        width: New width in pixels
        height: New height in pixels
    """
    # For Phase 1, this is a placeholder
    # Full implementation requires:
    # 1. Delete old texture
    # 2. Create new texture with new dimensions
    # 3. Resize FrameBuffer
    # 4. Update image widget size
    raise NotImplementedError("Dynamic viewport resizing is Phase 3+ feature")


# ============================================================================
# Viewport Click Handler (Phase 6: T136-T138)
# ============================================================================

def setup_viewport_click_handler(
    viewport_item_tag: str,
    command_queue: CommandQueue,
    display_width: int,
    display_height: int,
):
    """
    Setup mouse click handler for viewport entity picking.

    On left click within viewport bounds, converts pixel coords to
    normalized [0..1] and emits RayCastCommand.

    Constitutional Compliance:
    - Principle III: Runs on main thread (DPG handler)
    - Principle IV: Emits RayCastCommand via queue.Queue

    Args:
        viewport_item_tag: DPG viewport item tag used for bounds checking
            (typically "<texture_tag>_drawlist")
        command_queue: Command queue for RayCastCommand emission
        display_width: Viewport display width in pixels
        display_height: Viewport display height in pixels
    """
    def _on_mouse_click(sender, app_data):
        """Handle mouse click — check if within viewport, emit RayCastCommand."""
        # app_data is the mouse button (0 = left)
        if app_data != 0:
            return

        # Get mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Get viewport image bounds
        if not dpg.does_item_exist(viewport_item_tag):
            return

        rect_min = dpg.get_item_rect_min(viewport_item_tag)
        rect_max = dpg.get_item_rect_max(viewport_item_tag)

        mx, my = mouse_pos[0], mouse_pos[1]

        # Check if click is within viewport bounds
        if mx < rect_min[0] or mx > rect_max[0] or my < rect_min[1] or my > rect_max[1]:
            return

        # Convert to normalized [0..1] relative to viewport
        x_norm = (mx - rect_min[0]) / (rect_max[0] - rect_min[0])
        y_norm = (my - rect_min[1]) / (rect_max[1] - rect_min[1])

        # Clamp to [0..1]
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))

        # Emit RayCastCommand
        try:
            command_queue.put_nowait(RayCastCommand(x_norm=x_norm, y_norm=y_norm))
        except Exception as e:
            print(f"[VIEWPORT] Failed to emit RayCastCommand: {e}")

    # Register global mouse click handler
    with dpg.handler_registry(tag="viewport_click_handler"):
        dpg.add_mouse_click_handler(callback=_on_mouse_click)

    print(f"[VIEWPORT] Click handler registered for {viewport_item_tag}")
