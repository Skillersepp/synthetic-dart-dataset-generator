from pathlib import Path
from typing import Dict
import bpy
import math

from randomizers.base_randomizer import BaseRandomizer
from .scene_config import SceneRandomConfig


class SceneRandomizer(BaseRandomizer):
    """
    Handles all scene randomization steps using a dedicated RNG initialized
    with a deterministic seed. All randomness goes exclusively through this RNG.
    
    HDRIs are loaded once during initialization and then only switched between
    for efficiency.
    """

    def __init__(self, seed: int, config: SceneRandomConfig, base_path: Path = None):
        self.base_path = base_path or Path.cwd()
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
        """
        hdri_path = self.base_path / self.config.hdri_folder
        
        if not hdri_path.exists():
            print(f"Warning: HDRI folder not found at {hdri_path}")
            return
        
        # Find all HDR/EXR files
        hdri_files = list(hdri_path.glob("*.exr")) + list(hdri_path.glob("*.hdr"))
        
        if not hdri_files:
            print(f"Warning: No HDRI files found in {hdri_path}")
            return
        
        print(f"Loading {len(hdri_files)} HDRIs from {hdri_path}...")
        
        # First, clear existing HDRIs to ensure fresh reload
        for hdri_file in hdri_files:
            if hdri_file.name in bpy.data.images:
                bpy.data.images.remove(bpy.data.images[hdri_file.name])

        for hdri_file in hdri_files:
            try:
                # Load new image
                img = bpy.data.images.load(str(hdri_file), check_existing=True)
                print(f"  - Loaded: {hdri_file.name}")
                
                # Ensure image persists in memory
                img.use_fake_user = True
                self.hdri_images[hdri_file.name] = img
                
            except Exception as e:
                print(f"  - Failed to load {hdri_file.name}: {e}")
        
        print(f"Successfully loaded {len(self.hdri_images)} HDRIs")

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

