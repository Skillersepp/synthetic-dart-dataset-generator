from pathlib import Path
from typing import Dict
import bpy
import math

from randomizers.base_randomizer import BaseRandomizer
from .scene_config import SceneRandomConfig
from utils.asset_utils import set_base_path, load_hdris


class SceneRandomizer(BaseRandomizer):
    """
    Handles all scene randomization steps using a dedicated RNG initialized
    with a deterministic seed. All randomness goes exclusively through this RNG.
    
    HDRIs are loaded once during initialization and then only switched between
    for efficiency.
    """

    def __init__(self, seed: int, config: SceneRandomConfig, base_path: Path = None):
        # Set base path for asset loading (shared across all randomizers)
        if base_path:
            set_base_path(base_path)
        self.hdri_images: Dict[str, bpy.types.Image] = {}
        super().__init__(seed, config)

    # ---------------------------------------------------------------------
    # INITIALIZATION
    # ---------------------------------------------------------------------

    def _initialize(self) -> None:
        """Load all HDRIs once during initialization."""
        self._load_all_hdris()
        if bpy.context.scene:
            self._ensure_hdri_node_setup(bpy.context.scene)

    def _load_all_hdris(self) -> None:
        """
        Load all HDRI files from the configured folder into Blender's data structure.
        This is done once at initialization for efficiency.
        Uses asset_utils for consistent asset loading.
        """
        # Use asset_utils to load HDRIs
        self.hdri_images = load_hdris(
            self.config.hdri_folder,
            force_reload=True
        )

    def _ensure_hdri_node_setup(self, scene):
        """
        Ensure that the world node setup for HDRI environment mapping exists.
        """
        world = scene.world
        if world is None:
            world = bpy.data.worlds.new("World")
            scene.world = world

        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Check if setup already exists
        if "ENV_TEX" in nodes:
            return  # Setup exists → do nothing

        # Clear setup
        nodes.clear()

        # Create and name nodes
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.name = "TEX_CO"
        tex_coord.location = (-800, 300)

        mapping = nodes.new("ShaderNodeMapping")
        mapping.name = "MAPPING"
        mapping.location = (-600, 300)
        mapping.inputs["Rotation"].default_value[0] = math.radians(90)

        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.name = "ENV_TEX"
        env_tex.location = (-300, 300)

        background = nodes.new("ShaderNodeBackground")
        background.name = "BG"
        background.location = (0, 300)

        output = nodes.new("ShaderNodeOutputWorld")
        output.name = "OUT"
        output.location = (300, 300)

        # Link nodes
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
        links.new(env_tex.outputs["Color"], background.inputs["Color"])
        links.new(background.outputs["Background"], output.inputs["Surface"])

        print("World HDRI nodes initialized")


    # ---------------------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------------------

    def randomize(self, scene: bpy.types.Scene) -> None:
        """
        Apply all scene randomization steps.
        Currently randomizes:
        - HDRI environment texture
        - HDRI strength
        - HDRI rotation
        """
        self._randomize_hdri(scene)

    # ---------------------------------------------------------------------
    # INTERNAL METHODS
    # ---------------------------------------------------------------------

    def _randomize_hdri(self, scene):
        """
        Randomly select and apply an HDRI environment texture with random rotation and strength.
        """
        if not self.hdri_images:
            # print("No HDRIs available for randomization")
            return

        # self._ensure_hdri_node_setup(scene) # Removed to avoid node tree modification during render
        world = scene.world
        if not world or not world.node_tree:
            return

        nodes = world.node_tree.nodes
        
        if "ENV_TEX" not in nodes or "MAPPING" not in nodes or "BG" not in nodes:
            # print("HDRI nodes missing, skipping randomization")
            return

        env_tex = nodes["ENV_TEX"]
        mapping = nodes["MAPPING"]
        background = nodes["BG"]

        # HDRI auswählen
        hdri_key = self.rng.choice(list(self.hdri_images.keys()))
        new_image = self.hdri_images[hdri_key]
        
        # Verify image is valid
        try:
             _ = new_image.name
        except ReferenceError:
             # Image is dead, try to recover it from bpy.data.images or skip
             if hdri_key in bpy.data.images:
                 new_image = bpy.data.images[hdri_key]
                 self.hdri_images[hdri_key] = new_image # Update cache
             else:
                 print(f"HDRI {hdri_key} missing or invalid. Skipping.")
                 return

        # Optimization: Only assign if different to avoid unnecessary updates/crashes
        if env_tex.image != new_image:
            env_tex.image = new_image

        # Rotation
        rotation_z = self.rng.uniform(
            self.config.hdri_rotation_min,
            self.config.hdri_rotation_max
        )
        mapping.inputs["Rotation"].default_value[2] = rotation_z

        # Strength
        strength = self.rng.uniform(
            self.config.hdri_strength_min,
            self.config.hdri_strength_max
        )
        background.inputs["Strength"].default_value = strength

        # print(f"Applied HDRI: {image_name}, rot={rotation_z:.2f}, str={strength:.2f}")

