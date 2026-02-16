"""
Utility functions for dataset directory setup and Blender render configuration.
"""

import json
import dataclasses
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

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


def _serialize_value(obj: Any) -> Any:
    """
    Recursively serialize a value to a JSON-compatible type.
    
    Handles dataclasses, Enums, tuples, Paths, and other common types.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _serialize_value(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    elif isinstance(obj, Enum):
        return obj.name
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [_serialize_value(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): _serialize_value(v) for k, v in obj.items()}
    elif isinstance(obj, (int, float, bool, str, type(None))):
        return obj
    else:
        return str(obj)


def save_config_json(
    dataset_dir: Path,
    dataset_config: "DatasetConfig",
    configs: Dict[str, Any],
) -> Path:
    """
    Save all configuration settings to a JSON file in the dataset directory.
    
    Creates a structured JSON file with metadata and all config sections.
    The format is extensible — any new fields added to the dataclass configs
    will automatically be included on the next run.
    
    Args:
        dataset_dir: Root directory of the current dataset (parent of images/labels).
        dataset_config: The global DatasetConfig instance.
        configs: Dict mapping section names to config dataclass instances,
                 e.g. {"camera": CameraRandomConfig(), "scene": SceneRandomConfig(), ...}.
    
    Returns:
        Path to the written JSON file.
    """
    import bpy

    output: Dict[str, Any] = {}

    # Metadata block
    output["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "blender_version": ".".join(str(v) for v in bpy.app.version),
        "render_engine": bpy.context.scene.render.engine,
    }

    # Global dataset config
    output["dataset"] = _serialize_value(dataset_config)

    # All randomizer configs (camera, dart, dartboard, scene, throw, …)
    for section_name, cfg in configs.items():
        output[section_name] = _serialize_value(cfg)

    # Write JSON
    json_path = dataset_dir / "config.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"[DatasetUtils] Config saved to: {json_path}")
    return json_path
