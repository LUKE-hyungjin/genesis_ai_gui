"""
Genesis scene setup utilities for Phase 2 testing.

This module provides functions to create simple test scenes for validating
the Genesis→DPG rendering pipeline.

Constitutional Compliance: Principle I (Init-Main, Run-Threaded)
"""

import genesis as gs


# ============================================================================
# Scene Metrics (Phase 5: T125)
# ============================================================================

def compute_kinetic_energy(scene) -> float:
    """
    Compute total kinetic energy of all dynamic entities.

    KE = sum(0.5 * m * |v|^2) for entities with velocity.

    Args:
        scene: Genesis scene object

    Returns:
        Total kinetic energy (float)
    """
    total_ke = 0.0
    try:
        for entity in scene.entities:
            if not hasattr(entity, 'get_vel'):
                continue
            vel = entity.get_vel()
            if hasattr(vel, 'tolist'):
                vel = vel.tolist()
            elif hasattr(vel, '__iter__'):
                vel = list(vel)
            else:
                continue
            mass = getattr(entity, 'mass', 1.0)
            if hasattr(mass, 'item'):
                mass = mass.item()
            speed_sq = sum(v ** 2 for v in vel)
            total_ke += 0.5 * float(mass) * speed_sq
    except Exception:
        pass
    return total_ke


# ============================================================================
# Scene Creation (Phase 2: T041)
# ============================================================================

def create_test_scene(scene: gs.Scene) -> None:
    """
    Create simple test scene for Phase 2 validation.

    Scene contains:
    - Ground plane (static)
    - Cube (dynamic rigid body)
    - Sphere (dynamic rigid body)
    - Camera positioned to view all objects

    Constitutional Compliance:
    - Scene must be created on main thread (Principle I)
    - Called after gs.init() and before background thread starts

    Args:
        scene: Genesis Scene object (already created on main thread)
    """
    print("[SCENE] Creating test scene...")

    # Add ground plane
    scene.add_entity(
        gs.morphs.Plane(),
    )
    print("[SCENE] Added ground plane")

    # Add cube (dynamic rigid body)
    scene.add_entity(
        gs.morphs.Box(
            pos=(0.0, 0.0, 1.0),
            size=(0.5, 0.5, 0.5),
        ),
    )
    print("[SCENE] Added cube at (0, 0, 1)")

    # Add sphere (dynamic rigid body)
    scene.add_entity(
        gs.morphs.Sphere(
            pos=(1.0, 0.0, 1.5),
            radius=0.3,
        ),
    )
    print("[SCENE] Added sphere at (1, 0, 1.5)")

    print("[SCENE] Test scene created successfully")


def create_camera(scene: gs.Scene, width: int = 1280, height: int = 720):
    """
    Create camera for rendering.

    Constitutional Compliance:
    - Camera must be created on main thread (Principle I)

    Args:
        scene: Genesis Scene object
        width: Camera resolution width (default 1280)
        height: Camera resolution height (default 720)

    Returns:
        Camera object
    """
    camera = scene.add_camera(
        res=(width, height),
        pos=(3.0, -3.0, 2.0),
        lookat=(0.0, 0.0, 0.5),
    )
    print(f"[SCENE] Camera created: {width}x{height}, pos=(3, -3, 2)")
    return camera
