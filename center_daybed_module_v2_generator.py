from collections import Counter
from pathlib import Path
import csv
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
BLEND_PATH = ROOT / "center_daybed_module_v2.blend"
CUTLIST_PATH = ROOT / "center_daybed_module_v2_cutlist.csv"
DIMENSIONS_PATH = ROOT / "center_daybed_module_v2_dimensions.txt"
EPSILON = 1e-6

UPPER_MEMBER_X = (-27.75, -13.875, 0.0, 13.875, 27.75)
LOWER_MEMBER_X = (-27.75, -9.25, 9.25, 27.75)
POST_X = UPPER_MEMBER_X
POST_ROWS = (("REAR", 1.75), ("FRONT", 27.25))

COLLECTION_NAMES = (
    "ROOM_REFERENCE",
    "UPPER_FRAME_FLAT_2X4",
    "LOWER_FRAME_FLAT_2X4",
    "VERTICAL_POSTS",
    "PLYWOOD_DECK",
    "FRONT_PANEL_NAILERS",
    "MAPLE_FINISH",
    "DIMENSIONS",
    "CAMERAS",
)

CUTLIST_ROWS = (
    ("UPPER_FRONT_REAR_RAILS", "59", 2, "2x4"),
    ("LOWER_FRONT_REAR_RAILS", "59", 2, "2x4"),
    ("UPPER_OUTSIDE_SIDE_MEMBERS", "24.5", 2, "2x4"),
    ("UPPER_INTERIOR_CROSSMEMBERS", "24.5", 3, "2x4"),
    ("LOWER_OUTSIDE_SIDE_MEMBERS", "22", 2, "2x4"),
    ("LOWER_INTERIOR_CROSSMEMBERS", "22", 2, "2x4"),
    ("VERTICAL_POSTS", "6.75", 10, "2x4"),
)

FRAME_JOINT_NOTE = (
    "FRAME 90-DEGREE JOINTS:\n"
    "Flat 2x4 frame: use approximately 5 to 5-1/8 in structural wood screws\n"
    "through the 3.5 in-deep front/rear rail into the member end.\n"
    "Use two screws per joint where practical. Predrill."
)

POST_CONNECTION_NOTE = (
    "POST CONNECTIONS:\n"
    "Use approximately 3 to 3-1/8 in structural wood screws through the\n"
    "1.5 in-thick flat upper/lower frame into each vertical post.\n"
    "Primary top fastening for front posts passes through the upper front-to-back member\n"
    "into the post, not through the upper front rail near its rear edge.\n"
    "Wood glue may supplement both connection types.\n"
    "Do not use drywall screws. Metal angle brackets are not required."
)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def configure_scene():
    scene = bpy.context.scene
    scene.name = "CENTER_DAYBED_MODULE_V2"
    scene.unit_settings.system = "IMPERIAL"
    scene.unit_settings.length_unit = "INCHES"
    scene.unit_settings.scale_length = 0.0254
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = False
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.72, 0.72, 0.72)
    scene["coordinate_system"] = "X left/right, Y rear/front, Z vertical"
    scene["units"] = "inches"
    scene["module_scope"] = "CENTER MODULE V2 ONLY"
    scene["frame_orientation"] = "2x4 lumber laid flat; Z thickness 1.5in"
    return scene


def make_collections():
    collections = {}
    for name in COLLECTION_NAMES:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection
    return collections


def add_material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    return material


def make_materials():
    return {
        "framing": add_material("V2_NATURAL_FRAMING_LUMBER", (0.70, 0.47, 0.25)),
        "maple": add_material("V2_LIGHT_NATURAL_MAPLE", (0.88, 0.72, 0.48)),
        "nailer": add_material("V2_NAILER_PLYWOOD", (0.73, 0.52, 0.29)),
        "wall": add_material("V2_OFF_WHITE_WALL", (0.88, 0.87, 0.82)),
        "floor": add_material("V2_NEUTRAL_WOOD_FLOOR", (0.34, 0.22, 0.12)),
        "dimension": add_material("V2_DIMENSION_DARK", (0.025, 0.025, 0.025)),
    }


def move_to_collection(obj, collection):
    for owner in tuple(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def add_box(name, size, center, collection, material, **props):
    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    obj["dimensions_in"] = " x ".join(f"{value:g}" for value in size)
    for key, value in props.items():
        obj[key] = value
    return obj


def add_structural_piece(name, size, center, collection, material, cut_length, purpose, group):
    return add_box(
        name,
        size,
        center,
        collection,
        material,
        stock="2x4 actual 1.5in x 3.5in",
        cut_length_in=cut_length,
        purpose=purpose,
        validation_group=group,
        structural=True,
    )


def build_upper_frame(collection, material):
    upper = [
        add_structural_piece(
            "UPPER_REAR_RAIL_FLAT_59x3.5x1.5_CUT_59in",
            (59, 3.5, 1.5), (0, 1.75, 9), collection, material,
            59, "UPPER_REAR_RAIL", "upper_rail",
        ),
        add_structural_piece(
            "UPPER_FRONT_RAIL_FLAT_59x3.5x1.5_CUT_59in",
            (59, 3.5, 1.5), (0, 29.75, 9), collection, material,
            59, "UPPER_FRONT_RAIL", "upper_rail",
        ),
    ]
    members = (
        ("UPPER_LEFT_OUTSIDE_MEMBER_FLAT_3.5x24.5x1.5_CUT_24.5in", "UPPER_OUTSIDE_SIDE_MEMBER", "upper_outside"),
        ("UPPER_INTERIOR_CROSSMEMBER_FLAT_3.5x24.5x1.5_CUT_24.5in_01", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        ("UPPER_CENTER_CROSSMEMBER_FLAT_3.5x24.5x1.5_CUT_24.5in", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        ("UPPER_INTERIOR_CROSSMEMBER_FLAT_3.5x24.5x1.5_CUT_24.5in_02", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        ("UPPER_RIGHT_OUTSIDE_MEMBER_FLAT_3.5x24.5x1.5_CUT_24.5in", "UPPER_OUTSIDE_SIDE_MEMBER", "upper_outside"),
    )
    for x, (name, purpose, group) in zip(UPPER_MEMBER_X, members):
        obj = add_structural_piece(
            name, (3.5, 24.5, 1.5), (x, 15.75, 9), collection, material,
            24.5, purpose, group,
        )
        obj["x_centerline_in"] = x
        upper.append(obj)
    return upper


def build_lower_frame(collection, material):
    lower = [
        add_structural_piece(
            "LOWER_REAR_RAIL_FLAT_59x3.5x1.5_CUT_59in",
            (59, 3.5, 1.5), (0, 1.75, 0.75), collection, material,
            59, "LOWER_REAR_RAIL", "lower_rail",
        ),
        add_structural_piece(
            "LOWER_FRONT_RAIL_FLAT_59x3.5x1.5_CUT_59in",
            (59, 3.5, 1.5), (0, 27.25, 0.75), collection, material,
            59, "LOWER_FRONT_RAIL", "lower_rail",
        ),
    ]
    members = (
        ("LOWER_LEFT_OUTSIDE_MEMBER_FLAT_3.5x22x1.5_CUT_22in", "LOWER_OUTSIDE_SIDE_MEMBER", "lower_outside"),
        ("LOWER_INTERIOR_CROSSMEMBER_FLAT_3.5x22x1.5_CUT_22in_01", "LOWER_INTERIOR_CROSSMEMBER", "lower_interior"),
        ("LOWER_INTERIOR_CROSSMEMBER_FLAT_3.5x22x1.5_CUT_22in_02", "LOWER_INTERIOR_CROSSMEMBER", "lower_interior"),
        ("LOWER_RIGHT_OUTSIDE_MEMBER_FLAT_3.5x22x1.5_CUT_22in", "LOWER_OUTSIDE_SIDE_MEMBER", "lower_outside"),
    )
    for x, (name, purpose, group) in zip(LOWER_MEMBER_X, members):
        obj = add_structural_piece(
            name, (3.5, 22, 1.5), (x, 14.5, 0.75), collection, material,
            22, purpose, group,
        )
        obj["x_centerline_in"] = x
        lower.append(obj)
    return lower


def build_posts(collection, material):
    posts = []
    for row, y in POST_ROWS:
        for index, x in enumerate(POST_X, 1):
            position = "CENTER_X0in" if x == 0 else f"X{x:+g}in"
            size = (3.5, 1.5, 6.75) if row == "REAR" else (1.5, 3.5, 6.75)
            size_label = "3.5x1.5x6.75" if row == "REAR" else "1.5x3.5x6.75"
            post = add_structural_piece(
                f"POST_{row}_{position}_{size_label}_CUT_6.75in_{index:02d}",
                size, (x, y, 4.875), collection, material,
                6.75, f"{row}_VERTICAL_POST", "post",
            )
            post["post_row"] = row
            post["x_centerline_in"] = x
            if row == "FRONT":
                post["primary_top_fastening"] = "through upper front-to-back member into post"
            posts.append(post)
    return posts


def build_finish(collections, materials):
    deck = add_box(
        "CENTER_DECK_0.75_MAPLE", (60, 32, 0.75), (0, 15.5, 10.125),
        collections["PLYWOOD_DECK"], materials["maple"],
        stock="3/4in maple plywood", purpose="CENTER_DECK",
    )
    panel = add_box(
        "CENTER_FRONT_PANEL_0.5_MAPLE", (60, 0.5, 7.5), (0, 31.75, 6.75),
        collections["MAPLE_FINISH"], materials["maple"],
        stock="nominal 1/2in maple plywood", purpose="FRONT_FINISH_PANEL",
        approximate_width=True,
    )
    lower_nailer = add_box(
        "FRONT_PANEL_LOWER_NAILER_APPROX_59x2.5x0.75",
        (59, 2.5, 0.75), (0, 30.25, 3.875),
        collections["FRONT_PANEL_NAILERS"], materials["nailer"],
        stock="nominal 1x3", purpose="PANEL_LOWER_EDGE_NAILER",
        structural=False, approximate=True,
    )
    vertical_nailers = []
    for index, x in enumerate(UPPER_MEMBER_X, 1):
        vertical_nailers.append(add_box(
            f"FRONT_PANEL_VERTICAL_NAILER_APPROX_2.5x0.75x4_{index:02d}",
            (2.5, 0.75, 4), (x, 31.125, 6.25),
            collections["FRONT_PANEL_NAILERS"], materials["nailer"],
            stock="3/4in plywood strip", purpose="PANEL_VERTICAL_NAILER",
            structural=False, approximate=True,
        ))
    return deck, panel, [lower_nailer, *vertical_nailers]


def build_room_reference(collection, materials):
    add_box(
        "V2_FLOOR_REFERENCE_APPROX", (84, 60, 0.5), (0, 22, -0.25),
        collection, materials["floor"], purpose="FLOOR_REFERENCE", approximate=True,
    )
    add_box(
        "V2_CENTER_WALL_REFERENCE_60in_WIDE", (60, 0.5, 48), (0, -0.25, 24),
        collection, materials["wall"], purpose="60IN_FLAT_ARCHITECTURAL_AREA",
        approximate_height_and_thickness=True,
    )
    add_box(
        "V2_WINDOW_SILL_REFERENCE_UNDERSIDE_APPROX_15in", (60, 1, 1), (0, -0.25, 15.5),
        collection, materials["maple"], purpose="WINDOW_SILL_REFERENCE",
        underside_elevation_in=15.0, approximate=True,
    )


def add_text(name, body, location, rotation, collection, material, size=0.75, flip_x=False):
    data = bpy.data.curves.new(f"{name}_DATA", "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.size = size
    data.space_line = 1.2
    data.extrude = 0.01
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = rotation
    if flip_x:
        obj.scale.x = -1
    obj.show_in_front = True
    collection.objects.link(obj)
    return obj


def add_polyline(name, segments, collection, material):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.035
    curve.bevel_resolution = 0
    for start, end in segments:
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.show_in_front = True
    curve.materials.append(material)
    collection.objects.link(obj)
    return obj


def add_dimension(name, start, end, label, offset, plane, collection, material):
    start, end, offset = Vector(start), Vector(end), Vector(offset)
    dimension_start, dimension_end = start + offset, end + offset
    add_polyline(
        name,
        ((start, dimension_start), (dimension_start, dimension_end), (end, dimension_end)),
        collection,
        material,
    )
    rotations = {
        "TOP": (0, 0, math.pi / 2),
        "FRONT": (math.pi / 2, 0, 0),
        "SIDE": (math.pi / 2, 0, math.pi / 2),
    }
    return add_text(
        f"{name}_TEXT", label, (dimension_start + dimension_end) / 2,
        rotations[plane], collection, material, 0.9, plane == "FRONT",
    )


def build_dimensions_and_notes(collection, material):
    dimensions = (
        ("DIM_V2_ARCHITECTURAL_WIDTH_60in", (-30, 0, 15), (30, 0, 15), '60" ARCHITECTURAL FLAT AREA', (0, 0.05, 2), "FRONT"),
        ("DIM_V2_STRUCTURAL_WIDTH_59in", (-29.5, 31.5, 9.75), (29.5, 31.5, 9.75), '59" STRUCTURAL FRAME', (0, 2, 2), "FRONT"),
        ("DIM_V2_UPPER_DEPTH_31.5in", (-29.5, 0, 10.5), (-29.5, 31.5, 10.5), '31.5" UPPER DEPTH', (-3, 0, 0), "TOP"),
        ("DIM_V2_LOWER_DEPTH_29in", (29.5, 0, 1.5), (29.5, 29, 1.5), '29" LOWER DEPTH', (3, 0, 0), "TOP"),
        ("DIM_V2_FRONT_RECESS_2.5in", (29.5, 29, 5), (29.5, 31.5, 5), '2.5" RECESS', (3, 0, 0), "TOP"),
        ("DIM_V2_FLAT_FRAME_HEIGHT_1.5in", (29.5, 29.75, 8.25), (29.5, 29.75, 9.75), '1.5" FLAT FRAME', (3, 0, 0), "SIDE"),
        ("DIM_V2_POST_HEIGHT_6.75in", (29.5, 27.25, 1.5), (29.5, 27.25, 8.25), '6.75" POST', (3, 0, 0), "SIDE"),
        ("DIM_V2_UPPER_BOTTOM_8.25in", (-29.5, 31.5, 0), (-29.5, 31.5, 8.25), '8.25" UPPER BOTTOM', (-3, 0, 0), "FRONT"),
        ("DIM_V2_UPPER_TOP_9.75in", (-29.5, 31.5, 0), (-29.5, 31.5, 9.75), '9.75" UPPER TOP', (-6, 0, 0), "FRONT"),
        ("DIM_V2_DECK_TOP_10.5in", (29.5, 32, 0), (29.5, 32, 10.5), '10.5" DECK TOP', (6, 0, 0), "FRONT"),
        ("DIM_V2_SILL_UNDERSIDE_APPROX_15in", (30, 0, 0), (30, 0, 15), '~15" SILL UNDERSIDE', (6, 0.05, 0), "FRONT"),
    )
    for args in dimensions:
        add_dimension(*args, collection, material)

    note_rotation = (math.pi / 2, 0, 0)
    first = add_text(
        "V2_CONSTRUCTION_NOTE_FRAME_JOINTS", FRAME_JOINT_NOTE,
        (0, 0.05, 29), note_rotation, collection, material, 0.65, True,
    )
    second = add_text(
        "V2_CONSTRUCTION_NOTE_POST_CONNECTIONS", POST_CONNECTION_NOTE,
        (0, 0.05, 23), note_rotation, collection, material, 0.65, True,
    )
    first["construction_note"] = True
    second["construction_note"] = True


def add_camera(name, location, target, collection, orthographic=False, scale=1):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO" if orthographic else "PERSP"
    data.ortho_scale = scale
    data.lens = 52
    data.clip_start = 0.1
    data.clip_end = 1000
    camera = bpy.data.objects.new(name, data)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(camera)
    return camera


def build_cameras(collection):
    cameras = {
        "TOP_ORTHO": add_camera("TOP_ORTHO", (0, 15.5, 100), (0, 15.5, 0), collection, True, 50),
        "FRONT": add_camera("FRONT", (0, 100, 11), (0, 15, 8), collection, True, 52),
        "SIDE": add_camera("SIDE", (90, 15.5, 11), (0, 15.5, 8), collection, True, 36),
        "ISOMETRIC_FRAMING": add_camera("ISOMETRIC_FRAMING", (85, 95, 30), (0, 14, 5), collection),
        "ISOMETRIC_FINISHED": add_camera("ISOMETRIC_FINISHED", (70, 80, 50), (0, 15, 6), collection),
    }
    cameras["ISOMETRIC_FRAMING"]["intended_view_layer"] = "FRAMING"
    cameras["ISOMETRIC_FINISHED"]["intended_view_layer"] = "FINISHED"
    return cameras


def configure_view_layers():
    scene = bpy.context.scene
    finished = scene.view_layers[0]
    finished.name = "FINISHED"
    dimensioned = scene.view_layers.new("DIMENSIONED")
    framing = scene.view_layers.new("FRAMING")
    finished.layer_collection.children["DIMENSIONS"].exclude = True
    for name in ("PLYWOOD_DECK", "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "DIMENSIONS"):
        framing.layer_collection.children[name].exclude = True
    scene["dimension_view_layer"] = dimensioned.name


def bounds(obj):
    half = obj.dimensions / 2
    return (
        obj.location.x - half.x,
        obj.location.x + half.x,
        obj.location.y - half.y,
        obj.location.y + half.y,
        obj.location.z - half.z,
        obj.location.z + half.z,
    )


def union_bounds(objects):
    boxes = [bounds(obj) for obj in objects]
    return tuple(round(value, 6) for value in (
        min(box[0] for box in boxes), max(box[1] for box in boxes),
        min(box[2] for box in boxes), max(box[3] for box in boxes),
        min(box[4] for box in boxes), max(box[5] for box in boxes),
    ))


def dimensions(obj):
    return tuple(round(value, 6) for value in obj.dimensions)


def xy_contains(support, load):
    outer, inner = bounds(support), bounds(load)
    return (
        outer[0] <= inner[0] + EPSILON and outer[1] >= inner[1] - EPSILON
        and outer[2] <= inner[2] + EPSILON and outer[3] >= inner[3] - EPSILON
    )


def xy_overlaps(first, second):
    a, b = bounds(first), bounds(second)
    return (
        min(a[1], b[1]) - max(a[0], b[0]) > EPSILON
        and min(a[3], b[3]) - max(a[2], b[2]) > EPSILON
    )


def positive_volume_overlap(first, second):
    a, b = bounds(first), bounds(second)
    return all(
        min(a[maximum], b[maximum]) - max(a[minimum], b[minimum]) > EPSILON
        for minimum, maximum in ((0, 1), (2, 3), (4, 5))
    )


def validate_scene(upper, lower, posts, deck, panel, nailers):
    upper_bounds = union_bounds(upper)
    lower_bounds = union_bounds(lower)
    post_bounds = union_bounds(posts)
    deck_bounds = union_bounds([deck])
    assert upper_bounds == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75), upper_bounds
    assert lower_bounds == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5), lower_bounds
    assert post_bounds[4:] == (1.5, 8.25), post_bounds
    assert deck_bounds[4:] == (9.75, 10.5), deck_bounds
    assert upper_bounds[2] == lower_bounds[2] == 0.0
    assert round(upper_bounds[3] - lower_bounds[3], 6) == 2.5

    structural = upper + lower + posts
    groups = Counter(obj["validation_group"] for obj in structural)
    assert groups == Counter({
        "upper_rail": 2,
        "upper_outside": 2,
        "upper_interior": 3,
        "lower_rail": 2,
        "lower_outside": 2,
        "lower_interior": 2,
        "post": 10,
    }), groups
    assert groups["upper_outside"] + groups["upper_interior"] == 5
    assert groups["lower_outside"] + groups["lower_interior"] == 4

    upper_rails = [obj for obj in upper if obj["validation_group"] == "upper_rail"]
    upper_members = [obj for obj in upper if obj["validation_group"] in {"upper_outside", "upper_interior"}]
    lower_rails = [obj for obj in lower if obj["validation_group"] == "lower_rail"]
    lower_members = [obj for obj in lower if obj["validation_group"] in {"lower_outside", "lower_interior"}]
    assert all(dimensions(obj) == (59.0, 3.5, 1.5) and obj["cut_length_in"] == 59 for obj in upper_rails + lower_rails)
    assert all(dimensions(obj) == (3.5, 24.5, 1.5) and obj["cut_length_in"] == 24.5 for obj in upper_members)
    assert all(dimensions(obj) == (3.5, 22.0, 1.5) and obj["cut_length_in"] == 22 for obj in lower_members)
    rear_posts = [obj for obj in posts if obj["post_row"] == "REAR"]
    front_posts = [obj for obj in posts if obj["post_row"] == "FRONT"]
    assert all(dimensions(obj) == (3.5, 1.5, 6.75) and obj["cut_length_in"] == 6.75 for obj in rear_posts)
    assert all(dimensions(obj) == (1.5, 3.5, 6.75) and obj["cut_length_in"] == 6.75 for obj in front_posts)

    for row, expected_y in POST_ROWS:
        row_posts = [obj for obj in posts if obj["post_row"] == row]
        assert len(row_posts) == 5
        assert sorted(round(obj.location.x, 3) for obj in row_posts) == list(POST_X)
        assert all(abs(obj.location.y - expected_y) <= EPSILON for obj in row_posts)
    assert post_bounds[0] >= -29.5 - EPSILON and post_bounds[1] <= 29.5 + EPSILON

    lower_rear = next(obj for obj in lower_rails if obj["purpose"] == "LOWER_REAR_RAIL")
    lower_front = next(obj for obj in lower_rails if obj["purpose"] == "LOWER_FRONT_RAIL")
    upper_rear = next(obj for obj in upper_rails if obj["purpose"] == "UPPER_REAR_RAIL")
    upper_front = next(obj for obj in upper_rails if obj["purpose"] == "UPPER_FRONT_RAIL")
    for post in posts:
        post_box = bounds(post)
        lower_support = lower_rear if post["post_row"] == "REAR" else lower_front
        assert abs(bounds(lower_support)[5] - post_box[4]) <= EPSILON
        assert xy_contains(lower_support, post), f"Post lacks full lower bearing: {post.name}"
        if post["post_row"] == "REAR":
            assert abs(post_box[5] - bounds(upper_rear)[4]) <= EPSILON
            assert xy_contains(upper_rear, post), f"Rear post lacks upper rail bearing: {post.name}"
        else:
            assert tuple(round(value, 6) for value in post_box[2:4]) == (25.5, 29.0)
            contacts = [
                member for member in upper_members
                if abs(post_box[5] - bounds(member)[4]) <= EPSILON
                and bounds(member)[0] <= post_box[0] + EPSILON
                and bounds(member)[1] >= post_box[1] - EPSILON
                and abs(min(post_box[3], bounds(member)[3]) - max(post_box[2], bounds(member)[2]) - 2.5) <= EPSILON
            ]
            assert len(contacts) == 1, (post.name, [member.name for member in contacts])
            upper_front_box = bounds(upper_front)
            assert upper_front_box[0] <= post_box[0] + EPSILON and upper_front_box[1] >= post_box[1] - EPSILON
            front_rail_bearing = min(post_box[3], upper_front_box[3]) - max(post_box[2], upper_front_box[2])
            assert abs(front_rail_bearing - 1.0) <= EPSILON, (post.name, front_rail_bearing)
            assert post["primary_top_fastening"] == "through upper front-to-back member into post"

    overlaps = [
        (first.name, second.name)
        for index, first in enumerate(structural)
        for second in structural[index + 1:]
        if positive_volume_overlap(first, second)
    ]
    assert not overlaps, f"Impossible structural overlaps: {overlaps}"

    cut_totals = Counter(round(float(obj["cut_length_in"]), 3) for obj in structural)
    assert cut_totals == Counter({59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}), cut_totals
    assert len(structural) == 23

    lower_nailer = next(obj for obj in nailers if obj["purpose"] == "PANEL_LOWER_EDGE_NAILER")
    vertical_nailers = [obj for obj in nailers if obj["purpose"] == "PANEL_VERTICAL_NAILER"]
    assert len(vertical_nailers) == 5
    assert bounds(lower_nailer)[2:] == (29.0, 31.5, 3.5, 4.25)
    assert bounds(panel)[2] == 31.5
    for nailer in vertical_nailers:
        nailer_box = bounds(nailer)
        assert nailer_box[2:] == (30.75, 31.5, 4.25, 8.25)
        assert abs(nailer_box[4] - bounds(lower_nailer)[5]) <= EPSILON
        assert abs(nailer_box[5] - bounds(upper_front)[4]) <= EPSILON
    assert all(abs(bounds(obj)[3] - bounds(panel)[2]) <= EPSILON for obj in nailers)
    assert not any(positive_volume_overlap(nailer, member) for nailer in nailers for member in lower)

    assert set(COLLECTION_NAMES) <= set(bpy.data.collections.keys())
    assert {"TOP_ORTHO", "FRONT", "SIDE", "ISOMETRIC_FRAMING", "ISOMETRIC_FINISHED"} <= set(bpy.data.cameras.keys())

    return "\n".join((
        "CENTER DAYBED MODULE V2 - VALIDATION REPORT",
        "",
        "ARCHITECTURAL REFERENCE",
        "60.000 in flat wall area; 59.000 in structural width; 0.500 in nominal side clearance each side.",
        "",
        "UPPER FRAME - FLAT 2x4",
        "Outside: 59.000 W x 31.500 D x 1.500 H in",
        "Elevation: Z 8.250 to 9.750 in",
        "Rails: 2 x 59 in; front-to-back members: 5 x 24.5 in; interior crossmembers: 3",
        "",
        "LOWER FRAME - FLAT 2x4",
        "Outside: 59.000 W x 29.000 D x 1.500 H in",
        "Elevation: Z 0.000 to 1.500 in",
        "Rails: 2 x 59 in; front-to-back members: 4 x 22 in; interior crossmembers: 2",
        "Rear edges aligned: PASS; lower front recess: 2.500 in",
        "",
        "VERTICAL POSTS",
        "10 x 6.750 in posts; 5 rear and 5 front",
        "Post X positions per row: -27.750, -13.875, 0.000, 13.875, 27.750 in",
        "Post elevation: Z 1.500 to 8.250 in",
        "Rear posts fully bear between aligned rear rails: PASS",
        "Front posts: 1.500 X x 3.500 Y x 6.750 Z in; Y footprint 25.500 to 29.000 in",
        "Front posts fully bear on lower front rail: PASS",
        "Front-post upper bearing: 2.500 in under member; 1.000 in under front rail: PASS",
        "No post exceeds the 59 in structural envelope: PASS",
        "",
        "FINISHED HEIGHTS",
        "Deck: Z 9.750 to 10.500 in; finished wood platform height: 10.500 in",
        "Approximate cushion top: 14.500 in; approximate sill underside: 15.000 in",
        "",
        "STRUCTURAL CHECKS",
        "Wood-on-wood load path: deck -> upper frame -> posts -> lower frame -> floor",
        "Positive-volume lumber intersections: NONE (bearing faces allowed)",
        "Cut totals: 4 x 59 in, 5 x 24.5 in, 4 x 22 in, 10 x 6.75 in",
        "Front-panel nailers remain above and independent of the recessed lower frame: PASS",
        "",
        FRAME_JOINT_NOTE,
        "Wood glue may supplement this connection.",
        "",
        POST_CONNECTION_NOTE,
    ))


def write_exports(report):
    DIMENSIONS_PATH.write_text(report + "\n", encoding="utf-8")
    with CUTLIST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("purpose", "cut_length_in", "quantity", "stock"))
        writer.writerows(CUTLIST_ROWS)


def main():
    clear_scene()
    scene = configure_scene()
    collections = make_collections()
    materials = make_materials()

    build_room_reference(collections["ROOM_REFERENCE"], materials)
    upper = build_upper_frame(collections["UPPER_FRAME_FLAT_2X4"], materials["framing"])
    lower = build_lower_frame(collections["LOWER_FRAME_FLAT_2X4"], materials["framing"])
    posts = build_posts(collections["VERTICAL_POSTS"], materials["framing"])
    deck, panel, nailers = build_finish(collections, materials)
    build_dimensions_and_notes(collections["DIMENSIONS"], materials["dimension"])
    cameras = build_cameras(collections["CAMERAS"])
    configure_view_layers()
    scene.camera = cameras["ISOMETRIC_FINISHED"]

    try:
        report = validate_scene(upper, lower, posts, deck, panel, nailers)
    except AssertionError as conflict:
        print(f"V2 VALIDATION CONFLICT: {conflict}")
        raise

    print("\n" + report)
    write_exports(report)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"- Saved Blender model: {BLEND_PATH}")
    print(f"- Saved cut list: {CUTLIST_PATH}")
    print(f"- Saved dimension report: {DIMENSIONS_PATH}")
    print("V2 VALIDATION PASSED")


if __name__ == "__main__":
    main()
