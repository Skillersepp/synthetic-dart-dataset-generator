from dataclasses import dataclass
from pathlib import Path


@dataclass
class SceneRandomConfig:
    """Configuration for scene randomization parameters."""
    
    # HDRI settings
    hdri_folder: Path = Path("assets/HDRIs")
    hdri_strength_min: float = 0.2
    hdri_strength_max: float = 1.5
    hdri_rotation_min: float = 0.0  # in radians
    hdri_rotation_max: float = 6.28318530718  # 2*pi radians (360 degrees)
