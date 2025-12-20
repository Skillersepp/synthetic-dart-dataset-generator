import bpy
import math
from typing import Optional, List
from mathutils import Vector, Euler

from randomizers.base_randomizer import BaseRandomizer
from .throw_config import ThrowRandomConfig
from randomizers.dart.dart_randomizer import DartRandomizer
from randomizers.dart.dart import Dart

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
        self.spawned_darts: List[Dart] = []
        self.spawned_k_points: List[bpy.types.Object] = []
        self.template_dart_name = "Dart_Generator"
        self.template_k_name = "Dart_K"
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
        self.spawned_k_points.clear()

    def _spawn_dart_pool(self) -> None:
        """Spawn the configured number of darts into the pool."""
        template_dart = bpy.data.objects.get(self.template_dart_name)
        if not template_dart:
            print(f"[ThrowRandomizer] Template dart '{self.template_dart_name}' not found!")
            return
            
        template_k = bpy.data.objects.get(self.template_k_name)
        if not template_k:
            print(f"[ThrowRandomizer] Template K-Point '{self.template_k_name}' not found!")

        # Determine if we should use linked duplicates (shared data/materials)
        use_linked = self.config.same_appearance

        for i in range(self.config.num_darts):
            # 1. Spawn Dart
            new_dart_root = self._duplicate_hierarchy(template_dart, linked=use_linked)
            if new_dart_root:
                # Create Dart wrapper
                dart_instance = Dart(new_dart_root)
                self.spawned_darts.append(dart_instance)
                
                # Setup geometry references (Parent_Object links)
                if self.dart_randomizer:
                    self.dart_randomizer.setup_geometry_references(dart_instance)
            
            # 2. Spawn K-Point
            if template_k:
                new_k = template_k.copy()
                # Ensure visibility is enabled (template might be hidden)
                new_k.hide_viewport = False
                new_k.hide_render = False
                
                # Link to collection
                if self.collection:
                    self.collection.objects.link(new_k)
                self.spawned_k_points.append(new_k)
                
                # Associate K-Point with Dart instance
                if new_dart_root and self.spawned_darts:
                    self.spawned_darts[-1].k_point = new_k
        
        # Ensure template collection is hidden if possible
        if template_dart.users_collection:
            for coll in template_dart.users_collection:
                coll.hide_viewport = True
                coll.hide_render = True
        
        # Hide template K
        if template_k:
            template_k.hide_viewport = True
            template_k.hide_render = True

    def randomize(self, *args, **kwargs) -> None:
        """
        Randomize the existing darts in the pool.
        """
        # Safety check: if pool is empty or size mismatch (e.g. config changed), respawn
        # Check if objects in spawned_darts are valid (not deleted)
        self.spawned_darts = [d for d in self.spawned_darts if d is not None and d.root is not None]
        self.spawned_k_points = [k for k in self.spawned_k_points if k is not None]
        
        # Also check if they are actually in the scene/collection
        # self.spawned_darts = [d for d in self.spawned_darts if not self.collection or d.root.name in self.collection.objects]

        if len(self.spawned_darts) != self.config.num_darts:
             print(f"[ThrowRandomizer] Dart count mismatch ({len(self.spawned_darts)} != {self.config.num_darts}). Respawning pool.")
             self._clear_existing_darts()
             self._spawn_dart_pool()

        base_seed = self.rng.randint(0, 100000)
        
        for i, dart in enumerate(self.spawned_darts):
            if not dart or not dart.root: continue
            
            # Randomize Appearance
            if self.dart_randomizer:
                # Determine seed for this dart
                if self.config.same_appearance:
                    dart_seed = base_seed
                else:
                    dart_seed = self.rng.randint(0, 100000)
                
                self.dart_randomizer.update_seed(dart_seed)
                self.dart_randomizer.randomize(dart=dart)
            
            # Randomize Position/Rotation
            self._randomize_transform(dart.root)
            
            # Handle K-Point and Embedding
            if dart.k_point:
                k_point = dart.k_point
                # 1. Move K-Point to Dart's surface position
                k_point.location = dart.root.location
                k_point.rotation_euler = dart.root.rotation_euler
                
                # 2. Calculate Embedding Depth
                # Get tip length from the dart instance (cached!)
                # Value is in mm (from config/GeoNodes), convert to meters for world space transform
                tip_length_mm = dart.tip_length
                
                # If reading failed (shouldn't happen if randomized), fallback
                if tip_length_mm == 0.0:
                    tip_length_mm = 30.0 # Fallback 30mm
                
                tip_length_m = tip_length_mm / 1000.0
                
                embed_factor = self.rng.uniform(self.config.embed_depth_factor_min, self.config.embed_depth_factor_max)
                embed_depth_m = tip_length_m * embed_factor
                
                # 3. Move Dart INTO the board
                # Assuming Dart points in local Z direction (or whatever direction the arrow points)
                # If arrow points AWAY from board, then +Z is AWAY.
                # To move INTO board, we need to move in -Z direction.
                
                # Calculate translation vector in local space
                local_translation = Vector((0, 0, -embed_depth_m))
                
                # Apply to world location
                # location += rotation @ local_translation
                dart.root.location += dart.root.rotation_euler.to_matrix() @ local_translation

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
