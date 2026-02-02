import bpy
import math
from typing import Optional, List
from mathutils import Vector, Euler

from randomizers.base_randomizer import BaseRandomizer
from .throw_config import ThrowRandomConfig, DistributionMode
from randomizers.dart.dart_randomizer import DartRandomizer
from randomizers.dart.dart import Dart
from utils import DartboardLayout

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
        
        # Initialize Dartboard Layout
        self.board_layout = DartboardLayout()

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
        objects_to_delete = [obj for obj in self.collection.objects]
        
        # Track data blocks to check for cleanup (Meshes, Materials)
        meshes_to_check = set()
        materials_to_check = set()
        
        for obj in objects_to_delete:
            if obj.type == 'MESH' and obj.data:
                meshes_to_check.add(obj.data)
            
            if hasattr(obj, "material_slots"):
                for slot in obj.material_slots:
                    if slot.material:
                        materials_to_check.add(slot.material)
        
        # Use low-level remove to ensure deletion without selection context issues
        for obj in objects_to_delete:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as e:
                print(f"[ThrowRandomizer] Error removing object {obj.name}: {e}")
            
        self.spawned_darts.clear()
        self.spawned_k_points.clear()
        
        # Cleanup orphaned meshes
        for mesh in meshes_to_check:
            if mesh.users == 0:
                try:
                    bpy.data.meshes.remove(mesh)
                except Exception as e:
                     print(f"[ThrowRandomizer] Error removing orphan mesh: {e}")

        # Cleanup orphaned materials
        for mat in materials_to_check:
            if mat.users == 0:
                try:
                    bpy.data.materials.remove(mat)
                except Exception as e:
                     print(f"[ThrowRandomizer] Error removing orphan material: {e}")

    def _spawn_dart_pool(self) -> None:
        """Spawn the configured number of darts into the pool."""
        template_dart = bpy.data.objects.get(self.template_dart_name)
        if not template_dart:
            print(f"[ThrowRandomizer] Template dart '{self.template_dart_name}' not found!")
            return
        
        # Debug: Check constraints
        if template_dart.constraints:
            print(f"[ThrowRandomizer] Template Dart '{template_dart.name}' has constraints: {[c.name for c in template_dart.constraints]}")
            
        template_k = bpy.data.objects.get(self.template_k_name)
        if not template_k:
            print(f"[ThrowRandomizer] Template K-Point '{self.template_k_name}' not found!")

        # Determine if we should use linked duplicates (shared data/materials)
        use_linked = self.config.same_appearance

        for i in range(self.config.num_darts):
            # 1. Spawn Dart
            new_dart_root = self._duplicate_hierarchy(template_dart, linked=use_linked)
            if new_dart_root:
                # Clear constraints on the root to allow free movement (e.g. if template was constrained to center)
                new_dart_root.constraints.clear()

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

        base_seed = self.rng.randint(0, 1000000)
        
        # Prepare Gaussian parameters if needed
        gaussian_params = None
        if self.config.distribution_mode == DistributionMode.GAUSSIAN:
            # 1. Pick Target Point (Uniform on disk)
            t_angle = self.rng.random() * 2 * math.pi
            # Use square root for uniform area sampling
            t_radius = math.sqrt(self.rng.random()) * self.config.max_radius
            t_x = t_radius * math.cos(t_angle)
            t_y = t_radius * math.sin(t_angle)
            
            # 2. Pick Sigma
            sigma = self.rng.uniform(self.config.gaussian_sigma_min, self.config.gaussian_sigma_max)
            
            gaussian_params = (t_x, t_y, sigma)

        # set all darts invisible so we can enable them one by one
        for dart in self.spawned_darts:
            dart.set_visibility(False)
        
        # Keep track of active dart positions for collision checks
        active_dart_locations = []

        for i, dart in enumerate(self.spawned_darts):
            if not dart or not dart.root: continue
            
            # set dart visible
            dart.set_visibility(True)
            
            # Randomize Appearance
            self._randomize_appearance(dart, base_seed + i)
            
            # Randomize Position/Rotation
            # We pass active_dart_locations to check for collisions
            is_valid_pos = self._randomize_position(dart, gaussian_params, active_dart_locations)
            
            # If unable to find valid split (too crowded), handle as bouncer
            if not is_valid_pos:
                dart.set_visibility(False)
                continue
            
            # Handle Visibility (outside board, bouncers)
            if not self._handle_visibility(dart):
                # If it became invisible, we don't add it to active locations
                continue
            
            # Use current location as confirmed active location
            current_pos = dart.root.location.copy()
            active_dart_locations.append(current_pos)

            # Randomize Empedding Depth
            self._randomize_embedding_depth(dart)

            self._randomize_rotation(dart)


            # Handle K-Point and Embedding
            if dart.k_point:
                k_point = dart.k_point
                # Set K-Point to Dart location/rotation
                k_point.location = dart.root.location.copy()
                k_point.rotation_euler = dart.root.rotation_euler.copy()
                
                # Move Dart INTO the board
                # Calculate translation vector in local space
                embed_depth = dart.embed_tip_length / 1000  # convert mm to m
                local_translation = Vector((0, 0, -embed_depth)) # Local Z is usually 'up' for darts, check model
                
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

    def _randomize_position(self, dart, gaussian_params=None, active_locations=None) -> bool:
        """
        Apply random position to a dart.
        Tries to find a valid position that is not colliding with active_locations.
        Returns check result (True if valid position found, False if gave up/bouncer).
        """
        obj = dart.root
        
        MAX_ATTEMPTS = 50
        MIN_TIP_DISTANCE = 0.0022 # 2mm separation
        tip_r = MIN_TIP_DISTANCE # collision threshold
        
        valid_pos_found = False
        final_x, final_y, final_z = 0, 0, 0
        final_radius, final_angle = 0, 0
        
        for attempt in range(MAX_ATTEMPTS):
            # 1. Choose Random Position
            if gaussian_params:
                target_x, target_y, sigma = gaussian_params
                x = self.rng.gauss(target_x, sigma)
                y = self.rng.gauss(target_y, sigma)
                # Convert to polar for validation
                radius = math.sqrt(x*x + y*y)
                angle = math.atan2(y, x)
                if angle < 0: angle += 2 * math.pi
            else:
                angle = self.rng.random() * 2 * math.pi
                radius = math.sqrt(self.rng.random()) * self.config.max_radius
                
            # 2. Validate Wire (Snap to safe zone)
            radius = self.board_layout.validate_radius(radius)
            angle = self.board_layout.validate_angle(radius, angle)
            
            # Convert back to Cartesian
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            z = 0
            
            # 3. Check proximity to active darts
            is_too_close = False
            if active_locations:
                current_vec = Vector((x, y, z))
                for existing_pos in active_locations:
                    dist = (current_vec - existing_pos).length
                    if dist < tip_r: # e.g. 2*tip_radius logic
                        is_too_close = True
                        break
            
            if not is_too_close:
                final_x, final_y, final_z = x, y, z
                final_radius, final_angle = radius, angle
                valid_pos_found = True
                # DEBUG
                #if attempt > 0:
                #    print(f"valid pos found after {attempt} attempts")
                break
        
        # If loop finished without success, it's a bouncer (invalid pos)
        if not valid_pos_found:
            # DEBUG
            #print("bouncer")
            return False

        # Apply valid position
        # Store polar coordinates and score in the Dart object for annotation
        dart.polar_radius = final_radius
        dart.polar_angle = final_angle
        dart.score = self.board_layout.get_score_from_polar(final_radius, final_angle)
        
        # Debug
        # print(f"[ThrowRandomizer] {obj.name}: Radius={radius:.4f}, Angle={angle:.4f} -> ({x:.4f}, {y:.4f}, {z:.4f})")
        
        obj.location = Vector((final_x, final_y, final_z))
        
        # Debug: Check if location assignment worked (constraints might override it)
        if (obj.location - Vector((final_x, final_y, final_z))).length > 0.001:
             print(f"[ThrowRandomizer] Warning: Location assignment failed for {obj.name}! Wanted {Vector((final_x, final_y, final_z))}, got {obj.location}. Check for constraints.")

        return True

    def _randomize_rotation(self, dart) -> None:
        """Apply random rotation to a dart."""
        obj = dart.root

        # Rotation
        rx = math.radians(self.config.rot_x_min + self.rng.random() * (self.config.rot_x_max - self.config.rot_x_min))
        ry = math.radians(self.config.rot_y_min + self.rng.random() * (self.config.rot_y_max - self.config.rot_y_min))
        rz = math.radians(self.config.rot_z_min + self.rng.random() * (self.config.rot_z_max - self.config.rot_z_min))
        
        obj.rotation_euler = Euler((rx, ry, rz), 'XYZ')

    def _handle_visibility(self, dart) -> bool:
        """Handle visibility based on config (outside board, bouncers)."""
        
        # Calculate radius from current location (assuming board center is 0,0,0)
        current_radius = dart.root.location.xy.length
        
        # Rule 1: Outside board
        if current_radius > 0.225 and not self.config.allow_darts_outside_board:
            dart.set_visibility(False)
            # print(f"[ThrowRandomizer] Hiding {dart.root.name}: Radius {current_radius:.4f} > 0.225m")
            return False
            
        # Rule 2: Bouncer (only if not already hidden)
        if self.rng.random() < self.config.bouncer_probability:
            dart.set_visibility(False)
            # print(f"[ThrowRandomizer] Hiding {dart.root.name}: Bouncer (Prob: {self.config.bouncer_probability})")
            return False
        
        # Otherwise keep visible
        dart.set_visibility(True)
        return True

    def _randomize_appearance(self, dart: Dart, seed: int) -> None:
        """Delegate appearance randomization to DartRandomizer."""
        if self.dart_randomizer:
            # Determine seed for this dart
            if self.config.same_appearance:
                dart_seed = seed
            else:
                dart_seed = self.rng.randint(0, 1000000)
            
            self.dart_randomizer.update_seed(dart_seed)
            self.dart_randomizer.randomize(dart=dart) 

    def _randomize_embedding_depth(self, dart: Dart) -> None:
        """Randomize embedding depth of the dart into the board."""
        tip_length = dart.tip_length if dart.tip_length > 0 else 0.03 # Fallback to 3cm if unknown
        
        factor = self.rng.uniform(self.config.embed_depth_factor_min, self.config.embed_depth_factor_max)
        embed_depth_m = tip_length * factor
        
        # Store for later use in K-Point adjustment
        dart.embed_tip_length = embed_depth_m