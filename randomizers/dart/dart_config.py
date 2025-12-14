from dataclasses import dataclass, field
from typing import Optional

@dataclass
class RangeOrFixed:
    """
    Allows either a fixed value or a range for randomization.
    """
    min_val: float = 0.0
    max_val: float = 1.0
    fixed: Optional[float] = None
    
    def get_value(self, rng) -> float:
        """Returns either the fixed value or a random value within the range."""
        if self.fixed is not None:
            return self.fixed
        return rng.uniform(self.min_val, self.max_val)

@dataclass
class DartRandomConfig:
    """
    Configuration for dart geometry randomization.
    """
    # Tip Generator
    tip_length: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(20.0, 45.0))
    
    # Barrel Generator
    barrel_length: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(40.0, 55.0))
    barrel_thickness: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.15, 2.2))
    
    # Shaft Generator
    shaft_length: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(26.0, 56.0))
    shaft_shape_mix: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.0, 1.0))
    
    # Flight Generator
    flight_insertion_depth: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(10.0, 20.0))
    
    # Flight Selection
    randomize_flight_type: bool = True
    fixed_flight_index: int = 100

    # Flight Material
    prob_flight_texture_flags: float = 0.3
    prob_flight_texture_outpainted: float = 0.5
    prob_flight_gradient: float = 0.1
    prob_flight_solid: float = 0.1
    
    flight_roughness: RangeOrFixed = field(default_factory=lambda: RangeOrFixed(0.0, 1.0))
    
    # Color generation settings for gradient/solid
    flight_color_saturation_min: float = 0.5
    flight_color_saturation_max: float = 1.0
    flight_color_value_min: float = 0.5
    flight_color_value_max: float = 1.0
