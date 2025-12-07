import bpy
from typing import Optional, Tuple

from randomizers.base_randomizer import BaseRandomizer
from .dartboard_config import DartboardRandomConfig, ColorVariation
from utils.node_utils import find_node_group, set_node_input, set_geometry_node_input
from utils.color_utils import randomize_color_hsv


class DartboardRandomizer(BaseRandomizer):
    """
    Randomizes dartboard materials via Shader Node Group inputs.
    
    Supports:
    - Score texture materials (cracks, holes, field colors)
    - Number ring material (digit wear)
    
    Extensible for:
    - Geometry Nodes modifiers (future)
    """

    def __init__(self, seed: int, config: Optional[DartboardRandomConfig] = None):
        """
        Initialize the DartboardRandomizer.
        
        Args:
            seed: Initial seed for deterministic randomization
            config: Configuration for randomization
        """
        super().__init__(seed, config or DartboardRandomConfig())

    # -------------------------------------------------------------------------
    # INITIALIZATION (BaseRandomizer Interface)
    # -------------------------------------------------------------------------

    def _initialize(self) -> None:
        """
        Initialization at startup.
        
        Geometry Nodes modifiers could be cached here later.
        Currently no heavy initialization needed.
        """
        # Validate that required materials exist
        self._validate_materials()

    def _validate_materials(self) -> None:
        """Check if configured materials exist."""
        missing = []
        for key, mat_name in self.config.material_names.items():
            if mat_name not in bpy.data.materials:
                missing.append(f"{key}: {mat_name}")
        
        if missing:
            print(f"[DartboardRandomizer] Warning - Materials not found: {missing}")

    # -------------------------------------------------------------------------
    # PUBLIC API (BaseRandomizer Interface)
    # -------------------------------------------------------------------------

    def randomize(self, *args, **kwargs) -> None:
        """
        Perform dartboard randomization.
        
        Randomizes:
        - All score texture materials
        - Number ring material
        """
        # Randomize score materials
        self._randomize_score_materials()
        
        # Randomize number ring material
        self._randomize_number_ring_material()
        
        # Randomize Geometry Nodes (wire seeds)
        self._randomize_geometry_nodes()

    # -------------------------------------------------------------------------
    # SCORE MATERIALS
    # -------------------------------------------------------------------------

    def _randomize_score_materials(self) -> None:
        """Randomize all score texture materials."""
        score_materials = [
            ("score_red", "field_color_red"),
            ("score_green", "field_color_green"),
            ("score_white", "field_color_white"),
            ("score_black", "field_color_black"),
        ]
        
        # Generate shared values for all score materials so textures match across fields
        shared_seed = self.rng.randint(0, 10000)
        shared_crack_factor = self.config.crack_factor.get_value(self.rng) if self.config.randomize_cracks else None
        shared_hole_factor = self.config.hole_factor.get_value(self.rng) if self.config.randomize_holes else None
        
        for mat_key, color_attr in score_materials:
            mat_name = self.config.material_names.get(mat_key)
            if not mat_name or mat_name not in bpy.data.materials:
                continue
            
            material = bpy.data.materials[mat_name]
            color_config = getattr(self.config, color_attr)
            self._randomize_score_material(
                material, color_config,
                shared_seed, shared_crack_factor, shared_hole_factor
            )

    def _randomize_score_material(
        self, 
        material, 
        color_config: ColorVariation,
        seed: int,
        crack_factor: Optional[float],
        hole_factor: Optional[float]
    ) -> None:
        """
        Randomize a single score material.
        
        Args:
            material: The material to randomize
            color_config: Color configuration for this material
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
         
        # Field Color - set with optional variation based on color_config.randomize
        color = self._get_randomized_color(color_config)
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
            print(f"[DartboardRandomizer] Node Group '{group_name}' not found in {mat_name}")
            return
        
        # Set seed
        set_node_input(group_node, "Seed", self.rng.randint(0, 10000))
        
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
    # GEOMETRY NODES
    # -------------------------------------------------------------------------

    def _randomize_geometry_nodes(self) -> None:
        """
        Randomize Geometry Nodes modifiers.
        
        Sets the Seed input on each configured Geometry Nodes modifier.
        Uses a shared seed for consistent wire appearance across all modifiers.
        """
        # Generate a shared seed for consistent wire appearance
        wire_seed = self.rng.randint(0, 10000)
        
        # Iterate over all configured geometry node modifiers
        for obj_name, modifier_name in self.config.geometry_node_modifiers.items():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                print(f"[DartboardRandomizer] Object '{obj_name}' not found")
                continue
            
            success = set_geometry_node_input(obj, modifier_name, "Seed", wire_seed)
            if not success:
                print(f"[DartboardRandomizer] Could not set Seed on '{modifier_name}' in '{obj_name}'")
            else:
                # Force update of the object to ensure Geometry Nodes re-evaluate
                obj.update_tag()
        
        # Force dependency graph update to ensure geometry is recalculated
        # This is sometimes needed for Geometry Nodes to reflect changes immediately
        if bpy.context.view_layer:
            bpy.context.view_layer.update()

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
