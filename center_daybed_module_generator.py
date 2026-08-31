from collections import Counter
from pathlib import Path
import csv
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
BLEND_PATH = ROOT / "center_daybed_module.blend"
CUTLIST_PATH = ROOT / "center_daybed_2x4_cutlist.csv"
EPSILON = 1e-6
RISER_X_POSITIONS = (-27.75, -14.375, 0.0, 14.375, 27.75)

COLLECTION_NAMES = (
    "ROOM_REFERENCE",
    "UPPER_2X4_FRAME",
    "LOWER_2X4_FRAME",
    "VERTICAL_LEGS",
    "PLYWOOD_DECK",
    "FRONT_PANEL_NAILERS",
    "MAPLE_FINISH",
    "DIMENSIONS",
)

CUTLIST_ROWS = (
    ("UPPER_FRONT_RAIL", "59", 1, "2x4"),
    ("UPPER_REAR_RAIL", "59", 1, "2x4"),
    ("LOWER_FRONT_RAIL", "59", 1, "2x4"),
    ("LOWER_REAR_RAIL", "59", 1, "2x4"),
    ("UPPER_SIDE_RAIL", "28.5", 2, "2x4"),
    ("UPPER_INTERIOR_CROSSMEMBER", "28.5", 3, "2x4"),
    ("LOWER_SIDE_RAIL", "26", 2, "2x4"),
    ("LOWER_INTERIOR_CROSSMEMBER", "26", 2, "2x4"),
    ("VERTICAL_RISER", "2.75", 10, "2x4"),
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
    scene.name = "CENTER_DAYBED_MODULE"
    scene.unit_settings.system = "IMPERIAL"
    scene.unit_settings.length_unit = "INCHES"
    scene.unit_settings.scale_length = 0.0254
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.055, 0.055)
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
    scene["module_scope"] = "CENTER RECTANGULAR MODULE ONLY"
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
        "framing": add_material("NATURAL_FRAMING_LUMBER", (0.63, 0.39, 0.18)),
        "maple": add_material("LIGHT_NATURAL_MAPLE", (0.86, 0.69, 0.43)),
        "nailer": add_material("NAILER_PLYWOOD", (0.70, 0.50, 0.27)),
        "wall": add_material("NEUTRAL_OFF_WHITE", (0.88, 0.87, 0.82)),
        "floor": add_material("NEUTRAL_WOOD_FLOOR", (0.31, 0.19, 0.10)),
        "dimension": add_material("DIMENSION_DARK", (0.025, 0.025, 0.025)),
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
    objects = [
        add_structural_piece(
            "UPPER_REAR_RAIL_59in", (59, 1.5, 3.5), (0, 0.75, 8),
            collection, material, 59, "UPPER_REAR_RAIL", "upper_rail",
        ),
        add_structural_piece(
            "UPPER_FRONT_RAIL_59in", (59, 1.5, 3.5), (0, 30.75, 8),
            collection, material, 59, "UPPER_FRONT_RAIL", "upper_rail",
        ),
    ]
    members = (
        (-28.75, "UPPER_LEFT_SIDE_RAIL_28.5in", "UPPER_SIDE_RAIL", "upper_side"),
        (-14.375, "UPPER_INTERIOR_CROSSMEMBER_28.5in_01", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        (0, "UPPER_CENTER_CROSSMEMBER_28.5in", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        (14.375, "UPPER_INTERIOR_CROSSMEMBER_28.5in_02", "UPPER_INTERIOR_CROSSMEMBER", "upper_interior"),
        (28.75, "UPPER_RIGHT_SIDE_RAIL_28.5in", "UPPER_SIDE_RAIL", "upper_side"),
    )
    for x, name, purpose, group in members:
        objects.append(add_structural_piece(
            name, (1.5, 28.5, 3.5), (x, 15.75, 8),
            collection, material, 28.5, purpose, group,
        ))
    return objects


def build_lower_frame(collection, material):
    objects = [
        add_structural_piece(
            "LOWER_REAR_RAIL_59in", (59, 1.5, 3.5), (0, 0.75, 1.75),
            collection, material, 59, "LOWER_REAR_RAIL", "lower_rail",
        ),
        add_structural_piece(
            "LOWER_FRONT_RAIL_59in", (59, 1.5, 3.5), (0, 28.25, 1.75),
            collection, material, 59, "LOWER_FRONT_RAIL", "lower_rail",
        ),
    ]
    members = (
        (-28.75, "LOWER_LEFT_SIDE_RAIL_26in", "LOWER_SIDE_RAIL", "lower_side"),
        (-14.375, "LOWER_INTERIOR_CROSSMEMBER_26in_01", "LOWER_INTERIOR_CROSSMEMBER", "lower_interior"),
        (14.375, "LOWER_INTERIOR_CROSSMEMBER_26in_02", "LOWER_INTERIOR_CROSSMEMBER", "lower_interior"),
        (28.75, "LOWER_RIGHT_SIDE_RAIL_26in", "LOWER_SIDE_RAIL", "lower_side"),
    )
    for x, name, purpose, group in members:
        objects.append(add_structural_piece(
            name, (1.5, 26, 3.5), (x, 14.5, 1.75),
            collection, material, 26, purpose, group,
        ))
    return objects


def build_risers(collection, material):
    objects = []
    for row, y in (("REAR", 0.75), ("FRONT", 28.25)):
        for index, x in enumerate(RISER_X_POSITIONS, 1):
            position = "CENTER_X0in" if x == 0 else f"X{x:+g}in"
            objects.append(add_structural_piece(
                f"RISER_{row}_{position}_2.75in_{index:02d}",
                (3.5, 1.5, 2.75),
                (x, y, 4.875),
                collection,
                material,
                2.75,
                "VERTICAL_RISER",
                "riser",
            ))
            objects[-1]["riser_row"] = row
            objects[-1]["x_position_in"] = x
    return objects


def build_finish(collections, materials):
    deck = add_box(
        "CENTER_DECK_0.75IN_MAPLE",
        (60, 32, 0.75),
        (0, 15.5, 10.125),
        collections["PLYWOOD_DECK"],
        materials["maple"],
        stock="3/4in maple plywood",
        purpose="CENTER_DECK",
    )
    panel = add_box(
        "CENTER_FRONT_PANEL_0.5IN_MAPLE",
        (60, 0.5, 7.5),
        (0, 31.75, 6.75),
        collections["MAPLE_FINISH"],
        materials["maple"],
        stock="nominal 1/2in maple panel",
        purpose="FRONT_FINISH_PANEL",
    )
    nailers = []
    for index, x in enumerate((-22.5, -7.5, 7.5, 22.5), 1):
        nailers.append(add_box(
            f"PANEL_NAILER_VERTICAL_APPROX_2.5in_{index:02d}",
            (2.5, 0.75, 2.5),
            (x, 31.125, 5.0),
            collections["FRONT_PANEL_NAILERS"],
            materials["nailer"],
            stock="3/4in plywood strip",
            purpose="PANEL_VERTICAL_NAILER",
            approximate=True,
        ))
    nailers.append(add_box(
        "PANEL_NAILER_HORIZONTAL_LOWER_APPROX_59in",
        (59, 2.5, 0.75),
        (0, 30.25, 3.375),
        collections["FRONT_PANEL_NAILERS"],
        materials["nailer"],
        stock="nominal 1x3",
        purpose="PANEL_LOWER_EDGE_NAILER",
        approximate=True,
    ))
    return deck, panel, nailers


def build_room_reference(collection, materials):
    floor = add_box(
        "FLOOR_REFERENCE_APPROX",
        (84, 60, 0.5),
        (0, 22, -0.25),
        collection,
        materials["floor"],
        purpose="FLOOR_REFERENCE",
        approximate=True,
    )
    wall = add_box(
        "CENTER_WALL_REFERENCE_60in_WIDE",
        (60, 0.5, 48),
        (0, -0.25, 24),
        collection,
        materials["wall"],
        purpose="60IN_FLAT_ARCHITECTURAL_AREA",
        approximate_height_and_thickness=True,
    )
    sill = add_box(
        "WINDOW_SILL_REFERENCE_UNDERSIDE_APPROX_15in",
        (60, 1, 1),
        (0, -0.25, 15.5),
        collection,
        materials["maple"],
        purpose="WINDOW_SILL_REFERENCE",
        approximate=True,
        underside_elevation_in=15.0,
    )
    return floor, wall, sill


def add_polyline(name, segments, collection, material):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = 0.035
    curve.bevel_resolution = 0
    for start, end in segments:
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.show_in_front = True
    return obj


def add_dimension(name, start, end, label, offset, plane, collection, material):
    start = Vector(start)
    end = Vector(end)
    offset = Vector(offset)
    dimension_start = start + offset
    dimension_end = end + offset
    line = add_polyline(
        name,
        ((start, dimension_start), (dimension_start, dimension_end), (end, dimension_end)),
        collection,
        material,
    )
    text_data = bpy.data.curves.new(f"{name}_TEXT", "FONT")
    text_data.body = label
    text_data.align_x = "CENTER"
    text_data.align_y = "CENTER"
    text_data.size = 1.0
    text_data.extrude = 0.01
    text_data.materials.append(material)
    text = bpy.data.objects.new(f"{name}_TEXT", text_data)
    text.location = (dimension_start + dimension_end) / 2
    text.rotation_euler = {
        "TOP": (0, 0, math.pi / 2),
        "FRONT": (math.pi / 2, 0, 0),
        "SIDE": (math.pi / 2, 0, math.pi / 2),
    }[plane]
    if plane == "FRONT":
        text.scale.x = -1
    text.show_in_front = True
    collection.objects.link(text)
    return line, text


def build_dimensions(collection, material):
    dimensions = (
        ("DIM_ARCHITECTURAL_WIDTH_60in", (-30, 0, 15), (30, 0, 15), '60" ARCHITECTURAL FLAT AREA', (0, 0.05, 2), "FRONT"),
        ("DIM_STRUCTURAL_WIDTH_59in", (-29.5, 31.5, 9.75), (29.5, 31.5, 9.75), '59" STRUCTURAL FRAME', (0, 2, 2), "FRONT"),
        ("DIM_UPPER_DEPTH_31.5in", (-29.5, 0, 10.5), (-29.5, 31.5, 10.5), '31.5" UPPER DEPTH', (-3, 0, 0), "TOP"),
        ("DIM_LOWER_DEPTH_29in", (29.5, 0, 3.5), (29.5, 29, 3.5), '29" LOWER DEPTH', (3, 0, 0), "TOP"),
        ("DIM_FRONT_RECESS_2.5in", (29.5, 29, 5), (29.5, 31.5, 5), '2.5" RECESS', (3, 0, 0), "TOP"),
        ("DIM_RISER_HEIGHT_2.75in", (29.5, 28.25, 3.5), (29.5, 28.25, 6.25), '2.75" RISER', (3, 0, 0), "SIDE"),
        ("DIM_UPPER_BOTTOM_6.25in", (-29.5, 31.5, 0), (-29.5, 31.5, 6.25), '6.25" UPPER BOTTOM', (-3, 0, 0), "FRONT"),
        ("DIM_UPPER_TOP_9.75in", (-29.5, 31.5, 0), (-29.5, 31.5, 9.75), '9.75" UPPER TOP', (-6, 0, 0), "FRONT"),
        ("DIM_DECK_TOP_10.5in", (29.5, 32, 0), (29.5, 32, 10.5), '10.5" DECK TOP', (6, 0, 0), "FRONT"),
        ("DIM_SILL_UNDERSIDE_APPROX_15in", (30, 0, 0), (30, 0, 15), '~15" SILL UNDERSIDE', (6, 0.05, 0), "FRONT"),
    )
    for args in dimensions:
        add_dimension(*args, collection, material)


def add_camera(name, location, target, orthographic=False, scale=1):
    data = bpy.data.cameras.new(name)
    data.lens = 52
    data.clip_start = 0.1
    data.clip_end = 1000
    data.type = "ORTHO" if orthographic else "PERSP"
    if orthographic:
        data.ortho_scale = scale
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def build_cameras():
    cameras = {
        "TOP_ORTHO": add_camera("TOP_ORTHO", (0, 15.5, 100), (0, 15.5, 0), True, 72),
        "FRONT": add_camera("FRONT", (0, 100, 10), (0, 15, 7), True, 72),
        "SIDE": add_camera("SIDE", (90, 15.5, 10), (0, 15.5, 7), True, 44),
        "ISOMETRIC_FINISHED": add_camera("ISOMETRIC_FINISHED", (69, 76, 52), (0, 15, 6), False),
        "ISOMETRIC_FRAMING": add_camera("ISOMETRIC_FRAMING", (85, 95, 32), (0, 14, 4), False),
    }
    cameras["ISOMETRIC_FINISHED"]["intended_view_layer"] = "FINISHED"
    cameras["ISOMETRIC_FRAMING"]["intended_view_layer"] = "FRAMING"
    return cameras


def configure_view_layers():
    scene = bpy.context.scene
    finished = scene.view_layers[0]
    finished.name = "FINISHED"
    dimensioned = scene.view_layers.get("DIMENSIONED") or scene.view_layers.new("DIMENSIONED")
    framing = scene.view_layers.get("FRAMING") or scene.view_layers.new("FRAMING")
    finished.layer_collection.children["DIMENSIONS"].exclude = True
    for name in ("PLYWOOD_DECK", "MAPLE_FINISH", "FRONT_PANEL_NAILERS"):
        layer_collection = framing.layer_collection.children.get(name)
        if layer_collection:
            layer_collection.exclude = True
    framing.layer_collection.children["DIMENSIONS"].exclude = True
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


def positive_volume_overlap(first, second):
    a = bounds(first)
    b = bounds(second)
    return all(
        min(a[maximum], b[maximum]) - max(a[minimum], b[minimum]) > EPSILON
        for minimum, maximum in ((0, 1), (2, 3), (4, 5))
    )


def xy_contains(support, load):
    outer = bounds(support)
    inner = bounds(load)
    return (
        outer[0] <= inner[0] + EPSILON and outer[1] >= inner[1] - EPSILON
        and outer[2] <= inner[2] + EPSILON and outer[3] >= inner[3] - EPSILON
    )


def xy_overlaps(first, second):
    a = bounds(first)
    b = bounds(second)
    return (
        min(a[1], b[1]) - max(a[0], b[0]) > EPSILON
        and min(a[3], b[3]) - max(a[2], b[2]) > EPSILON
    )


def validate_scene(upper, lower, risers, deck):
    upper_bounds = union_bounds(upper)
    lower_bounds = union_bounds(lower)
    riser_bounds = union_bounds(risers)
    deck_bounds = union_bounds([deck])
    assert upper_bounds == (-29.5, 29.5, 0.0, 31.5, 6.25, 9.75), upper_bounds
    assert lower_bounds == (-29.5, 29.5, 0.0, 29.0, 0.0, 3.5), lower_bounds
    assert round(upper_bounds[3] - lower_bounds[3], 6) == 2.5
    assert lower_bounds[4] == 0.0
    assert riser_bounds[4:] == (3.5, 6.25)
    assert riser_bounds[:2] == (-29.5, 29.5)
    assert upper_bounds[4:] == (6.25, 9.75)
    assert deck_bounds[4:] == (9.75, 10.5)

    expected_positions = list(RISER_X_POSITIONS)
    for row in ("REAR", "FRONT"):
        actual_positions = sorted(
            round(obj.location.x, 3) for obj in risers if obj["riser_row"] == row
        )
        assert actual_positions == expected_positions, (row, actual_positions)

    lower_rails = [obj for obj in lower if obj["validation_group"] == "lower_rail"]
    for riser in risers:
        bearing_rails = [
            rail for rail in lower_rails
            if abs(bounds(rail)[5] - bounds(riser)[4]) <= EPSILON and xy_contains(rail, riser)
        ]
        assert len(bearing_rails) == 1, (riser.name, [rail.name for rail in bearing_rails])
        upper_contacts = [
            member for member in upper
            if abs(bounds(riser)[5] - bounds(member)[4]) <= EPSILON and xy_overlaps(riser, member)
        ]
        assert upper_contacts, f"Riser does not contact upper frame: {riser.name}"

    structural = upper + lower + risers
    overlaps = [
        (first.name, second.name)
        for index, first in enumerate(structural)
        for second in structural[index + 1:]
        if positive_volume_overlap(first, second)
    ]
    assert not overlaps, f"Impossible structural overlaps: {overlaps}"

    groups = Counter(obj["validation_group"] for obj in structural)
    assert groups["upper_interior"] == 3, groups
    assert groups["lower_interior"] == 2, groups
    assert groups["riser"] == 10, groups

    cut_totals = Counter(round(float(obj["cut_length_in"]), 3) for obj in structural)
    assert cut_totals == Counter({59.0: 4, 28.5: 5, 26.0: 4, 2.75: 10}), cut_totals
    assert len(structural) == 23

    required_cameras = {"TOP_ORTHO", "FRONT", "SIDE", "ISOMETRIC_FINISHED", "ISOMETRIC_FRAMING"}
    assert required_cameras <= set(bpy.data.cameras.keys())
    assert set(COLLECTION_NAMES) <= set(bpy.data.collections.keys())

    print("\nCENTER DAYBED MODULE DIMENSION SUMMARY")
    print("- Architectural flat area: 60.000 in")
    print("- Upper frame outside: 59.000 W x 31.500 D x 3.500 H in")
    print("- Lower frame outside: 59.000 W x 29.000 D x 3.500 H in")
    print("- Lower front recess: 2.500 in")
    print("- Lower frame elevation: Z 0.000 to 3.500 in")
    print("- Riser elevation: Z 3.500 to 6.250 in (2.750 in high)")
    print("- Riser X positions per row: -27.750, -14.375, 0.000, 14.375, 27.750 in")
    print("- Upper frame elevation: Z 6.250 to 9.750 in")
    print("- Deck elevation: Z 9.750 to 10.500 in")
    print("- Approximate cushion top: Z 14.500 in")
    print("- Approximate sill underside: Z 15.000 in")
    print("- Structural overlap check: PASS (shared boundary faces allowed)")
    print("- Upper interior crossmembers: 3")
    print("- Lower interior crossmembers: 2")
    print("- Vertical risers: 10")
    print("- 2x4 cut totals: 4 x 59, 5 x 28.5, 4 x 26, 10 x 2.75 in")


def write_cutlist():
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
    upper = build_upper_frame(collections["UPPER_2X4_FRAME"], materials["framing"])
    lower = build_lower_frame(collections["LOWER_2X4_FRAME"], materials["framing"])
    risers = build_risers(collections["VERTICAL_LEGS"], materials["framing"])
    deck, _panel, _nailers = build_finish(collections, materials)
    build_dimensions(collections["DIMENSIONS"], materials["dimension"])
    cameras = build_cameras()
    configure_view_layers()
    scene.camera = cameras["ISOMETRIC_FINISHED"]

    validate_scene(upper, lower, risers, deck)
    write_cutlist()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"- Saved Blender model: {BLEND_PATH}")
    print(f"- Saved cut list: {CUTLIST_PATH}")
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
