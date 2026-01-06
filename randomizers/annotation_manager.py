import bpy
import bpy_extras
import json
import os
import numpy as np
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
        Calculates the 2D bounding box (normalized) for an object and its children based on mesh vertices.
        Returns dictionary with min/max coordinates.
        Using direct numpy calculation for performance and accuracy.
        """
        depsgraph = bpy.context.evaluated_depsgraph_get()

        # Camera matrices
        render = scene.render
        w = int(render.resolution_x * render.resolution_percentage / 100.0)
        h = int(render.resolution_y * render.resolution_percentage / 100.0)

        cam_eval = camera.evaluated_get(depsgraph)
        cam_data = cam_eval.data

        # Projection matrix (camera -> clip space)
        scale_x = render.pixel_aspect_x
        scale_y = render.pixel_aspect_y
        proj = cam_eval.calc_matrix_camera(
            depsgraph,
            x=w, y=h,
            scale_x=scale_x, scale_y=scale_y
        )

        # World -> camera
        view = cam_eval.matrix_world.inverted()

        # Collect all mesh objects in hierarchy (root + children)
        # (children_recursive gives access to all descendants)
        objs = [obj] + list(obj.children_recursive)

        all_min = np.array([np.inf, np.inf], dtype=np.float64)
        all_max = np.array([-np.inf, -np.inf], dtype=np.float64)
        found = False

        for current_obj in objs:
            if current_obj.type != 'MESH':
                continue
            
            # Hide render checks? 
            # If the object is hidden in render, we should arguably skip it.
            if current_obj.hide_render:
                continue

            obj_eval = current_obj.evaluated_get(depsgraph)

            # Get evaluated mesh (modifiers applied etc.)
            mesh = obj_eval.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
            if not mesh or len(mesh.vertices) == 0:
                if mesh:
                    obj_eval.to_mesh_clear()
                continue

            # Pull vertex coords fast
            co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            mesh.vertices.foreach_get("co", co)
            co = co.reshape((-1, 3))

            # Homogeneous coords
            ones = np.ones((co.shape[0], 1), dtype=np.float64)
            co_h = np.concatenate([co, ones], axis=1)

            # Local -> world
            mw = np.array(obj_eval.matrix_world, dtype=np.float64)
            world = (mw @ co_h.T).T

            # World -> camera
            view_m = np.array(view, dtype=np.float64)
            cam_space = (view_m @ world.T).T

            # Camera -> clip
            proj_m = np.array(proj, dtype=np.float64)
            clip = (proj_m @ cam_space.T).T

            # Perspective divide -> NDC
            w_comp = clip[:, 3]
            # Check for vertices in front of camera
            in_front = w_comp > 1e-8
            if not np.any(in_front):
                obj_eval.to_mesh_clear()
                continue

            ndc = clip[in_front, :3] / w_comp[in_front, None]

            # NDC (-1..1) -> normalized screen (0..1)
            # Standard NDC: x right, y up.
            x = (ndc[:, 0] + 1.0) * 0.5
            y = (ndc[:, 1] + 1.0) * 0.5
            
            # Flip y so (0, 0) is top-left in the image.
            y = 1.0 - y

            # Clamp to [0, 1]
            x = np.clip(x, 0.0, 1.0)
            y = np.clip(y, 0.0, 1.0)

            mn = np.array([x.min(), y.min()])
            mx = np.array([x.max(), y.max()])

            all_min = np.minimum(all_min, mn)
            all_max = np.maximum(all_max, mx)
            found = True

            obj_eval.to_mesh_clear()

        if not found:
            return None

        min_x, min_y = float(all_min[0]), float(all_min[1])
        max_x, max_y = float(all_max[0]), float(all_max[1])

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
        # Ensure scene is updated
        bpy.context.view_layer.update()

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
