"""
Utility functions for loading and managing assets (images, textures, HDRIs) in Blender.

This module provides a unified interface for loading assets from the assets folder.
All asset paths should be defined in the respective config files and loaded using
these utility functions to ensure consistent behavior across all randomizers.

Lazy Loading Pattern:
- Use get_texture_paths() to scan folder paths at startup (fast)
- Use load_single_image() to load individual images on-demand during randomize()
- This avoids loading thousands of images at startup
"""

import bpy
from pathlib import Path
from typing import List, Optional, Set


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


def get_texture_paths(
    folder_path: str | Path,
    extensions: Optional[List[str]] = None,
    recursive: bool = False
) -> List[Path]:
    """
    Get all texture file paths from a folder WITHOUT loading them into Blender.
    
    This is the preferred method for discovering assets. It's very fast because
    it only scans the filesystem. Use load_single_image() to load individual 
    images on-demand during randomize() calls.
    
    Args:
        folder_path: Relative path to texture folder (e.g. "assets/textures/dart/flight")
        extensions: List of file extensions to include (default: common image formats)
        recursive: Whether to search recursively in subfolders
        
    Returns:
        Sorted list of absolute Path objects to texture files
    """
    if extensions is None:
        extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.hdr']
    
    # Normalize extensions to lowercase
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    # Resolve path
    abs_path = resolve_asset_path(folder_path)
    
    if not abs_path.exists() or not abs_path.is_dir():
        return []
    
    # Find all image files
    image_files = []
    
    if recursive:
        # Use rglob for recursive search
        # Note: rglob does not support multiple extensions directly like glob lists so we iterate
        for ext in extensions:
             image_files.extend(abs_path.rglob(f"*{ext}"))
             image_files.extend(abs_path.rglob(f"*{ext.upper()}"))
    else:
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
    
    return sorted(unique_files)


def load_single_image(
    file_path: str | Path,
    force_reload: bool = False,
    use_fake_user: bool = False
) -> Optional[bpy.types.Image]:
    """
    Load a single image into Blender's data.
    
    This is the preferred method for loading images. Call this on-demand during
    randomize() with a path from get_texture_paths(). Images are cached by Blender,
    so repeated loads of the same file are fast.
    
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
        # Use check_existing=True to let Blender find the loaded image by path
        # This prevents creating duplicates (leak) if the image is already loaded
        img = bpy.data.images.load(str(file_path.resolve()), check_existing=True)
        
        # If the loaded image has a broken path (e.g. from a different machine),
        # but check_existing=True found it (maybe by name match in some blender versions? 
        # or if we are just fixing properties), ensure filepath is correct.
        # Note: check_existing=True usually matches by path. 
        # If we moved the project, it creates a new image. This is acceptable.
        
        # Set fake user to keep image in memory
        if use_fake_user:
            img.use_fake_user = True

        if force_reload:
            img.reload()
        
        return img
        
    except Exception as e:
        print(f"[AssetUtils] Error loading {file_path}: {e}")
        return None


def cleanup_orphaned_images():
    """
    Remove images that have no users (users == 0).
    Expected to be called periodically during rendering to prevent RAM saturation,
    especially when load_single_image(..., use_fake_user=False) is used.
    """
    removed_count = 0
    for img in list(bpy.data.images):
        if img.users == 0:
            try:
                bpy.data.images.remove(img)
                removed_count += 1
            except Exception as e:
                print(f"[AssetUtils] Failed to remove orphaned image {img.name}: {e}")
    
    if removed_count > 0:
        print(f"[AssetUtils] Cleaned up {removed_count} orphaned images.")

