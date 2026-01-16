from dataclasses import dataclass


@dataclass
class SceneRandomConfig:
    """Configuration for scene randomization parameters."""
    
    # HDRI settings - path relative to project root
    hdri_folder: str = "assets/HDRIs"
    hdri_strength_min: float = 0.2
    hdri_strength_max: float = 1.5
    hdri_rotation_min: float = 0.0  # in radians
    hdri_rotation_max: float = 6.28318530718  # 2*pi radians (360 degrees)
