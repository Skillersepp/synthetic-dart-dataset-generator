import bpy
import bpy_extras
import json
import os
from mathutils import Vector
from typing import List, Dict, Any, Tuple
from pathlib import Path
from randomizers.throw.throw_randomizer import ThrowRandomizer

class AnnotationManager:
    def __init__(self, throw_randomizer: ThrowRandomizer, base_path: Path):
        self.throw_randomizer = throw_randomizer
        # Output directory for labels
        self.output_dir = base_path / "output" / "dataset_v1" / "labels"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_normalized_coords(self, scene: bpy.types.Scene, camera: bpy.types.Object, world_coord: Vector) -> Vector:
        """
        Projects a 3D world coordinate to 2D normalized camera coordinates (0.0 to 1.0).
        Origin is Top-Left.
        Returns (x, y, z) where z is depth.
        """
        co_2d = bpy_extras.object_utils.world_to_camera_view(scene, camera, world_coord)
        
        # Blender: (0,0) is Bottom-Left
        # Image: (0,0) is Top-Left
        # x is same, y needs flip
        
        x = co_2d.x
        y = 1.0 - co_2d.y
        
        return Vector((x, y, co_2d.z))

    def get_bbox_from_object(self, scene: bpy.types.Scene, camera: bpy.types.Object, obj: bpy.types.Object) -> Dict[str, float]:
        """
        Calculates the 2D bounding box (normalized) for an object and its children.
        Returns dictionary with min/max coordinates.
        """
        min_x, max_x = 1.0, 0.0
        min_y, max_y = 1.0, 0.0
        found_points = False

        def process_obj(o):
            nonlocal min_x, max_x, min_y, max_y, found_points
            if o.type == 'MESH' and o.bound_box:
                # Get the 8 corners of the bounding box in world space
                bbox_corners = [o.matrix_world @ Vector(corner) for corner in o.bound_box]
                
                for corner in bbox_corners:
                    coords = self.get_normalized_coords(scene, camera, corner)
                    
                    # Clamp to [0, 1] for bbox calculation
                    cx = max(0.0, min(1.0, coords.x))
                    cy = max(0.0, min(1.0, coords.y))
                    
                    min_x = min(min_x, cx)
                    max_x = max(max_x, cx)
                    min_y = min(min_y, cy)
                    max_y = max(max_y, cy)
                    found_points = True
            
            for child in o.children:
                process_obj(child)

        process_obj(obj)

        if not found_points:
            return None

        return {
            "min_x": min_x,
            "min_y": min_y,
            "max_x": max_x,
            "max_y": max_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
            "center_x": min_x + (max_x - min_x) / 2,
            "center_y": min_y + (max_y - min_y) / 2
        }

    def annotate(self, scene: bpy.types.Scene, camera: bpy.types.Object):
        """
        Generates a JSON annotation file for the current frame.
        """
        frame_idx = scene.frame_current
        filename = f"{frame_idx:04d}.json"
        filepath = self.output_dir / filename
        
        data = {
            "frame": frame_idx,
            "dartboard": {},
            "darts": []
        }
        
        # --- 1. Dartboard Bounding Box ---
        # Target object: "Score_Face"
        score_face = bpy.data.objects.get("Score_Face")
        if score_face:
            bbox = self.get_bbox_from_object(scene, camera, score_face)
            data["dartboard"]["bbox"] = bbox
        else:
            data["dartboard"]["bbox"] = None
            print("[Annotation] Warning: Object 'Score_Face' not found.")

        # --- 2. Dartboard Keypoints ---
        # Collection: "Keypoints" (inside Dartboard collection usually, but name is unique)
        data["dartboard"]["keypoints"] = []
        kp_collection = bpy.data.collections.get("Keypoints")
        
        if kp_collection:
            # Sort objects by name to ensure consistent order if needed, or just list them
            sorted_kps = sorted(kp_collection.objects, key=lambda o: o.name)
            for obj in sorted_kps:
                coords = self.get_normalized_coords(scene, camera, obj.matrix_world.translation)
                data["dartboard"]["keypoints"].append({
                    "name": obj.name,
                    "x": coords.x,
                    "y": coords.y,
                    "z_depth": coords.z,
                    "is_visible": coords.z > 0
                })
        else:
            print("[Annotation] Warning: Collection 'Keypoints' not found.")

        # --- 3. Dart Keypoints ---
        for i, dart in enumerate(self.throw_randomizer.spawned_darts):
            if dart.k_point:
                # Only include if hide_render is False
                if not dart.k_point.hide_render:
                    coords = self.get_normalized_coords(scene, camera, dart.k_point.matrix_world.translation)
                    data["darts"].append({
                        "dart_index": i,
                        "name": dart.k_point.name,
                        "x": coords.x,
                        "y": coords.y,
                        "z_depth": coords.z,
                        "is_visible": coords.z > 0
                    })

        # Write to JSON file
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[Annotation] Error saving {filepath}: {e}")
