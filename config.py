"""
Global configuration for the Blender Dart Dataset Generator.

This module contains default values for rendering and dataset generation.
"""

from dataclasses import dataclass


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    
    # Seed for reproducibility
    global_seed: int = 1
    
    # Frame range
    start_frame: int = 1
    end_frame: int = 300000
    
    # Output paths (relative to project root)
    output_base: str = "output"
    
    # Render settings
    render_engine: str = "EEVEE"  # "CYCLES" or "EEVEE"
    render_samples: int = 8
    resolution_x: int = 1024
    resolution_y: int = 1024
    render_transparent: bool = True  # Transparent background for compositing
    
    @property
    def dataset_name(self) -> str:
        """Generate dataset folder name based on global seed."""
        return f"dataset_{self.global_seed}"
    
    @property
    def frame_digits(self) -> int:
        """Calculate the number of digits needed for frame numbering."""
        return len(str(self.end_frame))


# Default configuration instance
DEFAULT_CONFIG = DatasetConfig()
