import sys
from pathlib import Path
import random
import importlib
import os
import time

# Ensure this project root is on sys.path so Blender can import local modules
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

import bpy

DEV_RELOAD = True  # Set to False for production / faster execution

PROJECT_MODULES = [
    "config",
    "utils",
    "utils.asset_utils",
    "utils.math_utils",
    "utils.camera_utils",
    "utils.node_utils",
    "utils.color_utils",
    "utils.dartboard_layout",
	"utils.annotation_manager",
    "randomizers.base_randomizer",
    "randomizers.camera.camera_config",
    "randomizers.camera.camera_randomizer",
    "randomizers.camera",
    "randomizers.scene.scene_config",
    "randomizers.scene.scene_randomizer",
    "randomizers.scene",
    "randomizers.dartboard.dartboard_config",
    "randomizers.dartboard.dartboard_randomizer",
    "randomizers.dartboard",
    "randomizers.dart.dart_config",
    "randomizers.dart.dart_randomizer",
    "randomizers.dart",
    "randomizers.throw.throw_config",
    "randomizers.throw.throw_randomizer",
    "randomizers.throw",
    "randomization_manager",
]

def _dev_hot_reload():
	if not DEV_RELOAD:
		return
	# Invalidate filesystem caches (in case of new files / changes)
	importlib.invalidate_caches()
	for mod_name in PROJECT_MODULES:
		if mod_name in sys.modules:
			try:
				importlib.reload(sys.modules[mod_name])
			except Exception as e:
				print(f"[DEV_RELOAD] Error reloading {mod_name}: {e}")
		else:
			try:
				__import__(mod_name)
			except Exception as e:
				print(f"[DEV_RELOAD] Error importing {mod_name}: {e}")

_dev_hot_reload()


from config import DatasetConfig
from utils.dataset_utils import setup_output_paths, setup_blender_render_path
from randomization_manager import RandomizationManager
from bpy.app.handlers import persistent

# === Dataset Configuration ===
config = DatasetConfig()

# Set frame range in Blender
bpy.context.scene.frame_start = config.start_frame
bpy.context.scene.frame_end = config.end_frame

# Paths will be set up when rendering starts
images_path = None
labels_path = None
manager = None
_render_initialized = False

def _initialize_for_render():
    """Initialize output paths and manager when rendering starts."""
    global images_path, labels_path, manager, _render_initialized
    
    if _render_initialized:
        return
    
    # Setup output directories (creates folders)
    images_path, labels_path = setup_output_paths(PROJECT_ROOT, config)
    
    # Configure Blender render output with dynamic frame digits
    setup_blender_render_path(images_path, config.render_transparent, config.frame_digits)
    
    # Initialize manager with paths
    manager = RandomizationManager(
        global_seed=config.global_seed,
        base_path=PROJECT_ROOT,
        labels_path=labels_path,
        frame_digits=config.frame_digits
    )
    
    _render_initialized = True
    print("[Init] Render initialization complete.")

# Initialize manager for viewport preview (without creating folders)
preview_manager = RandomizationManager(
    global_seed=config.global_seed,
    base_path=PROJECT_ROOT,
    labels_path=PROJECT_ROOT / config.output_base / config.dataset_name / "labels",  # Not created yet
    frame_digits=config.frame_digits
)
bpy.context.scene.render.use_lock_interface = True  # Lock UI during rendering

@persistent
def on_frame_change_pre(scene):
	"""
	Called BEFORE the frame changes/updates.
	Use this to set new random values.
	"""
	if not scene or not scene.camera:
		return

	camera = scene.camera
	frame = scene.frame_current
	
	# Use render manager if initialized, otherwise preview manager
	active_manager = manager if _render_initialized else preview_manager
	
	try:
		active_manager.randomize(frame, camera, scene)
	except Exception as e:
		print(f"Error in frame_change_pre: {e}")

@persistent
def on_render_init(scene):
	"""
	Called ONCE before rendering starts (before first frame).
	Use this to setup output directories.
	"""
	_initialize_for_render()

@persistent
def on_render_post(scene):
	"""
	Called AFTER the frame is rendered.
	Use this to read the calculated positions (Annotation) to ensure sync with render.
	"""
	
	if not scene or not scene.camera:
		return
	
	if not manager:
		print("[Warning] Manager not initialized, skipping annotation.")
		return
		
	try:
		manager.annotation_manager.annotate(scene, scene.camera)
	except Exception as e:
		print(f"Error in render_post: {e}")

@persistent
def on_render_complete(scene):
	"""Called when render animation completes."""
	global _render_initialized
	_render_initialized = False
	print("[Init] Render complete. Reset initialization flag.")

@persistent
def on_render_cancel(scene):
	"""Called when render is cancelled."""
	global _render_initialized
	_render_initialized = False
	print("[Init] Render cancelled. Reset initialization flag.")

# Register event handlers
# Clear old handlers
for h in [h for h in bpy.app.handlers.frame_change_pre if h.__name__ in ("on_frame_change_pre", "on_frame_change")]:
    bpy.app.handlers.frame_change_pre.remove(h)

for h in [h for h in bpy.app.handlers.render_init if h.__name__ == "on_render_init"]:
    bpy.app.handlers.render_init.remove(h)

for h in [h for h in bpy.app.handlers.render_post if h.__name__ == "on_render_post"]:
    bpy.app.handlers.render_post.remove(h)

for h in [h for h in bpy.app.handlers.render_complete if h.__name__ == "on_render_complete"]:
    bpy.app.handlers.render_complete.remove(h)

for h in [h for h in bpy.app.handlers.render_cancel if h.__name__ == "on_render_cancel"]:
    bpy.app.handlers.render_cancel.remove(h)

# Append new handlers
bpy.app.handlers.frame_change_pre.append(on_frame_change_pre)
bpy.app.handlers.render_init.append(on_render_init)
bpy.app.handlers.render_post.append(on_render_post)
bpy.app.handlers.render_complete.append(on_render_complete)
bpy.app.handlers.render_cancel.append(on_render_cancel)

print(f"Handlers registered: Pre ({len(bpy.app.handlers.frame_change_pre)}), Render Init ({len(bpy.app.handlers.render_init)}), Render Post ({len(bpy.app.handlers.render_post)})")

# Initial trigger for viewport preview
on_frame_change_pre(bpy.context.scene)
# Force update for the initial state
bpy.context.view_layer.update()


