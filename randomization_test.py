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

DEV_RELOAD = True  # auf False setzen für Produktion / schnelleren Lauf

PROJECT_MODULES = [
	"utils.math_utils",
	"utils.camera_utils",
	"randomizers.base_randomizer",
	"randomizers.camera.camera_config",
	"randomizers.camera.camera_randomizer",
	"randomizers.camera",
	"randomizers.scene.scene_config",
	"randomizers.scene.scene_randomizer",
	"randomizers.scene",
	"randomization_manager",
]

def _dev_hot_reload():
	if not DEV_RELOAD:
		return
	# Dateisystem-Caches invalidieren (falls neue Dateien / Änderungen)
	importlib.invalidate_caches()
	for mod_name in PROJECT_MODULES:
		if mod_name in sys.modules:
			try:
				importlib.reload(sys.modules[mod_name])
			except Exception as e:
				print(f"[DEV_RELOAD] Fehler beim Reload von {mod_name}: {e}")
		else:
			try:
				__import__(mod_name)
			except Exception as e:
				print(f"[DEV_RELOAD] Fehler beim Erstimport von {mod_name}: {e}")

_dev_hot_reload()


from randomization_manager import RandomizationManager
from bpy.app.handlers import persistent

manager = RandomizationManager(global_seed=0, base_path=PROJECT_ROOT)
bpy.context.scene.render.use_lock_interface = True  # UI sperren während Rendern

@persistent
def on_frame_change(scene):
	"""
	Frame change handler. Always gets fresh references from bpy.context
	to avoid stale scene references when settings are changed.
	"""
	# Safety check: Ensure scene and camera exist
	if not scene or not scene.camera:
		return

	# Get fresh references to avoid stale pointers
	camera = scene.camera
	frame = scene.frame_current
	
	try:
		manager.randomize(frame, camera, scene)
	except Exception as e:
		print(f"Error in frame change handler: {e}")

# Event anhängen
# Alten Handler entfernen, falls vorhanden (um Duplikate bei Reload zu vermeiden)
handlers_to_remove = [h for h in bpy.app.handlers.frame_change_pre if h.__name__ == "on_frame_change"]
for h in handlers_to_remove:
    bpy.app.handlers.frame_change_pre.remove(h)

bpy.app.handlers.frame_change_pre.append(on_frame_change)
print(f"Frame Change Handler registriert (Anzahl Handler: {len(bpy.app.handlers.frame_change_pre)})")


	