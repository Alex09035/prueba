"""
Script de Blender (bpy) para recrear una portada estilo Minecraft inspirada
en la imagen de referencia proporcionada por el usuario.

Uso:
1) Abre Blender.
2) Ve a Scripting > New.
3) Pega este script y ejecútalo.
4) Renderiza con F12.

El script genera:
- Fondo celeste con nubes simples.
- Isla flotante voxel con césped/tierra.
- Personajes tipo bloques (Steve y Alex simplificados).
- Árbol y oveja low-poly voxel.
- Texto 3D "MINECRAFT" con acabado de bloque.
"""

import bpy
import random
from math import radians
from mathutils import Vector

SEED = 42
random.seed(SEED)


# ------------------------------
# Utilidades
# ------------------------------

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)
    for img in bpy.data.images:
        bpy.data.images.remove(img)


def make_mat(name, color, roughness=0.85, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_cube(name, location, scale=(1, 1, 1), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if material:
        if len(obj.data.materials):
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
    return obj


def set_world(color=(0.18, 0.67, 0.91)):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1.0)
    bg.inputs[1].default_value = 1.0


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024


# ------------------------------
# Construcción del entorno
# ------------------------------

def build_island(mats):
    grass = mats["grass"]
    dirt = mats["dirt"]
    stone = mats["stone"]

    size = 9
    max_h = 4

    for x in range(-size, size + 1):
        for y in range(-size, size + 1):
            dist = abs(x) + abs(y) * 0.85
            if dist < 11:
                h = int(max(1, max_h - dist * 0.28 + random.uniform(-0.4, 0.5)))

                top_z = h
                add_cube(
                    f"grass_{x}_{y}",
                    location=(x, y, top_z),
                    scale=(0.5, 0.5, 0.5),
                    material=grass,
                )

                for z in range(h - 1, -3, -1):
                    mat = dirt if z > -1 else stone
                    add_cube(
                        f"dirt_{x}_{y}_{z}",
                        location=(x, y, z),
                        scale=(0.5, 0.5, 0.5),
                        material=mat,
                    )


def build_clouds(mat_cloud):
    cloud_sets = [
        [(-12, -7, 17), (-10, -7, 17), (-8, -6, 17), (-6, -6, 17)],
        [(6, 10, 16), (8, 10, 16), (10, 11, 16)],
        [(-2, 14, 15), (0, 14, 15), (2, 14, 15), (4, 14, 15)],
    ]
    for i, cloud in enumerate(cloud_sets):
        for j, loc in enumerate(cloud):
            add_cube(
                f"cloud_{i}_{j}",
                location=loc,
                scale=(1.2, 0.6, 0.2),
                material=mat_cloud,
            )


def build_tree(mats, base=(6, 2, 5)):
    wood = mats["wood"]
    leaf = mats["leaf"]

    bx, by, bz = base
    for i in range(4):
        add_cube(f"tree_trunk_{i}", (bx, by, bz + i), (0.5, 0.5, 0.5), wood)

    for x in range(-2, 3):
        for y in range(-2, 3):
            for z in range(2):
                if abs(x) + abs(y) < 4:
                    add_cube(
                        f"leaf_{x}_{y}_{z}",
                        (bx + x, by + y, bz + 4 + z),
                        (0.5, 0.5, 0.5),
                        leaf,
                    )


def build_character(name, mats, origin=(0, 0, 6), shirt=(0.1, 0.6, 0.8), pants=(0.25, 0.2, 0.8), hair=(0.3, 0.16, 0.08)):
    skin = mats["skin"]
    shirt_mat = make_mat(f"{name}_shirt", shirt, roughness=0.7)
    pants_mat = make_mat(f"{name}_pants", pants, roughness=0.7)
    hair_mat = make_mat(f"{name}_hair", hair, roughness=0.8)

    ox, oy, oz = origin

    # Piernas
    add_cube(f"{name}_leg_l", (ox - 0.35, oy, oz), (0.22, 0.22, 0.7), pants_mat)
    add_cube(f"{name}_leg_r", (ox + 0.35, oy, oz), (0.22, 0.22, 0.7), pants_mat)

    # Torso
    add_cube(f"{name}_torso", (ox, oy, oz + 1.1), (0.55, 0.3, 0.6), shirt_mat)

    # Brazos
    add_cube(f"{name}_arm_l", (ox - 0.82, oy, oz + 1.1), (0.2, 0.2, 0.6), skin)
    add_cube(f"{name}_arm_r", (ox + 0.82, oy, oz + 1.1), (0.2, 0.2, 0.6), skin)

    # Cabeza + pelo
    add_cube(f"{name}_head", (ox, oy, oz + 2.0), (0.42, 0.42, 0.42), skin)
    add_cube(f"{name}_hair", (ox, oy, oz + 2.28), (0.44, 0.44, 0.18), hair_mat)

    # Pose leve dinámica
    for obj in [
        bpy.data.objects[f"{name}_arm_l"],
        bpy.data.objects[f"{name}_leg_l"],
    ]:
        obj.rotation_euler.y = radians(18)

    for obj in [
        bpy.data.objects[f"{name}_arm_r"],
        bpy.data.objects[f"{name}_leg_r"],
    ]:
        obj.rotation_euler.y = radians(-15)


def build_sheep(mats, origin=(8, -4, 5.5)):
    wool = mats["wool"]
    dark = mats["dark"]
    ox, oy, oz = origin

    add_cube("sheep_body", (ox, oy, oz + 0.4), (0.65, 0.4, 0.4), wool)
    add_cube("sheep_head", (ox + 0.75, oy, oz + 0.4), (0.25, 0.25, 0.25), dark)
    for i, dx in enumerate([-0.35, 0.35]):
        for j, dy in enumerate([-0.2, 0.2]):
            add_cube(f"sheep_leg_{i}_{j}", (ox + dx, oy + dy, oz - 0.15), (0.1, 0.1, 0.25), dark)


def build_logo(mats):
    logo_mat = mats["logo"]
    shadow_mat = mats["logo_shadow"]

    bpy.ops.object.text_add(location=(0, -5.8, 16.8))
    txt = bpy.context.active_object
    txt.name = "MinecraftLogo"
    txt.data.body = "MINECRAFT"
    txt.data.extrude = 0.33
    txt.data.bevel_depth = 0.04
    txt.data.align_x = 'CENTER'

    if len(txt.data.materials):
        txt.data.materials[0] = logo_mat
    else:
        txt.data.materials.append(logo_mat)

    bpy.ops.object.duplicate()
    shadow = bpy.context.active_object
    shadow.name = "MinecraftLogoShadow"
    shadow.location += Vector((0.35, -0.4, -0.42))
    shadow.data = txt.data.copy()
    shadow.data.materials.clear()
    shadow.data.materials.append(shadow_mat)


# ------------------------------
# Cámara y luces
# ------------------------------

def setup_camera_and_lights():
    bpy.ops.object.camera_add(location=(0, -20, 10), rotation=(radians(73), 0, 0))
    cam = bpy.context.active_object
    cam.data.lens = 28
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type='SUN', location=(8, -10, 25))
    sun = bpy.context.active_object
    sun.data.energy = 4.0
    sun.rotation_euler = (radians(35), radians(10), radians(30))

    bpy.ops.object.light_add(type='AREA', location=(-12, -8, 14))
    fill = bpy.context.active_object
    fill.data.energy = 350
    fill.data.size = 14


# ------------------------------
# Main
# ------------------------------

def main():
    clear_scene()
    set_world()
    setup_render()

    mats = {
        "grass": make_mat("Grass", (0.22, 0.84, 0.22), roughness=0.95),
        "dirt": make_mat("Dirt", (0.67, 0.47, 0.2), roughness=0.95),
        "stone": make_mat("Stone", (0.48, 0.48, 0.5), roughness=0.9),
        "wood": make_mat("Wood", (0.5, 0.3, 0.12), roughness=0.9),
        "leaf": make_mat("Leaf", (0.2, 0.65, 0.22), roughness=0.95),
        "skin": make_mat("Skin", (0.95, 0.73, 0.56), roughness=0.75),
        "wool": make_mat("Wool", (0.9, 0.9, 0.9), roughness=0.95),
        "dark": make_mat("Dark", (0.35, 0.35, 0.35), roughness=0.85),
        "cloud": make_mat("Cloud", (0.85, 0.95, 1.0), roughness=1.0),
        "logo": make_mat("Logo", (0.78, 0.78, 0.78), roughness=0.4),
        "logo_shadow": make_mat("LogoShadow", (0.06, 0.06, 0.06), roughness=0.7),
    }

    build_island(mats)
    build_clouds(mats["cloud"])
    build_tree(mats)

    build_character(
        "Steve",
        mats,
        origin=(-0.6, -0.5, 6),
        shirt=(0.09, 0.54, 0.75),
        pants=(0.28, 0.24, 0.78),
        hair=(0.32, 0.18, 0.09),
    )
    build_character(
        "Alex",
        mats,
        origin=(-2.0, 0.3, 6),
        shirt=(0.33, 0.72, 0.33),
        pants=(0.4, 0.25, 0.14),
        hair=(0.95, 0.54, 0.2),
    )

    build_sheep(mats)
    build_logo(mats)

    setup_camera_and_lights()


if __name__ == "__main__":
    main()
