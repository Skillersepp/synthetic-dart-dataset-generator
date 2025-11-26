import bpy

def get_render_aspect_ratio(scene=None):
    """Calculate the render aspect ratio considering resolution and pixel aspect."""
    if scene is None:
        scene = bpy.context.scene
    render = scene.render
    res_x = render.resolution_x * render.pixel_aspect_x
    res_y = render.resolution_y * render.pixel_aspect_y
    if res_y <= 0:
        raise ValueError("Calculated res_y must be > 0")
    return res_x / res_y

def get_camera_aspect_ratio(camera):
    """Calculate the camera's aspect ratio based on sensor dimensions."""
    if camera.data.sensor_height <= 0:
        raise ValueError("sensor_height must be > 0")
    return camera.data.sensor_width / camera.data.sensor_height