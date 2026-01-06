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
	"utils.math_utils",
	"utils.camera_utils",
	"utils.node_utils",
	"utils.color_utils",
	"utils.dartboard_layout",
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
	"randomizers.annotation_manager",
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


from randomization_manager import RandomizationManager
from bpy.app.handlers import persistent

manager = RandomizationManager(global_seed=0, base_path=PROJECT_ROOT)
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
	
	try:
		manager.randomize(frame, camera, scene)
	except Exception as e:
		print(f"Error in frame_change_pre: {e}")

@persistent
def on_render_post(scene):
	"""
	Called AFTER the frame is rendered.
	Use this to read the calculated positions (Annotation) to ensure sync with render.
	"""
	
	if not scene or not scene.camera:
		return
	try:
		manager.annotation_manager.annotate(scene, scene.camera)
	except Exception as e:
		print(f"Error in render_post: {e}")

# Register event handlers
# Clear old handlers
for h in [h for h in bpy.app.handlers.frame_change_pre if h.__name__ in ("on_frame_change_pre", "on_frame_change")]:
    bpy.app.handlers.frame_change_pre.remove(h)

for h in [h for h in bpy.app.handlers.render_post if h.__name__ == "on_render_post"]:
    bpy.app.handlers.render_post.remove(h)

# Append new handlers
bpy.app.handlers.frame_change_pre.append(on_frame_change_pre)
bpy.app.handlers.render_post.append(on_render_post)

print(f"Handlers registered: Pre ({len(bpy.app.handlers.frame_change_pre)}), Render Post ({len(bpy.app.handlers.render_post)})")

# Initial trigger
on_frame_change_pre(bpy.context.scene)
# Force update for the initial state
bpy.context.view_layer.update()


	