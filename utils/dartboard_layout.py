import math

class DartboardLayout:
    """
    Represents the physical layout of a standard WDF dartboard.
    Provides methods for coordinate validation and field identification.
    """
    
    # Dimensions in mm (WDF Standards)
    R_INNER_BULL = 6.35
    R_OUTER_BULL = 15.9
    R_INNER_TREBLE = 97.4
    R_OUTER_TREBLE = 107.4
    R_INNER_DOUBLE = 160.0
    R_OUTER_DOUBLE = 170.0

    # Wire diameters in mm
    D_INNER_BULL_WIRE = 1.2
    D_OUTER_BULL_WIRE = 1.2
    D_TREBLE_WIRE = 1.0
    D_DOUBLE_WIRE = 1.0
    
    # Default dart tip radius in mm (used for collision checks)
    DEFAULT_R_TIP = 1.1

    def __init__(self, r_tip: float = DEFAULT_R_TIP):
        self.r_tip = r_tip
        self.invalid_intervals = self._calculate_invalid_intervals()

    def _calculate_invalid_intervals(self):
        """
        Pre-calculates the invalid radius intervals where a dart would hit a wire.
        Returns a list of (start, end) tuples in mm.
        """
        # Short aliases for readability
        rib = self.R_INNER_BULL
        rob = self.R_OUTER_BULL
        rit = self.R_INNER_TREBLE
        rot = self.R_OUTER_TREBLE
        rid = self.R_INNER_DOUBLE
        rod = self.R_OUTER_DOUBLE

        dib = self.D_INNER_BULL_WIRE
        dob = self.D_OUTER_BULL_WIRE
        dt = self.D_TREBLE_WIRE
        dd = self.D_DOUBLE_WIRE
        
        rt = self.r_tip

        # Define invalid intervals (open intervals)
        # Each tuple is (start, end)
        return [
            (rib - rt, rib + dib + rt),
            (rob - rt, rob + dob + rt),
            (rit - dt - rt, rit + rt),
            (rot - dt - rt, rot + rt),
            (rid - dd - rt, rid + rt),
            (rod - dd - rt, rod + rt)
        ]

    def validate_radius(self, radius_m: float) -> float:
        """
        Validate and adjust the radius to ensure the dart doesn't hit the wire.
        
        Args:
            radius_m: Radius in meters.
            
        Returns:
            Adjusted radius in meters.
        """
        r_mm = radius_m * 1000.0
        
        for start, end in self.invalid_intervals:
            if start < r_mm < end:
                # Radius is in invalid interval
                dist_to_start = abs(r_mm - start)
                dist_to_end = abs(r_mm - end)
                
                if dist_to_start < dist_to_end:
                    r_mm = start
                else:
                    r_mm = end
                
                # Since intervals are open, setting to boundary is fine
                break 
        
        return r_mm / 1000.0

    def validate_angle(self, radius_m: float, angle_rad: float) -> float:
        """
        Validate and adjust the angle to ensure the dart doesn't hit the radial wires.
        
        Args:
            radius_m: Radius in meters.
            angle_rad: Angle in radians.
            
        Returns:
            Adjusted angle in radians.
        """
        r_mm = radius_m * 1000.0
        
        # Only check if radius is within the specified interval [15.8, 180.0]
        if not (15.8 <= r_mm <= 180.0):
            return angle_rad
            
        # Calculate required angular margin
        # margin = 0.6mm (half wire) + r_tip
        margin_mm = 0.6 + self.r_tip
        
        # Calculate angular half-width of the exclusion zone
        # sin(dtheta) = margin / r
        # For small angles, sin(x) approx x, but we use asin for correctness
        if margin_mm >= r_mm:
            # Should not happen in valid range, but safety check
            return angle_rad
            
        dtheta = math.asin(margin_mm / r_mm)
        
        # Dartboard geometry:
        # 20 segments, each 18 degrees (pi/10 radians)
        # 0 degrees is at the center of the "6" segment (Right)
        # Wires are at +/- 9 degrees (pi/20) from the center of each segment
        
        segment_angle = 2 * math.pi / 20 # 18 degrees
        half_segment = segment_angle / 2 # 9 degrees
        
        # Shift angle so that wires are at 0, segment_angle, 2*segment_angle...
        # Original wires: +/- 9 deg, +/- 27 deg...
        # Add 9 deg (half_segment) -> wires at 0, 18, 36...
        angle_shifted = angle_rad + half_segment
        
        # Modulo segment angle to find position within the "wire-to-wire" interval
        angle_mod = angle_shifted % segment_angle
        
        # Distance to the nearest wire (which is at 0 or segment_angle in this shifted space)
        dist_to_wire = min(angle_mod, segment_angle - angle_mod)
        
        if dist_to_wire < dtheta:
            # Collision with wire
            correction = dtheta - dist_to_wire
            # Determine direction to push
            if angle_mod < half_segment:
                # Closer to the "left" wire (0 in shifted space)
                # Push away (increase angle)
                angle_rad += correction
            else:
                # Closer to the "right" wire (segment_angle in shifted space)
                # Push away (decrease angle)
                angle_rad -= correction
                
        return angle_rad

    def get_field_from_polar(self, radius_m: float, angle_rad: float):
        """
        Determines the dartboard field from polar coordinates.
        (Placeholder for future implementation)
        """
        pass
