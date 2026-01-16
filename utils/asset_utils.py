"""
Utility functions for loading and managing assets (images, textures, HDRIs) in Blender.

This module provides a unified interface for loading assets from the assets folder.
All asset paths should be defined in the respective config files and loaded using
these utility functions to ensure consistent behavior across all randomizers.
"""

import bpy
from pathlib import Path
from typing import List, Dict, Optional, Set


# Module-level base path, set during initialization
_base_path: Optional[Path] = None


def set_base_path(path: Path) -> None:
    """
    Set the base path for asset loading.
    
    This should be called once during addon initialization with the path
    to the root of the project (where the assets folder is located).
    
    Args:
        path: The base path to the project root
    """
    global _base_path
    _base_path = Path(path)
    print(f"[AssetUtils] Base path set to: {_base_path}")


def get_base_path() -> Path:
    """
    Get the current base path.
    
    Returns:
        The base path, defaults to current working directory if not set
    """
    global _base_path
    if _base_path is None:
        _base_path = Path.cwd()
        print(f"[AssetUtils] Warning: Base path not set, using cwd: {_base_path}")
    return _base_path


def resolve_asset_path(relative_path: str | Path) -> Path:
    """
    Resolve a relative asset path to an absolute path.
    
    Args:
        relative_path: Path relative to the project root (e.g. "assets/HDRIs")
        
    Returns:
        Absolute path to the asset folder/file
    """
    base = get_base_path()
    return base / relative_path


def repair_image_path(image: bpy.types.Image, expected_folder: Path) -> bool:
    """
    Repair an image's filepath if it points to a non-existent location.
    
    This is useful when switching between different machines (e.g., Windows/Linux)
    where absolute paths in the .blend file become invalid.
    
    Args:
        image: The Blender image datablock to repair
        expected_folder: The folder where the image should be located
        
    Returns:
        True if path was repaired, False if no repair was needed or possible
    """
    current_path = Path(bpy.path.abspath(image.filepath))
    
    # If current path exists, no repair needed
    if current_path.exists():
        return False
    
    # Try to find the file in the expected folder
    expected_path = expected_folder / image.name
    if expected_path.exists():
        image.filepath = str(expected_path)
        image.reload()
        return True
    
    # Try case-insensitive search
    if expected_folder.exists():
        for file in expected_folder.iterdir():
            if file.name.lower() == image.name.lower():
                image.filepath = str(file)
                image.reload()
                return True
    
    return False


def repair_all_image_paths() -> int:
    """
    Attempt to repair all broken image paths in the current .blend file.
    
    This scans all images and tries to find them relative to the base path.
    
    Returns:
        Number of images that were repaired
    """
    base = get_base_path()
    repaired = 0
    
    for img in bpy.data.images:
        # Skip packed images and generated images
        if img.packed_file or img.source == 'GENERATED':
            continue
            
        current_path = Path(bpy.path.abspath(img.filepath))
        
        # If path exists, no repair needed
        if current_path.exists():
            continue
        
        # Try to find the file somewhere in the assets folder
        filename = Path(img.filepath).name
        assets_path = base / "assets"
        
        if assets_path.exists():
            # Search recursively for the file
            found = False
            for found_file in assets_path.rglob(filename):
                img.filepath = str(found_file)
                img.reload()
                repaired += 1
                found = True
                break
            
            if not found:
                # Case-insensitive search
                for found_file in assets_path.rglob("*"):
                    if found_file.is_file() and found_file.name.lower() == filename.lower():
                        img.filepath = str(found_file)
                        img.reload()
                        repaired += 1
                        break
    
    if repaired > 0:
        print(f"[AssetUtils] Repaired {repaired} image paths")
    
    return repaired


def load_images_from_folder(
    folder_path: str | Path,
    extensions: Optional[List[str]] = None,
    force_reload: bool = False,
    use_fake_user: bool = True
) -> List[bpy.types.Image]:
    """
    Load all images from a folder into Blender's data.
    
    Args:
        folder_path: Relative path to the folder (e.g. "assets/textures/dart/flight/flags")
        extensions: List of file extensions to load (default: common image formats)
        force_reload: If True, reload existing images from disk
        use_fake_user: If True, set fake user on loaded images to prevent garbage collection
        
    Returns:
        List of loaded Blender Image datablocks
    """
    if extensions is None:
        extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.exr', '.hdr']
    
    # Normalize extensions to lowercase
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    # Resolve path
    abs_path = resolve_asset_path(folder_path)
    
    if not abs_path.exists():
        print(f"[AssetUtils] Warning: Folder not found: {abs_path}")
        return []
    
    if not abs_path.is_dir():
        print(f"[AssetUtils] Warning: Path is not a directory: {abs_path}")
        return []
    
    # Find all image files
    image_files = []
    for ext in extensions:
        image_files.extend(abs_path.glob(f"*{ext}"))
        image_files.extend(abs_path.glob(f"*{ext.upper()}"))
    
    # Remove duplicates (case-insensitive systems might find same file twice)
    seen: Set[str] = set()
    unique_files = []
    for f in image_files:
        if f.name.lower() not in seen:
            seen.add(f.name.lower())
            unique_files.append(f)
    image_files = unique_files
    
    if not image_files:
        print(f"[AssetUtils] Warning: No image files found in {abs_path}")
        return []
    
    # Load images
    loaded_images = []
    for img_file in sorted(image_files):
        try:
            img = load_single_image(img_file, force_reload=force_reload, use_fake_user=use_fake_user)
            if img:
                loaded_images.append(img)
        except Exception as e:
            print(f"[AssetUtils] Failed to load {img_file.name}: {e}")
    
    print(f"[AssetUtils] Loaded {len(loaded_images)} images from {folder_path}")
    return loaded_images


def load_single_image(
    file_path: str | Path,
    force_reload: bool = False,
    use_fake_user: bool = True
) -> Optional[bpy.types.Image]:
    """
    Load a single image into Blender's data.
    
    Automatically repairs broken paths when switching between different machines
    (e.g., Windows/Linux) where absolute paths in the .blend file become invalid.
    
    Args:
        file_path: Absolute or relative path to the image file
        force_reload: If True, reload from disk even if image exists
        use_fake_user: If True, set fake user to prevent garbage collection
        
    Returns:
        The loaded Blender Image datablock, or None if loading failed
    """
    # Resolve path if relative
    if not Path(file_path).is_absolute():
        file_path = resolve_asset_path(file_path)
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"[AssetUtils] Warning: File not found: {file_path}")
        return None
    
    try:
        # Check if image already exists in Blender (by name)
        if file_path.name in bpy.data.images:
            img = bpy.data.images[file_path.name]
            
            # Always update the filepath to the correct location
            # This fixes cross-platform path issues (Windows <-> Linux)
            current_filepath = Path(bpy.path.abspath(img.filepath))
            if current_filepath != file_path or not current_filepath.exists():
                img.filepath = str(file_path)
                img.reload()
            elif force_reload:
                img.reload()
        else:
            # Load new image using absolute path
            # Use check_existing=False to avoid reusing images with broken paths
            img = bpy.data.images.load(str(file_path.resolve()), check_existing=False)
        
        # Set fake user to keep image in memory
        if use_fake_user:
            img.use_fake_user = True
        
        return img
        
    except Exception as e:
        print(f"[AssetUtils] Error loading {file_path}: {e}")
        return None


def load_hdris(
    folder_path: str | Path,
    force_reload: bool = False
) -> Dict[str, bpy.types.Image]:
    """
    Load all HDRI files from a folder.
    
    Args:
        folder_path: Relative path to HDRI folder (e.g. "assets/HDRIs")
        force_reload: If True, reload from disk
        
    Returns:
        Dictionary mapping filename to Image datablock
    """
    extensions = ['.exr', '.hdr']
    images = load_images_from_folder(
        folder_path,
        extensions=extensions,
        force_reload=force_reload,
        use_fake_user=True
    )
    
    return {img.name: img for img in images}


def load_textures(
    folder_path: str | Path,
    force_reload: bool = False
) -> List[bpy.types.Image]:
    """
    Load all texture files from a folder.
    
    Args:
        folder_path: Relative path to texture folder
        force_reload: If True, reload from disk
        
    Returns:
        List of loaded Image datablocks
    """
    extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
    return load_images_from_folder(
        folder_path,
        extensions=extensions,
        force_reload=force_reload,
        use_fake_user=True
    )

