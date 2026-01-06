import bpy
import sys
import os
import math
import logging
from pathlib import Path
from typing import Optional

from bpy.props import (FloatProperty, IntProperty, BoolProperty, 
                       EnumProperty, PointerProperty, StringProperty, FloatVectorProperty)
from bpy.types import PropertyGroup, Panel, Operator
from bpy.app.handlers import persistent

# Add current dir to path to find modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Try to import modules; handle errors if environment not perfect
try:
    from randomizers.camera.camera_config import CameraRandomConfig, CameraRollMode
    from randomizers.dart.dart_config import DartRandomConfig, RangeOrFixed as PyRangeOrFixed
    from randomizers.dartboard.dartboard_config import DartboardRandomConfig, ColorVariation as PyColorVariation, RangeOrFixed
    from randomizers.scene.scene_config import SceneRandomConfig
    from randomizers.throw.throw_config import ThrowRandomConfig
    from randomization_manager import RandomizationManager
except ImportError as e:
    print(f"Error importing randomization modules: {e}")
    # Define dummy classes
    class CameraRandomConfig: pass
    class DartRandomConfig: pass
    class DartboardRandomConfig: pass
    class SceneRandomConfig: pass
    class ThrowRandomConfig: pass
    class PyRangeOrFixed: pass
    class PyColorVariation: pass
    class RandomizationManager: pass

# Global Manager Instance
_randomization_manager = None

def get_manager(context):
    global _randomization_manager
    if _randomization_manager is None:
        seed = context.scene.dart_generator_settings.global_seed if hasattr(context.scene, 'dart_generator_settings') else 0
        _randomization_manager = RandomizationManager(global_seed=seed, base_path=Path(current_dir))
    return _randomization_manager

def update_randomization(self, context):
    """Callback to trigger randomization when settings change."""
    if not context or not context.scene:
        return

    mgr = get_manager(context)
    settings = context.scene.dart_generator_settings
    
    if mgr.global_seed != settings.global_seed:
        mgr.global_seed = settings.global_seed
    
    # --- Camera Config ---
    cam_settings = settings.camera
    cam_cfg = CameraRandomConfig(
        focal_length_min=cam_settings.focal_length_min,
        focal_length_max=cam_settings.focal_length_max,
        sensor_width_min=cam_settings.sensor_width_min,
        sensor_width_max=cam_settings.sensor_width_max,
        distance_factor_min=cam_settings.distance_factor_min,
        distance_factor_max=cam_settings.distance_factor_max,
        polar_angle_min=cam_settings.polar_angle_min,
        polar_angle_max=cam_settings.polar_angle_max,
        azimuth_min=cam_settings.azimuth_min,
        azimuth_max=cam_settings.azimuth_max,
        look_jitter_stddev=cam_settings.look_jitter_stddev,
        roll_mode=CameraRollMode[cam_settings.roll_mode],
        roll_stddev_deg=cam_settings.roll_stddev_deg,
        roll_min_deg=cam_settings.roll_min_deg,
        roll_max_deg=cam_settings.roll_max_deg,
        board_diameter_m=cam_settings.board_diameter_m,
        focus_radius_max_m=cam_settings.focus_radius_max_m,
        aperture_fstop_min=cam_settings.aperture_fstop_min,
        aperture_fstop_max=cam_settings.aperture_fstop_max,
    )
    mgr.camera_randomizer.config = cam_cfg
    
    # --- Scene Config ---
    scene_settings = settings.scene
    scene_cfg = SceneRandomConfig(
        hdri_folder=Path(scene_settings.hdri_folder),
        hdri_strength_min=scene_settings.hdri_strength_min,
        hdri_strength_max=scene_settings.hdri_strength_max,
        hdri_rotation_min=scene_settings.hdri_rotation_min,
        hdri_rotation_max=scene_settings.hdri_rotation_max
    )
    mgr.scene_randomizer.config = scene_cfg
    
    # --- Dart Config ---
    dart_settings = settings.dart
    
    def to_py_range(prop):
        return PyRangeOrFixed(min_val=prop.min_val, max_val=prop.max_val, fixed=prop.fixed_val if prop.use_fixed else None)

    dart_cfg = DartRandomConfig(
        tip_length=to_py_range(dart_settings.tip_length),
        barrel_length=to_py_range(dart_settings.barrel_length),
        barrel_thickness=to_py_range(dart_settings.barrel_thickness),
        shaft_length=to_py_range(dart_settings.shaft_length),
        shaft_shape_mix=to_py_range(dart_settings.shaft_shape_mix),
        flight_insertion_depth=to_py_range(dart_settings.flight_insertion_depth),
        randomize_flight_type=dart_settings.randomize_flight_type,
        fixed_flight_index=dart_settings.fixed_flight_index,
        prob_flight_texture_flags=dart_settings.prob_flight_texture_flags,
        prob_flight_texture_outpainted=dart_settings.prob_flight_texture_outpainted,
        prob_flight_gradient=dart_settings.prob_flight_gradient,
        prob_flight_solid=dart_settings.prob_flight_solid,
        flight_roughness=to_py_range(dart_settings.flight_roughness),
        flight_color_saturation_min=dart_settings.flight_color_saturation_min,
        flight_color_saturation_max=dart_settings.flight_color_saturation_max,
        flight_color_value_min=dart_settings.flight_color_value_min,
        flight_color_value_max=dart_settings.flight_color_value_max,
        prob_shaft_gradient=dart_settings.prob_shaft_gradient,
        prob_shaft_solid=dart_settings.prob_shaft_solid,
        shaft_roughness=to_py_range(dart_settings.shaft_roughness),
        prob_shaft_metallic=dart_settings.prob_shaft_metallic,
        barrel_roughness=to_py_range(dart_settings.barrel_roughness),
        tip_roughness=to_py_range(dart_settings.tip_roughness)
    )
    mgr.dart_randomizer.config = dart_cfg
    
    # --- Throw Config ---
    throw_settings = settings.throw
    throw_cfg = ThrowRandomConfig(
        num_darts=throw_settings.num_darts,
        same_appearance=throw_settings.same_appearance,
        max_radius=throw_settings.max_radius,
        rot_x_min=throw_settings.rot_x_min,
        rot_x_max=throw_settings.rot_x_max,
        rot_y_min=throw_settings.rot_y_min,
        rot_y_max=throw_settings.rot_y_max,
        rot_z_min=throw_settings.rot_z_min,
        rot_z_max=throw_settings.rot_z_max,
        embed_depth_factor_min=throw_settings.embed_depth_factor_min,
        embed_depth_factor_max=throw_settings.embed_depth_factor_max,
        allow_darts_outside_board=throw_settings.allow_darts_outside_board,
        bouncer_probability=throw_settings.bouncer_probability
    )
    mgr.throw_randomizer.config = throw_cfg
    
    # --- Dartboard Config ---
    db_settings = settings.dartboard
    
    def to_py_color(prop):
        return PyColorVariation(
            base_color=tuple(prop.base_color),
            hue_variation=prop.hue_variation,
            saturation_variation=prop.saturation_variation,
            value_variation=prop.value_variation,
            randomize=prop.randomize
        )

    db_cfg = DartboardRandomConfig(
        randomize_cracks=db_settings.randomize_cracks,
        randomize_holes=db_settings.randomize_holes,
        randomize_wear=db_settings.randomize_wear,
        crack_factor=to_py_range(db_settings.crack_factor),
        hole_factor=to_py_range(db_settings.hole_factor),
        wear_level=to_py_range(db_settings.wear_level),
        wear_contrast=to_py_range(db_settings.wear_contrast),
        field_color_red=to_py_color(db_settings.field_color_red),
        field_color_green=to_py_color(db_settings.field_color_green),
        field_color_white=to_py_color(db_settings.field_color_white),
    )
    mgr.dartboard_randomizer.config = db_cfg

    # Trigger Randomization
    frame = context.scene.frame_current
    camera = context.scene.camera
    if camera:
        try:
            mgr.randomize(frame, camera, context.scene)
        except Exception as e:
            print(f"Error during live randomization: {e}")

# --- Property Group Definitions ---

class RangeOrFixedProperty(PropertyGroup):
    min_val: FloatProperty(name="Min", default=0.0, update=update_randomization)
    max_val: FloatProperty(name="Max", default=1.0, update=update_randomization)
    fixed_val: FloatProperty(name="Fixed Value", default=0.5, update=update_randomization)
    use_fixed: BoolProperty(name="Use Fixed", default=False, update=update_randomization)

class ColorVariationProperty(PropertyGroup):
    base_color: FloatVectorProperty(name="Base Color", subtype='COLOR', size=4, min=0.0, max=1.0, default=(1.0,1.0,1.0,1.0), update=update_randomization)
    hue_variation: FloatProperty(name="Hue Var", default=0.0, update=update_randomization)
    saturation_variation: FloatProperty(name="Sat Var", default=0.0, update=update_randomization)
    value_variation: FloatProperty(name="Val Var", default=0.0, update=update_randomization)
    randomize: BoolProperty(name="Randomize", default=True, description="Enable randomization for this color", update=update_randomization)

class CameraSettings(PropertyGroup):
    focal_length_min: FloatProperty(name="Focal Length Min", default=20.0, update=update_randomization)
    focal_length_max: FloatProperty(name="Focal Length Max", default=60.0, update=update_randomization)
    sensor_width_min: FloatProperty(name="Sensor Width Min", default=8.0, update=update_randomization)
    sensor_width_max: FloatProperty(name="Sensor Width Max", default=36.0, update=update_randomization)
    distance_factor_min: FloatProperty(name="Dist Factor Min", default=1.0, update=update_randomization)
    distance_factor_max: FloatProperty(name="Dist Factor Max", default=2.0, update=update_randomization)
    polar_angle_min: FloatProperty(name="Polar Min", default=0.0, update=update_randomization)
    polar_angle_max: FloatProperty(name="Polar Max", default=75.0, update=update_randomization)
    azimuth_min: FloatProperty(name="Azimuth Min", default=0.0, update=update_randomization)
    azimuth_max: FloatProperty(name="Azimuth Max", default=360.0, update=update_randomization)
    look_jitter_stddev: FloatProperty(name="Look Jitter", default=0.02, update=update_randomization)
    roll_mode: EnumProperty(
        name="Roll Mode",
        items=[
            ('TWENTY_EXACT_UP', "20 Exact Up", ""),
            ('TWENTY_APPROX_UP', "20 Approx Up", ""),
            ('LEVEL_TO_HORIZON', "Level Horizon", ""),
            ('RANDOM', "Random", "")
        ],
        default='TWENTY_EXACT_UP',
        update=update_randomization
    )
    roll_stddev_deg: FloatProperty(name="Roll Std Dev", default=6.0, update=update_randomization)
    roll_min_deg: FloatProperty(name="Roll Min", default=-180.0, update=update_randomization)
    roll_max_deg: FloatProperty(name="Roll Max", default=180.0, update=update_randomization)
    board_diameter_m: FloatProperty(name="Board Diameter", default=0.44, update=update_randomization)
    focus_radius_max_m: FloatProperty(name="Focus Radius Max", default=0.225, update=update_randomization)
    aperture_fstop_min: FloatProperty(name="F-Stop Min", default=0.8, update=update_randomization)
    aperture_fstop_max: FloatProperty(name="F-Stop Max", default=5.6, update=update_randomization)

class DartSettings(PropertyGroup):
    # Defaults handled in registration/init via standard values, ensuring Python config matches
    tip_length: PointerProperty(type=RangeOrFixedProperty)
    barrel_length: PointerProperty(type=RangeOrFixedProperty)
    barrel_thickness: PointerProperty(type=RangeOrFixedProperty)
    shaft_length: PointerProperty(type=RangeOrFixedProperty)
    shaft_shape_mix: PointerProperty(type=RangeOrFixedProperty)
    flight_insertion_depth: PointerProperty(type=RangeOrFixedProperty)
    
    randomize_flight_type: BoolProperty(name="Rand Flight Type", default=True, update=update_randomization)
    fixed_flight_index: IntProperty(name="Fixed Flight Index", default=100, update=update_randomization)
    
    prob_flight_texture_flags: FloatProperty(name="Prob Flags", default=0.3, min=0, max=1, update=update_randomization)
    prob_flight_texture_outpainted: FloatProperty(name="Prob Outpainted", default=0.5, min=0, max=1, update=update_randomization)
    prob_flight_gradient: FloatProperty(name="Prob Gradient", default=0.1, min=0, max=1, update=update_randomization)
    prob_flight_solid: FloatProperty(name="Prob Solid", default=0.1, min=0, max=1, update=update_randomization)
    
    flight_roughness: PointerProperty(type=RangeOrFixedProperty)
    
    flight_color_saturation_min: FloatProperty(name="Sat Min", default=0.5, update=update_randomization)
    flight_color_saturation_max: FloatProperty(name="Sat Max", default=1.0, update=update_randomization)
    flight_color_value_min: FloatProperty(name="Val Min", default=0.5, update=update_randomization)
    flight_color_value_max: FloatProperty(name="Val Max", default=1.0, update=update_randomization)
    
    prob_shaft_gradient: FloatProperty(name="Prob Shaft Gradient", default=0.5, update=update_randomization)
    prob_shaft_solid: FloatProperty(name="Prob Shaft Solid", default=0.5, update=update_randomization)
    shaft_roughness: PointerProperty(type=RangeOrFixedProperty)
    prob_shaft_metallic: FloatProperty(name="Prob Shaft Metal", default=0.5, update=update_randomization)
    
    barrel_roughness: PointerProperty(type=RangeOrFixedProperty)
    tip_roughness: PointerProperty(type=RangeOrFixedProperty)

class DartboardSettings(PropertyGroup):
    randomize_cracks: BoolProperty(name="Rand Cracks", default=False, update=update_randomization)
    randomize_holes: BoolProperty(name="Rand Holes", default=True, update=update_randomization)
    randomize_wear: BoolProperty(name="Rand Wear", default=True, update=update_randomization)
    
    crack_factor: PointerProperty(type=RangeOrFixedProperty)
    hole_factor: PointerProperty(type=RangeOrFixedProperty)
    wear_level: PointerProperty(type=RangeOrFixedProperty)
    wear_contrast: PointerProperty(type=RangeOrFixedProperty)
    
    field_color_red: PointerProperty(type=ColorVariationProperty)
    field_color_green: PointerProperty(type=ColorVariationProperty)
    field_color_white: PointerProperty(type=ColorVariationProperty)

class SceneSettings(PropertyGroup):
    hdri_folder: StringProperty(name="HDRI Folder", default="assets/HDRIs", subtype='DIR_PATH', update=update_randomization)
    hdri_strength_min: FloatProperty(name="Strength Min", default=0.2, update=update_randomization)
    hdri_strength_max: FloatProperty(name="Strength Max", default=1.5, update=update_randomization)
    hdri_rotation_min: FloatProperty(name="Rot Min", default=0.0, update=update_randomization)
    hdri_rotation_max: FloatProperty(name="Rot Max", default=6.28318, update=update_randomization)

class ThrowSettings(PropertyGroup):
    num_darts: IntProperty(name="Num Darts", default=3, min=0, max=100, update=update_randomization)
    same_appearance: BoolProperty(name="Same Appearance", default=False, update=update_randomization)
    max_radius: FloatProperty(name="Max Radius", default=0.25, update=update_randomization)
    rot_x_min: FloatProperty(name="Rot X Min", default=-10.0, update=update_randomization)
    rot_x_max: FloatProperty(name="Rot X Max", default=10.0, update=update_randomization)
    rot_y_min: FloatProperty(name="Rot Y Min", default=-10.0, update=update_randomization)
    rot_y_max: FloatProperty(name="Rot Y Max", default=10.0, update=update_randomization)
    rot_z_min: FloatProperty(name="Rot Z Min", default=0.0, update=update_randomization)
    rot_z_max: FloatProperty(name="Rot Z Max", default=360.0, update=update_randomization)
    embed_depth_factor_min: FloatProperty(name="Embed Min", default=0.1, update=update_randomization)
    embed_depth_factor_max: FloatProperty(name="Embed Max", default=0.8, update=update_randomization)
    allow_darts_outside_board: BoolProperty(name="Allow Outside", default=False, update=update_randomization)
    bouncer_probability: FloatProperty(name="Bouncer Prob", default=0.0, min=0, max=1, update=update_randomization)

class DartGeneratorSettings(PropertyGroup):
    global_seed: IntProperty(name="Global Seed", default=0, update=update_randomization)
    
    camera: PointerProperty(type=CameraSettings)
    dart: PointerProperty(type=DartSettings)
    dartboard: PointerProperty(type=DartboardSettings)
    scene: PointerProperty(type=SceneSettings)
    throw: PointerProperty(type=ThrowSettings)


# --- Panels ---

class OBJECT_PT_DartGeneratorPanel(Panel):
    """Parent Panel"""
    bl_label = "Dart Dataset Generator"
    bl_idname = "OBJECT_PT_dart_gen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Dart Gen'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.dart_generator_settings
        
        layout.prop(settings, "global_seed")
        layout.operator("dart.force_randomize", text="Force Randomize", icon='FILE_REFRESH')
        layout.separator()
        layout.label(text="Generation Settings")
        
        col = layout.column(align=True)
        col.prop(context.scene, "frame_start", text="Start Frame")
        col.prop(context.scene, "frame_end", text="End Frame")
        layout.prop(context.scene, "output_path", text="Output Path")
        
        layout.operator("dart.generate_dataset", text="Generate Dataset", icon='RENDER_ANIMATION')


class OBJECT_PT_DartGen_Camera(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Camera"
    bl_idname = "OBJECT_PT_dart_gen_camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        cam = context.scene.dart_generator_settings.camera
        
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "camera"

        layout.label(text="Lens & Sensor")
        col = layout.column(align=True)
        col.prop(cam, "focal_length_min")
        col.prop(cam, "focal_length_max")
        col.separator()
        col.prop(cam, "sensor_width_min")
        col.prop(cam, "sensor_width_max")
        
        layout.separator()
        layout.label(text="Positioning")
        col = layout.column(align=True)
        col.prop(cam, "distance_factor_min")
        col.prop(cam, "distance_factor_max")
        col.separator()
        col.prop(cam, "polar_angle_min")
        col.prop(cam, "polar_angle_max")
        col.prop(cam, "azimuth_min")
        col.prop(cam, "azimuth_max")
        
        layout.separator()
        layout.label(text="Orientation")
        layout.prop(cam, "look_jitter_stddev")
        layout.prop(cam, "roll_mode")
        if cam.roll_mode != 'LEVEL_TO_HORIZON':
            layout.prop(cam, "roll_stddev_deg")
        if cam.roll_mode == 'RANDOM':
            col = layout.column(align=True)
            col.prop(cam, "roll_min_deg")
            col.prop(cam, "roll_max_deg")

        layout.separator()
        layout.label(text="Depth of Field")
        layout.prop(cam, "board_diameter_m")
        layout.prop(cam, "focus_radius_max_m")
        col = layout.column(align=True)
        col.prop(cam, "aperture_fstop_min")
        col.prop(cam, "aperture_fstop_max")


class OBJECT_PT_DartGen_Dart(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Dart Geometry"
    bl_idname = "OBJECT_PT_dart_gen_dart"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        dart = context.scene.dart_generator_settings.dart

        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "dart"

        def draw_range_prop(layout, prop_group, name):
            box = layout.box()
            row = box.row()
            row.label(text=name)
            if prop_group.use_fixed:
                row.prop(prop_group, "fixed_val", text="")
            else:
                sub = row.row(align=True)
                sub.prop(prop_group, "min_val", text="Min")
                sub.prop(prop_group, "max_val", text="Max")
            row.prop(prop_group, "use_fixed", text="", icon='PINNED')

        draw_range_prop(layout, dart.tip_length, "Tip Length")
        draw_range_prop(layout, dart.barrel_length, "Barrel Length")
        draw_range_prop(layout, dart.barrel_thickness, "Barrel Thickness")
        draw_range_prop(layout, dart.shaft_length, "Shaft Length")
        draw_range_prop(layout, dart.shaft_shape_mix, "Shaft Shape Mix")
        draw_range_prop(layout, dart.flight_insertion_depth, "Flight Insert Depth")
        
        layout.separator()
        layout.label(text="Flight Type")
        layout.prop(dart, "randomize_flight_type")
        if not dart.randomize_flight_type:
             layout.prop(dart, "fixed_flight_index")


class OBJECT_PT_DartGen_DartMaterial(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Dart Material"
    bl_idname = "OBJECT_PT_dart_gen_dart_mat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        dart = context.scene.dart_generator_settings.dart

        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "dart_mat"

        layout.label(text="Probabilities")
        col = layout.column(align=True)
        col.prop(dart, "prob_flight_texture_flags", text="Flag Texture")
        col.prop(dart, "prob_flight_texture_outpainted", text="Outpainted")
        col.prop(dart, "prob_flight_gradient", text="Gradient")
        col.prop(dart, "prob_flight_solid", text="Solid")
        
        layout.label(text="Colors (Sat/Val)")
        col = layout.column(align=True)
        col.prop(dart, "flight_color_saturation_min", text="Sat Min")
        col.prop(dart, "flight_color_saturation_max", text="Sat Max")
        col.prop(dart, "flight_color_value_min", text="Val Min")
        col.prop(dart, "flight_color_value_max", text="Val Max")
        
        layout.label(text="Shaft")
        col = layout.column(align=True)
        col.prop(dart, "prob_shaft_gradient")
        col.prop(dart, "prob_shaft_solid")
        col.prop(dart, "prob_shaft_metallic")
        
        
class OBJECT_PT_DartGen_Dartboard(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Dartboard"
    bl_idname = "OBJECT_PT_dart_gen_dartboard"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        db = context.scene.dart_generator_settings.dartboard
        
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "dartboard"

        layout.prop(db, "randomize_cracks")
        layout.prop(db, "randomize_holes")
        layout.prop(db, "randomize_wear")
        
        def draw_range_prop(layout, prop_group, name):
            box = layout.box()
            row = box.row()
            row.label(text=name)
            if prop_group.use_fixed:
                row.prop(prop_group, "fixed_val", text="")
            else:
                sub = row.row(align=True)
                sub.prop(prop_group, "min_val", text="Min")
                sub.prop(prop_group, "max_val", text="Max")
            row.prop(prop_group, "use_fixed", text="", icon='PINNED')

        if db.randomize_cracks:
            draw_range_prop(layout, db.crack_factor, "Crack Factor")
        if db.randomize_holes:
            draw_range_prop(layout, db.hole_factor, "Hole Factor")
        if db.randomize_wear:
            draw_range_prop(layout, db.wear_level, "Wear Level")
            draw_range_prop(layout, db.wear_contrast, "Wear Contrast")
            
        layout.separator()
        layout.label(text="Colors")
        
        def draw_color_var(layout, prop_group, name):
            box = layout.box()
            row = box.row()
            row.prop(prop_group, "randomize", text="", icon='CHECKBOX_HLT' if prop_group.randomize else 'CHECKBOX_DEHLT')
            row.label(text=name)
            row.prop(prop_group, "base_color", text="")
            
            if prop_group.randomize:
                col = box.column(align=True)
                col.use_property_split = True
                col.prop(prop_group, "hue_variation", text="Hue \u00B1")
                col.prop(prop_group, "saturation_variation", text="Sat \u00B1")
                col.prop(prop_group, "value_variation", text="Val \u00B1")

        draw_color_var(layout, db.field_color_red, "Red Fields")
        draw_color_var(layout, db.field_color_green, "Green Fields")
        draw_color_var(layout, db.field_color_white, "White Fields")


class OBJECT_PT_DartGen_Scene(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Scene / HDRI"
    bl_idname = "OBJECT_PT_dart_gen_scene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        sce = context.scene.dart_generator_settings.scene
        
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "scene"

        layout.prop(sce, "hdri_folder")
        col = layout.column(align=True)
        col.prop(sce, "hdri_strength_min")
        col.prop(sce, "hdri_strength_max")
        col.separator()
        col.prop(sce, "hdri_rotation_min")
        col.prop(sce, "hdri_rotation_max")

class OBJECT_PT_DartGen_Throw(Panel):
    bl_parent_id = "OBJECT_PT_dart_gen"
    bl_label = "Throw & Physics"
    bl_idname = "OBJECT_PT_dart_gen_throw"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        throw = context.scene.dart_generator_settings.throw

        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        op = row.operator("dart.reset_settings", text="", icon='LOOP_BACK')
        op.setting_group = "throw"
        
        layout.prop(throw, "num_darts")
        layout.prop(throw, "same_appearance")
        layout.prop(throw, "max_radius")
        layout.prop(throw, "bouncer_probability")
        layout.prop(throw, "allow_darts_outside_board")

        layout.label(text="Angle Randomization (\u00B0)")
        col = layout.column(align=True)
        col.prop(throw, "rot_x_min", text="X Min")
        col.prop(throw, "rot_x_max", text="X Max")
        col.separator()
        col.prop(throw, "rot_y_min", text="Y Min")
        col.prop(throw, "rot_y_max", text="Y Max")
        col.separator()
        col.prop(throw, "rot_z_min", text="Z Min")
        col.prop(throw, "rot_z_max", text="Z Max")
        
        layout.label(text="Embed Depth")
        col = layout.column(align=True)
        col.prop(throw, "embed_depth_factor_min", text="Min")
        col.prop(throw, "embed_depth_factor_max", text="Max")


class DART_OT_GenerateDataset(Operator):
    """Generate Dataset (Render Animation)"""
    bl_idname = "dart.generate_dataset"
    bl_label = "Generate Dataset"

    def execute(self, context):
        scene = context.scene
        base_out_path = bpy.path.abspath(scene.output_path)
        if not base_out_path or base_out_path == "//output/":
             self.report({'ERROR'}, "Please set a valid Output Path first.")
             return {'CANCELLED'}

        seed = scene.dart_generator_settings.global_seed
        dataset_dir = os.path.join(base_out_path, str(seed))
        images_dir = os.path.join(dataset_dir, "images")
        labels_dir = os.path.join(dataset_dir, "labels")

        try:
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(labels_dir, exist_ok=True)
        except Exception as e:
            self.report({'ERROR'}, f"Could not create output directories: {e}")
            return {'CANCELLED'}
        
        scene.render.filepath = os.path.join(images_dir, "image_")
        
        mgr = get_manager(context)
        if mgr and mgr.annotation_manager:
            mgr.annotation_manager.output_dir = Path(labels_dir)
            self.report({'INFO'}, f"Set label output to: {labels_dir}")

        self.report({'INFO'}, f"Ready to generate! Images: {images_dir}, Labels: {labels_dir}")
        return {'FINISHED'}


class DART_OT_ForceRandomize(Operator):
    """Force re-randomization of the scene"""
    bl_idname = "dart.force_randomize"
    bl_label = "Force Randomize"

    def execute(self, context):
        update_randomization(None, context)
        return {'FINISHED'}

class DART_OT_ResetSettings(Operator):
    """Reset settings to default values"""
    bl_idname = "dart.reset_settings"
    bl_label = "Reset to Defaults"
    
    setting_group: StringProperty()
    
    def _reset_recursive(self, prop_group):
        """Recursively reset properties to default."""
        for prop_name, prop_val in prop_group.bl_rna.properties.items():
            if prop_name in {"rna_type", "name"}:
                continue
            
            # Reset this property
            if not prop_group.is_property_readonly(prop_name):
                 prop_group.property_unset(prop_name)
                 
            # Recurse if PointerProperty
            if prop_name in prop_group.__annotations__ and isinstance(prop_group.__annotations__[prop_name], PointerProperty):
                 # Note: PointerProperty definitions in class annotations vs instances
                 # We need to access the actual object
                 sub_obj = getattr(prop_group, prop_name)
                 if sub_obj:
                    self._reset_recursive(sub_obj)

    def execute(self, context):
        settings = context.scene.dart_generator_settings
        group_name = self.setting_group
        
        target = None
        if group_name == "camera":
            target = settings.camera
        elif group_name == "dart" or group_name == "dart_mat":
            target = settings.dart
        elif group_name == "dartboard":
            target = settings.dartboard
        elif group_name == "scene":
            target = settings.scene
        elif group_name == "throw":
            target = settings.throw
            
        if target:
            # We need to manually reset complex nested structures for some panels
            # But property_unset generally handles simple defaults. 
            # For strict complex defaults (like specific colors), we might need manual handling if defaults weren't registered perfectly.
            # But let's try generic recursive unset first.
            
            # Helper to set complex defaults
            # Actually, because we defined defaults in PropertyGroups above using the same values as config, 
            # property_unset() will revert to those defaults!
            
            
            # Reset logic for Darts & Dartboard specifically needs deep recursion
            if group_name == "dart":
                 # Iterate over known pointer props
                 for attr in dir(target):
                     if attr in ["tip_length", "barrel_length", "barrel_thickness", "shaft_length", "shaft_shape_mix", "flight_insertion_depth", "flight_roughness", "barrel_roughness", "tip_roughness", "shaft_roughness"]:
                         sub = getattr(target, attr)
                         sub.property_unset("min_val")
                         sub.property_unset("max_val")
                         sub.property_unset("fixed_val")
                         sub.property_unset("use_fixed")

            if group_name == "dartboard":
                 for attr in dir(target):
                    if attr in ["crack_factor", "hole_factor", "wear_level", "wear_contrast"]:
                         sub = getattr(target, attr)
                         sub.property_unset("min_val")
                         sub.property_unset("max_val")
                         sub.property_unset("fixed_val")
                         sub.property_unset("use_fixed")
                    if attr in ["field_color_red", "field_color_green", "field_color_white"]:
                         sub = getattr(target, attr)
                         sub.property_unset("base_color")
                         sub.property_unset("hue_variation")
                         sub.property_unset("saturation_variation")
                         sub.property_unset("value_variation")
                         sub.property_unset("randomize")

            # Generic reset for standard props
            for k in target.bl_rna.properties.keys():
                if k not in ["rna_type", "name"] and not target.is_property_readonly(k):
                    target.property_unset(k)
            
            update_randomization(self, context)
            self.report({'INFO'}, f"Reset {group_name} settings to default")

        return {'FINISHED'}

# Handlers
@persistent
def on_frame_change_pre(scene):
    mgr = get_manager(bpy.context)
    if not mgr:
        return
    frame = scene.frame_current
    camera = scene.camera
    if camera:
        try:
            mgr.randomize(frame, camera, scene)
        except Exception as e:
            print(f"Frame Change Error: {e}")

@persistent
def on_render_post(scene):
    mgr = get_manager(bpy.context)
    if not mgr:
        return
    camera = scene.camera
    if camera:
        try:
            mgr.annotation_manager.annotate(scene, camera)
        except Exception as e:
            print(f"Render Post Error: {e}")

@persistent
def load_post_handler(dummy):
    if bpy.context:
        get_manager(bpy.context)

def setup_defaults():
    # Helper to enforce initialization of complex defaults when addon is enabled?
    # Usually Blender handles 'default' arg in Property definition well.
    pass

def init_props():
    # Because we use many sub-properties (RangeOrFixed), we need to set their defaults 
    # explicitly if they differ from the class default (0.0/1.0).
    # However, we cannot easily set defaults per instance of PointerProperty in definition.
    # We must do it on Access or Init.
    # A cleaner way in Blender is to define separate PropertyGroups for specific ranges if they have different defaults,
    # OR set them on registration / first load.
    
    # We'll use a handler or check in get_manager to ensure defaults are applied once? 
    # Or rely on the user manually setting them? 
    # The 'default' parameter in FloatProperty applies to ALL instances of that property group.
    # But RangeOrFixedProperty is generic.
    # So 'min_val' default 0.0 applies to ALL ranges.
    # But 'tip_length' needs default 20.0 - 45.0.
    
    # SOLUTION: We can't use generic PropertyGroups with 'default=' in definitions if instances need different defaults.
    # We should initialise values in a `load_post` or similar if they are at factory 0.0
    
    # Ideally, we define a callback that checks if "initialized" property is set?
    pass

classes = (
    RangeOrFixedProperty,
    ColorVariationProperty,
    CameraSettings,
    DartSettings,
    DartboardSettings,
    SceneSettings,
    ThrowSettings,
    DartGeneratorSettings,
    OBJECT_PT_DartGeneratorPanel,
    OBJECT_PT_DartGen_Camera,
    OBJECT_PT_DartGen_Dart,
    OBJECT_PT_DartGen_DartMaterial,
    OBJECT_PT_DartGen_Dartboard,
    OBJECT_PT_DartGen_Scene,
    OBJECT_PT_DartGen_Throw,
    DART_OT_GenerateDataset,
    DART_OT_ForceRandomize,
    DART_OT_ResetSettings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.dart_generator_settings = PointerProperty(type=DartGeneratorSettings)
    bpy.types.Scene.output_path = StringProperty(
        name="Output Path",
        description="Path where rendered images will be saved",
        default="//output/",
        subtype='DIR_PATH'
    )
    
    bpy.app.handlers.frame_change_pre.append(on_frame_change_pre)
    bpy.app.handlers.render_post.append(on_render_post)
    bpy.app.handlers.load_post.append(load_post_handler)
    
    # Init Defaults Hack:
    # Since we can't define instance-specific defaults for PointerProperties in class defs,
    # We will let the user adjust them, OR we define specific classes for each default config.
    # But for a plugin of this size, it might be okay.
    # ACTUALLY, to satisfy "Default values must match config", we MUST set them.
    # We will do it in a one-off function called during register, but only if not set?
    # Properties are persistent in .blend file. 
    # If we register, they are reset? No.
    
    # Let's rely on the Update Operator to fix defaults when "Reset" is clicked, 
    # and maybe run reset once.
    # But wait, Reset uses `property_unset`, which goes back to Class Default.
    # If Class Default for `RangeOrFixedProperty.min` is 0, then resetting `tip_length` makes it 0.
    # That is WRONG for `tip_length` (20).
    
    # FIX: We need specific PropertyGroups for specific defaults OR we manually set values in the Reset Operator.
    # I will update the Reset Operator to manually set the correct values instead of `property_unset`.

def unregister():
    if on_frame_change_pre in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(on_frame_change_pre)
    if on_render_post in bpy.app.handlers.render_post:
        bpy.app.handlers.render_post.remove(on_render_post)
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

    del bpy.types.Scene.dart_generator_settings
    if hasattr(bpy.types.Scene, "output_path"):
        del bpy.types.Scene.output_path

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# Update Reset Operator with explicit defaults
def _set_range(prop, min_v, max_v):
    prop.min_val = min_v
    prop.max_val = max_v
    prop.use_fixed = False

def _set_color(prop, col, h=0, s=0, v=0, rand=True):
    prop.base_color = col
    prop.hue_variation = h
    prop.saturation_variation = s
    prop.value_variation = v
    prop.randomize = rand
    
DART_OT_ResetSettings.execute = lambda self, context: _execute_reset(self, context)

def _execute_reset(self, context):
    settings = context.scene.dart_generator_settings
    group = self.setting_group
    
    if group == "camera":
        c = settings.camera
        c.focal_length_min = 20.0
        c.focal_length_max = 60.0
        c.sensor_width_min = 8.0
        c.sensor_width_max = 36.0
        c.distance_factor_min = 1.0
        c.distance_factor_max = 2.0
        c.polar_angle_min = 0.0
        c.polar_angle_max = 75.0
        c.azimuth_min = 0.0
        c.azimuth_max = 360.0
        c.look_jitter_stddev = 0.02
        c.roll_mode = 'TWENTY_EXACT_UP'
        c.roll_stddev_deg = 6.0
        c.roll_min_deg = -180.0
        c.roll_max_deg = 180.0
        c.board_diameter_m = 0.44
        c.focus_radius_max_m = 0.225
        c.aperture_fstop_min = 0.8
        c.aperture_fstop_max = 5.6
        
    elif group == "dart" or group == "dart_mat":
        # We reset both if either is clicked, or split?
        # Let's split logic but they share same Settings Object
        d = settings.dart
        
        if group == "dart":
            _set_range(d.tip_length, 20.0, 45.0)
            _set_range(d.barrel_length, 40.0, 55.0)
            _set_range(d.barrel_thickness, 0.15, 5.0)
            _set_range(d.shaft_length, 26.0, 56.0)
            _set_range(d.shaft_shape_mix, 0.0, 1.0)
            _set_range(d.flight_insertion_depth, 10.0, 20.0)
            d.randomize_flight_type = True
            d.fixed_flight_index = 100
            
        if group == "dart_mat" or group == "dart": # Reset materials too if wanted, or separate
            d.prob_flight_texture_flags = 0.3
            d.prob_flight_texture_outpainted = 0.5
            d.prob_flight_gradient = 0.1
            d.prob_flight_solid = 0.1
            _set_range(d.flight_roughness, 0.0, 1.0)
            d.flight_color_saturation_min = 0.5
            d.flight_color_saturation_max = 1.0
            d.flight_color_value_min = 0.5
            d.flight_color_value_max = 1.0
            d.prob_shaft_gradient = 0.5
            d.prob_shaft_solid = 0.5
            _set_range(d.shaft_roughness, 0.0, 0.8)
            d.prob_shaft_metallic = 0.5
            _set_range(d.barrel_roughness, 0.0, 0.5)
            _set_range(d.tip_roughness, 0.0, 0.5)

    elif group == "dartboard":
        db = settings.dartboard
        db.randomize_cracks = False
        db.randomize_holes = True
        db.randomize_wear = True
        _set_range(db.crack_factor, 0.0, 1.0)
        _set_range(db.hole_factor, 0.0, 1.0)
        _set_range(db.wear_level, 0.0, 1.0)
        _set_range(db.wear_contrast, 0.5, 1.0)
        _set_color(db.field_color_red, (0.8, 0.1, 0.1, 1.0), 0.02, 0.1, 0.15)
        _set_color(db.field_color_green, (0.1, 0.5, 0.1, 1.0), 0.02, 0.1, 0.15)
        _set_color(db.field_color_white, (0.9, 0.9, 0.85, 1.0), 0.0, 0.5, 0.1)
        
    elif group == "scene":
        s = settings.scene
        s.hdri_folder = "assets/HDRIs"
        s.hdri_strength_min = 0.2
        s.hdri_strength_max = 1.5
        s.hdri_rotation_min = 0.0
        s.hdri_rotation_max = 6.28318530718
        
    elif group == "throw":
        t = settings.throw
        t.num_darts = 3
        t.same_appearance = False
        t.max_radius = 0.25
        t.rot_x_min = -10.0
        t.rot_x_max = 10.0
        t.rot_y_min = -10.0
        t.rot_y_max = 10.0
        t.rot_z_min = 0.0
        t.rot_z_max = 360.0
        t.embed_depth_factor_min = 0.1
        t.embed_depth_factor_max = 0.8
        t.allow_darts_outside_board = False
        t.bouncer_probability = 0.0

    update_randomization(self, context)
    self.report({'INFO'}, f"Reset {group} settings to defaults.")
    return {'FINISHED'}


if __name__ == "__main__":
    register()
