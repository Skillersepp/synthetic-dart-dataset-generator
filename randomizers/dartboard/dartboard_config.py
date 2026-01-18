from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import math


@dataclass
class WeightedChoice:
    """
    Allows weighted random selection from a list of values.
    
    Each value has an associated weight (probability).
    Weights are normalized automatically.
    """
    values: List[int] = field(default_factory=lambda: [1])
    weights: List[float] = field(default_factory=lambda: [1.0])
    
    def get_value(self, rng) -> int:
        """Returns a weighted random value from the list."""
        return rng.choices(self.values, weights=self.weights, k=1)[0]


@dataclass
class NormalDistribution:
    """
    Configuration for normal (Gaussian) distribution sampling.
    
    Optionally clamps values to a min/max range.
    """
    mean: float = 0.0
    std_dev: float = 1.0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    
    def get_value(self, rng) -> float:
        """Returns a normally distributed random value, optionally clamped."""
        value = rng.gauss(self.mean, self.std_dev)
        if self.min_val is not None:
            value = max(self.min_val, value)
        if self.max_val is not None:
            value = min(self.max_val, value)
        return value


@dataclass
class OuterRingMappingConfig:
    """
    Configuration for outer ring texture Mapping node randomization.
    
    Controls Location, Rotation and Scale of the texture mapping.
    """
    randomize: bool = True
    
    # Location: X uniform [0, 1], Y normal distribution
    location_x_min: float = 0.0
    location_x_max: float = 1.0
    location_y: NormalDistribution = field(default_factory=lambda: NormalDistribution(
        mean=0.0, std_dev=0.1
    ))
    
    # Rotation: Z normal distribution (in degrees, will be converted to radians)
    rotation_z_degrees: NormalDistribution = field(default_factory=lambda: NormalDistribution(
        mean=0.0, std_dev=0.5
    ))
    
    # Scale: Weighted integer choice (same value for X, Y, Z)
    scale: WeightedChoice = field(default_factory=lambda: WeightedChoice(
        values=[1, 2, 3, 4],
        weights=[0.8, 0.1, 0.05, 0.05]  # 80%, 10%, 5%, 5%
    ))


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
    randomize_cracks: bool = True
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
        saturation_variation=0.5,
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
    # Outer Ring Mapping Node Configuration
    # -------------------------------------------------------------------------
    outer_ring_mapping: OuterRingMappingConfig = field(default_factory=OuterRingMappingConfig)
    
    # -------------------------------------------------------------------------
    # Asset paths (relative to project root)
    # -------------------------------------------------------------------------
    outer_ring_textures_folder: str = "assets/textures/dartboard/ring"
    
    # -------------------------------------------------------------------------
    # Material name mapping (for easy adjustment when names change)
    # -------------------------------------------------------------------------
    material_names: dict = field(default_factory=lambda: {
        "score_red": "red_score_texture_material",
        "score_green": "green_score_texture_material",
        "score_white": "white_score_texture_material",
        "score_black": "black_score_texture_material",
        "number_ring": "number_ring",
        "outer_ring": "outer_ring_texture_material",
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
