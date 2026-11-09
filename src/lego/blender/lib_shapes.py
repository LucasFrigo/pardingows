# Small shared shapes.
import bpy


def plane(name, coll, centre, w, h, mat):
    """A flat panel facing -Y, centred on a point."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for l, q in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l.uv = q
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location = centre
    return ob
