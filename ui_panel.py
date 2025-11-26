import bpy
#from randomization_manager import RandomizationManager

class DatasetGeneratorPanel(bpy.types.Panel):
    bl_label = "Dart Dataset Generator"
    bl_idname = "VIEW3D_PT_dart_dataset"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Dataset Generator'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "dart_seed")
        layout.prop(scene, "image_count")
        layout.prop(scene, "output_path")
        layout.operator("dart.generate_dataset", text="Generate Dataset", icon='RENDER_STILL')

        row = self.layout.row()
        row.operator("mesh.primitive_cube_add", text="Add Cube", icon='MESH_CUBE')


def register():
    bpy.utils.register_class(DatasetGeneratorPanel)


def unregister():
    bpy.utils.unregister_class(DatasetGeneratorPanel)