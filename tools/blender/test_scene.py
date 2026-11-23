"""Blender headless check: a lit, animated scene rendered to a vertical 1080x1920 video.

Usage: blender -b -P tools/blender/test_scene.py -- out.mp4 [frames]
"""
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "/tmp/blender_test.mp4"
frames = int(argv[1]) if len(argv) > 1 else 60

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, frames
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.filepath = out

world = bpy.data.worlds.new("World")
world.color = (0.03, 0.04, 0.08)
scene.world = world

bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
floor = bpy.context.object
mat = bpy.data.materials.new("Floor")
mat.diffuse_color = (0.08, 0.1, 0.14, 1)
floor.data.materials.append(mat)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1.2), segments=48, ring_count=24)
ball = bpy.context.object
bpy.ops.object.shade_smooth()
bm = bpy.data.materials.new("Ball")
bm.diffuse_color = (0.91, 0.69, 0.13, 1)
ball.data.materials.append(bm)
for f, z in ((1, 1.2), (frames // 2, 3.0), (frames, 1.2)):   # a bounce
    ball.location.z = z
    ball.keyframe_insert("location", frame=f)

bpy.ops.object.light_add(type="AREA", location=(3, -3, 6))
light = bpy.context.object
light.data.energy = 900
light.data.size = 4
light.rotation_euler = (math.radians(40), 0, math.radians(45))

bpy.ops.object.camera_add(location=(0, -9, 3.2), rotation=(math.radians(82), 0, 0))
scene.camera = bpy.context.object
bpy.context.object.data.lens = 40

bpy.ops.render.render(animation=True)
print("RENDERED", out)
