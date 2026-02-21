"""
Scene tree widget for entity selection.

This module implements a list view of Genesis scene entities,
allowing users to select entities for property inspection and editing.

Constitutional Compliance:
- Principle III: Main-thread DPG operations only
- Principle VI: Selection triggers inspector update via direct callback

Phase: 4 (Property Editing & Undo)
Tasks: T092-T095
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Callable, Dict, Any


# ============================================================================
# Scene Tree Widget
# ============================================================================

class SceneTreeWidget:
    """
    Scene tree widget for displaying and selecting Genesis entities.

    Constitutional Compliance: T092-T095
    - DPG selectable widgets for clickable entity list
    - Selection triggers direct callback (no event queue round-trip)
    - Main thread only (DPG requirement)
    """

    def __init__(self, parent_tag: str, on_select: Optional[Callable] = None, width: int = 300, height: int = 400):
        """
        Initialize scene tree widget.

        Args:
            parent_tag: DPG parent container tag
            on_select: Callback when entity selected/deselected.
                       Signature: on_select(entity_id: Optional[int])
                       entity_id=None means deselection.
            width: Tree widget width in pixels
            height: Tree widget height in pixels
        """
        self.parent_tag = parent_tag
        self.on_select = on_select
        self.width = width
        self.height = height

        # Selection state
        self.selected_entity_id: Optional[int] = None

        # DPG widget tags
        self.tree_tag = f"{parent_tag}_scene_tree"
        self.entity_nodes: Dict[int, str] = {}  # entity_id -> DPG node tag

        # Create tree widget
        self._create_tree()

    def _create_tree(self):
        """Create DPG entity list structure (no tree_node to avoid click swallowing)."""
        with dpg.child_window(
            tag=self.tree_tag,
            parent=self.parent_tag,
            width=self.width,
            height=self.height,
            border=False,
        ):
            # Header
            dpg.add_text("Scene Entities", color=(200, 200, 200))
            dpg.add_separator()

            # Container group for entity items
            self.list_tag = f"{self.tree_tag}_list"
            dpg.add_group(tag=self.list_tag)

            # Placeholder text
            self.placeholder_tag = f"{self.tree_tag}_placeholder"
            dpg.add_text(
                "(No entities loaded)",
                tag=self.placeholder_tag,
                parent=self.list_tag,
                color=(150, 150, 150),
            )

    def populate_from_scene(self, scene):
        """
        Populate list from Genesis scene entities.

        Args:
            scene: Genesis scene object with entities

        Constitutional Compliance: T093
        - Queries Genesis scene for all entities
        - Creates DPG selectables for each entity
        - Main thread only (DPG operations)
        """
        # Clear existing entity nodes
        for node_tag in self.entity_nodes.values():
            if dpg.does_item_exist(node_tag):
                dpg.delete_item(node_tag)
        self.entity_nodes.clear()

        # Remove placeholder
        if dpg.does_item_exist(self.placeholder_tag):
            dpg.delete_item(self.placeholder_tag)

        # Enumerate entities from scene
        entity_list = self._enumerate_entities(scene)

        if not entity_list:
            print("[SCENE_TREE] Warning: No entities found in scene")
            dpg.add_text(
                "(No entities found)",
                tag=self.placeholder_tag,
                parent=self.list_tag,
                color=(150, 150, 150),
            )
            return

        # Create selectable for each entity
        for entity_id, name in entity_list:
            self._add_entity_node(entity_id, name)

        print(f"[SCENE_TREE] Populated {len(entity_list)} entities")

    def _enumerate_entities(self, scene):
        """
        Enumerate entities from Genesis scene.

        Tries multiple Genesis API patterns to find entities.

        Args:
            scene: Genesis scene object

        Returns:
            List of (entity_id, name) tuples
        """
        result = []

        # Strategy 1: scene.entities (most common Genesis API)
        try:
            entities = scene.entities
            if entities is not None and len(entities) > 0:
                for i, entity in enumerate(entities):
                    name = getattr(entity, 'name', None)
                    if name is None:
                        # Try to determine type from morph
                        morph = getattr(entity, 'morph', None)
                        if morph is not None:
                            type_name = type(morph).__name__
                            name = f"{type_name} {i}"
                        else:
                            name = f"Entity {i}"
                    eid = getattr(entity, 'id', i)
                    result.append((eid, name))
                print(f"[SCENE_TREE] Found {len(result)} entities via scene.entities")
                return result
        except (AttributeError, TypeError) as e:
            print(f"[SCENE_TREE] scene.entities failed: {e}")

        # Strategy 2: scene.rigid_solver.entities or similar
        try:
            if hasattr(scene, 'rigid_solver') and scene.rigid_solver is not None:
                solver = scene.rigid_solver
                if hasattr(solver, 'entities'):
                    for i, entity in enumerate(solver.entities):
                        name = getattr(entity, 'name', f"Rigid {i}")
                        eid = getattr(entity, 'id', i)
                        result.append((eid, name))
                    if result:
                        print(f"[SCENE_TREE] Found {len(result)} entities via rigid_solver")
                        return result
        except Exception as e:
            print(f"[SCENE_TREE] rigid_solver fallback failed: {e}")

        # Strategy 3: Generic fallback with index-based naming (no hardcoded scene assumptions)
        try:
            entities = getattr(scene, 'entities', None)
            if entities is not None:
                for i, entity in enumerate(entities):
                    name = getattr(entity, 'name', f"Entity {i}")
                    eid = getattr(entity, 'id', i)
                    result.append((eid, name))
                if result:
                    print(f"[SCENE_TREE] Found {len(result)} entities via generic fallback")
                    return result
        except Exception as e:
            print(f"[SCENE_TREE] generic fallback failed: {e}")

        print("[SCENE_TREE] No entities discovered")
        return result

    def _add_entity_node(self, entity_id: int, name: str):
        """
        Add entity item to list.

        Args:
            entity_id: Entity ID
            name: Entity display name

        Constitutional Compliance: T092, T094
        - Uses DPG add_selectable for reliable click detection
        - Direct callback to inspector (no event queue round-trip)
        """
        node_tag = f"{self.tree_tag}_entity_{entity_id}"

        # Use closure to capture entity_id per item
        eid = entity_id

        def on_click(sender, app_data, user_data):
            self._on_entity_clicked(sender, app_data, eid)

        dpg.add_selectable(
            label=f"  {name}",
            tag=node_tag,
            parent=self.list_tag,
            callback=on_click,
        )

        self.entity_nodes[entity_id] = node_tag
        print(f"[SCENE_TREE] Added entity: {name} (ID: {entity_id})")

    def _on_entity_clicked(self, sender, app_data, entity_id):
        """
        Handle entity click via DPG selectable callback.

        Args:
            sender: DPG widget that triggered callback
            app_data: DPG app data (unused)
            entity_id: Entity ID from closure

        Constitutional Compliance: T094
        - Direct callback to inspector (no event queue round-trip)
        """
        is_selected = dpg.get_value(sender)

        if is_selected:
            # Deselect previous selection
            if self.selected_entity_id is not None and self.selected_entity_id != entity_id:
                prev_tag = self.entity_nodes.get(self.selected_entity_id)
                if prev_tag and dpg.does_item_exist(prev_tag):
                    dpg.set_value(prev_tag, False)

            self.selected_entity_id = entity_id
            print(f"[SCENE_TREE] Entity {entity_id} selected")

            if self.on_select is not None:
                self.on_select(entity_id)
        else:
            # Deselection (clicked same item again)
            self.selected_entity_id = None
            print("[SCENE_TREE] Selection cleared")

            if self.on_select is not None:
                self.on_select(None)

    def set_on_select(self, callback: Callable):
        """
        Set selection callback (for late binding after inspector creation).

        Args:
            callback: on_select(entity_id: Optional[int])
        """
        self.on_select = callback

    def get_selected_entity_id(self) -> Optional[int]:
        """Get currently selected entity ID."""
        return self.selected_entity_id

    def select_entity(self, entity_id: Optional[int]):
        """
        Programmatically select an entity (e.g., from raycast).

        Updates DPG selectable highlight without triggering on_select callback
        (to avoid recursive loops when raycast result syncs back to tree).

        Args:
            entity_id: Entity ID to select, or None to clear.

        Phase 6: T142 (raycast → scene tree sync)
        """
        # Deselect previous
        if self.selected_entity_id is not None and self.selected_entity_id != entity_id:
            prev_tag = self.entity_nodes.get(self.selected_entity_id)
            if prev_tag and dpg.does_item_exist(prev_tag):
                dpg.set_value(prev_tag, False)

        if entity_id is not None and entity_id in self.entity_nodes:
            # Select new
            node_tag = self.entity_nodes[entity_id]
            if dpg.does_item_exist(node_tag):
                dpg.set_value(node_tag, True)
            self.selected_entity_id = entity_id
        else:
            self.selected_entity_id = None

    def clear_selection(self):
        """Clear entity selection."""
        # Deselect current in DPG
        if self.selected_entity_id is not None:
            prev_tag = self.entity_nodes.get(self.selected_entity_id)
            if prev_tag and dpg.does_item_exist(prev_tag):
                dpg.set_value(prev_tag, False)

        self.selected_entity_id = None

        if self.on_select is not None:
            self.on_select(None)


# ============================================================================
# Utility Functions
# ============================================================================

def create_scene_tree(
    parent_tag: str,
    on_select: Optional[Callable] = None,
    width: int = 300,
    height: int = 400,
) -> SceneTreeWidget:
    """
    Create and return scene tree widget.

    Args:
        parent_tag: DPG parent container tag
        on_select: Callback when entity selected/deselected.
                   Signature: on_select(entity_id: Optional[int])
        width: Tree widget width
        height: Tree widget height

    Returns:
        SceneTreeWidget instance

    Constitutional Compliance: T092
    - Factory function for scene tree creation
    - Returns widget instance for integration with main window
    """
    return SceneTreeWidget(
        parent_tag=parent_tag,
        on_select=on_select,
        width=width,
        height=height,
    )
