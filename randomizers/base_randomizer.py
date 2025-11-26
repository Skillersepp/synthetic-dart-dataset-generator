import random
from abc import ABC, abstractmethod


class BaseRandomizer(ABC):
    """
    Abstract base class for all randomizers.
    
    Provides:
    - Deterministic RNG with seed management
    - Common interface (update_seed, randomize)
    - Separation of initialization (constructor) and per-frame randomization
    """

    def __init__(self, seed: int, config):
        """
        Initialize the randomizer with a seed and configuration.
        
        Heavy initialization (e.g., loading assets) should happen here.
        This is called only ONCE at the start.
        
        Args:
            seed: Initial random seed
            config: Configuration object specific to this randomizer
        """
        self.config = config
        self.rng = random.Random(seed)
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """
        Perform heavy initialization tasks (e.g., loading assets).
        Called once during __init__.
        
        Override this in subclasses for asset loading, setup, etc.
        """
        pass

    def update_seed(self, new_seed: int) -> None:
        """
        Update the RNG seed for the next randomization iteration.
        
        This is called before each frame to ensure deterministic randomization.
        
        Args:
            new_seed: New random seed for this frame
        """
        self.rng.seed(new_seed)

    @abstractmethod
    def randomize(self, *args, **kwargs) -> None:
        """
        Perform the actual randomization.
        
        This is called once per frame after update_seed().
        Should be lightweight and only change parameters, not load assets.
        
        Override this in subclasses to implement specific randomization logic.
        """
        pass
