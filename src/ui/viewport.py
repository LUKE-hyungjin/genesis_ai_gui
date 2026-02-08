"""
DearPyGui viewport for displaying simulation frames.

This module handles the 3D viewport rendering using DPG's raw texture API
with the constitutional float32 RGBA [0..1] format.

Constitutional Compliance: Principle V (Viewport Pipeline Spec)
"""

import dearpygui.dearpygui as dpg
import numpy as np
from typing import Optional, Tuple, Union

from src.core.ipc import FrameBuffer


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

    # Create image widget to display the texture
    # Use display_width/display_height if provided (Phase 4 responsive layout)
    # Otherwise use texture dimensions (Phase 3 fixed layout)
    image_tag = f"{tag}_image"

    if display_width is not None and display_height is not None:
        # Phase 4: Use specified display dimensions (scaled to fit container)
        image_width = display_width
        image_height = display_height
    else:
        # Phase 3: Use texture dimensions directly
        image_width = texture_width
        image_height = texture_height

    dpg.add_image(
        texture_tag=tag,
        tag=image_tag,
        parent=parent,
        width=image_width,
        height=image_height,
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
