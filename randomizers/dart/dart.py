import bpy
from typing import Optional

class Dart:
    """
    Wrapper class for a single Dart instance in the scene.
    Caches references to the Blender objects (Tip, Barrel, Shaft, Flight)
    and their current state to avoid repeated scene traversals.
    """
    def __init__(self, root_obj: bpy.types.Object, k_point_obj: Optional[bpy.types.Object] = None):
        self.root = root_obj
        self.k_point = k_point_obj
        
        # Cache child objects
        self.tip = self._find_child(self.root, "Tip_Generator")
        self.barrel = self._find_child(self.root, "Barrel_Generator")
        self.shaft = self._find_child(self.root, "Shaft_Generator")
        self.flight = self._find_child(self.root, "Flight_Generator")
        
        # Cache modifier names
        self.tip_mod = self._get_geo_nodes_modifier_name(self.tip)
        self.barrel_mod = self._get_geo_nodes_modifier_name(self.barrel)
        self.shaft_mod = self._get_geo_nodes_modifier_name(self.shaft)
        self.flight_mod = self._get_geo_nodes_modifier_name(self.flight)

        # State cache (lengths in meters)
        self.tip_length: float = 0.0
        self.barrel_length: float = 0.0
        self.shaft_length: float = 0.0
        self.flight_insertion_depth: float = 0.0
        self.flight_index: int = 0
        self.is_visible: bool = True

    def set_visibility(self, visible: bool) -> None:
        """
        Sets the visibility (viewport and render) for the entire dart hierarchy.
        """
        self.is_visible = visible
        
        # Helper to set visibility for an object and its children recursively
        def _set_obj_visibility(obj: bpy.types.Object, state: bool):
            obj.hide_viewport = not state
            obj.hide_render = not state
            for child in obj.children:
                _set_obj_visibility(child, state)

        if self.root:
            _set_obj_visibility(self.root, visible)
            
        if self.k_point:
            self.k_point.hide_viewport = not visible
            self.k_point.hide_render = not visible
        
    def _find_child(self, parent: bpy.types.Object, name_part: str) -> Optional[bpy.types.Object]:
        """Recursive search for a child object by name pattern."""
        if name_part in parent.name:
            return parent
        for child in parent.children:
            found = self._find_child(child, name_part)
            if found:
                return found
        return None

    def _get_geo_nodes_modifier_name(self, obj: bpy.types.Object) -> Optional[str]:
        """Find the first Geometry Nodes modifier on the object."""
        if not obj:
            return None
        for mod in obj.modifiers:
            if mod.type == 'NODES':
                return mod.name
        return None
