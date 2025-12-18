import bpy
import math
from typing import Optional, List
from mathutils import Vector, Euler

from randomizers.base_randomizer import BaseRandomizer
from .throw_config import ThrowRandomConfig
from randomizers.dart.dart_randomizer import DartRandomizer

class ThrowRandomizer(BaseRandomizer):
    """
    Spawns multiple darts on the dartboard.
    
    Handles:
    - Duplicating the dart hierarchy
    - Positioning darts
    - Delegating appearance randomization to DartRandomizer
    """

    def __init__(self, seed: int, config: Optional[ThrowRandomConfig] = None, dart_randomizer: DartRandomizer = None):
        self.dart_randomizer = dart_randomizer
        self.spawned_darts: List[bpy.types.Object] = []
        self.template_dart_name = "Dart_Generator"
        self.collection_name = "Generated_Darts"
        self.collection = None
        
        # Call super init which calls _initialize
        super().__init__(seed, config or ThrowRandomConfig())

    def _initialize(self) -> None:
        """
        Initialize the dart pool.
        Creates a collection and spawns the required number of darts.
        """
        self._ensure_collection()
        self._clear_existing_darts()
        self._spawn_dart_pool()

    def _ensure_collection(self):
        """Ensure the collection for generated darts exists."""
        if self.collection_name in bpy.data.collections:
            self.collection = bpy.data.collections[self.collection_name]
        else:
            self.collection = bpy.data.collections.new(self.collection_name)
            bpy.context.scene.collection.children.link(self.collection)

    def _clear_existing_darts(self) -> None:
        """Remove all objects from the generated darts collection."""
        if not self.collection:
            return
            
        # Collect all objects in the collection
        objects_to_delete = set()
        for obj in self.collection.objects:
            objects_to_delete.add(obj)
            # Also include children recursively to be safe
            for child in obj.children_recursive:
                objects_to_delete.add(child)
        
        if objects_to_delete:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects_to_delete:
                # Only select if object is in current view layer (safety check)
                try:
                    obj.select_set(True)
                except RuntimeError:
                    pass
            
            # Delete selected
            bpy.ops.object.delete()
            
        self.spawned_darts.clear()

    def _spawn_dart_pool(self) -> None:
        """Spawn the configured number of darts into the pool."""
        template_dart = bpy.data.objects.get(self.template_dart_name)
        if not template_dart:
            print(f"[ThrowRandomizer] Template dart '{self.template_dart_name}' not found!")
            return

        # Determine if we should use linked duplicates (shared data/materials)
        use_linked = self.config.same_appearance

        for i in range(self.config.num_darts):
            new_dart_root = self._duplicate_hierarchy(template_dart, linked=use_linked)
            if new_dart_root:
                self.spawned_darts.append(new_dart_root)
                
                # Setup geometry references (Parent_Object links)
                if self.dart_randomizer:
                    self.dart_randomizer.setup_geometry_references(new_dart_root)
        
        # Ensure template collection is hidden if possible
        if template_dart.users_collection:
            for coll in template_dart.users_collection:
                coll.hide_viewport = True
                coll.hide_render = True

    def _clear_existing_darts(self) -> None:
        """Remove all objects from the generated darts collection."""
        if not self.collection:
            return
            
        # Collect all objects in the collection
        # Since we link all parts of the hierarchy to the collection, 
        # iterating collection.objects is sufficient.
        objects_to_delete = [obj for obj in self.collection.objects]
        
        # Use low-level remove to ensure deletion without selection context issues
        for obj in objects_to_delete:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as e:
                print(f"[ThrowRandomizer] Error removing object {obj.name}: {e}")
            
        self.spawned_darts.clear()

    def randomize(self, *args, **kwargs) -> None:
        """
        Randomize the existing darts in the pool.
        """
        # Safety check: if pool is empty or size mismatch (e.g. config changed), respawn
        # Check if objects in spawned_darts are valid (not deleted)
        self.spawned_darts = [d for d in self.spawned_darts if d is not None]
        
        # Also check if they are actually in the scene/collection
        self.spawned_darts = [d for d in self.spawned_darts if not self.collection or d.name in self.collection.objects]

        if len(self.spawned_darts) != self.config.num_darts:
             print(f"[ThrowRandomizer] Dart count mismatch ({len(self.spawned_darts)} != {self.config.num_darts}). Respawning pool.")
             self._clear_existing_darts()
             self._spawn_dart_pool()

        base_seed = self.rng.randint(0, 100000)
        
        for i, dart_root in enumerate(self.spawned_darts):
            if not dart_root: continue
            
            # Randomize Appearance
            if self.dart_randomizer:
                # Determine seed for this dart
                if self.config.same_appearance:
                    dart_seed = base_seed
                else:
                    dart_seed = self.rng.randint(0, 100000)
                
                self.dart_randomizer.update_seed(dart_seed)
                self.dart_randomizer.randomize(root_obj=dart_root)
            
            # Randomize Position/Rotation
            self._randomize_transform(dart_root)

    def _duplicate_hierarchy(self, root_obj: bpy.types.Object, linked: bool = False) -> bpy.types.Object:
        """
        Duplicate an object hierarchy using low-level API.
        
        Args:
            root_obj: The root object to duplicate.
            linked: If True, shares Mesh data and Materials (Linked Duplicate). 
                    If False, creates deep copies of Data and Materials.
        """
        
        def copy_recursive(obj, parent_new_obj=None):
            # Copy object wrapper (always needed for separate transform/modifiers)
            new_obj = obj.copy()
            
            # Ensure visibility
            new_obj.hide_render = False
            new_obj.hide_viewport = False
            
            if not linked:
                # Deep copy data (mesh, curve, etc.)
                if obj.data:
                    new_obj.data = obj.data.copy()
                
                # Deep copy materials
                if hasattr(new_obj, "material_slots"):
                    for i, slot in enumerate(new_obj.material_slots):
                        if slot.material:
                            new_mat = slot.material.copy()
                            slot.material = new_mat
            # If linked=True, we keep the references to original data and materials
            # This saves memory and ensures they look identical

            # Link to new collection
            if self.collection:
                self.collection.objects.link(new_obj)
            
            # Parent to new parent
            if parent_new_obj:
                new_obj.parent = parent_new_obj
                # Maintain offset
                new_obj.matrix_parent_inverse = obj.matrix_parent_inverse.copy()

            # Process children
            for child in obj.children:
                copy_recursive(child, new_obj)
            
            return new_obj

        new_root = copy_recursive(root_obj)
        return new_root

    def _randomize_transform(self, obj: bpy.types.Object) -> None:
        """Apply random position and rotation."""
        # Position
        x = self.config.pos_x_min + self.rng.random() * (self.config.pos_x_max - self.config.pos_x_min)
        y = self.config.pos_y_min + self.rng.random() * (self.config.pos_y_max - self.config.pos_y_min)
        z = self.config.pos_z_fixed # Assuming board plane
        
        obj.location = Vector((x, y, z))
        
        # Rotation
        rx = math.radians(self.config.rot_x_min + self.rng.random() * (self.config.rot_x_max - self.config.rot_x_min))
        ry = math.radians(self.config.rot_y_min + self.rng.random() * (self.config.rot_y_max - self.config.rot_y_min))
        rz = math.radians(self.config.rot_z_min + self.rng.random() * (self.config.rot_z_max - self.config.rot_z_min))
        
        obj.rotation_euler = Euler((rx, ry, rz), 'XYZ')
