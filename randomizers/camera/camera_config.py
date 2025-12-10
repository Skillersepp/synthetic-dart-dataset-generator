from dataclasses import dataclass
from enum import Enum

class CameraRollMode(Enum):
    """Camera roll strategies."""
    TWENTY_EXACT_UP = 1     # 20 is exactly up (no jitter)
    TWENTY_APPROX_UP = 2    # 20 is approximately up (small jitter)
    LEVEL_TO_HORIZON = 3    # Camera does not roll (horizon remains level)
    RANDOM = 4              # Random roll

@dataclass
class CameraRandomConfig:
    """Configuration for camera randomization parameters."""

    # Optical parameters
    focal_length_min: float = 20.0
    focal_length_max: float = 60.0
    sensor_width_min: float = 8
    sensor_width_max: float = 36.0

    # Distance factors around the computed minimum distance
    distance_factor_min: float = 1.0
    distance_factor_max: float = 2.0

    # Spherical angles (camera on a spherical shell)
    polar_angle_min: float = 0.0
    polar_angle_max: float = 75.0
    azimuth_min: float = 0.0
    azimuth_max: float = 360.0

    # Look jitter (simulating imperfect aiming)
    look_jitter_stddev: float = 0.02

    # Camera roll behaviour
    roll_mode: CameraRollMode = CameraRollMode.TWENTY_EXACT_UP
    roll_stddev_deg: float = 6.0           # small natural camera roll
    roll_min_deg: float = -180.0            # used when full-roll is enabled
    roll_max_deg: float = 180.0

    # DOF
    board_diameter_m: float = 0.44
    focus_radius_max_m: float = 0.225
    aperture_fstop_min: float = 0.8
    aperture_fstop_max: float = 5.6
