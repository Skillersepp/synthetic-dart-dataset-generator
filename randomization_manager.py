import hashlib
import time
import logging
from pathlib import Path
from randomizers.camera import CameraRandomizer, CameraRandomConfig
from randomizers.scene import SceneRandomizer, SceneRandomConfig
from randomizers.dartboard import DartboardRandomizer, DartboardRandomConfig, RangeOrFixed
from randomizers.dart import DartRandomizer, DartRandomConfig
from randomizers.throw import ThrowRandomizer, ThrowRandomConfig


class RandomizationManager:
    """
    Central orchestrator that generates deterministic sub-seeds.
    
    Randomizers are initialized once and reused across frames for efficiency.
    Only seeds are updated per frame.
    """

    def __init__(self, global_seed: int, base_path: Path = None):
        self.global_seed = global_seed
        self.base_path = base_path or Path.cwd()
        
        # Initialize all randomizers ONCE with initial seeds
        # Heavy initialization (e.g., loading HDRIs) happens here
        cam_cfg = CameraRandomConfig()
        self.camera_randomizer = CameraRandomizer(
            seed=self._make_seed("camera", 0),
            config=cam_cfg
        )
        
        scene_cfg = SceneRandomConfig()
        self.scene_randomizer = SceneRandomizer(
            seed=self._make_seed("scene", 0),
            config=scene_cfg,
            base_path=self.base_path
        )
        
        # Dartboard Randomizer with default config
        dartboard_cfg = DartboardRandomConfig(
            randomize_cracks=True,
            randomize_holes=True,
            randomize_wear=True,
            crack_factor=RangeOrFixed(0.0, 1.0),
            hole_factor=RangeOrFixed(0.0, 1.0),
            wear_level=RangeOrFixed(0.0, 1.0),
            wear_contrast=RangeOrFixed(0.5, 1.0),
        )
        self.dartboard_randomizer = DartboardRandomizer(
            seed=self._make_seed("dartboard", 0),
            config=dartboard_cfg
        )
        
        # Dart Randomizer
        dart_cfg = DartRandomConfig()
        self.dart_randomizer = DartRandomizer(
            seed=self._make_seed("dart", 0),
            config=dart_cfg,
            base_path=self.base_path
        )
        
        # Throw Randomizer
        throw_cfg = ThrowRandomConfig()
        self.throw_randomizer = ThrowRandomizer(
            seed=self._make_seed("throw", 0),
            config=throw_cfg,
            dart_randomizer=self.dart_randomizer
        )

    def _make_seed(self, tag: str, index: int) -> int:
        """Deterministic sub-seed generation."""
        data = f"{self.global_seed}_{tag}_{index}".encode('utf-8')
        digest = hashlib.md5(data).hexdigest()
        # Convert hex digest to int and keep it within a reasonable range (32-bit)
        return int(digest, 16) % (2**32)

    def randomize(self, image_index: int, camera, scene):
        """
        Randomize all enabled components for the given frame.
        
        Updates seeds and performs lightweight randomization.
        No heavy loading occurs here.
        """
        logger = logging.getLogger(__name__)
        # Basic config if not already configured (ensures output to console)
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='%(message)s')

        start_time = time.perf_counter()

        # Camera randomization
        t0 = time.perf_counter()
        cam_seed = self._make_seed("camera", image_index)
        self.camera_randomizer.update_seed(cam_seed)
        self.camera_randomizer.randomize(camera, scene)
        t1 = time.perf_counter()
        
        # Scene randomization
        scene_seed = self._make_seed("scene", image_index)
        self.scene_randomizer.update_seed(scene_seed)
        self.scene_randomizer.randomize(scene)
        t2 = time.perf_counter()
        
        # Dartboard randomization
        dartboard_seed = self._make_seed("dartboard", image_index)
        self.dartboard_randomizer.update_seed(dartboard_seed)
        self.dartboard_randomizer.randomize()
        t3 = time.perf_counter()
        
        # Throw randomization (handles dart spawning and randomization)
        throw_seed = self._make_seed("throw", image_index)
        self.throw_randomizer.update_seed(throw_seed)
        self.throw_randomizer.randomize()
        t4 = time.perf_counter()

        logger.info(f"--- Randomization Timing (Frame {image_index}) ---")
        logger.info(f"Camera:    {t1 - t0:.4f}s")
        logger.info(f"Scene:     {t2 - t1:.4f}s")
        logger.info(f"Dartboard: {t3 - t2:.4f}s")
        logger.info(f"Throw:     {t4 - t3:.4f}s")
        logger.info(f"Total:     {t4 - start_time:.4f}s")
        logger.info("-------------------------------------------")
