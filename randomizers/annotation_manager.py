import bpy
import bpy_extras
from mathutils import Vector
from typing import List, Dict, Any
from randomizers.throw.throw_randomizer import ThrowRandomizer

class AnnotationManager:
    def __init__(self, throw_randomizer: ThrowRandomizer):
        self.throw_randomizer = throw_randomizer
        self.dartboard_keypoints = [
            "Dartboard_Center",
            "Dartboard_K1",
            "Dartboard_K2",
            "Dartboard_K3",
            "Dartboard_K4"
        ]

    def project_3d_to_2d(self, scene: bpy.types.Scene, camera: bpy.types.Object, world_coord: Vector) -> Vector:
        """
        Projects a 3D world coordinate to 2D camera pixel coordinates.
        Returns (x, y, z) where (x, y) are pixel coordinates and z is depth.
        Origin is top-left.
        """
        co_2d = bpy_extras.object_utils.world_to_camera_view(scene, camera, world_coord)
        render = scene.render
        
        # Convert normalized coordinates to pixel coordinates
        # Blender (0,0) is bottom-left.
        # We convert to top-left origin for standard image coordinates.
        
        x = co_2d.x * render.resolution_x
        y = (1 - co_2d.y) * render.resolution_y 
        
        return Vector((x, y, co_2d.z))

    def annotate(self, scene: bpy.types.Scene, camera: bpy.types.Object):
        # Note: We assume the dependency graph is already updated (e.g. called in render_pre)
        # If called in frame_change_pre, coordinates might be stale unless view_layer.update() is called.
        
        print("-" * 30)
        print(f"Frame: {scene.frame_current}")
        
        # 1. Dartboard Keypoints
        print("Dartboard Keypoints:")
        for kp_name in self.dartboard_keypoints:
            obj = bpy.data.objects.get(kp_name)
            if obj:
                # Get world location (considering parent transforms)
                world_loc = obj.matrix_world.translation
                coords = self.project_3d_to_2d(scene, camera, world_loc)
                
                # Check if point is behind camera
                visibility = "Visible" if coords.z > 0 else "Behind Camera"
                
                print(f"  {kp_name}: Pixel=({coords.x:.1f}, {coords.y:.1f}) [{visibility}]")
            else:
                print(f"  {kp_name}: Not found")

        # 2. Dart Keypoints
        print("Dart Keypoints:")
        for i, dart in enumerate(self.throw_randomizer.spawned_darts):
            if dart.k_point:
                world_loc = dart.k_point.matrix_world.translation
                coords = self.project_3d_to_2d(scene, camera, world_loc)
                
                visibility = "Visible" if coords.z > 0 else "Behind Camera"
                
                print(f"  Dart {i}: Pixel=({coords.x:.1f}, {coords.y:.1f}) [{visibility}]")
            else:
                print(f"  Dart {i}: No Keypoint Object")
        print("-" * 30)
