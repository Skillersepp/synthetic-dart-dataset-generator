import math
from mathutils import Vector, Euler, Matrix
import bpy
from bpy_extras.object_utils import world_to_camera_view

from randomizers.base_randomizer import BaseRandomizer
from .camera_config import CameraRandomConfig, CameraRollMode
from utils.math_utils import sph_to_cart, cyl_to_cart
from utils.camera_utils import get_render_aspect_ratio, get_camera_aspect_ratio


class CameraRandomizer(BaseRandomizer):
    """
    Handles all camera randomization steps using a dedicated RNG initialized
    with a deterministic seed. All randomness goes exclusively through this RNG.
    """

    def _initialize(self) -> None:
        """No heavy initialization needed for camera randomizer."""
        pass

    # ---------------------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------------------

    def randomize(self, camera: bpy.types.Object, scene: bpy.types.Scene) -> None:
        """Apply all camera randomization steps.

        Ensures the camera starts from a clean, known baseline so no values
        from previous runs bleed into the current randomization.
        """
        self._randomize_optics(camera, scene)
        target = self._compute_target_location()
        min_distance = self._compute_min_distance(camera, target)
        self._randomize_pose(camera, min_distance, target)
        self._randomize_dof(camera)

    # ---------------------------------------------------------------------
    # INTERNAL METHODS
    # ---------------------------------------------------------------------

    def _randomize_optics(self, camera, scene):
        """Randomize focal length and sensor width."""
        c = self.config
        
        camera.data.lens = self.rng.uniform(c.focal_length_min, c.focal_length_max)
        camera.data.sensor_width = self.rng.uniform(c.sensor_width_min, c.sensor_width_max)
        camera.data.sensor_height = camera.data.sensor_width / get_render_aspect_ratio(scene)

    def _compute_target_location(self):
        """Compute a jittered target location around the origin."""
        c = self.config
        return Vector((self.rng.gauss(0, c.look_jitter_stddev), self.rng.gauss(0, c.look_jitter_stddev), 0.0))

    def _compute_min_distance(self, camera, target=Vector((0,0,0))):
        """Compute minimal camera distance so the board fits into frame."""
        c = self.config
        if camera.data.sensor_width <= 0 or camera.data.sensor_height <= 0:
            raise ValueError("sensor_width and sensor_height must be > 0")
        
        shorter_side = min(camera.data.sensor_width, camera.data.sensor_height)
        return ((c.board_diameter_m + target.length) * camera.data.lens) / shorter_side

    def _randomize_pose(self, camera, min_distance, target=Vector((0,0,0))):
        """Place camera on a spherical shell and aim at the dartboard."""
        c = self.config

        # Distance along sphere
        r = min_distance * self.rng.uniform(c.distance_factor_min, c.distance_factor_max)

        # Spherical coordinates
        theta = math.radians(self.rng.uniform(c.polar_angle_min, c.polar_angle_max))
        phi = math.radians(self.rng.uniform(c.azimuth_min, c.azimuth_max))

        x, y, z = sph_to_cart(r, theta, phi)
        camera.location = Vector((x, y, z))
        
        # Aim at target with calculated Roll
        # We calculate the rotation matrix analytically to avoid dependency on 
        # bpy.context.view_layer.update() which is not thread-safe during render.
        
        view_vector = camera.location - target
        
        # Determine Up Vector based on Roll Mode
        if c.roll_mode.value == CameraRollMode.LEVEL_TO_HORIZON.value:
            # Align Camera Up (Local Y) with World Z (Horizon level)
            up_vector = Vector((0, 0, 1.0))

        elif c.roll_mode.value == CameraRollMode.TWENTY_EXACT_UP.value:
            # Align Camera Up with World Y (where "20" is) exactly
            up_vector = Vector((0, 1.0, 0.0))
            
        elif c.roll_mode.value == CameraRollMode.TWENTY_APPROX_UP.value:
            # Align Camera Up with World Y (where "20" is), plus jitter
            up_vector = Vector((0, 1.0, 0.0))
            jitter_deg = self.rng.gauss(0, c.roll_stddev_deg)
            up_vector.rotate(Euler((0.0, 0.0, math.radians(jitter_deg)), 'XYZ'))
            # print(f"Applied roll jitter: {jitter_deg:.2f}°")
            
        elif c.roll_mode.value == CameraRollMode.RANDOM.value:
            # Align Camera Up with World Y rotated randomly
            up_vector = Vector((0, 1.0, 0.0))
            random_deg = self.rng.uniform(c.roll_min_deg, c.roll_max_deg)
            up_vector.rotate(Euler((0.0, 0.0, math.radians(random_deg)), 'XYZ'))
            # print("Applied random roll.")
        else:
            # Fallback
            up_vector = Vector((0, 0, 1.0))

        # Construct Rotation Matrix
        # Camera looks down -Z, Up is +Y
        z_axis = view_vector.normalized()
        
        # Handle singularity if looking straight along up_vector
        if abs(z_axis.dot(up_vector.normalized())) > 0.99:
            # Fallback to Z as up if we are looking along Y, else Y
            if abs(z_axis.z) < 0.9:
                up_vector = Vector((0, 0, 1))
            else:
                up_vector = Vector((0, 1, 0))
            
        x_axis = up_vector.cross(z_axis).normalized()
        y_axis = z_axis.cross(x_axis)
        
        # Matrix columns: X, Y, Z
        R = Matrix((x_axis, y_axis, z_axis)).transposed()
        camera.rotation_euler = R.to_euler()

    def _randomize_dof(self, camera):
        """Randomize DOF (focus distance + aperture)."""
        c = self.config

        # Choose a random focus point on the plane of the dartboard
        r = self.rng.uniform(0, c.focus_radius_max_m)
        phi = math.radians(self.rng.uniform(0, 360))
        x, y, z = cyl_to_cart(r, phi, 0)

        dist = (camera.location - Vector((x, y, z))).length
        camera.data.dof.focus_distance = dist
        camera.data.dof.aperture_fstop = self.rng.uniform(
            c.aperture_fstop_min, c.aperture_fstop_max
        )

