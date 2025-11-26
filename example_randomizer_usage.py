"""
Example demonstrating the improved randomizer architecture with inheritance.

Shows how randomizers are initialized once and reused across frames.
"""

import bpy
from pathlib import Path
from randomization_manager import RandomizationManager


def main():
    # Get camera and scene
    camera = bpy.data.objects.get("Camera")
    scene = bpy.context.scene
    
    if not camera:
        print("No camera found!")
        return
    
    # Initialize manager ONCE
    # Heavy initialization (loading HDRIs, etc.) happens here
    base_path = Path(__file__).parent
    manager = RandomizationManager(global_seed=42, base_path=base_path)
    
    print("=" * 60)
    print("Randomizers initialized! HDRIs loaded.")
    print("=" * 60)
    
    # Simulate multiple frames
    for frame_idx in range(5):
        print(f"\n--- Frame {frame_idx} ---")
        
        # Only seeds are updated, no reloading of assets!
        manager.randomize(frame_idx, camera, scene)
        
        print(f"Frame {frame_idx} randomized successfully")
    
    print("\n" + "=" * 60)
    print("Done! Notice how HDRIs were only loaded once.")
    print("=" * 60)


if __name__ == "__main__":
    main()
