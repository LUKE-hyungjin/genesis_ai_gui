"""
Transform gizmo overlay for direct entity manipulation.

DPG drawlist-based gizmo that renders axis handles (X=red, Y=green, Z=blue)
on top of the viewport. Supports drag-to-move with Undo integration.

Constitutional Compliance:
- Principle III (Explicit Main-Thread Ops): All DPG drawing on main thread
- Principle VI (Optimistic UI): PreviewPropertyCommand during drag, UpdatePropertyCommand on release
- Principle VII (Performance Targets): Gizmo render overhead < 1ms
"""

import dearpygui.dearpygui as dpg
import numpy as np
from contextlib import nullcontext
from typing import Optional, Tuple, Dict

from src.core.commands import PreviewPropertyCommand, UpdatePropertyCommand
from src.core.picking import (
    get_camera_params,
    build_view_matrix,
    build_projection_matrix,
    project_to_screen,
    project_direction_to_screen,
)


# ============================================================================
# Constants
# ============================================================================

AXIS_LENGTH_PX = 60  # Gizmo axis length in pixels
AXIS_THICKNESS = 3.0
PICK_TOLERANCE_PX = 12  # Mouse distance for axis selection

AXIS_COLORS = {
    "x": (220, 60, 60, 255),   # Red
    "y": (60, 200, 60, 255),   # Green
    "z": (60, 100, 220, 255),  # Blue
}

AXIS_HIGHLIGHT_COLORS = {
    "x": (255, 120, 120, 255),
    "y": (120, 255, 120, 255),
    "z": (120, 160, 255, 255),
}

AXIS_DIRECTIONS = {
    "x": (1.0, 0.0, 0.0),
    "y": (0.0, 1.0, 0.0),
    "z": (0.0, 0.0, 1.0),
}


# ============================================================================
# Transform Gizmo (T143-T149)
# ============================================================================

class TransformGizmo:
    """
    DPG drawlist-based transform gizmo for entity position manipulation.

    Renders colored axis lines at the selected entity's screen position.
    Supports click-and-drag on individual axes with preview/commit pattern.

    Drawing is done on the viewport's shared drawlist (created by create_viewport),
    which already contains the rendered texture as its background layer. This ensures
    gizmo axes appear ON TOP of the viewport image without a separate drawlist widget.

    Constitutional Compliance:
    - Principle III: All DPG operations on main thread
    - Principle VI: Preview during drag, commit on release
    - Principle VII: Render overhead < 1ms per frame
    """

    def __init__(
        self,
        drawlist_tag: str,
        command_queue,
        display_width: int,
        display_height: int,
        scene_lock=None,
    ):
        """
        Initialize transform gizmo.

        Args:
            drawlist_tag: Tag of the existing DPG drawlist to draw gizmo on
                          (the viewport's drawlist created by create_viewport)
            command_queue: Command queue for property commands
            display_width: Viewport display width in pixels
            display_height: Viewport display height in pixels
            scene_lock: Optional lock shared with simulation scene updates
        """
        self.drawlist_tag = drawlist_tag
        self.command_queue = command_queue
        self.display_width = display_width
        self.display_height = display_height
        self.scene_lock = scene_lock

        # Entity state
        self.active_entity_id = None  # type: Optional[int]
        self.scene = None
        self.camera = None

        # Projection matrices (cached per set_entity call)
        self.view_mat = None  # type: Optional[np.ndarray]
        self.proj_mat = None  # type: Optional[np.ndarray]

        # Screen-space gizmo data
        self.screen_center = (0.0, 0.0)  # Pixel coords
        self.axis_endpoints = {}  # type: Dict[str, Tuple[float, float]]
        self.axis_screen_dirs = {}  # type: Dict[str, Tuple[float, float]]

        # Drag state
        self.dragging_axis = None  # type: Optional[str]
        self.drag_start_mouse = (0.0, 0.0)
        self.original_position = (0.0, 0.0, 0.0)
        # Axis screen direction captured at drag start — held constant during drag
        # to prevent jitter as the entity moves and the projection changes each frame.
        self.drag_axis_screen_dir = (0.0, 0.0)  # type: Tuple[float, float]
        self.visible = False

        # Store integer UUIDs of live gizmo draw items.
        # dpg.draw_*(parent=drawlist_tag) returns the item's internal UUID (int).
        # Deleting by UUID avoids all string-alias timing issues and does not
        # require tags or a draw_node container.
        self._gizmo_uuids = []  # type: list

        # Handler registry tag (unique per drawlist)
        self.handler_tag = f"{drawlist_tag}_gizmo_handler"

        # Setup mouse handlers (drawlist already created externally)
        self._setup_mouse_handlers()

    def _setup_mouse_handlers(self):
        """Setup mouse handlers for gizmo interaction."""
        with dpg.handler_registry(tag=self.handler_tag):
            dpg.add_mouse_down_handler(
                button=0,
                callback=self._on_mouse_down,
            )
            dpg.add_mouse_release_handler(
                button=0,
                callback=self._on_mouse_release,
            )

    def set_entity(self, entity_id, scene, camera):
        """
        Set active entity for gizmo display.

        Args:
            entity_id: Entity ID or None to hide gizmo
            scene: Genesis scene reference
            camera: Genesis camera reference
        """
        self.scene = scene
        self.camera = camera

        if entity_id is None:
            self.active_entity_id = None
            self.visible = False
            self._clear_drawlist()
            return

        self.active_entity_id = entity_id
        self.visible = True

        # Build projection matrices
        cam = get_camera_params(camera)
        self.view_mat = build_view_matrix(cam['pos'], cam['lookat'], cam['up'])
        aspect = cam['res'][0] / cam['res'][1]
        self.proj_mat = build_projection_matrix(cam['fov'], aspect)

    def update(self):
        """
        Update gizmo rendering each frame.

        Reprojects entity position to screen coords and redraws axes.
        Called once per GUI frame (~60 Hz).

        Performance Target: < 1ms total (Principle VII).
        """
        if not self.visible or self.active_entity_id is None:
            self._clear_drawlist()
            return

        if self.scene is None or self.camera is None:
            if self.dragging_axis is not None:
                self._handle_drag_move()
            return

        if self.view_mat is None or self.proj_mat is None:
            if self.dragging_axis is not None:
                self._handle_drag_move()
            return

        # Get entity position
        entity_pos = self._get_entity_position()
        if entity_pos is None:
            self._clear_drawlist()
            return

        # Project entity center to screen pixels
        sx, sy, depth = project_to_screen(entity_pos, self.view_mat, self.proj_mat)

        # Allow a margin beyond screen edges so the gizmo remains visible when
        # the entity is dragged near the viewport boundary (p95 drift ~5-10%).
        # Behind-camera (depth <= 0) is the only hard exclusion.
        in_view = depth > 0 and -0.2 <= sx <= 1.2 and -0.2 <= sy <= 1.2

        if in_view:
            # Clamp pixel coords to a few pixels inside the drawlist bounds
            cx = max(5.0, min(float(self.display_width - 5), sx * self.display_width))
            cy = max(5.0, min(float(self.display_height - 5), sy * self.display_height))
            self.screen_center = (cx, cy)

            # Compute axis endpoints and screen directions
            self.axis_endpoints.clear()
            self.axis_screen_dirs.clear()

            for axis_name, direction in AXIS_DIRECTIONS.items():
                # Project axis direction to screen
                dx, dy = project_direction_to_screen(
                    entity_pos, direction, self.view_mat, self.proj_mat
                )
                self.axis_screen_dirs[axis_name] = (dx, dy)

                # Compute endpoint in pixels
                ex = cx + dx * AXIS_LENGTH_PX
                ey = cy + dy * AXIS_LENGTH_PX
                self.axis_endpoints[axis_name] = (ex, ey)

            # Redraw gizmo at updated position
            self._draw_gizmo()

        elif not self.dragging_axis:
            # Entity is off-screen and no active drag: hide gizmo
            self._clear_drawlist()
        # If dragging and entity went off-screen: keep last drawn gizmo position
        # (don't clear) so the user still sees the axes while dragging near edges.

        # Always handle drag movement regardless of whether the entity is in view.
        # This prevents drag from freezing the moment the entity crosses the edge.
        if self.dragging_axis is not None:
            self._handle_drag_move()

    def _get_entity_position(self):
        """Get active entity's world position."""
        try:
            lock_ctx = self.scene_lock if self.scene_lock is not None else nullcontext()
            with lock_ctx:
                if not hasattr(self.scene, 'entities'):
                    return None
                if self.active_entity_id >= len(self.scene.entities):
                    return None

                entity = self.scene.entities[self.active_entity_id]
                pos = entity.get_pos()
                if hasattr(pos, 'tolist'):
                    return tuple(pos.tolist())
                elif hasattr(pos, '__iter__'):
                    return tuple(pos)
                return None
        except Exception:
            return None

    def _draw_gizmo(self):
        """Draw gizmo axes directly onto the shared viewport drawlist.

        Each draw_* call returns an integer UUID which is stored in _gizmo_uuids.
        _clear_drawlist() deletes items by UUID, completely bypassing DPG's string
        alias system and avoiding any tag-reuse or parent-deduction errors.
        """
        self._clear_drawlist()

        cx, cy = self.screen_center
        dl = self.drawlist_tag

        # Draw center circle — store returned UUID
        uid = dpg.draw_circle(
            center=(cx, cy),
            radius=4,
            color=(255, 255, 255, 200),
            fill=(255, 255, 255, 100),
            parent=dl,
        )
        self._gizmo_uuids.append(uid)

        # Draw axes
        for axis_name in ["x", "y", "z"]:
            endpoint = self.axis_endpoints.get(axis_name)
            if endpoint is None:
                continue

            # Highlight active axis
            if self.dragging_axis == axis_name:
                color = AXIS_HIGHLIGHT_COLORS[axis_name]
                thickness = AXIS_THICKNESS + 2
            else:
                color = AXIS_COLORS[axis_name]
                thickness = AXIS_THICKNESS

            # Draw axis line
            uid = dpg.draw_line(
                p1=(cx, cy),
                p2=endpoint,
                color=color,
                thickness=thickness,
                parent=dl,
            )
            self._gizmo_uuids.append(uid)

            # Draw axis tip (small circle)
            uid = dpg.draw_circle(
                center=endpoint,
                radius=5,
                color=color,
                fill=color,
                parent=dl,
            )
            self._gizmo_uuids.append(uid)

            # Draw axis label
            label_offset = 8
            dx, dy = self.axis_screen_dirs.get(axis_name, (0, 0))
            label_x = endpoint[0] + dx * label_offset
            label_y = endpoint[1] + dy * label_offset
            uid = dpg.draw_text(
                pos=(label_x, label_y),
                text=axis_name.upper(),
                color=color,
                size=14,
                parent=dl,
            )
            self._gizmo_uuids.append(uid)

    def _clear_drawlist(self):
        """Delete live gizmo draw items by UUID.

        dpg.draw_* returns the item's integer UUID. Deleting by UUID is immediate
        and does not involve DPG's string alias registry, so there are no
        tag-reuse or parent-deduction errors between frames.
        """
        for uid in self._gizmo_uuids:
            if dpg.does_item_exist(uid):
                dpg.delete_item(uid)
        self._gizmo_uuids.clear()

    def _on_mouse_down(self, sender, app_data):
        """Handle mouse down — check for gizmo axis selection."""
        if not self.visible or self.active_entity_id is None:
            return

        # Get mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Check if mouse is within viewport area (using drawlist bounds)
        if not dpg.does_item_exist(self.drawlist_tag):
            return

        rect_min = dpg.get_item_rect_min(self.drawlist_tag)
        rect_max = dpg.get_item_rect_max(self.drawlist_tag)

        mx, my = mouse_pos[0], mouse_pos[1]

        if mx < rect_min[0] or mx > rect_max[0] or my < rect_min[1] or my > rect_max[1]:
            return

        # Convert to drawlist-local coords
        local_x = mx - rect_min[0]
        local_y = my - rect_min[1]

        # Check each axis for hit
        cx, cy = self.screen_center
        hit_axis = self._hit_test_axes(local_x, local_y, cx, cy)

        if hit_axis is not None:
            self.dragging_axis = hit_axis
            self.drag_start_mouse = (mx, my)
            self.original_position = self._get_entity_position() or (0, 0, 0)
            # Snapshot the axis screen direction at drag start.
            # Held constant for the entire drag so direction doesn't shift as the
            # entity moves and the projection changes each frame.
            self.drag_axis_screen_dir = self.axis_screen_dirs.get(hit_axis, (0.0, 0.0))

    def _hit_test_axes(self, mx, my, cx, cy) -> Optional[str]:
        """
        Test if mouse position hits a gizmo axis.

        Args:
            mx, my: Mouse position in drawlist-local coords
            cx, cy: Gizmo center in drawlist-local coords

        Returns:
            Axis name ('x', 'y', 'z') or None
        """
        best_axis = None
        best_dist = float('inf')

        for axis_name, endpoint in self.axis_endpoints.items():
            # Point-to-line-segment distance
            dist = self._point_to_segment_distance(mx, my, cx, cy, endpoint[0], endpoint[1])

            if dist < PICK_TOLERANCE_PX and dist < best_dist:
                best_dist = dist
                best_axis = axis_name

        return best_axis

    @staticmethod
    def _point_to_segment_distance(px, py, x1, y1, x2, y2) -> float:
        """Calculate distance from point (px,py) to line segment (x1,y1)-(x2,y2)."""
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq < 1e-8:
            return np.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        # Parameter along segment [0..1]
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

        # Nearest point on segment
        nx = x1 + t * dx
        ny = y1 + t * dy

        return np.sqrt((px - nx) ** 2 + (py - ny) ** 2)

    def _handle_drag_move(self):
        """
        Handle continuous drag movement.

        Projects mouse delta onto axis screen direction, converts to world
        delta, and emits PreviewPropertyCommand.

        Constitutional Compliance: Principle VI (Optimistic UI)
        """
        if self.dragging_axis is None or self.active_entity_id is None:
            return

        # Get current mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)
        mx, my = mouse_pos[0], mouse_pos[1]

        # Mouse delta from drag start
        delta_mx = mx - self.drag_start_mouse[0]
        delta_my = my - self.drag_start_mouse[1]

        # Use the axis screen direction captured at drag start, not the current frame's
        # direction. This prevents the drag from becoming erratic as the entity moves
        # and changes the projected axis direction each frame.
        screen_dir = self.drag_axis_screen_dir
        if abs(screen_dir[0]) < 1e-8 and abs(screen_dir[1]) < 1e-8:
            return

        # Dot product: how far along the axis we've dragged (in pixels)
        axis_delta_px = delta_mx * screen_dir[0] + delta_my * screen_dir[1]

        # Convert pixel delta to world delta
        # Scale: pixels → world units (approximate based on depth/FOV)
        # Rough scale: 1 pixel ≈ world_scale units at entity depth
        world_scale = 0.01  # Tunable: each pixel ≈ 0.01 world units
        world_delta = axis_delta_px * world_scale

        # Compute new position
        axis_idx = {"x": 0, "y": 1, "z": 2}[self.dragging_axis]
        new_pos = list(self.original_position)
        new_pos[axis_idx] += world_delta

        # Emit PreviewPropertyCommand for the modified axis
        property_path = f"position.{self.dragging_axis}"

        try:
            self.command_queue.put_nowait(PreviewPropertyCommand(
                entity_id=self.active_entity_id,
                property_path=property_path,
                value=new_pos[axis_idx],
            ))
        except Exception:
            pass

    def _on_mouse_release(self, sender, app_data):
        """
        Handle mouse release — commit gizmo drag.

        Emits UpdatePropertyCommand with old_value and new_value.

        Constitutional Compliance: Principle VI (single Undo entry on release)
        """
        if self.dragging_axis is None or self.active_entity_id is None:
            self.dragging_axis = None
            return

        # Get final position
        current_pos = self._get_entity_position()
        if current_pos is None:
            self.dragging_axis = None
            return

        axis_idx = {"x": 0, "y": 1, "z": 2}[self.dragging_axis]
        property_path = f"position.{self.dragging_axis}"

        old_value = self.original_position[axis_idx]
        new_value = current_pos[axis_idx]

        # Only commit if value changed
        if abs(new_value - old_value) > 1e-6:
            try:
                self.command_queue.put_nowait(UpdatePropertyCommand(
                    entity_id=self.active_entity_id,
                    property_path=property_path,
                    old_value=old_value,
                    new_value=new_value,
                ))
            except Exception:
                pass

        self.dragging_axis = None

    def clear(self):
        """Hide gizmo and reset state."""
        self.active_entity_id = None
        self.visible = False
        self.dragging_axis = None
        self._clear_drawlist()
