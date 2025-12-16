import bpy
from typing import Optional, List, Dict
from pathlib import Path
from mathutils import Vector
import colorsys

from randomizers.base_randomizer import BaseRandomizer
from .dart_config import DartRandomConfig
from utils.node_utils import set_geometry_node_input, find_node_group, set_node_input

class DartRandomizer(BaseRandomizer):
    """
    Randomizes dart geometry via Geometry Nodes inputs.
    
    Controls:
    - Tip, Barrel, Shaft, Flight parameters
    - Updates the root Empty object size based on generated geometry
    """

    def __init__(self, seed: int, config: Optional[DartRandomConfig] = None, base_path: Path = None):
        self.base_path = base_path or Path.cwd()
        self.flight_textures_flags: List[bpy.types.Image] = []
        self.flight_textures_outpainted: List[bpy.types.Image] = []
        super().__init__(seed, config or DartRandomConfig())

    def _initialize(self) -> None:
        """Load flight textures."""
        base_path = self.base_path / "assets/textures/dart/flight"
        self.flight_textures_flags = self._load_textures(base_path / "flags")
        self.flight_textures_outpainted = self._load_textures(base_path / "outpainted")

    def _load_textures(self, path: Path) -> List[bpy.types.Image]:
        """Load all images from a directory."""
        images = []
        if not path.exists():
            print(f"[DartRandomizer] Warning: Texture path not found: {path}")
            return images
            
        for img_file in path.glob("*"):
            if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
                try:
                    if img_file.name in bpy.data.images:
                        img = bpy.data.images[img_file.name]
                    else:
                        # Use absolute path to ensure Blender finds the file
                        img = bpy.data.images.load(str(img_file.resolve()), check_existing=True)
                    img.use_fake_user = True
                    images.append(img)
                except Exception as e:
                    print(f"[DartRandomizer] Failed to load texture {img_file}: {e}")
        print(f"[DartRandomizer] Loaded {len(images)} textures from {path}")
        return images

    def randomize(self, *args, **kwargs) -> None:
        """
        Randomize the dart parameters and update the container size.
        """
        self._randomize_generators()
        self._randomize_flight_material()
        self._randomize_shaft_material()
        self._randomize_barrel_material()
        self._randomize_tip_material()
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

    def _randomize_flight_material(self) -> None:
        """Randomize the flight material (texture, gradient, solid color, roughness)."""
        # Find the material on the Flight object (or Flight_Generator)
        # Assuming the material is named "Flight" and is on the Flight_Generator or its instances
        # Since Flight_Generator generates instances, we might need to check the original objects in the "Flights" collection
        # OR if the material is on the Flight_Generator itself (if it overrides).
        # Based on user description, let's look for material "Flight" in bpy.data.materials
        
        mat_name = "Flight"
        if mat_name not in bpy.data.materials:
            print(f"[DartRandomizer] Material '{mat_name}' not found")
            return
            
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return

        # 1. Randomize Roughness on Principled BSDF
        bsdf = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if bsdf:
            roughness = self.config.flight_roughness.get_value(self.rng)
            set_node_input(bsdf, "Roughness", roughness)

        # 2. Find Flight_Texture Node Group
        group_node = find_node_group(material.node_tree, "Flight_Texture")
        if not group_node:
            print(f"[DartRandomizer] Node Group 'Flight_Texture' not found in material '{mat_name}'")
            return

        # 3. Determine Mode
        # Modes: 0=Flags, 1=Outpainted, 2=Gradient, 3=Solid
        probs = [
            self.config.prob_flight_texture_flags,
            self.config.prob_flight_texture_outpainted,
            self.config.prob_flight_gradient,
            self.config.prob_flight_solid
        ]
        
        # Normalize probabilities if they don't sum to 1
        total_prob = sum(probs)
        if total_prob > 0:
            probs = [p / total_prob for p in probs]
        else:
            probs = [0.25, 0.25, 0.25, 0.25] # Fallback equal distribution

        mode = self.rng.choices(range(4), weights=probs, k=1)[0]

        if mode == 0: # Flags
            self._set_flight_texture(group_node, self.flight_textures_flags)
            set_node_input(group_node, "Mix_factor_1", 0.0)
            set_node_input(group_node, "Mix_factor_2", 0.0)
            
        elif mode == 1: # Outpainted
            self._set_flight_texture(group_node, self.flight_textures_outpainted)
            set_node_input(group_node, "Mix_factor_1", 0.0)
            set_node_input(group_node, "Mix_factor_2", 0.0)
            
        elif mode == 2: # Gradient
            col1 = self._get_random_color()
            col2 = self._get_random_color()
            set_node_input(group_node, "Gradient_color_1", col1)
            set_node_input(group_node, "Gradient_color_2", col2)
            set_node_input(group_node, "Mix_factor_1", 1.0)
            set_node_input(group_node, "Mix_factor_2", 0.0)
            
        elif mode == 3: # Solid
            col = self._get_random_color()
            set_node_input(group_node, "Solid_color", col)
            # Mix_factor_1 can be anything, Mix_factor_2 must be 1.0
            set_node_input(group_node, "Mix_factor_2", 1.0)

    def _randomize_shaft_material(self) -> None:
        """Randomize the shaft material (gradient, solid color, roughness, metallic)."""
        mat_name = "Shaft"
        if mat_name not in bpy.data.materials:
            print(f"[DartRandomizer] Material '{mat_name}' not found")
            return
            
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return

        # 1. Randomize Principled BSDF (Roughness, Metallic)
        bsdf = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if bsdf:
            # Roughness
            roughness = self.config.shaft_roughness.get_value(self.rng)
            set_node_input(bsdf, "Roughness", roughness)
            
            # Metallic
            is_metallic = self.rng.random() < self.config.prob_shaft_metallic
            set_node_input(bsdf, "Metallic", 1.0 if is_metallic else 0.0)

        # 2. Find Shaft_Texture Node Group
        group_node = find_node_group(material.node_tree, "Shaft_Texture")
        if not group_node:
            print(f"[DartRandomizer] Node Group 'Shaft_Texture' not found in material '{mat_name}'")
            return

        # 3. Determine Mode
        # Modes: 0=Gradient, 1=Solid
        probs = [
            self.config.prob_shaft_gradient,
            self.config.prob_shaft_solid
        ]
        
        # Normalize
        total_prob = sum(probs)
        if total_prob > 0:
            probs = [p / total_prob for p in probs]
        else:
            probs = [0.5, 0.5]

        mode = self.rng.choices(range(2), weights=probs, k=1)[0]

        if mode == 0: # Gradient
            col1 = self._get_random_color()
            col2 = self._get_random_color()
            set_node_input(group_node, "Gradient_color_1", col1)
            set_node_input(group_node, "Gradient_color_2", col2)
            set_node_input(group_node, "Mix_factor", 0.0)
            
        elif mode == 1: # Solid
            col = self._get_random_color()
            set_node_input(group_node, "Solid_color", col)
            set_node_input(group_node, "Mix_factor", 1.0)

    def _randomize_barrel_material(self) -> None:
        """Randomize the barrel material (seed, roughness)."""
        mat_name = "Barrel_Domain_Randomization"
        if mat_name not in bpy.data.materials:
            print(f"[DartRandomizer] Material '{mat_name}' not found")
            return
            
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return

        # 1. Randomize Principled BSDF (Roughness)
        bsdf = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if bsdf:
            roughness = self.config.barrel_roughness.get_value(self.rng)
            set_node_input(bsdf, "Roughness", roughness)

        # 2. Find Node Group and set Seed
        group_node = find_node_group(material.node_tree, "NG_Barrel_Domain_Randomization")
        if group_node:
            set_node_input(group_node, "Seed", self.rng.randint(0, 10000))
        else:
            print(f"[DartRandomizer] Node Group 'NG_Barrel_Domain_Randomization' not found in material '{mat_name}'")

    def _randomize_tip_material(self) -> None:
        """Randomize the tip material (seed, roughness)."""
        mat_name = "Tip_Domain_Randomization"
        if mat_name not in bpy.data.materials:
            print(f"[DartRandomizer] Material '{mat_name}' not found")
            return
            
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return

        # 1. Randomize Principled BSDF (Roughness)
        bsdf = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if bsdf:
            roughness = self.config.tip_roughness.get_value(self.rng)
            set_node_input(bsdf, "Roughness", roughness)

        # 2. Find Node Group and set Seed
        group_node = find_node_group(material.node_tree, "NG_Tip_Domain_Randomization")
        if group_node:
            set_node_input(group_node, "Seed", self.rng.randint(0, 10000))
        else:
            print(f"[DartRandomizer] Node Group 'NG_Tip_Domain_Randomization' not found in material '{mat_name}'")

    def _get_random_color(self):
        """Helper to generate random saturated color based on config."""
        h = self.rng.random()
        s = self.rng.uniform(self.config.flight_color_saturation_min, self.config.flight_color_saturation_max)
        v = self.rng.uniform(self.config.flight_color_value_min, self.config.flight_color_value_max)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (r, g, b, 1.0)

    def _set_flight_texture(self, group_node: bpy.types.Node, texture_list: List[bpy.types.Image]) -> None:
        """Pick a random texture from the list and assign it to the Image Texture node inside the group."""
        if not texture_list:
            return
            
        image = self.rng.choice(texture_list)
        
        # Find Image Texture node inside the group
        img_node = None
        for node in group_node.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                img_node = node
                break
        
        if img_node:
            img_node.image = image
        else:
            print("[DartRandomizer] Image Texture node not found inside 'Flight_Texture' group")

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
