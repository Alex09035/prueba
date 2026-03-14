"""
Portada estilo Minecraft en Blender (bpy), más detallada y cercana al arte promocional.

Qué crea:
- Cielo azul con gradiente y nubes angulosas.
- Isla flotante voxel con capas de césped, tierra y piedra.
- Río y cascada lateral.
- Flores y hierba en superficie.
- Árbol principal y árbol de cerezo estilo voxel.
- Personajes tipo Steve y Alex en pose dinámica.
- Pico simple en mano de Steve.
- Oveja y zorro low-poly voxel.
- Logo 3D "MINECRAFT" con sombra posterior.

Uso:
1) Blender > Scripting > New
2) Pegar y ejecutar.
3) F12 para render.
"""

import bpy
import random
from math import radians
from mathutils import Vector

SEED = 2026
RNG = random.Random(SEED)


# ============================================================
# Utilidades base
# ============================================================

def clear_scene():
    """Elimina todo el contenido de la escena actual de forma segura."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.worlds,
    ):
        for datablock in list(collection):
            collection.remove(datablock)


def ensure_collection(name):
    """Crea/obtiene colección y la vincula a la escena si falta."""
    scene_col = bpy.context.scene.collection
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
    if col.name not in scene_col.children:
        scene_col.children.link(col)
    return col


def link_to_collection(obj, collection):
    """Mueve objeto a una colección concreta para mantener orden."""
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def make_mat(name, color, roughness=0.85, metallic=0.0, emission=0.0):
    """Material PBR básico con Principled BSDF."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    out = nodes.get("Material Output")

    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    if emission > 0:
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (*color, 1.0)
        emit.inputs["Strength"].default_value = emission
        mix = nodes.new("ShaderNodeMixShader")
        fres = nodes.new("ShaderNodeFresnel")
        fres.inputs[0].default_value = 1.2
        links.new(fres.outputs[0], mix.inputs[0])
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(emit.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs[0])

    return mat


def add_cube(name, location, scale=(1, 1, 1), material=None, collection=None, rotation=(0, 0, 0)):
    """Añade cubo voxel reutilizable."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale

    if material:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    if collection is not None:
        link_to_collection(obj, collection)

    return obj


def set_world_sky():
    """Configura cielo con gradiente y luz ambiental suave."""
    world = bpy.data.worlds.new("MinecraftSky")
    bpy.context.scene.world = world
    world.use_nodes = True

    ntree = world.node_tree
    nodes = ntree.nodes
    links = ntree.links

    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg_top = nodes.new("ShaderNodeBackground")
    bg_bottom = nodes.new("ShaderNodeBackground")
    mix = nodes.new("ShaderNodeMixShader")
    grad = nodes.new("ShaderNodeTexGradient")
    mapping = nodes.new("ShaderNodeMapping")
    texcoord = nodes.new("ShaderNodeTexCoord")
    ramp = nodes.new("ShaderNodeValToRGB")

    bg_top.inputs[0].default_value = (0.14, 0.65, 0.95, 1.0)
    bg_top.inputs[1].default_value = 1.0

    bg_bottom.inputs[0].default_value = (0.45, 0.80, 0.94, 1.0)
    bg_bottom.inputs[1].default_value = 0.8

    mapping.inputs["Rotation"].default_value = (radians(90), 0, 0)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.88

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[0])
    links.new(bg_bottom.outputs["Background"], mix.inputs[1])
    links.new(bg_top.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 180
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.film_transparent = False


# ============================================================
# Construcción procedural del escenario
# ============================================================

def terrain_height(x, y):
    """Perfil de altura de la isla superior."""
    r = (x * x * 0.72 + y * y * 0.95) ** 0.5
    noise = RNG.uniform(-0.28, 0.34)
    return max(1, int(5.6 - r * 0.44 + noise))


def build_island(mats, collection):
    """Isla flotante con topología gruesa y faldón inferior."""
    grass = mats["grass"]
    dirt = mats["dirt"]
    stone = mats["stone"]
    ore = mats["ore"]

    size = 11
    top_map = {}

    for x in range(-size, size + 1):
        for y in range(-size, size + 1):
            ellipse = (x / 10.8) ** 2 + (y / 8.8) ** 2
            if ellipse <= 1.0:
                h = terrain_height(x, y)
                top_map[(x, y)] = h

                add_cube(
                    f"grass_{x}_{y}",
                    location=(x, y, h),
                    scale=(0.5, 0.5, 0.5),
                    material=grass,
                    collection=collection,
                )

                depth_min = -5 - int((abs(x) + abs(y)) * 0.08)
                for z in range(h - 1, depth_min, -1):
                    mat = dirt if z > -2 else stone

                    # veta de mineral expuesta en lateral
                    if z < -2 and RNG.random() < 0.025 and (abs(x) > 7 or abs(y) > 7):
                        mat = ore

                    add_cube(
                        f"mass_{x}_{y}_{z}",
                        location=(x, y, z),
                        scale=(0.5, 0.5, 0.5),
                        material=mat,
                        collection=collection,
                    )

    return top_map


def build_water(top_map, mats, collection):
    """Canal de agua superficial y cascada lateral."""
    water = mats["water"]

    river_cells = [
        (-1, 4), (0, 4), (1, 4), (2, 3), (3, 2), (4, 1), (5, 0), (6, -1)
    ]

    for x, y in river_cells:
        if (x, y) in top_map:
            z = top_map[(x, y)] + 0.05
            add_cube(
                f"river_{x}_{y}",
                location=(x, y, z),
                scale=(0.5, 0.5, 0.15),
                material=water,
                collection=collection,
            )

    # Cascada por el borde
    start = (6, -1)
    if start in top_map:
        sx, sy = start
        top_z = top_map[start]
        for i in range(0, 9):
            add_cube(
                f"waterfall_{i}",
                location=(sx + 1.2, sy - 0.1, top_z - i * 0.9),
                scale=(0.35, 0.38, 0.42),
                material=water,
                collection=collection,
            )


def build_clouds(mats, collection):
    """Nubes con formas rotas tipo portada Minecraft."""
    cloud = mats["cloud"]

    cloud_shapes = [
        {
            "origin": Vector((-9.5, -7.5, 17.5)),
            "cells": [(-2, 0), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1), (2, 1)],
            "scale": (1.05, 0.75, 0.18),
        },
        {
            "origin": Vector((7.0, 9.8, 16.2)),
            "cells": [(-1, 0), (0, 0), (1, 0), (2, 0), (0, 1), (1, 1)],
            "scale": (1.15, 0.7, 0.2),
        },
        {
            "origin": Vector((-0.5, 13.6, 15.2)),
            "cells": [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1)],
            "scale": (1.1, 0.65, 0.18),
        },
    ]

    for idx, shape in enumerate(cloud_shapes):
        for cidx, (cx, cy) in enumerate(shape["cells"]):
            loc = shape["origin"] + Vector((cx * 1.1, cy * 0.85, RNG.uniform(-0.05, 0.05)))
            add_cube(
                f"cloud_{idx}_{cidx}",
                location=loc,
                scale=shape["scale"],
                material=cloud,
                collection=collection,
                rotation=(0, radians(RNG.uniform(-2.0, 2.0)), radians(RNG.uniform(-8.0, 8.0))),
            )


def place_ground_detail(top_map, mats, collection):
    """Hierba alta y flores para dar vida al plano superior."""
    flower_yellow = mats["flower_yellow"]
    flower_blue = mats["flower_blue"]
    tall_grass = mats["tall_grass"]

    cells = list(top_map.keys())
    RNG.shuffle(cells)

    for idx, (x, y) in enumerate(cells[:90]):
        z = top_map[(x, y)]
        r = RNG.random()

        if r < 0.14:
            add_cube(
                f"flower_y_{idx}",
                location=(x + RNG.uniform(-0.2, 0.2), y + RNG.uniform(-0.2, 0.2), z + 0.55),
                scale=(0.08, 0.08, 0.22),
                material=flower_yellow,
                collection=collection,
            )
        elif r < 0.22:
            add_cube(
                f"flower_b_{idx}",
                location=(x + RNG.uniform(-0.18, 0.18), y + RNG.uniform(-0.18, 0.18), z + 0.55),
                scale=(0.08, 0.08, 0.22),
                material=flower_blue,
                collection=collection,
            )
        elif r < 0.52:
            add_cube(
                f"grass_blade_{idx}",
                location=(x + RNG.uniform(-0.2, 0.2), y + RNG.uniform(-0.2, 0.2), z + 0.45),
                scale=(0.06, 0.06, 0.18 + RNG.uniform(-0.03, 0.04)),
                material=tall_grass,
                collection=collection,
            )


def build_tree_oak(mats, collection, base=(6.0, 1.4, 6.0)):
    """Árbol voxel clásico."""
    wood = mats["wood"]
    leaf = mats["leaf"]

    bx, by, bz = base

    for i in range(5):
        add_cube(
            f"oak_trunk_{i}",
            location=(bx, by, bz + i),
            scale=(0.5, 0.5, 0.5),
            material=wood,
            collection=collection,
        )

    for x in range(-2, 3):
        for y in range(-2, 3):
            for z in range(0, 3):
                cond = abs(x) + abs(y) + z < 6
                if cond and not (x == 0 and y == 0 and z < 2):
                    add_cube(
                        f"oak_leaf_{x}_{y}_{z}",
                        location=(bx + x, by + y, bz + 4 + z),
                        scale=(0.5, 0.5, 0.5),
                        material=leaf,
                        collection=collection,
                    )


def build_tree_cherry(mats, collection, base=(-6.8, -1.5, 6.1)):
    """Cerezo voxel para asemejar la portada moderna."""
    wood = mats["wood"]
    pink = mats["cherry_leaf"]

    bx, by, bz = base

    for i in range(5):
        add_cube(
            f"cherry_trunk_{i}",
            location=(bx, by, bz + i),
            scale=(0.5, 0.5, 0.5),
            material=wood,
            collection=collection,
        )

    # ramas secundarias
    branch_offsets = [(-1, 0, 3), (1, 0, 3), (0, 1, 2), (0, -1, 2)]
    for idx, (ox, oy, oz) in enumerate(branch_offsets):
        add_cube(
            f"ch_branch_{idx}",
            location=(bx + ox, by + oy, bz + oz),
            scale=(0.45, 0.45, 0.45),
            material=wood,
            collection=collection,
        )

    for x in range(-3, 4):
        for y in range(-3, 4):
            for z in range(0, 4):
                if (x * x + y * y + (z - 1.5) ** 2) < 10.5:
                    if RNG.random() > 0.08:
                        add_cube(
                            f"cherry_leaf_{x}_{y}_{z}",
                            location=(bx + x * 0.9, by + y * 0.9, bz + 4 + z * 0.72),
                            scale=(0.45, 0.45, 0.35),
                            material=pink,
                            collection=collection,
                        )


def build_character(name, mats, collection, origin=(0, 0, 6), palette=None, action_pose=True):
    """Personaje bípede tipo Minecraft con colorimetría configurable."""
    if palette is None:
        palette = {
            "skin": mats["skin"],
            "shirt": mats["steve_shirt"],
            "pants": mats["steve_pants"],
            "hair": mats["steve_hair"],
            "boots": mats["boots"],
        }

    ox, oy, oz = origin

    # Piernas
    leg_l = add_cube(
        f"{name}_leg_l",
        (ox - 0.33, oy, oz),
        (0.21, 0.21, 0.68),
        palette["pants"],
        collection=collection,
    )
    leg_r = add_cube(
        f"{name}_leg_r",
        (ox + 0.33, oy, oz),
        (0.21, 0.21, 0.68),
        palette["pants"],
        collection=collection,
    )

    add_cube(
        f"{name}_boot_l",
        (ox - 0.33, oy + 0.02, oz - 0.55),
        (0.21, 0.24, 0.12),
        palette["boots"],
        collection=collection,
    )
    add_cube(
        f"{name}_boot_r",
        (ox + 0.33, oy + 0.02, oz - 0.55),
        (0.21, 0.24, 0.12),
        palette["boots"],
        collection=collection,
    )

    torso = add_cube(
        f"{name}_torso",
        (ox, oy, oz + 1.08),
        (0.55, 0.32, 0.60),
        palette["shirt"],
        collection=collection,
    )

    arm_l = add_cube(
        f"{name}_arm_l",
        (ox - 0.82, oy, oz + 1.06),
        (0.19, 0.19, 0.60),
        palette["skin"],
        collection=collection,
    )
    arm_r = add_cube(
        f"{name}_arm_r",
        (ox + 0.82, oy, oz + 1.06),
        (0.19, 0.19, 0.60),
        palette["skin"],
        collection=collection,
    )

    head = add_cube(
        f"{name}_head",
        (ox, oy, oz + 2.02),
        (0.42, 0.42, 0.42),
        palette["skin"],
        collection=collection,
    )
    add_cube(
        f"{name}_hair",
        (ox, oy, oz + 2.30),
        (0.44, 0.44, 0.17),
        palette["hair"],
        collection=collection,
    )

    # Pose
    if action_pose:
        arm_l.rotation_euler = (radians(5), radians(18), radians(4))
        arm_r.rotation_euler = (radians(-10), radians(-45), radians(-2))
        leg_l.rotation_euler = (radians(0), radians(16), radians(0))
        leg_r.rotation_euler = (radians(0), radians(-14), radians(0))
        torso.rotation_euler = (radians(0), radians(5), radians(0))
        head.rotation_euler = (radians(0), radians(8), radians(0))

    return {
        "head": head,
        "arm_l": arm_l,
        "arm_r": arm_r,
        "torso": torso,
    }


def build_pickaxe(mats, collection, origin=(0.35, -0.5, 7.6), yaw_deg=-35):
    """Pico cúbico simple para mano de Steve."""
    wood = mats["wood"]
    iron = mats["iron"]

    ox, oy, oz = origin

    # Mango
    for i in range(4):
        add_cube(
            f"pick_handle_{i}",
            (ox + i * 0.18, oy - i * 0.16, oz + i * 0.15),
            (0.09, 0.09, 0.18),
            wood,
            collection=collection,
            rotation=(0, 0, radians(yaw_deg)),
        )

    # Cabeza del pico
    head_offsets = [(-0.2, 0.1, 0.32), (0.0, 0.0, 0.38), (0.2, -0.1, 0.32), (0.35, -0.22, 0.24)]
    for idx, (dx, dy, dz) in enumerate(head_offsets):
        add_cube(
            f"pick_head_{idx}",
            (ox + 0.55 + dx, oy - 0.5 + dy, oz + 0.52 + dz),
            (0.14, 0.14, 0.14),
            iron,
            collection=collection,
            rotation=(radians(8), 0, radians(yaw_deg)),
        )


def build_sheep(mats, collection, origin=(8.2, -3.8, 5.7)):
    """Oveja voxel lateral derecha."""
    wool = mats["wool"]
    dark = mats["dark"]
    skin = mats["skin"]

    ox, oy, oz = origin

    add_cube("sheep_body", (ox, oy, oz + 0.5), (0.68, 0.45, 0.42), wool, collection=collection)
    add_cube("sheep_head", (ox + 0.85, oy + 0.02, oz + 0.47), (0.27, 0.25, 0.25), skin, collection=collection)
    add_cube("sheep_nose", (ox + 1.08, oy + 0.02, oz + 0.42), (0.09, 0.08, 0.07), dark, collection=collection)

    for i, dx in enumerate([-0.33, 0.33]):
        for j, dy in enumerate([-0.2, 0.2]):
            add_cube(
                f"sheep_leg_{i}_{j}",
                (ox + dx, oy + dy, oz - 0.12),
                (0.1, 0.1, 0.28),
                dark,
                collection=collection,
            )


def build_fox(mats, collection, origin=(-1.7, 2.2, 8.2)):
    """Zorro simplificado en el fondo para acercarse a la composición original."""
    orange = mats["fox_orange"]
    white = mats["fox_white"]
    dark = mats["dark"]

    ox, oy, oz = origin

    add_cube("fox_body", (ox, oy, oz), (0.35, 0.18, 0.18), orange, collection=collection)
    add_cube("fox_head", (ox + 0.45, oy + 0.02, oz + 0.03), (0.18, 0.16, 0.16), orange, collection=collection)
    add_cube("fox_muzzle", (ox + 0.63, oy + 0.02, oz - 0.02), (0.08, 0.08, 0.06), white, collection=collection)
    add_cube("fox_tail", (ox - 0.45, oy - 0.05, oz + 0.04), (0.25, 0.12, 0.12), orange, collection=collection)
    add_cube("fox_tail_tip", (ox - 0.63, oy - 0.05, oz + 0.04), (0.08, 0.08, 0.08), white, collection=collection)

    for idx, dx in enumerate([-0.16, 0.16]):
        for idy, dy in enumerate([-0.08, 0.08]):
            add_cube(
                f"fox_leg_{idx}_{idy}",
                (ox + dx, oy + dy, oz - 0.22),
                (0.06, 0.06, 0.12),
                dark,
                collection=collection,
            )


def build_logo(mats, collection):
    """Logo 3D con relieve y sombra trasera para look portada."""
    logo_mat = mats["logo"]
    logo_dark = mats["logo_shadow"]

    bpy.ops.object.text_add(location=(0.0, -5.95, 17.1), rotation=(radians(88.4), 0, 0))
    txt = bpy.context.active_object
    txt.name = "MinecraftLogo"

    txt.data.body = "MINECRAFT"
    txt.data.extrude = 0.40
    txt.data.bevel_depth = 0.03
    txt.data.bevel_resolution = 2
    txt.data.align_x = 'CENTER'
    txt.data.space_character = 1.02

    if txt.data.materials:
        txt.data.materials[0] = logo_mat
    else:
        txt.data.materials.append(logo_mat)

    link_to_collection(txt, collection)

    bpy.ops.object.duplicate()
    shadow = bpy.context.active_object
    shadow.name = "MinecraftLogoShadow"
    shadow.location += Vector((0.45, -0.35, -0.52))
    shadow.data = txt.data.copy()
    shadow.data.materials.clear()
    shadow.data.materials.append(logo_dark)
    link_to_collection(shadow, collection)


# ============================================================
# Cámara, luces y post
# ============================================================

def setup_camera():
    bpy.ops.object.camera_add(location=(0.1, -22.0, 10.8), rotation=(radians(73), 0, radians(0.9)))
    cam = bpy.context.active_object
    cam.data.lens = 27
    cam.data.sensor_width = 36
    cam.data.dof.use_dof = False
    bpy.context.scene.camera = cam
    return cam


def setup_lights():
    # Luz principal
    bpy.ops.object.light_add(type='SUN', location=(7.5, -11.0, 25.0))
    sun = bpy.context.active_object
    sun.name = "SunKey"
    sun.data.energy = 4.6
    sun.rotation_euler = (radians(36), radians(10), radians(31))

    # Relleno azul suave
    bpy.ops.object.light_add(type='AREA', location=(-13.0, -8.5, 13.5))
    fill = bpy.context.active_object
    fill.name = "FillBlue"
    fill.data.energy = 320
    fill.data.size = 16
    fill.data.color = (0.67, 0.85, 1.0)

    # Contraluz cálida
    bpy.ops.object.light_add(type='AREA', location=(13.5, 11.0, 16.0))
    rim = bpy.context.active_object
    rim.name = "RimWarm"
    rim.data.energy = 260
    rim.data.size = 11
    rim.data.color = (1.0, 0.82, 0.65)


def setup_color_management():
    scene = bpy.context.scene
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = 0.45
    scene.view_settings.gamma = 0.98


# ============================================================
# MAIN
# ============================================================

def main():
    clear_scene()
    set_world_sky()
    setup_render()
    setup_color_management()

    # Colecciones
    col_env = ensure_collection("ENV")
    col_chars = ensure_collection("CHARACTERS")
    col_fx = ensure_collection("DETAILS")
    col_logo = ensure_collection("LOGO")

    # Materiales
    mats = {
        "grass": make_mat("Grass", (0.25, 0.84, 0.24), roughness=0.92),
        "tall_grass": make_mat("TallGrass", (0.18, 0.70, 0.15), roughness=0.95),
        "dirt": make_mat("Dirt", (0.69, 0.49, 0.23), roughness=0.95),
        "stone": make_mat("Stone", (0.49, 0.49, 0.52), roughness=0.88),
        "ore": make_mat("Ore", (0.73, 0.63, 0.50), roughness=0.72, metallic=0.08),
        "water": make_mat("Water", (0.19, 0.62, 0.94), roughness=0.18, metallic=0.0, emission=0.04),
        "wood": make_mat("Wood", (0.54, 0.33, 0.14), roughness=0.87),
        "leaf": make_mat("Leaf", (0.22, 0.67, 0.24), roughness=0.94),
        "cherry_leaf": make_mat("CherryLeaf", (0.97, 0.63, 0.78), roughness=0.92),
        "skin": make_mat("Skin", (0.95, 0.73, 0.56), roughness=0.7),
        "boots": make_mat("Boots", (0.24, 0.23, 0.22), roughness=0.92),
        "steve_shirt": make_mat("SteveShirt", (0.09, 0.54, 0.75), roughness=0.73),
        "steve_pants": make_mat("StevePants", (0.28, 0.24, 0.78), roughness=0.76),
        "steve_hair": make_mat("SteveHair", (0.32, 0.18, 0.09), roughness=0.82),
        "alex_shirt": make_mat("AlexShirt", (0.35, 0.74, 0.34), roughness=0.73),
        "alex_pants": make_mat("AlexPants", (0.43, 0.28, 0.15), roughness=0.75),
        "alex_hair": make_mat("AlexHair", (0.96, 0.56, 0.22), roughness=0.8),
        "wool": make_mat("Wool", (0.92, 0.92, 0.92), roughness=0.95),
        "dark": make_mat("Dark", (0.30, 0.30, 0.30), roughness=0.88),
        "fox_orange": make_mat("FoxOrange", (0.87, 0.44, 0.15), roughness=0.88),
        "fox_white": make_mat("FoxWhite", (0.93, 0.93, 0.89), roughness=0.9),
        "iron": make_mat("Iron", (0.78, 0.83, 0.90), roughness=0.28, metallic=0.55),
        "cloud": make_mat("Cloud", (0.90, 0.96, 1.0), roughness=1.0),
        "flower_yellow": make_mat("FlowerYellow", (0.98, 0.85, 0.17), roughness=0.72, emission=0.03),
        "flower_blue": make_mat("FlowerBlue", (0.34, 0.63, 0.98), roughness=0.72, emission=0.02),
        "logo": make_mat("Logo", (0.78, 0.78, 0.78), roughness=0.36, metallic=0.06),
        "logo_shadow": make_mat("LogoShadow", (0.07, 0.07, 0.07), roughness=0.72),
    }

    # Escenario
    top_map = build_island(mats, col_env)
    build_water(top_map, mats, col_env)
    build_clouds(mats, col_env)
    place_ground_detail(top_map, mats, col_fx)
    build_tree_oak(mats, col_env)
    build_tree_cherry(mats, col_env)

    # Personajes
    steve_palette = {
        "skin": mats["skin"],
        "shirt": mats["steve_shirt"],
        "pants": mats["steve_pants"],
        "hair": mats["steve_hair"],
        "boots": mats["boots"],
    }
    alex_palette = {
        "skin": mats["skin"],
        "shirt": mats["alex_shirt"],
        "pants": mats["alex_pants"],
        "hair": mats["alex_hair"],
        "boots": mats["boots"],
    }

    build_character("Steve", mats, col_chars, origin=(-0.35, -0.55, 6.05), palette=steve_palette, action_pose=True)
    build_character("Alex", mats, col_chars, origin=(-1.95, 0.20, 6.0), palette=alex_palette, action_pose=True)

    # Props y fauna
    build_pickaxe(mats, col_chars, origin=(0.35, -0.45, 7.45))
    build_sheep(mats, col_chars)
    build_fox(mats, col_chars)

    # Logo
    build_logo(mats, col_logo)

    # Cámara e iluminación
    setup_camera()
    setup_lights()


if __name__ == "__main__":
    main()
