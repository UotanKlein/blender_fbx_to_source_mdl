import bpy
import sys
import os
import subprocess
import shutil
from pathlib import Path

BONE_NAME = 'root'
ARMATURE_NAME = 'armature'
ACTION_NAME = 'idle'

def main():
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    file_path, export_path, engine_path = sys.argv[sys.argv.index("--") + 1:]

    file_path_info = Path(file_path)
    file_path_stem = file_path_info.stem

    root_path_info = Path(os.path.join(export_path, file_path_stem))

    export_path = os.path.join(root_path_info, 'smd')
    export_path_info = Path(export_path)
    export_path_info.mkdir(parents=True, exist_ok=True)

    materials_path_info = Path(os.path.join(root_path_info, 'materials', 'models', file_path_stem))
    materials_path_info.mkdir(parents=True, exist_ok=True)

    models_path_info = Path(os.path.join(root_path_info, 'models'))
    models_path_info.mkdir(parents=True, exist_ok=True)

    model_name_dir_path = os.path.join('dynamic', 'objects', file_path_stem)

    qc_text = f"""$modelname "{os.path.join(model_name_dir_path, f'{file_path_stem}.mdl')}"
$bodygroup "{file_path_stem}"
{{
    studio "{file_path_stem}.smd"
}}
$surfaceprop "default"
$contents "solid"
$illumposition 33.674 0.007 13.301
$cdmaterials "/models/{file_path_stem}/"
$cbox 0 0 0 0 0 0
$bbox -57.067 -42.419 -14.332 57.053 109.766 40.933
$definebone "root" "" 0.000000 0.000000 0.000000 -0.000000 0.000000 89.999985 0.000000 0.000000 0.000000 -0.000000 0.000000 0.000000
$sequence "idle" {{
    "anims/idle.smd"
    fadein 0.2
    fadeout 0.2
    fps 1
    loop
}}"""

    qc_file_path = os.path.join(export_path, f'{file_path_stem}.qc')
    qc_file = open(qc_file_path, 'w')
    qc_file.write(qc_text)
    qc_file.close()

    bpy.data.scenes[bpy.context.scene.name].name = file_path_stem
    bpy.data.collections[bpy.context.collection.name].name = file_path_stem

    bpy.ops.import_scene.fbx(filepath=file_path, global_scale=39.35)
    bpy.ops.object.select_all(action='DESELECT')
    for object in bpy.data.objects:
        if object.type == 'MESH' and bpy.context.view_layer.objects.get(object.name):
            bpy.context.view_layer.objects.active = object
            object.select_set(True)
    bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active

    armature_data = bpy.data.armatures.new(name=ARMATURE_NAME)
    armature_obj = bpy.data.objects.new(name=ARMATURE_NAME, object_data=armature_data)
    bpy.context.collection.objects.link(armature_obj)
    bpy.context.view_layer.objects.active = armature_obj

    bpy.ops.object.mode_set(mode='EDIT')
    
    bone = armature_data.edit_bones.new(name=BONE_NAME)
    bone.head = (0, 0, 0)
    bone.tail = (0, 0, 1)

    bpy.ops.object.mode_set(mode='OBJECT')
    
    vertex_group = mesh.vertex_groups.new(name=BONE_NAME)
    all_vertex_indices = list(range(len(mesh.data.vertices)))
    vertex_group.add(all_vertex_indices, 1.0, 'ADD')
    
    armature_mod = mesh.modifiers.new(name='Armature', type='ARMATURE')
    armature_mod.object = armature_obj
    armature_mod.vertex_group = vertex_group.name
    armature_mod.use_vertex_groups = True
    
    action = bpy.data.actions.new(name=ACTION_NAME)
    armature_obj.animation_data_create()
    armature_obj.animation_data.action = action
    
    fcurve = action.fcurves.new(data_path=f'pose.bones["{BONE_NAME}"].location', index=2)
    keyframe_points = fcurve.keyframe_points
    keyframe_points.add(1)
    keyframe_points[0].co = (0, 0)

    #"$bumpmap" "models/ui/ui_menu_01_normal"

    # "$phong" "1"
	# "$phongboost" "5"
	
	# "$phongexponenttexture" "models/ui/ui_menu_01_roughness"
	# "$phongalbedotint" "0"										
	# "$phongfresnelranges"	"[.1 .5  1]"

    # "$selfillummask" 	"models/ui/ui_menu_01_selfillum_mask"
	# "$selfillum" "1"
	# "$selfillumtint" "[2 1 1]"

    for mat_slot in mesh.material_slots:
        material = mat_slot.material
        if material.use_nodes:
            for mat_node in material.node_tree.nodes:
                if hasattr(mat_node, 'image'):
                    image_filepath_info = Path(mat_node.image.filepath)
                    material.name = image_filepath_info.stem
                    print(material.name)
                    vmt_text = f'''"VertexLitGeneric"
{{
    "$model" "1"
    "$basetexture" "models/{file_path_stem}/{image_filepath_info.stem}"
}}'''
                    vmt_file = open(os.path.join(materials_path_info, f'{image_filepath_info.stem}.vmt'), 'w')
                    vmt_file.write(vmt_text)
                    vmt_file.close()

                    if not os.path.exists(os.path.join(materials_path_info, f'{image_filepath_info.stem}.vtf')):
                        subprocess.run(['vtfcmd', '-file', image_filepath_info, '-output', materials_path_info])

    vs = bpy.context.scene.vs
    vs.export_format = 'SMD'
    vs.export_path = export_path
    vs.engine_path = engine_path
    bpy.ops.export_scene.smd(export_scene=True)

    engine_path_info = Path(engine_path, '..', 'garrysmod').resolve()
    subprocess.run([os.path.join(engine_path, 'studiomdl.exe'), '-game', engine_path_info, '-nop4', '-verbose', qc_file_path])
    shutil.move(os.path.join(engine_path_info, 'models', 'dynamic'), models_path_info)
main()
