from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ThrowRandomConfig:
    """
    Configuration for dart throwing randomization.
    """
    num_darts: int = 3
    same_appearance: bool = False  # If True, all darts look the same (same seed)
    
    # Position randomization (Polar coordinates)
    # Radius in meters
    max_radius: float = 0.25
    
    # Rotation randomization (in degrees)
    rot_x_min: float = -10.0
    rot_x_max: float = 10.0
    rot_y_min: float = -10.0
    rot_y_max: float = 10.0
    rot_z_min: float = 0.0
    rot_z_max: float = 360.0

    # Embedding depth (factor of tip length)
    embed_depth_factor_min: float = 0.1
    embed_depth_factor_max: float = 0.8

    # Visibility / Bouncer settings
    allow_darts_outside_board: bool = False # If False, darts with radius > 0.225m are hidden
    bouncer_probability: float = 0.0 # Probability (0.0 to 1.0) that a dart is hidden (simulating a bouncer)
