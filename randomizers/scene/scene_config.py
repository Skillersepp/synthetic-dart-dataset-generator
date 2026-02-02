from dataclasses import dataclass


@dataclass
class SceneRandomConfig:
    """Configuration for scene randomization parameters."""
    
    # HDRI settings - path relative to project root
    hdri_folder: str = "assets/HDRIs"
    hdri_strength_min: float = 0.7
    hdri_strength_max: float = 1.3
    hdri_rotation_min: float = 0.0  # in radians
    hdri_rotation_max: float = 6.28318530718  # 2*pi radians (360 degrees)

    # Background Plane settings
    background_plane_enabled: bool = True
    background_plane_probability: float = 0.7  # Probability that the plane is visible (0.0 to 1.0)
    background_texture_folder: str = "assets/textures/background"
    
    # Background Mapping Randomization (X, Y, Z)
    # Location
    bg_location_min: tuple = (-0.5, -0.5, 0.0)
    bg_location_max: tuple = (0.5, 0.5, 0.0)
    
    # Rotation (Radians)
    bg_rotation_min: tuple = (0.0, 0.0, 0.0)
    bg_rotation_max: tuple = (0.0, 0.0, 6.283)
    
    # Scale
    bg_scale_min: tuple = (0.8, 0.8, 1.0)
    bg_scale_max: tuple = (1.2, 1.2, 1.0)
