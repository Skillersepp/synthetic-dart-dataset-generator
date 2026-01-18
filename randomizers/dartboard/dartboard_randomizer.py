import bpy
from pathlib import Path
from typing import Optional, Tuple, List

from randomizers.base_randomizer import BaseRandomizer
from .dartboard_config import DartboardRandomConfig, ColorVariation
from utils.node_utils import find_node_group, set_node_input, set_geometry_node_input
from utils.color_utils import randomize_color_hsv
from utils.asset_utils import get_texture_paths, load_single_image


class DartboardRandomizer(BaseRandomizer):
    """
    Randomizes dartboard materials via Shader Node Group inputs.
    
    Supports:
    - Score texture materials (cracks, holes, field colors)
    - Number ring material (digit wear)
    """

    def __init__(self, seed: int, config: Optional[DartboardRandomConfig] = None):
        """
        Initialize the DartboardRandomizer.
        
        Args:
            seed: Initial seed for deterministic randomization
            config: Configuration for randomization
        """
        super().__init__(seed, config or DartboardRandomConfig())
        
        # Texture paths for outer ring (loaded on demand)
        self._outer_ring_texture_paths: List[Path] = []
        
        # Cached node references (set during _initialize)
        self._outer_ring_image_node: Optional[bpy.types.ShaderNodeTexImage] = None
        self._outer_ring_group_node: Optional[bpy.types.ShaderNodeGroup] = None
        self._outer_ring_mapping_node: Optional[bpy.types.ShaderNodeMapping] = None

    # -------------------------------------------------------------------------
    # INITIALIZATION (BaseRandomizer Interface)
    # -------------------------------------------------------------------------

    def _initialize(self) -> None:
        """
        Initialization at startup.
        
        Scans outer ring texture paths and validates materials.
        """
        # Validate that required materials exist
        self._validate_materials()
        
        # Scan outer ring texture paths (fast, doesn't load images)
        self._outer_ring_texture_paths = get_texture_paths(
            self.config.outer_ring_textures_folder
        )
        print(f"[DartboardRandomizer] Found {len(self._outer_ring_texture_paths)} outer ring texture paths")
        
        # Cache outer ring material nodes
        self._cache_outer_ring_nodes()

    def _validate_materials(self) -> None:
        """Check if configured materials exist."""
        missing = []
        for key, mat_name in self.config.material_names.items():
            if mat_name not in bpy.data.materials:
                missing.append(f"{key}: {mat_name}")
        
        if missing:
            print(f"[DartboardRandomizer] Warning: Materials not found: {missing}")

    def _cache_outer_ring_nodes(self) -> None:
        """Cache node references for outer ring material to avoid repeated lookups."""
        mat_name = self.config.material_names.get("outer_ring")
        if not mat_name or mat_name not in bpy.data.materials:
            return
        
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return
        
        node_tree = material.node_tree
        
        # Find and cache the Image Texture node
        for node in node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                self._outer_ring_image_node = node
                break
        
        # Find and cache the Mapping node
        for node in node_tree.nodes:
            if node.type == 'MAPPING':
                self._outer_ring_mapping_node = node
                break
        
        # Find and cache the group_black_score_texture node
        self._outer_ring_group_node = find_node_group(
            node_tree, self.config.node_group_names["score_black"]
        )

    # -------------------------------------------------------------------------
    # PUBLIC API (BaseRandomizer Interface)
    # -------------------------------------------------------------------------

    def randomize(self, *args, **kwargs) -> None:
        """
        Perform dartboard randomization.
        
        Randomizes:
        - All score texture materials
        - Number ring material
        - Outer ring texture material
        """
        # Ensure outer ring is initialized (lazy loading for module reloads)
        if not self._outer_ring_texture_paths or not self._outer_ring_image_node:
            self._initialize_outer_ring()
        
        # Generate shared values for score materials and outer ring
        shared_seed = self.rng.randint(0, 1000000)
        shared_crack_factor = self.config.crack_factor.get_value(self.rng) if self.config.randomize_cracks else None
        shared_hole_factor = self.config.hole_factor.get_value(self.rng) if self.config.randomize_holes else None
        shared_black_color = self._get_randomized_color(self.config.field_color_black)
        
        # Randomize score materials with shared values
        self._randomize_score_materials(shared_seed, shared_crack_factor, shared_hole_factor, shared_black_color)
        
        # Randomize outer ring material with same shared values
        self._randomize_outer_ring_material(shared_seed, shared_crack_factor, shared_hole_factor, shared_black_color)
        
        # Randomize number ring material
        self._randomize_number_ring_material()
        
        # Randomize Geometry Nodes (wire seeds)
        self._randomize_geometry_nodes()

    def _initialize_outer_ring(self) -> None:
        """Initialize outer ring texture paths and cache nodes. Can be called multiple times safely."""
        # Scan texture paths if not done yet
        if not self._outer_ring_texture_paths:
            self._outer_ring_texture_paths = get_texture_paths(
                self.config.outer_ring_textures_folder
            )
        
        # Cache nodes if not cached
        if not self._outer_ring_image_node:
            self._cache_outer_ring_nodes()

    # -------------------------------------------------------------------------
    # SCORE MATERIALS
    # -------------------------------------------------------------------------

    def _randomize_score_materials(
        self,
        shared_seed: int,
        shared_crack_factor: Optional[float],
        shared_hole_factor: Optional[float],
        shared_black_color: Tuple[float, float, float, float]
    ) -> None:
        """
        Randomize all score texture materials.
        
        Args:
            shared_seed: Shared seed for consistent textures across all score materials
            shared_crack_factor: Shared crack factor value (None if not randomizing)
            shared_hole_factor: Shared hole factor value (None if not randomizing)
            shared_black_color: Pre-generated color for black fields (shared with outer ring)
        """
        score_materials = [
            ("score_red", "field_color_red"),
            ("score_green", "field_color_green"),
            ("score_white", "field_color_white"),
            ("score_black", None),  # Uses shared_black_color
        ]
        
        for mat_key, color_attr in score_materials:
            mat_name = self.config.material_names.get(mat_key)
            if not mat_name or mat_name not in bpy.data.materials:
                continue
            
            material = bpy.data.materials[mat_name]
            
            # For black, use the shared color; for others, generate from config
            if color_attr is None:
                color = shared_black_color
            else:
                color_config = getattr(self.config, color_attr)
                color = self._get_randomized_color(color_config)
            
            self._randomize_score_material(
                material, color,
                shared_seed, shared_crack_factor, shared_hole_factor
            )

    def _randomize_score_material(
        self, 
        material,
        color: Tuple[float, float, float, float],
        seed: int,
        crack_factor: Optional[float],
        hole_factor: Optional[float]
    ) -> None:
        """
        Randomize a single score material.
        
        Args:
            material: The material to randomize
            color: RGBA color tuple for the field
            seed: Shared seed for consistent textures across all score materials
            crack_factor: Shared crack factor value (None if not randomizing)
            hole_factor: Shared hole factor value (None if not randomizing)
        """
        if not material.use_nodes:
            return
        
        node_tree = material.node_tree
        
        # Find any score texture node group in this material
        group_node = find_node_group(node_tree, self.config.node_group_names["score_white_and_color"])
        if not group_node:
            group_node = find_node_group(node_tree, self.config.node_group_names["score_black"])
        if not group_node:
            return
        
        # Set shared seed for consistent textures across all fields
        set_node_input(group_node, "Seed", seed)
        
        # Crack Factor (shared across all materials)
        if crack_factor is not None:
            set_node_input(group_node, "Crack_factor", crack_factor)
        
        # Hole Factor (shared across all materials)
        if hole_factor is not None:
            set_node_input(group_node, "Hole_factor", hole_factor)
        
        # Field Color
        set_node_input(group_node, "Field_color", color)

    # -------------------------------------------------------------------------
    # NUMBER RING MATERIAL
    # -------------------------------------------------------------------------

    def _randomize_number_ring_material(self) -> None:
        """Randomize the number ring material (digit wear)."""
        mat_name = self.config.material_names.get("number_ring")
        if not mat_name or mat_name not in bpy.data.materials:
            return
        
        material = bpy.data.materials[mat_name]
        if not material.use_nodes:
            return
        
        node_tree = material.node_tree
        group_name = self.config.node_group_names["digit_wear"]
        group_node = find_node_group(node_tree, group_name)
        
        if not group_node:
            return
        
        # Set seed
        set_node_input(group_node, "Seed", self.rng.randint(0, 1000000))
        
        # Wear Level
        if self.config.randomize_wear:
            wear_val = self.config.wear_level.get_value(self.rng)
            set_node_input(group_node, "Wear_level", wear_val)
            
            contrast_val = self.config.wear_contrast.get_value(self.rng)
            set_node_input(group_node, "Wear_contrast", contrast_val)
        
        # Digit Color - set with optional variation based on digit_color.randomize
        color = self._get_randomized_color(self.config.digit_color)
        set_node_input(group_node, "Digit_color", color)

    # -------------------------------------------------------------------------
    # OUTER RING MATERIAL
    # -------------------------------------------------------------------------

    def _randomize_outer_ring_material(
        self,
        shared_seed: int,
        shared_crack_factor: Optional[float],
        shared_hole_factor: Optional[float],
        shared_black_color: Tuple[float, float, float, float]
    ) -> None:
        """
        Randomize the outer ring texture material.
        
        Sets a random texture from the loaded textures and applies the same
        group_black_score_texture parameters as the score materials.
        Uses cached node references for better performance.
        
        Args:
            shared_seed: Shared seed for consistent textures
            shared_crack_factor: Shared crack factor value (None if not randomizing)
            shared_hole_factor: Shared hole factor value (None if not randomizing)
            shared_black_color: Field color matching black_score_texture_material
        """
        # Set random texture in cached Image Texture node
        if self._outer_ring_texture_paths and self._outer_ring_image_node:
            random_texture_path = self.rng.choice(self._outer_ring_texture_paths)
            # Load only this one image (fast, uses cache if already loaded)
            texture = load_single_image(random_texture_path, use_fake_user=False)
            if texture:
                self._outer_ring_image_node.image = texture
        
        # Randomize Mapping node (Location, Rotation, Scale)
        self._randomize_outer_ring_mapping()
        
        # Apply values to cached group_black_score_texture node
        if self._outer_ring_group_node:
            set_node_input(self._outer_ring_group_node, "Seed", shared_seed)
            set_node_input(self._outer_ring_group_node, "Field_color", shared_black_color)
            
            if shared_crack_factor is not None:
                set_node_input(self._outer_ring_group_node, "Crack_factor", shared_crack_factor)
            
            if shared_hole_factor is not None:
                set_node_input(self._outer_ring_group_node, "Hole_factor", shared_hole_factor)

    def _randomize_outer_ring_mapping(self) -> None:
        """
        Randomize the Mapping node in the outer ring material.
        
        Randomizes:
        - Location X: Uniform distribution
        - Location Y: Normal distribution
        - Rotation Z: Normal distribution (degrees converted to radians)
        - Scale: Weighted integer choice (same for X, Y, Z)
        """
        import math
        
        if not self._outer_ring_mapping_node:
            return
        
        mapping_config = self.config.outer_ring_mapping
        if not mapping_config.randomize:
            return
        
        mapping_node = self._outer_ring_mapping_node
        
        # Location X: Uniform distribution
        loc_x = self.rng.uniform(mapping_config.location_x_min, mapping_config.location_x_max)
        
        # Location Y: Normal distribution
        loc_y = mapping_config.location_y.get_value(self.rng)
        
        # Keep Z at 0 (no randomization for Z location)
        mapping_node.inputs['Location'].default_value = (loc_x, loc_y, 0.0)
        
        # Rotation Z: Normal distribution (convert degrees to radians)
        rot_z_deg = mapping_config.rotation_z_degrees.get_value(self.rng)
        rot_z_rad = math.radians(rot_z_deg)
        
        # Keep X and Y rotation at 0
        mapping_node.inputs['Rotation'].default_value = (0.0, 0.0, rot_z_rad)
        
        # Scale X: Weighted integer choice (Y and Z stay at 1)
        scale_x = float(mapping_config.scale.get_value(self.rng))
        mapping_node.inputs['Scale'].default_value = (scale_x, 1.0, 1.0)

    # -------------------------------------------------------------------------
    # GEOMETRY NODES
    # -------------------------------------------------------------------------

    def _randomize_geometry_nodes(self) -> None:
        """
        Randomize Geometry Nodes modifiers.
        
        Sets the Seed input on each configured Geometry Nodes modifier.
        Uses a shared seed for consistent wire appearance across all modifiers.
        """
        # Generate a shared seed for consistent wire appearance
        wire_seed = self.rng.randint(0, 1000000)
        
        # Iterate over all configured geometry node modifiers
        for obj_name, modifier_name in self.config.geometry_node_modifiers.items():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                continue
            
            if set_geometry_node_input(obj, modifier_name, "Seed", wire_seed):
                obj.update_tag()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_randomized_color(self, config: ColorVariation) -> Tuple[float, float, float, float]:
        """
        Generate a randomized color based on the configuration.
        
        Args:
            config: The color configuration
            
        Returns:
            RGBA tuple with the randomized color
        """
        if not config.randomize:
            return config.base_color
        
        return randomize_color_hsv(
            config.base_color,
            self.rng,
            hue_variation=config.hue_variation,
            saturation_variation=config.saturation_variation,
            value_variation=config.value_variation
        )
