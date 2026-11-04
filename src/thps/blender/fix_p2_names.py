# One-off repair for the file built before s03 got P2 right. s03 now does all of this on a rebuild. Safe to re-run.
# 1. The torso mesh took the name "P2_body", the hip empty became "P2_body.001", and s10 keyed the hips onto the torso.
# 2. Setting .parent clears matrix_parent_inverse, so the copied parts sat away from their bones.
import bpy

OB = bpy.data.objects
if not OB.get("P2_torso"):
    torso, hips = OB["P2_body"], OB["P2_body.001"]
    assert torso.type == "MESH" and hips.type == "EMPTY"
    if torso.animation_data:
        torso.animation_data_clear()
    torso.name = "P2_torso"
    hips.name = "P2_body"
    src = OB["body"]
    torso.location = src.location
    torso.rotation_euler = src.rotation_euler
    torso.scale = src.scale
    marker = OB["P2_marker"]
    marker.parent = hips
    marker.location = (0, 0, 8.6)

for child in OB["Armature"].children:
    if not child.name.startswith("phone"):
        OB["P2_torso" if child.name == "body" else "P2_" + child.name].matrix_parent_inverse = child.matrix_parent_inverse

OB["phone cop"].scale = (0.8,) * 3  # matches s09
bpy.ops.wm.save_mainfile()
print("P2 parents:", OB["P2_arm"].parent.name, OB["P2_marker"].parent.name, "| torso:", OB["P2_torso"].type, OB["P2_torso"].parent.name)
