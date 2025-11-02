"""
Scene tree widget for entity selection.

This module implements a hierarchical tree view of Genesis scene entities,
allowing users to select entities for property inspection and editing.

Constitutional Compliance:
- Principle III: Main-thread DPG operations only
- Principle IV: Commands via queue.Queue for selection changes
- Principle VI: Selection triggers inspector update via events

Phase: 4 (Property Editing & Undo)
Tasks: T092-T095
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Callable, Dict, Any
from src.core.commands import EntitySelectedEvent


# ============================================================================
# Scene Tree Widget
# ============================================================================

class SceneTreeWidget:
    """
    Scene tree widget for displaying and selecting Genesis entities.

    Constitutional Compliance: T092-T095
    - DPG tree node widget for hierarchical entity display
    - Selection callback emits EntitySelectedEvent to event queue
    - Main thread only (DPG requirement)
    """

    def __init__(self, parent_tag: str, event_queue, width: int = 300, height: int = 400):
        """
        Initialize scene tree widget.

        Args:
            parent_tag: DPG parent container tag
            event_queue: Event queue for EntitySelectedEvent
            width: Tree widget width in pixels
            height: Tree widget height in pixels
        """
        self.parent_tag = parent_tag
        self.event_queue = event_queue
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
        """Create DPG tree widget structure."""
        with dpg.child_window(
            tag=self.tree_tag,
            parent=self.parent_tag,
            width=self.width,
            height=self.height,
            border=False,
        ):
            # Tree root node
            self.root_tag = f"{self.tree_tag}_root"
            with dpg.tree_node(
                label="Scene Entities",
                tag=self.root_tag,
                default_open=True,
            ):
                # Entities will be populated here
                dpg.add_text("(No entities loaded)", tag=f"{self.root_tag}_placeholder", color=(150, 150, 150))

    def populate_from_scene(self, scene):
        """
        Populate tree from Genesis scene entities.

        Args:
            scene: Genesis scene object with entities

        Constitutional Compliance: T093
        - Queries Genesis scene for all entities
        - Creates DPG tree nodes for each entity
        - Main thread only (DPG operations)
        """
        # Clear existing entity nodes
        for node_tag in self.entity_nodes.values():
            if dpg.does_item_exist(node_tag):
                dpg.delete_item(node_tag)
        self.entity_nodes.clear()

        # Get all entities from scene
        try:
            entities = scene.entities
        except AttributeError:
            # Fallback: Genesis might use different API
            # For Phase 4, we'll use a simple test with ground/cube/sphere
            entities = []
            if hasattr(scene, 'ground'):
                entities.append(('ground', 0, scene.ground))
            if hasattr(scene, 'rigid_entities'):
                for i, entity in enumerate(scene.rigid_entities):
                    entities.append((f'entity_{i}', i + 1, entity))

        # Clear placeholder text if exists
        if dpg.does_item_exist(f"{self.root_tag}_placeholder"):
            dpg.delete_item(f"{self.root_tag}_placeholder")

        # Create tree nodes for each entity
        for entity_info in entities:
            if isinstance(entity_info, tuple):
                name, entity_id, entity_obj = entity_info
            else:
                # Handle different entity format
                entity_id = getattr(entity_info, 'id', len(self.entity_nodes))
                name = getattr(entity_info, 'name', f'Entity {entity_id}')
                entity_obj = entity_info

            self._add_entity_node(entity_id, name)

    def _add_entity_node(self, entity_id: int, name: str):
        """
        Add entity node to tree.

        Args:
            entity_id: Entity ID
            name: Entity display name

        Constitutional Compliance: T092, T094
        - Uses DPG tree_node with item_handler for click detection
        - Callback emits EntitySelectedEvent
        """
        node_tag = f"{self.tree_tag}_entity_{entity_id}"

        # Create tree node with selectable parameter
        dpg.add_tree_node(
            label=f"{name} (ID: {entity_id})",
            tag=node_tag,
            parent=self.root_tag,
            leaf=True,
            selectable=True,
            user_data=entity_id,
        )

        # Setup item handler for click detection
        handler_tag = f"{node_tag}_handler"
        with dpg.item_handler_registry(tag=handler_tag) as handler:
            dpg.add_item_clicked_handler(
                callback=lambda sender, app_data: self._on_entity_selected(entity_id)
            )

        dpg.bind_item_handler_registry(node_tag, handler_tag)

        self.entity_nodes[entity_id] = node_tag

    def _on_entity_selected(self, entity_id: int):
        """
        Handle entity selection.

        Args:
            entity_id: Selected entity ID

        Constitutional Compliance: T094
        - Emits EntitySelectedEvent to event queue
        - Event triggers inspector update in GUI loop
        """
        # Update selection state
        self.selected_entity_id = entity_id

        # Emit selection event
        event = EntitySelectedEvent(entity_id=entity_id)
        try:
            self.event_queue.put_nowait(event)
            print(f"[SCENE_TREE] Entity {entity_id} selected")
        except Exception as e:
            print(f"[SCENE_TREE] Failed to emit EntitySelectedEvent: {e}")

    def get_selected_entity_id(self) -> Optional[int]:
        """Get currently selected entity ID."""
        return self.selected_entity_id

    def clear_selection(self):
        """Clear entity selection."""
        self.selected_entity_id = None
        # Emit deselection event
        event = EntitySelectedEvent(entity_id=None)
        try:
            self.event_queue.put_nowait(event)
        except Exception as e:
            print(f"[SCENE_TREE] Failed to emit deselection event: {e}")


# ============================================================================
# Utility Functions
# ============================================================================

def create_scene_tree(
    parent_tag: str,
    event_queue,
    width: int = 300,
    height: int = 400,
) -> SceneTreeWidget:
    """
    Create and return scene tree widget.

    Args:
        parent_tag: DPG parent container tag
        event_queue: Event queue for EntitySelectedEvent
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
        event_queue=event_queue,
        width=width,
        height=height,
    )
