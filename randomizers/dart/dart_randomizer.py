import bpy
from typing import Optional
from mathutils import Vector

from randomizers.base_randomizer import BaseRandomizer
from .dart_config import DartRandomConfig
from utils.node_utils import set_geometry_node_input

class DartRandomizer(BaseRandomizer):
    """
    Randomizes dart geometry via Geometry Nodes inputs.
    
    Controls:
    - Tip, Barrel, Shaft, Flight parameters
    - Updates the root Empty object size based on generated geometry
    """

    def __init__(self, seed: int, config: Optional[DartRandomConfig] = None):
        super().__init__(seed, config or DartRandomConfig())

    def _initialize(self) -> None:
        pass

    def randomize(self, *args, **kwargs) -> None:
        """
        Randomize the dart parameters and update the container size.
        """
        self._randomize_generators()
        self._update_dart_size()

    def _get_geo_nodes_modifier_name(self, obj: bpy.types.Object) -> str:
        """Find the first Geometry Nodes modifier on the object."""
        for mod in obj.modifiers:
            if mod.type == 'NODES':
                return mod.name
        return "GeometryNodes"

    def _randomize_generators(self) -> None:
        # 1. Tip Generator
        tip_obj = bpy.data.objects.get("Tip_Generator")
        if tip_obj:
            mod_name = self._get_geo_nodes_modifier_name(tip_obj)
            length = self.config.tip_length.get_value(self.rng)
            set_geometry_node_input(tip_obj, mod_name, "Length", length)
            set_geometry_node_input(tip_obj, mod_name, "Seed", self.rng.randint(0, 10000))
            tip_obj.update_tag()

        # 2. Barrel Generator
        barrel_obj = bpy.data.objects.get("Barrel_Generator")
        if barrel_obj:
            mod_name = self._get_geo_nodes_modifier_name(barrel_obj)
            length = self.config.barrel_length.get_value(self.rng)
            thickness = self.config.barrel_thickness.get_value(self.rng)
            set_geometry_node_input(barrel_obj, mod_name, "Length", length)
            set_geometry_node_input(barrel_obj, mod_name, "Thickness", thickness)
            set_geometry_node_input(barrel_obj, mod_name, "Seed", self.rng.randint(0, 10000))
            barrel_obj.update_tag()

        # 3. Shaft Generator
        shaft_obj = bpy.data.objects.get("Shaft_Generator")
        if shaft_obj:
            mod_name = self._get_geo_nodes_modifier_name(shaft_obj)
            length = self.config.shaft_length.get_value(self.rng)
            mix = self.config.shaft_shape_mix.get_value(self.rng)
            set_geometry_node_input(shaft_obj, mod_name, "Length", length)
            set_geometry_node_input(shaft_obj, mod_name, "Shape_mix_factor", mix)
            set_geometry_node_input(shaft_obj, mod_name, "Seed", self.rng.randint(0, 10000))
            shaft_obj.update_tag()

        # 4. Flight Generator
        flight_obj = bpy.data.objects.get("Flight_Generator")
        if flight_obj:
            mod_name = self._get_geo_nodes_modifier_name(flight_obj)
            depth = self.config.flight_insertion_depth.get_value(self.rng)
            set_geometry_node_input(flight_obj, mod_name, "Insertion_depth", depth)
            
            # Instance Index
            # Hardcoded max count of flight types
            count = 105
            
            if self.config.randomize_flight_type:
                idx = self.rng.randint(0, count - 1)
            else:
                idx = self.config.fixed_flight_index % count
            
            set_geometry_node_input(flight_obj, mod_name, "Instance_index", idx)
            
            flight_obj.update_tag()

    def _update_dart_size(self) -> None:
        """
        Calculate the total length of the dart along its local Z axis
        and update the root Empty's display size.
        """
        # Update dependency graph to ensure geometry is up to date after parameter changes
        bpy.context.view_layer.update()
        
        root_obj = bpy.data.objects.get("Dart_Generator")
        if not root_obj:
            return

        # Collect all objects in the hierarchy to identify relevant instances
        hierarchy_objects = set()
        def collect_hierarchy(obj):
            hierarchy_objects.add(obj)
            for child in obj.children:
                collect_hierarchy(child)
        collect_hierarchy(root_obj)

        depsgraph = bpy.context.evaluated_depsgraph_get()
        
        min_z = float('inf')
        max_z = float('-inf')
        found_geometry = False
        
        # Pre-calculate inverse root matrix for local space conversion
        root_mat_inv = root_obj.matrix_world.inverted()

        # Iterate over all object instances in the depsgraph
        # This includes both real objects and generated instances (e.g. from Geometry Nodes)
        for inst in depsgraph.object_instances:
            is_relevant = False
            
            # Check if instance belongs to our hierarchy
            if inst.is_instance:
                # Generated instance: check parent (the generator)
                if inst.parent and inst.parent.original in hierarchy_objects:
                    is_relevant = True
            else:
                # Real object: check the object itself
                if inst.object.original in hierarchy_objects:
                    is_relevant = True
            
            if is_relevant:
                obj_eval = inst.object
                if obj_eval.type == 'MESH' and obj_eval.data:
                    # Use the instance's world matrix
                    world_mat = inst.matrix_world
                    
                    # Transform bounding box corners to world space
                    bbox_corners = [world_mat @ Vector(corner) for corner in obj_eval.bound_box]
                    
                    # Transform to root local space and update bounds
                    for world_v in bbox_corners:
                        local_v = root_mat_inv @ world_v
                        if local_v.z < min_z: min_z = local_v.z
                        if local_v.z > max_z: max_z = local_v.z
                    
                    found_geometry = True

        if found_geometry and min_z != float('inf') and max_z != float('-inf'):
            length = max_z - min_z
            # Set Empty size
            root_obj.empty_display_size = length
            # print(f"[DartRandomizer] Updated Dart Size: {length:.4f} (MinZ: {min_z:.4f}, MaxZ: {max_z:.4f})")
