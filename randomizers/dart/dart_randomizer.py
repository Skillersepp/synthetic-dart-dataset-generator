import bpy
from typing import Optional, List, Dict
from pathlib import Path
from mathutils import Vector
import colorsys

from randomizers.base_randomizer import BaseRandomizer
from .dart_config import DartRandomConfig
from .dart import Dart
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
        base_path = self.base_path / "assets/Textures/Dart/Flight"
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
                    # Optimization: Reload existing image instead of remove/load
                    # This preserves references in materials and is faster than removing used datablocks
                    if img_file.name in bpy.data.images:
                        img = bpy.data.images[img_file.name]
                        # Force reload from disk to get latest changes
                        img.reload()
                    else:
                        # Use absolute path to ensure Blender finds the file
                        img = bpy.data.images.load(str(img_file.resolve()), check_existing=True)
                    
                    img.use_fake_user = True
                    images.append(img)
                except Exception as e:
                    print(f"[DartRandomizer] Failed to load texture {img_file}: {e}")
        print(f"[DartRandomizer] Loaded {len(images)} textures from {path}")
        return images

    def setup_geometry_references(self, dart: Dart) -> None:
        """
        Links the Geometry Nodes 'Parent_Object' inputs for the dart hierarchy.
        Should be called once after spawning a new dart instance.
        """
        # Barrel needs Tip
        if dart.barrel and dart.tip:
            set_geometry_node_input(dart.barrel, dart.barrel_mod, "Parent_Object", dart.tip)
        
        # Shaft needs Barrel
        if dart.shaft and dart.barrel:
            set_geometry_node_input(dart.shaft, dart.shaft_mod, "Parent_Object", dart.barrel)
            
        # Flight needs Shaft
        if dart.flight and dart.shaft:
            set_geometry_node_input(dart.flight, dart.flight_mod, "Parent_Object", dart.shaft)

    def randomize(self, dart: Dart) -> None:
        """
        Randomize the dart parameters and update the container size.
        
        Args:
            dart: The Dart instance to randomize.
        """
        if not dart or not dart.root:
            print("[DartRandomizer] No valid dart instance provided.")
            return

        self._randomize_generators(dart)
        
        self._update_dart_size(dart)
        
        # Pass dart to material randomizers
        self._randomize_flight_material(dart)
        self._randomize_shaft_material(dart)
        self._randomize_barrel_material(dart)
        self._randomize_tip_material(dart)

    def _get_material_from_generator(self, generator_obj: bpy.types.Object, material_prefix: str) -> Optional[bpy.types.Material]:
        """Helper to find a material on a generator object or its children."""
        if not generator_obj:
            return None
            
        # Check generator object itself
        if generator_obj.active_material and generator_obj.active_material.name.startswith(material_prefix):
            return generator_obj.active_material
            
        # Check children (e.g. the mesh object inside the generator)
        for child in generator_obj.children:
            if child.active_material and child.active_material.name.startswith(material_prefix):
                return child.active_material
        
        return None

    def _randomize_generators(self, dart: Dart) -> None:
        # 1. Tip Generator
        if dart.tip:
            length = self.config.tip_length.get_value(self.rng)
            dart.tip_length = length # Cache value
            set_geometry_node_input(dart.tip, dart.tip_mod, "Length", length)
            set_geometry_node_input(dart.tip, dart.tip_mod, "Seed", self.rng.randint(0, 10000))
            dart.tip.update_tag()

        # 2. Barrel Generator
        if dart.barrel:
            length = self.config.barrel_length.get_value(self.rng)
            thickness = self.config.barrel_thickness.get_value(self.rng)
            dart.barrel_length = length # Cache value
            set_geometry_node_input(dart.barrel, dart.barrel_mod, "Length", length)
            set_geometry_node_input(dart.barrel, dart.barrel_mod, "Thickness", thickness)
            set_geometry_node_input(dart.barrel, dart.barrel_mod, "Seed", self.rng.randint(0, 10000))
            dart.barrel.update_tag()

        # 3. Shaft Generator
        if dart.shaft:
            length = self.config.shaft_length.get_value(self.rng)
            mix = self.config.shaft_shape_mix.get_value(self.rng)
            dart.shaft_length = length # Cache value
            set_geometry_node_input(dart.shaft, dart.shaft_mod, "Length", length)
            set_geometry_node_input(dart.shaft, dart.shaft_mod, "Shape_mix_factor", mix)
            set_geometry_node_input(dart.shaft, dart.shaft_mod, "Seed", self.rng.randint(0, 10000))
            dart.shaft.update_tag()

        # 4. Flight Generator
        if dart.flight:
            depth = self.config.flight_insertion_depth.get_value(self.rng)
            dart.flight_insertion_depth = depth # Cache value
            set_geometry_node_input(dart.flight, dart.flight_mod, "Insertion_depth", depth)
            
            # Instance Index
            # Hardcoded max count of flight types
            count = 105
            
            if self.config.randomize_flight_type:
                idx = self.rng.randint(0, count - 1)
            else:
                idx = self.config.fixed_flight_index % count
            
            dart.flight_index = idx # Cache value
            set_geometry_node_input(dart.flight, dart.flight_mod, "Instance_index", idx)
            
            dart.flight.update_tag()

    def _assign_material_to_modifier(self, obj: bpy.types.Object, mod_name: str, material: bpy.types.Material) -> None:
        """
        Assigns the given material to the Geometry Nodes modifier input named 'Material'.
        This ensures the Geometry Nodes use the unique material instance.
        """
        # Try to set "Material" input
        set_geometry_node_input(obj, mod_name, "Material", material)

    def _ensure_unique_node_group(self, group_node: bpy.types.Node) -> None:
        """
        Ensures that the node group used by this node is unique (a copy).
        This prevents changes to the node group from affecting other materials/objects.
        """
        if not group_node.node_tree:
            return
            
        # Optimization: If the node tree has only 1 user, it is already unique to this material.
        # Since we deep-copied the material for each dart, if we also deep-copied the node group once,
        # it will have users=1 (the current material).
        if group_node.node_tree.users <= 1:
            return

        # Simply duplicate it to be safe and assign the copy
        # We append a suffix to identify it as a unique copy
        original_tree = group_node.node_tree
        new_tree = original_tree.copy()
        new_tree.name = f"{original_tree.name}_Unique"
        group_node.node_tree = new_tree

    def _randomize_flight_material(self, dart: Dart) -> None:
        """Randomize the flight material (texture, gradient, solid color, roughness)."""
        material = self._get_material_from_generator(dart.flight, "Flight")
        
        if not material:
            # Fallback to global lookup if not found on object (legacy behavior)
            if "Flight" in bpy.data.materials:
                material = bpy.data.materials["Flight"]
            else:
                print(f"[DartRandomizer] Material 'Flight' not found on object or globally")
                return

        # Ensure Geometry Nodes use this specific material instance
        if dart.flight:
             self._assign_material_to_modifier(dart.flight, dart.flight_mod, material)
            
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
            print(f"[DartRandomizer] Node Group 'Flight_Texture' not found in material '{material.name}'")
            return
            
        # IMPORTANT: Make the node group unique for this material instance
        # because we might modify its internal nodes (Image Texture)
        self._ensure_unique_node_group(group_node)

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

    def _randomize_shaft_material(self, dart: Dart) -> None:
        """Randomize the shaft material (gradient, solid color, roughness, metallic)."""
        material = self._get_material_from_generator(dart.shaft, "Shaft")
        
        if not material:
            if "Shaft" in bpy.data.materials:
                material = bpy.data.materials["Shaft"]
            else:
                print(f"[DartRandomizer] Material 'Shaft' not found")
                return

        # Ensure Geometry Nodes use this specific material instance
        if dart.shaft:
             self._assign_material_to_modifier(dart.shaft, dart.shaft_mod, material)
            
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
            print(f"[DartRandomizer] Node Group 'Shaft_Texture' not found in material '{material.name}'")
            return
            
        # IMPORTANT: Make the node group unique for this material instance
        self._ensure_unique_node_group(group_node)

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

    def _randomize_barrel_material(self, dart: Dart) -> None:
        """Randomize the barrel material (seed, roughness)."""
        material = self._get_material_from_generator(dart.barrel, "Barrel_Domain_Randomization")
        
        if not material:
            if "Barrel_Domain_Randomization" in bpy.data.materials:
                material = bpy.data.materials["Barrel_Domain_Randomization"]
            else:
                print(f"[DartRandomizer] Material 'Barrel_Domain_Randomization' not found")
                return

        # Ensure Geometry Nodes use this specific material instance
        if dart.barrel:
             self._assign_material_to_modifier(dart.barrel, dart.barrel_mod, material)
            
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
            print(f"[DartRandomizer] Node Group 'NG_Barrel_Domain_Randomization' not found in material '{material.name}'")

    def _randomize_tip_material(self, dart: Dart) -> None:
        """Randomize the tip material (seed, roughness)."""
        material = self._get_material_from_generator(dart.tip, "Tip_Domain_Randomization")
        
        if not material:
            if "Tip_Domain_Randomization" in bpy.data.materials:
                material = bpy.data.materials["Tip_Domain_Randomization"]
            else:
                print(f"[DartRandomizer] Material 'Tip_Domain_Randomization' not found")
                return

        # Ensure Geometry Nodes use this specific material instance
        if dart.tip:
             self._assign_material_to_modifier(dart.tip, dart.tip_mod, material)
            
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
            print(f"[DartRandomizer] Node Group 'NG_Tip_Domain_Randomization' not found in material '{material.name}'")

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

    def _update_dart_size(self, dart: Dart) -> None:
        """
        Read the total length from the Flight generator's output attribute
        and update the root Empty's display size.
        """
        if not dart or not dart.root or not dart.flight:
            return

        flight_insertion_depth_m = dart.flight_insertion_depth / 1000.0

        length_m = dart.tip.dimensions[2] + dart.barrel.dimensions[2] + dart.shaft.dimensions[2] + dart.flight.dimensions[2] - flight_insertion_depth_m
        dart.root.empty_display_size = length_m
