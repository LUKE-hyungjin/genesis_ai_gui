"""
Screen-space projection picking for viewport entity selection.

This module implements entity picking by projecting 3D world positions
to 2D screen coordinates via view-projection matrices, then finding
the closest entity to the click point.

Constitutional Compliance:
- Principle IV (Data Pathway Segregation): Called from sim thread via RayCastCommand
- Principle VII (Performance Targets): Pick latency < 100ms
"""

import numpy as np
from typing import Optional, Tuple


# ============================================================================
# Matrix Builders
# ============================================================================

def build_view_matrix(
    cam_pos: Tuple[float, float, float],
    cam_lookat: Tuple[float, float, float],
    cam_up: Tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> np.ndarray:
    """
    Build 4x4 view matrix (world → camera space).

    Args:
        cam_pos: Camera world position (x, y, z)
        cam_lookat: Camera look-at target (x, y, z)
        cam_up: Camera up vector (default Z-up)

    Returns:
        4x4 float64 view matrix
    """
    eye = np.array(cam_pos, dtype=np.float64)
    target = np.array(cam_lookat, dtype=np.float64)
    up = np.array(cam_up, dtype=np.float64)

    # Forward (camera looks along -Z in camera space)
    forward = target - eye
    forward = forward / np.linalg.norm(forward)

    # Right
    right = np.cross(forward, up)
    norm = np.linalg.norm(right)
    if norm < 1e-8:
        # Fallback: use Y-up if Z-up is degenerate
        up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        right = np.cross(forward, up)
        norm = np.linalg.norm(right)
    right = right / norm

    # Recompute true up
    true_up = np.cross(right, forward)

    # Build view matrix (rotation + translation)
    view = np.eye(4, dtype=np.float64)
    view[0, :3] = right
    view[1, :3] = true_up
    view[2, :3] = -forward
    view[0, 3] = -np.dot(right, eye)
    view[1, 3] = -np.dot(true_up, eye)
    view[2, 3] = np.dot(forward, eye)

    return view


def build_projection_matrix(
    fov_deg: float = 60.0,
    aspect: float = 16.0 / 9.0,
    near: float = 0.01,
    far: float = 100.0,
) -> np.ndarray:
    """
    Build 4x4 perspective projection matrix.

    Args:
        fov_deg: Vertical field of view in degrees
        aspect: Width / height aspect ratio
        near: Near clipping plane
        far: Far clipping plane

    Returns:
        4x4 float64 projection matrix
    """
    fov_rad = np.radians(fov_deg)
    f = 1.0 / np.tan(fov_rad / 2.0)

    proj = np.zeros((4, 4), dtype=np.float64)
    proj[0, 0] = f / aspect
    proj[1, 1] = f
    proj[2, 2] = (far + near) / (near - far)
    proj[2, 3] = (2.0 * far * near) / (near - far)
    proj[3, 2] = -1.0

    return proj


# ============================================================================
# Projection Helpers
# ============================================================================

def project_to_screen(
    world_pos: Tuple[float, float, float],
    view_mat: np.ndarray,
    proj_mat: np.ndarray,
) -> Tuple[float, float, float]:
    """
    Project 3D world position to normalized [0..1] screen coordinates.

    Args:
        world_pos: 3D position (x, y, z)
        view_mat: 4x4 view matrix
        proj_mat: 4x4 projection matrix

    Returns:
        (x_norm, y_norm, depth) where x_norm/y_norm in [0..1] and depth is Z in camera space.
        Returns (-1, -1, -1) if behind camera.
    """
    # Homogeneous world position
    pos4 = np.array([world_pos[0], world_pos[1], world_pos[2], 1.0], dtype=np.float64)

    # Transform to clip space
    view_pos = view_mat @ pos4
    clip_pos = proj_mat @ view_pos

    # Behind camera check
    if clip_pos[3] <= 0:
        return (-1.0, -1.0, -1.0)

    # Perspective divide → NDC [-1..1]
    ndc = clip_pos[:3] / clip_pos[3]

    # Convert to screen [0..1] (Y inverted: NDC Y+ is up, screen Y+ is down)
    x_norm = (ndc[0] + 1.0) * 0.5
    y_norm = (1.0 - ndc[1]) * 0.5

    return (x_norm, y_norm, -view_pos[2])  # depth = distance from camera


def project_direction_to_screen(
    origin: Tuple[float, float, float],
    direction: Tuple[float, float, float],
    view_mat: np.ndarray,
    proj_mat: np.ndarray,
    scale: float = 0.5,
) -> Tuple[float, float]:
    """
    Project a 3D direction vector to 2D screen-space direction.

    Projects origin and origin+direction*scale, returns normalized 2D direction.

    Args:
        origin: 3D origin position
        direction: 3D unit direction vector
        view_mat: 4x4 view matrix
        proj_mat: 4x4 projection matrix
        scale: Scale factor for direction endpoint

    Returns:
        (dx_screen, dy_screen) normalized 2D screen direction
    """
    p0 = project_to_screen(origin, view_mat, proj_mat)
    endpoint = (
        origin[0] + direction[0] * scale,
        origin[1] + direction[1] * scale,
        origin[2] + direction[2] * scale,
    )
    p1 = project_to_screen(endpoint, view_mat, proj_mat)

    if p0[2] < 0 or p1[2] < 0:
        return (0.0, 0.0)

    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = np.sqrt(dx * dx + dy * dy)

    if length < 1e-8:
        return (0.0, 0.0)

    return (dx / length, dy / length)


# ============================================================================
# Camera Parameter Extraction
# ============================================================================

def get_camera_params(camera) -> dict:
    """
    Extract camera parameters from Genesis camera object.

    Uses attribute access with fallback defaults for compatibility.

    Args:
        camera: Genesis camera object

    Returns:
        Dict with pos, lookat, fov, res, up keys
    """
    params = {}

    # Position
    if hasattr(camera, 'pos'):
        pos = camera.pos
        if hasattr(pos, 'tolist'):
            params['pos'] = tuple(pos.tolist())
        elif hasattr(pos, '__iter__'):
            params['pos'] = tuple(pos)
        else:
            params['pos'] = (3.0, -3.0, 2.0)
    else:
        params['pos'] = (3.0, -3.0, 2.0)

    # Lookat
    if hasattr(camera, 'lookat'):
        lookat = camera.lookat
        if hasattr(lookat, 'tolist'):
            params['lookat'] = tuple(lookat.tolist())
        elif hasattr(lookat, '__iter__'):
            params['lookat'] = tuple(lookat)
        else:
            params['lookat'] = (0.0, 0.0, 0.5)
    else:
        params['lookat'] = (0.0, 0.0, 0.5)

    # FOV
    if hasattr(camera, 'fov'):
        fov = camera.fov
        if hasattr(fov, 'item'):
            params['fov'] = float(fov.item())
        else:
            params['fov'] = float(fov)
    else:
        params['fov'] = 60.0

    # Resolution
    if hasattr(camera, 'res'):
        res = camera.res
        if hasattr(res, 'tolist'):
            params['res'] = tuple(res.tolist())
        elif hasattr(res, '__iter__'):
            params['res'] = tuple(res)
        else:
            params['res'] = (1280, 720)
    else:
        params['res'] = (1280, 720)

    # Up vector (default Z-up for Genesis)
    params['up'] = (0.0, 0.0, 1.0)

    return params


# ============================================================================
# Entity Picking (T140)
# ============================================================================

def pick_nearest_entity(
    x_norm: float,
    y_norm: float,
    scene,
    camera,
    pick_radius: float = 0.05,
) -> Optional[int]:
    """
    Pick the nearest entity to a screen click point.

    Projects all entity positions to screen space, finds the closest
    one within pick_radius of the click point.

    Args:
        x_norm: Normalized screen X [0..1]
        y_norm: Normalized screen Y [0..1]
        scene: Genesis scene object
        camera: Genesis camera object
        pick_radius: Maximum normalized distance for pick (default 0.05 ≈ 30px at 680px)

    Returns:
        Entity index (int) or None if no entity within radius.
        Skips entity 0 (ground plane).

    Performance Target: < 100ms for small scenes (< 100 entities)
    """
    try:
        # Build matrices from camera params
        cam = get_camera_params(camera)
        view_mat = build_view_matrix(cam['pos'], cam['lookat'], cam['up'])
        aspect = cam['res'][0] / cam['res'][1]
        proj_mat = build_projection_matrix(cam['fov'], aspect)

        # Get entities
        if not hasattr(scene, 'entities'):
            return None

        entities = scene.entities
        if not entities:
            return None

        best_entity_id = None
        best_dist = float('inf')

        for i, entity in enumerate(entities):
            # Skip ground plane (entity 0)
            if i == 0:
                continue

            # Get entity position
            try:
                pos = entity.get_pos()
                if hasattr(pos, 'tolist'):
                    pos = pos.tolist()
                elif hasattr(pos, '__iter__'):
                    pos = list(pos)
                else:
                    continue
            except Exception:
                continue

            # Project to screen
            sx, sy, depth = project_to_screen(tuple(pos), view_mat, proj_mat)

            # Skip if behind camera or off screen
            if depth < 0 or sx < 0 or sx > 1 or sy < 0 or sy > 1:
                continue

            # Distance to click point
            dist = np.sqrt((sx - x_norm) ** 2 + (sy - y_norm) ** 2)

            if dist < pick_radius and dist < best_dist:
                best_dist = dist
                best_entity_id = i

        return best_entity_id

    except Exception as e:
        print(f"[PICKING] Error in pick_nearest_entity: {e}")
        return None
