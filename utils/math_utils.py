import math
from mathutils import Vector


# ---------------------------------------------------------------------------
# SPHERICAL COORDINATES
# ---------------------------------------------------------------------------

def sph_to_cart(r: float, theta: float, phi: float) -> tuple[float, float, float]:
    """
    Convert spherical coordinates to Cartesian coordinates.

    Spherical system definition:
        r     = radius (distance from origin)
        theta = polar angle measured from the positive Z-axis (0 to π)
        phi   = azimuth angle measured in the XY-plane from +X (0 to 2π)

    Returns:
        (x, y, z): Cartesian coordinates.
    """
    sin_theta = math.sin(theta)
    x = r * sin_theta * math.cos(phi)
    y = r * sin_theta * math.sin(phi)
    z = r * math.cos(theta)
    return x, y, z


def cart_to_sph(x: float, y: float, z: float) -> tuple[float, float, float]:
    """
    Convert Cartesian coordinates to spherical coordinates.

    Returns:
        (r, theta, phi):
            r     = sqrt(x² + y² + z²)
            theta = angle from Z-axis
            phi   = angle in XY-plane from +X
    """
    r = math.sqrt(x*x + y*y + z*z)
    theta = math.acos(z / r) if r != 0 else 0.0
    phi = math.atan2(y, x)
    return r, theta, phi


# ---------------------------------------------------------------------------
# CYLINDRICAL COORDINATES
# ---------------------------------------------------------------------------

def cyl_to_cart(r: float, phi: float, z: float) -> tuple[float, float, float]:
    """
    Convert cylindrical coordinates to Cartesian coordinates.

    Cylindrical system:
        r   = radial distance in the XY-plane
        phi = azimuth angle in XY-plane (0 to 2π)
        z   = height along Z-axis

    Returns:
        (x, y, z)
    """
    x = r * math.cos(phi)
    y = r * math.sin(phi)
    return x, y, z


def cart_to_cyl(x: float, y: float, z: float) -> tuple[float, float, float]:
    """
    Convert Cartesian coordinates to cylindrical coordinates.

    Returns:
        (r, phi, z)
          r   = sqrt(x² + y²)
          phi = atan2(y, x)
          z   = z (unchanged)
    """
    r = math.sqrt(x*x + y*y)
    phi = math.atan2(y, x)
    return r, phi, z




