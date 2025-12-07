from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class RangeOrFixed:
    """
    Allows either a fixed value or a range for randomization.
    
    If fixed is set, this value will always be used.
    Otherwise, a random value between min_val and max_val is chosen.
    """
    min_val: float = 0.0
    max_val: float = 1.0
    fixed: Optional[float] = None
    
    def get_value(self, rng) -> float:
        """Returns either the fixed value or a random value within the range."""
        if self.fixed is not None:
            return self.fixed
        return rng.uniform(self.min_val, self.max_val)
    
    def is_randomized(self) -> bool:
        """Checks if this parameter is being randomized."""
        return self.fixed is None


@dataclass
class ColorVariation:
    """
    Configuration for color variations in HSV color space.
    
    Enables subtle changes to Hue, Saturation and Value
    to simulate realistic aging/wear effects.
    """
    base_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)  # RGBA
    hue_variation: float = 0.0        # ±percent hue shift (0.02 = ±2%)
    saturation_variation: float = 0.0  # ±percent saturation change
    value_variation: float = 0.0       # ±percent value/brightness change
    randomize: bool = True            # Whether to randomize color


@dataclass
class DartboardRandomConfig:
    """
    Configuration for dartboard material randomization.
    
    Controls randomization of:
    - Score texture materials (cracks, holes, colors)
    - Number ring material (digit wear)
    
    Can be extended for Geometry Nodes later.
    """
    
    # -------------------------------------------------------------------------
    # Enable/disable randomization per parameter group
    # -------------------------------------------------------------------------
    randomize_cracks: bool = False
    randomize_holes: bool = True
    randomize_wear: bool = True
    
    # -------------------------------------------------------------------------
    # Score Texture Parameters (for all score materials)
    # Used in: group_white_and_color_score_texture, group_black_score_texture
    # -------------------------------------------------------------------------
    crack_factor: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.0, 1.0))
    hole_factor: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.0, 1.0))
    
    # -------------------------------------------------------------------------
    # Digit Wear Parameters (for number_ring material)
    # Used in: group_digit_wear
    # -------------------------------------------------------------------------
    wear_level: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.0, 1.0))
    wear_contrast: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.5, 1.0))
    
    # -------------------------------------------------------------------------
    # Color configurations for the different fields
    # -------------------------------------------------------------------------
    field_color_red: ColorVariation = field(default_factory=lambda: ColorVariation(
        base_color=(0.8, 0.1, 0.1, 1.0),
        hue_variation=0.02,
        saturation_variation=0.1,
        value_variation=0.15,
        randomize=True
    ))
    
    field_color_green: ColorVariation = field(default_factory=lambda: ColorVariation(
        base_color=(0.1, 0.5, 0.1, 1.0),
        hue_variation=0.02,
        saturation_variation=0.1,
        value_variation=0.15,
        randomize=True
    ))
    
    field_color_white: ColorVariation = field(default_factory=lambda: ColorVariation(
        base_color=(0.9, 0.9, 0.85, 1.0),
        hue_variation=0.0,
        saturation_variation=0.05,
        value_variation=0.1,
        randomize=True
    ))
    
    field_color_black: ColorVariation = field(default_factory=lambda: ColorVariation(
        base_color=(0.02, 0.02, 0.02, 1.0),
        hue_variation=0.0,
        saturation_variation=0.0,
        value_variation=0.02,
        randomize=True
    ))
    
    digit_color: ColorVariation = field(default_factory=lambda: ColorVariation(
        base_color=(0.9, 0.9, 0.9, 1.0),
        hue_variation=0.0,
        saturation_variation=0.0,
        value_variation=0.1,
        randomize=True
    ))
    
    # -------------------------------------------------------------------------
    # Material name mapping (for easy adjustment when names change)
    # -------------------------------------------------------------------------
    material_names: dict = field(default_factory=lambda: {
        "score_red": "red_score_texture_material",
        "score_green": "green_score_texture_material",
        "score_white": "white_score_texture_material",
        "score_black": "black_score_texture_material",
        "number_ring": "number_ring",
    })
    
    # -------------------------------------------------------------------------
    # Node group names (for easy adjustment)
    # -------------------------------------------------------------------------
    node_group_names: dict = field(default_factory=lambda: {
        "score_white_and_color": "group_white_and_color_score_texture",
        "score_black": "group_black_score_texture",
        "digit_wear": "group_digit_wear",
    })
    
    # -------------------------------------------------------------------------
    # Geometry Nodes configuration
    # Maps object names to their Geometry Nodes modifier names
    # -------------------------------------------------------------------------
    geometry_node_modifiers: dict = field(default_factory=lambda: {
        # Object name -> Modifier name
        "Dartboard_Digit_Wire": "GeometryNodes",
        "Dartboard_Digit_Wire_Digits": "GeometryNodes",
    })
