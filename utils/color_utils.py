"""
Utility functions for color operations.

Contains helpers for:
- HSV color variation
- Color randomization
"""

import colorsys
from typing import Tuple
from random import Random


def randomize_color_hsv(
    base_color: Tuple[float, float, float, float],
    rng: Random,
    hue_variation: float = 0.0,
    saturation_variation: float = 0.0,
    value_variation: float = 0.0
) -> Tuple[float, float, float, float]:
    """
    Generate a randomized color through HSV variation.
    
    Args:
        base_color: RGBA base color (values 0-1)
        rng: Random generator for deterministic results
        hue_variation: ±variation of hue value (0.02 = ±2%)
        saturation_variation: ±variation of saturation
        value_variation: ±variation of brightness
        
    Returns:
        RGBA tuple with the randomized color
        
    Example:
        >>> rng = Random(42)
        >>> base = (0.8, 0.1, 0.1, 1.0)  # Red
        >>> randomize_color_hsv(base, rng, hue_variation=0.02, value_variation=0.1)
        (0.82, 0.09, 0.11, 1.0)  # Slightly varied red
    """
    r, g, b, a = base_color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    
    # Hue variation (modulo 1.0 for wrap-around)
    if hue_variation > 0:
        h = (h + rng.uniform(-hue_variation, hue_variation)) % 1.0
    
    # Saturation variation (clamped to 0-1)
    if saturation_variation > 0:
        s = clamp(s + rng.uniform(-saturation_variation, saturation_variation), 0.0, 1.0)
    
    # Value variation (clamped to 0-1)
    if value_variation > 0:
        v = clamp(v + rng.uniform(-value_variation, value_variation), 0.0, 1.0)
    
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b, a)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamps a value to the range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def lerp_color(
    color_a: Tuple[float, float, float, float],
    color_b: Tuple[float, float, float, float],
    factor: float
) -> Tuple[float, float, float, float]:
    """
    Linear interpolation between two colors.
    
    Args:
        color_a: Start color (RGBA)
        color_b: End color (RGBA)
        factor: Interpolation factor (0 = color_a, 1 = color_b)
        
    Returns:
        Interpolated color
    """
    factor = clamp(factor, 0.0, 1.0)
    return tuple(
        a + (b - a) * factor
        for a, b in zip(color_a, color_b)
    )


def rgb_to_hsv(color: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert RGB to HSV."""
    return colorsys.rgb_to_hsv(*color)


def hsv_to_rgb(color: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Convert HSV to RGB."""
    return colorsys.hsv_to_rgb(*color)


def adjust_brightness(
    color: Tuple[float, float, float, float], 
    factor: float
) -> Tuple[float, float, float, float]:
    """
    Adjust the brightness of a color.
    
    Args:
        color: RGBA color
        factor: Brightness factor (>1 = brighter, <1 = darker)
        
    Returns:
        Adjusted color
    """
    r, g, b, a = color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v = clamp(v * factor, 0.0, 1.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b, a)


def adjust_saturation(
    color: Tuple[float, float, float, float], 
    factor: float
) -> Tuple[float, float, float, float]:
    """
    Adjust the saturation of a color.
    
    Args:
        color: RGBA color
        factor: Saturation factor (>1 = more saturated, <1 = less saturated)
        
    Returns:
        Adjusted color
    """
    r, g, b, a = color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = clamp(s * factor, 0.0, 1.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b, a)
