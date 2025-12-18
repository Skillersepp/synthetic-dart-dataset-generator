from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ThrowRandomConfig:
    """
    Configuration for dart throwing randomization.
    """
    num_darts: int = 3
    same_appearance: bool = False  # If True, all darts look the same (same seed)
    
    # Position randomization (simple box for now, can be extended)
    # Assuming dartboard is at origin facing Y or similar.
    # Adjust these defaults based on scene scale.
    pos_x_min: float = -0.15
    pos_x_max: float = 0.15
    pos_y_min: float = -0.15
    pos_y_max: float = 0.15
    pos_z_fixed: float = 0.0 # Distance from board? Or is board at 0?
    
    # Rotation randomization (in degrees)
    rot_x_min: float = -10.0
    rot_x_max: float = 10.0
    rot_y_min: float = -10.0
    rot_y_max: float = 10.0
    rot_z_min: float = 0.0
    rot_z_max: float = 360.0
