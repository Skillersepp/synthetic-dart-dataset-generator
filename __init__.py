bl_info = {
    "name": "Dart Dataset Generator",
    "author": "Tim Vesper",
    "version": (1, 0, 0),
    "blender": (4, 5, 3),
    "location": "3D View > UI > Dataset Generator",
    "description": "Generates a synthetic dataset of dartboards and darts.",
    "category": "Object",
}

import bpy

# import modules
from . import ui_panel


modules = [
    ui_panel,
]

def register():
    """Wird aufgerufen, wenn das Add-on aktiviert wird."""
    for module in modules:
        module.register()

def unregister():
    """Wird aufgerufen, wenn das Add-on deaktiviert wird."""
    for module in reversed(modules):
        module.unregister()
