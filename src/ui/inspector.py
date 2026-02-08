"""
Property inspector widget for entity property editing.

This module implements a property inspector that displays and allows editing
of selected entity properties with Undo/Redo support.

Constitutional Compliance:
- Principle VI: Optimistic UI (preview during drag, commit on release)
- Principle III: Main-thread DPG operations only
- Principle IV: Commands via queue.Queue

Phase: 4 (Property Editing & Undo)
Tasks: T096-T101
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Dict, Any, Callable, Tuple, List
from dataclasses import dataclass
from src.core.commands import PreviewPropertyCommand, UpdatePropertyCommand


# ============================================================================
# Property Metadata
# ============================================================================

@dataclass
class PropertyMetadata:
    """
    Metadata for a single property.

    Used for widget type selection and validation.
    """
    path: str                    # Property path (e.g., "position.x")
    display_name: str           # Human-readable name
    value_type: str             # "float", "int", "bool", "vec3", "enum"
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    enum_options: Optional[list] = None


# ============================================================================
# Property Inspector Widget
# ============================================================================

class PropertyInspectorWidget:
    """
    Property inspector for displaying and editing entity properties.

    Constitutional Compliance: T096-T101
    - Widget registry for property type → DPG widget mapping
    - Preview callbacks emit PreviewPropertyCommand (no Undo)
    - Commit callbacks emit UpdatePropertyCommand (with Undo)
    - Original value stored at drag start for Undo support
    """

    def __init__(self, parent_tag: str, command_queue, width: int = 300, height: int = 600, scene_lock=None):
        """
        Initialize property inspector.

        Args:
            parent_tag: DPG parent container tag
            command_queue: Command queue for property edit commands
            width: Inspector width in pixels
            height: Inspector height in pixels
            scene_lock: Optional lock for thread-safe scene state reads.
                         Should be the same lock used by FrameBuffer (TimedLock).
        """
        self.parent_tag = parent_tag
        self.command_queue = command_queue
        self.width = width
        self.height = height
        self.scene_lock = scene_lock

        # Inspector state
        self.current_entity_id: Optional[int] = None
        self.current_scene = None  # Reference to Genesis scene
        self.properties: Dict[str, PropertyMetadata] = {}

        # Edit state (for Undo support)
        self.drag_active: Dict[str, bool] = {}  # property_path → is_dragging
        self.original_values: Dict[str, Any] = {}  # property_path → value at drag start

        # DPG widget tags
        self.inspector_tag = f"{parent_tag}_inspector"
        self.property_widgets: Dict[str, str] = {}  # property_path → DPG widget tag

        # Create inspector window
        self._create_inspector()

    def _create_inspector(self):
        """Create DPG inspector widget structure."""
        with dpg.child_window(
            tag=self.inspector_tag,
            parent=self.parent_tag,
            width=self.width,
            height=self.height,
            border=True,
        ):
            # Header
            dpg.add_text("Property Inspector", color=(200, 200, 200))
            dpg.add_separator()

            # Selected entity display
            self.entity_label_tag = f"{self.inspector_tag}_entity_label"
            dpg.add_text("No entity selected", tag=self.entity_label_tag, color=(150, 150, 150))

            dpg.add_separator()

            # Properties container (will be populated dynamically)
            self.properties_container_tag = f"{self.inspector_tag}_properties"
            with dpg.group(tag=self.properties_container_tag):
                pass

    def set_scene_reference(self, scene):
        """
        Set Genesis scene reference for property queries.

        Args:
            scene: Genesis scene object
        """
        self.current_scene = scene

    def populate_inspector(self, entity_id: int):
        """
        Populate inspector with entity properties.

        Args:
            entity_id: Entity ID to inspect

        Constitutional Compliance: T098
        - Queries entity properties from Genesis scene
        - Creates appropriate DPG widgets based on property types
        - Wires callbacks for preview and commit
        """
        if self.current_scene is None:
            print("[INSPECTOR] No scene reference set")
            return

        # Update state
        self.current_entity_id = entity_id

        # Update header
        dpg.set_value(self.entity_label_tag, f"Entity ID: {entity_id}")

        # Clear existing property widgets
        self._clear_properties()

        # Query entity properties
        properties = self._query_entity_properties(entity_id)

        # Create widgets for each property
        for prop in properties:
            self._add_property_widget(prop)

    def _query_entity_properties(self, entity_id: int) -> List[PropertyMetadata]:
        """
        Query entity properties from scene.

        Args:
            entity_id: Entity ID

        Returns:
            List of PropertyMetadata

        Constitutional Compliance: T098
        - Queries Genesis scene for entity properties
        - Returns metadata for widget creation
        """
        properties = []

        # For Phase 4 testing: Simple hardcoded properties
        # TODO: Replace with actual Genesis scene property introspection
        if entity_id == 0:  # Ground
            properties.append(PropertyMetadata(
                path="position.z",
                display_name="Height (Z)",
                value_type="float",
                min_val=-5.0,
                max_val=5.0,
            ))
        else:  # Cube/Sphere
            properties.extend([
                PropertyMetadata(
                    path="position.x",
                    display_name="Position X",
                    value_type="float",
                    min_val=-10.0,
                    max_val=10.0,
                ),
                PropertyMetadata(
                    path="position.y",
                    display_name="Position Y",
                    value_type="float",
                    min_val=-10.0,
                    max_val=10.0,
                ),
                PropertyMetadata(
                    path="position.z",
                    display_name="Position Z",
                    value_type="float",
                    min_val=0.0,
                    max_val=20.0,
                ),
            ])

        return properties

    def _add_property_widget(self, prop: PropertyMetadata):
        """
        Add property widget to inspector.

        Args:
            prop: Property metadata

        Constitutional Compliance: T097, T099-T101
        - Widget type selected based on property type
        - Callbacks wired for preview (drag) and commit (release)
        - Original value stored at drag start
        """
        widget_tag = f"{self.inspector_tag}_prop_{prop.path.replace('.', '_')}"
        self.property_widgets[prop.path] = widget_tag

        # Get current property value
        current_value = self._get_property_value(prop.path)

        # Create widget based on type (T097)
        parent = self.properties_container_tag

        # Label
        dpg.add_text(prop.display_name, parent=parent, color=(180, 180, 180))

        if prop.value_type == "float":
            # Float slider (T097)
            dpg.add_slider_float(
                tag=widget_tag,
                parent=parent,
                default_value=current_value,
                min_value=prop.min_val if prop.min_val is not None else -100.0,
                max_value=prop.max_val if prop.max_val is not None else 100.0,
                width=self.width - 40,
                callback=lambda s, v, u: self._on_preview(prop.path, v),
                user_data=prop.path,
            )

            # Setup drag start/end callbacks for Undo support (T101)
            with dpg.item_handler_registry() as handler:
                dpg.add_item_active_handler(
                    callback=lambda: self._on_drag_start(prop.path)
                )
                dpg.add_item_deactivated_handler(
                    callback=lambda: self._on_drag_end(prop.path)
                )
            dpg.bind_item_handler_registry(widget_tag, handler)

        elif prop.value_type == "int":
            # Integer slider (T097)
            dpg.add_slider_int(
                tag=widget_tag,
                parent=parent,
                default_value=int(current_value),
                min_value=int(prop.min_val) if prop.min_val is not None else -100,
                max_value=int(prop.max_val) if prop.max_val is not None else 100,
                width=self.width - 40,
                callback=lambda s, v, u: self._on_preview(prop.path, v),
                user_data=prop.path,
            )

        elif prop.value_type == "bool":
            # Boolean checkbox (T097)
            dpg.add_checkbox(
                tag=widget_tag,
                parent=parent,
                default_value=bool(current_value),
                callback=lambda s, v, u: self._on_commit_immediate(prop.path, v),
                user_data=prop.path,
            )

        elif prop.value_type == "vec3":
            # Vec3 input (T097)
            dpg.add_input_floatx(
                tag=widget_tag,
                parent=parent,
                default_value=list(current_value) if current_value else [0.0, 0.0, 0.0],
                size=3,
                width=self.width - 40,
                callback=lambda s, v, u: self._on_preview(prop.path, tuple(v)),
                user_data=prop.path,
            )

        elif prop.value_type == "enum" and prop.enum_options:
            # Enum combo box (T097)
            dpg.add_combo(
                tag=widget_tag,
                parent=parent,
                items=prop.enum_options,
                default_value=current_value,
                width=self.width - 40,
                callback=lambda s, v, u: self._on_commit_immediate(prop.path, v),
                user_data=prop.path,
            )

        dpg.add_separator(parent=parent)

        # Store property metadata
        self.properties[prop.path] = prop

        # Initialize drag state
        self.drag_active[prop.path] = False
        self.original_values[prop.path] = current_value

    def _get_property_value(self, property_path: str) -> Any:
        """
        Get current property value from scene (thread-safe).

        Uses scene_lock to synchronize with simulation thread when reading
        entity state, preventing race conditions.

        Args:
            property_path: Property path (e.g., "position.x")

        Returns:
            Current property value
        """
        if self.current_entity_id is None or self.current_scene is None:
            return 0.0

        try:
            # Get entity from scene
            if not hasattr(self.current_scene, 'entities') or self.current_entity_id >= len(self.current_scene.entities):
                return 0.0

            entity = self.current_scene.entities[self.current_entity_id]

            # Parse property path
            path_parts = property_path.split('.')

            # Use scene_lock for thread-safe reads if available
            if self.scene_lock is not None:
                with self.scene_lock:
                    return self._read_property(entity, path_parts)
            else:
                return self._read_property(entity, path_parts)

        except Exception as e:
            print(f"[INSPECTOR] Failed to get property {property_path}: {e}")
            return 0.0

    def _read_property(self, entity, path_parts: list) -> Any:
        """
        Read property value from entity (must be called under lock if threaded).

        Args:
            entity: Genesis entity object
            path_parts: Property path split into parts

        Returns:
            Property value
        """
        if path_parts[0] == 'position':
            # Get position from entity
            pos = entity.get_pos()

            # Convert to list if needed
            if hasattr(pos, 'tolist'):
                pos_list = pos.tolist()
            else:
                pos_list = list(pos)

            # Return specific axis
            if len(path_parts) == 2:
                axis = path_parts[1].lower()
                if axis == 'x':
                    return float(pos_list[0])
                elif axis == 'y':
                    return float(pos_list[1])
                elif axis == 'z':
                    return float(pos_list[2])

        # Generic property access (for future properties)
        obj = entity
        for part in path_parts:
            obj = getattr(obj, part)
        return obj

    def _on_drag_start(self, property_path: str):
        """
        Handle drag start (store original value).

        Args:
            property_path: Property being edited

        Constitutional Compliance: T101
        - Stores original value for UpdatePropertyCommand.old_value
        - Marks drag as active
        """
        self.drag_active[property_path] = True
        self.original_values[property_path] = self._get_property_value(property_path)
        print(f"[INSPECTOR] Drag start: {property_path} = {self.original_values[property_path]}")

    def _on_drag_end(self, property_path: str):
        """
        Handle drag end (commit change).

        Args:
            property_path: Property being edited

        Constitutional Compliance: T100
        - Emits UpdatePropertyCommand with old_value and new_value
        - Creates single Undo entry
        """
        if not self.drag_active.get(property_path, False):
            return

        self.drag_active[property_path] = False

        # Get final value
        widget_tag = self.property_widgets.get(property_path)
        if widget_tag and dpg.does_item_exist(widget_tag):
            new_value = dpg.get_value(widget_tag)
            old_value = self.original_values.get(property_path)

            # Only commit if value changed
            if new_value != old_value:
                self._on_commit(property_path, old_value, new_value)

    def _on_preview(self, property_path: str, value: Any):
        """
        Handle property preview (during drag).

        Args:
            property_path: Property being edited
            value: Preview value

        Constitutional Compliance: T099
        - Emits PreviewPropertyCommand (no Undo)
        - Provides immediate visual feedback
        """
        if self.current_entity_id is None:
            return

        # Emit preview command
        command = PreviewPropertyCommand(
            entity_id=self.current_entity_id,
            property_path=property_path,
            value=value,
        )

        try:
            self.command_queue.put_nowait(command)
        except Exception as e:
            print(f"[INSPECTOR] Failed to emit PreviewPropertyCommand: {e}")

    def _on_commit(self, property_path: str, old_value: Any, new_value: Any):
        """
        Handle property commit (on release).

        Args:
            property_path: Property being edited
            old_value: Value before editing
            new_value: Value after editing

        Constitutional Compliance: T100
        - Emits UpdatePropertyCommand (with Undo support)
        - Creates single Undo entry for entire drag operation
        """
        if self.current_entity_id is None:
            return

        # Emit update command
        command = UpdatePropertyCommand(
            entity_id=self.current_entity_id,
            property_path=property_path,
            old_value=old_value,
            new_value=new_value,
        )

        try:
            self.command_queue.put_nowait(command)
            print(f"[INSPECTOR] Committed: {property_path} {old_value} → {new_value}")
        except Exception as e:
            print(f"[INSPECTOR] Failed to emit UpdatePropertyCommand: {e}")

    def _on_commit_immediate(self, property_path: str, value: Any):
        """
        Handle immediate commit (for checkboxes, combos).

        Args:
            property_path: Property being edited
            value: New value

        Constitutional Compliance: T100
        - Emits UpdatePropertyCommand immediately (no drag)
        - Uses previous value as old_value
        - Skips if value unchanged (avoids UpdatePropertyCommand validation error)
        """
        if self.current_entity_id is None:
            return

        old_value = self._get_property_value(property_path)

        # Skip if value unchanged
        if old_value == value:
            return

        # Emit update command
        command = UpdatePropertyCommand(
            entity_id=self.current_entity_id,
            property_path=property_path,
            old_value=old_value,
            new_value=value,
        )

        try:
            self.command_queue.put_nowait(command)
            print(f"[INSPECTOR] Committed: {property_path} {old_value} → {value}")
        except Exception as e:
            print(f"[INSPECTOR] Failed to emit UpdatePropertyCommand: {e}")

    def update_property_display(self, property_path: str, value: Any):
        """
        Update property display (from PropertyChangedEvent).

        Args:
            property_path: Property path
            value: New value to display
        """
        widget_tag = self.property_widgets.get(property_path)
        if widget_tag and dpg.does_item_exist(widget_tag):
            dpg.set_value(widget_tag, value)

    def _clear_properties(self):
        """Clear all property widgets."""
        # Delete all property widgets
        for widget_tag in self.property_widgets.values():
            if dpg.does_item_exist(widget_tag):
                dpg.delete_item(widget_tag)

        # Clear all child items in properties container
        if dpg.does_item_exist(self.properties_container_tag):
            dpg.delete_item(self.properties_container_tag, children_only=True)

        # Reset state
        self.property_widgets.clear()
        self.properties.clear()
        self.drag_active.clear()
        self.original_values.clear()

    def clear(self):
        """Clear inspector (no entity selected)."""
        self.current_entity_id = None
        self._clear_properties()
        dpg.set_value(self.entity_label_tag, "No entity selected")

    def refresh(self):
        """
        Refresh property values from scene (called every frame).

        This updates all property widget values to reflect current scene state,
        allowing real-time display of physics simulation changes.

        Constitutional Compliance: Phase 4 extension
        - Updates property displays without emitting commands
        - Skips properties currently being dragged (don't interrupt user input)
        """
        if self.current_entity_id is None or self.current_scene is None:
            return

        # Update each property widget with current value from scene
        # Use list() snapshot to avoid RuntimeError if populate_inspector
        # modifies property_widgets during iteration (entity selection mid-frame)
        for prop_path, widget_tag in list(self.property_widgets.items()):
            # Skip if widget doesn't exist
            if not dpg.does_item_exist(widget_tag):
                continue

            # Skip if currently being dragged (don't interrupt user input)
            if self.drag_active.get(prop_path, False):
                continue

            # Get current value from scene
            current_value = self._get_property_value(prop_path)

            # Update widget display
            try:
                dpg.set_value(widget_tag, current_value)
            except Exception as e:
                # Ignore errors (widget might not support set_value)
                pass


# ============================================================================
# Utility Functions
# ============================================================================

def create_property_inspector(
    parent_tag: str,
    command_queue,
    width: int = 300,
    height: int = 600,
    scene_lock=None,
) -> PropertyInspectorWidget:
    """
    Create and return property inspector widget.

    Args:
        parent_tag: DPG parent container tag
        command_queue: Command queue for property edit commands
        width: Inspector width
        height: Inspector height
        scene_lock: Optional lock for thread-safe scene state reads

    Returns:
        PropertyInspectorWidget instance

    Constitutional Compliance: T096
    - Factory function for inspector creation
    - Returns widget instance for integration with main window
    """
    return PropertyInspectorWidget(
        parent_tag=parent_tag,
        command_queue=command_queue,
        width=width,
        height=height,
        scene_lock=scene_lock,
    )
