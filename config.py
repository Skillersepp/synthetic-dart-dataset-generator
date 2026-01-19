"""
Global configuration for the Blender Dart Dataset Generator.

This module contains default values for rendering and dataset generation.
"""

from dataclasses import dataclass


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    
    # Seed for reproducibility
    global_seed: int = 0
    
    # Frame range
    start_frame: int = 1
    end_frame: int = 50
    
    # Output paths (relative to project root)
    output_base: str = "output"
    
    # Render settings
    render_engine: str = "EEVEE"  # "CYCLES" or "EEVEE"
    render_samples: int = 8
    resolution_x: int = 1000
    resolution_y: int = 1000
    render_transparent: bool = True  # Transparent background for compositing
    
    @property
    def dataset_name(self) -> str:
        """Generate dataset folder name based on global seed."""
        return f"dataset_{self.global_seed}"


# Default configuration instance
DEFAULT_CONFIG = DatasetConfig()
