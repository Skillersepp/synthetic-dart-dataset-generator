"""
Utility functions for dataset directory setup and Blender render configuration.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import DatasetConfig


def setup_output_paths(base_path: Path, config: "DatasetConfig") -> tuple[Path, Path]:
    """
    Setup and create output directory structure for the dataset.
    
    Creates:
        <base_path>/<output_base>/dataset_<global_seed>/
            ├── images/
            └── labels/
    
    Args:
        base_path: Project root path.
        config: Dataset configuration.
        
    Returns:
        Tuple of (images_path, labels_path).
    """
    # Build paths
    dataset_dir = base_path / config.output_base / config.dataset_name
    images_path = dataset_dir / "images"
    labels_path = dataset_dir / "labels"
    
    # Create directories if they don't exist
    images_path.mkdir(parents=True, exist_ok=True)
    labels_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[DatasetUtils] Dataset directory: {dataset_dir}")
    print(f"[DatasetUtils] Images path: {images_path}")
    print(f"[DatasetUtils] Labels path: {labels_path}")
    
    return images_path, labels_path


def setup_blender_render_path(images_path: Path, transparent: bool = True, frame_digits: int = 4) -> None:
    """
    Configure Blender's render output path and transparency settings.
    
    Args:
        images_path: Path to the images directory.
        transparent: Whether to render with transparent background.
        frame_digits: Number of digits for frame numbering (e.g., 6 for 000001.png).
    """
    import bpy
    
    # Set render output path with frame number placeholder
    # Blender uses '#' for each digit in the frame number
    frame_placeholder = '#' * frame_digits
    render_path = str(images_path) + "/" + frame_placeholder
    bpy.context.scene.render.filepath = render_path
    
    # Set file format
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    
    # Set transparency (Film > Transparent in Blender UI)
    bpy.context.scene.render.film_transparent = transparent
    
    print(f"[DatasetUtils] Blender render path set to: {render_path}")
    print(f"[DatasetUtils] Transparent background: {transparent}")
