import csv
import json
import math
from pathlib import Path

import bpy
import mathutils


CENTER_FLAT_WALL_WIDTH = 60.0
DAYBED_FINISHED_DEPTH = 32.0
MEASURED_INTERIOR_CORNER_ANGLE = 135.5
MEASURED_WALL_TURN = 44.5
STRUCTURAL_SIDE_ANGLE = 45.0
APPROX_SILL_UNDERSIDE_HEIGHT = 15.0
APPROX_SILL_PROJECTION = 2.5
MEASURED_CORNER_TO_CORNER_WIDTH = 106.0
FACET_CENTER_FLAT = 5.0
FACET_TRANSITION = 1.0
SIDE_STEP_INTERVAL = 8.0
SIDE_REAR_STRUCTURAL_SETBACK = 8.0
SIDE_EDGE_STRUCTURE_INSET = 1.0
SIDE_LOWER_FRONT_RECESS = 2.5
SIDE_UPPER_FRONT_EDGE_Y = 31.5
SIDE_LOWER_FRONT_EDGE_Y = 29.0
FINISHED_FRONT_Y = 32.0
SHORT_RAIL_THRESHOLD = 3.0
MAX_UNSUPPORTED_DECK_SPAN = 16.0
ACTUAL_2X4_THICKNESS = 1.5
ACTUAL_2X4_WIDTH = 3.5
PROVISIONAL_STATUS = "PROVISIONAL / FIELD VERIFY"
PLYWOOD_FIELD_STATUS = "FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING"
SHORT_RAIL_DETAIL = "SHORT_RAIL_SINGLE_SCREW_DETAIL"
TOL = 1e-6

OUTPUT_DIR = Path(__file__).resolve().parent
CUTLIST_PATH = OUTPUT_DIR / "bay_daybed_v4_cutlist.csv"
DIMENSIONS_PATH = OUTPUT_DIR / "bay_daybed_v4_dimensions.txt"
BLEND_PATH = OUTPUT_DIR / "bay_daybed_v4.blend"

COLLECTION_NAMES = (
    "ROOM_REFERENCE",
    "CENTER_UPPER_FRAME",
    "CENTER_LOWER_FRAME",
    "CENTER_POSTS",
    "LEFT_UPPER_STEP_FRAME",
    "LEFT_LOWER_STEP_FRAME",
    "LEFT_POSTS",
    "RIGHT_UPPER_STEP_FRAME",
    "RIGHT_LOWER_STEP_FRAME",
    "RIGHT_POSTS",
    "PLYWOOD_DECKS",
    "MAPLE_FINISH",
    "FRONT_PANEL_NAILERS",
    "CUSHION_REFERENCE",
    "FASTENER_REFERENCE",
    "DIMENSIONS",
    "CAMERAS",
)


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _signed_area(poly):
    return 0.5 * sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])
    )


def polygon_area(poly):
    return abs(_signed_area(poly))


def _line_side(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _segment_line_intersection(p, q, a, b):
    dp = _line_side(a, b, p)
    dq = _line_side(a, b, q)
    if abs(dp - dq) <= TOL:
        return q
    t = dp / (dp - dq)
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


def polygon_intersection(subject, clipper):
    if not subject or not clipper:
        return []
    clip = clipper if _signed_area(clipper) > 0 else list(reversed(clipper))
    output = list(subject)
    for a, b in zip(clip, clip[1:] + clip[:1]):
        source, output = output, []
        if not source:
            break
        previous = source[-1]
        previous_inside = _line_side(a, b, previous) >= -TOL
        for current in source:
            current_inside = _line_side(a, b, current) >= -TOL
            if current_inside != previous_inside:
                output.append(_segment_line_intersection(previous, current, a, b))
            if current_inside:
                output.append(current)
            previous, previous_inside = current, current_inside
    return output


def positive_overlap_area(a, b):
    return polygon_area(polygon_intersection(a, b))


def point_in_polygon(point, poly):
    oriented = poly if _signed_area(poly) > 0 else list(reversed(poly))
    return all(
        _line_side(a, b, point) >= -TOL
        for a, b in zip(oriented, oriented[1:] + oriented[:1])
    )


def side_x(module, u):
    assert module in {"LEFT", "RIGHT"}
    return 30.0 + u if module == "LEFT" else -30.0 - u


def side_u(module, x):
    assert module in {"LEFT", "RIGHT"}
    return x - 30.0 if module == "LEFT" else -30.0 - x


def local_to_world(module, footprint):
    points = [(side_x(module, u), y) for u, y in footprint]
    return list(reversed(points)) if _signed_area(points) < 0 else points


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def configure_units():
    settings = bpy.context.scene.unit_settings
    settings.system = "IMPERIAL"
    settings.length_unit = "INCHES"
    settings.scale_length = 0.0254


def create_collections():
    result = {}
    for name in COLLECTION_NAMES:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        result[name] = collection
    return result


def _material(name, color, alpha=1.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    if alpha < 1.0:
        material.surface_render_method = "DITHERED"
    return material


def create_materials():
    return {
        "lumber": _material("MAT_NATURAL_FRAMING_LUMBER", (0.58, 0.36, 0.17)),
        "maple": _material("MAT_LIGHT_NATURAL_MAPLE", (0.82, 0.68, 0.43)),
        "wall": _material("MAT_OFF_WHITE_WALL", (0.88, 0.86, 0.79)),
        "floor": _material("MAT_LIGHT_NEUTRAL_WOOD", (0.53, 0.39, 0.25)),
        "cushion": _material("MAT_WARM_IVORY_CUSHION", (0.83, 0.78, 0.67)),
        "reference": _material("MAT_REFERENCE_BLUE", (0.08, 0.52, 1.0)),
        "fastener": _material("MAT_FASTENER_REFERENCE", (0.12, 0.12, 0.14)),
    }


def _set_props(obj, props):
    for key, value in props.items():
        obj[key] = json.dumps(value) if isinstance(value, (list, tuple, dict)) else value


def add_prism(name, footprint, z0, z1, collection, material=None, **props):
    footprint = footprint if _signed_area(footprint) > 0 else list(reversed(footprint))
    count = len(footprint)
    vertices = [(x, y, z0) for x, y in footprint] + [(x, y, z1) for x, y in footprint]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
    faces.extend(
        (i, (i + 1) % count, (i + 1) % count + count, i + count)
        for i in range(count)
    )
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    _set_props(obj, {"footprint": footprint, "z0": z0, "z1": z1, **props})
    return obj


def add_box(name, x0, x1, y0, y1, z0, z1, collection, material=None, **props):
    return add_prism(name, rect(x0, x1, y0, y1), z0, z1, collection, material, **props)


def bounds(obj):
    coordinates = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        min(v.x for v in coordinates), max(v.x for v in coordinates),
        min(v.y for v in coordinates), max(v.y for v in coordinates),
        min(v.z for v in coordinates), max(v.z for v in coordinates),
    )


def union_bounds(objects):
    values = [bounds(obj) for obj in objects]
    return tuple(round(value, 6) for value in (
        min(v[0] for v in values), max(v[1] for v in values),
        min(v[2] for v in values), max(v[3] for v in values),
        min(v[4] for v in values), max(v[5] for v in values),
    ))


def object_footprint(obj):
    return [(float(x), float(y)) for x, y in json.loads(obj["footprint"])]


def validate_parameters():
    assert MEASURED_WALL_TURN == 44.5
    assert MEASURED_INTERIOR_CORNER_ANGLE == 135.5
    assert STRUCTURAL_SIDE_ANGLE == 45.0
    assert STRUCTURAL_SIDE_ANGLE != 45.5
    assert SIDE_REAR_STRUCTURAL_SETBACK == 8.0
    assert abs(SIDE_UPPER_FRONT_EDGE_Y - SIDE_LOWER_FRONT_EDGE_Y - 2.5) < TOL
    assert abs(FINISHED_FRONT_Y - SIDE_LOWER_FRONT_EDGE_Y - 3.0) < TOL
    assert PLYWOOD_FIELD_STATUS == "FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING"
    assert abs(polygon_area(rect(0, 1, 0, 1)) - 1.0) < TOL
    assert positive_overlap_area(rect(0, 1, 0, 1), rect(1, 2, 0, 1)) < TOL
    assert abs(positive_overlap_area(rect(0, 2, 0, 2), rect(1, 2, 1, 2)) - 1.0) < TOL
    return ["V4 parameter and planar geometry checks passed"]


def _structural_props(module, purpose, cut_length, orientation, status):
    return {
        "module": module,
        "purpose": purpose,
        "cut_length": float(cut_length),
        "cut_type": "SQUARE / 90 DEGREE",
        "orientation": orientation,
        "status": status,
        "structural_2x4": True,
    }


def _center_board(name, purpose, cut_length, orientation, footprint, z0, z1, collection, material):
    return add_prism(
        name,
        footprint,
        z0,
        z1,
        collection,
        material,
        **_structural_props("CENTER", purpose, cut_length, orientation, "RESOLVED"),
    )


def build_center(collections, materials):
    lumber = materials["lumber"]
    upper, lower, posts = [], [], []
    upper_collection = collections["CENTER_UPPER_FRAME"]
    lower_collection = collections["CENTER_LOWER_FRAME"]
    post_collection = collections["CENTER_POSTS"]

    upper.append(_center_board(
        "CENTER_UPPER_REAR_RAIL_59IN", "UPPER_REAR_RAIL", 59, "X",
        rect(-29.5, 29.5, 0, 3.5), 8.25, 9.75, upper_collection, lumber,
    ))
    upper.append(_center_board(
        "CENTER_UPPER_FRONT_RAIL_59IN", "UPPER_FRONT_RAIL", 59, "X",
        rect(-29.5, 29.5, 28, 31.5), 8.25, 9.75, upper_collection, lumber,
    ))
    upper_positions = [-27.75, -13.875, 0.0, 13.875, 27.75]
    upper_purposes = [
        "UPPER_LEFT_OUTSIDE_MEMBER", "UPPER_INTERIOR_CROSSMEMBER_01",
        "UPPER_CENTER_CROSSMEMBER", "UPPER_INTERIOR_CROSSMEMBER_02",
        "UPPER_RIGHT_OUTSIDE_MEMBER",
    ]
    for index, (x, purpose) in enumerate(zip(upper_positions, upper_purposes), 1):
        upper.append(_center_board(
            f"CENTER_{purpose}_24.5IN_{index:02d}", purpose, 24.5, "Y",
            rect(x - 1.75, x + 1.75, 3.5, 28), 8.25, 9.75,
            upper_collection, lumber,
        ))

    lower.append(_center_board(
        "CENTER_LOWER_REAR_RAIL_59IN", "LOWER_REAR_RAIL", 59, "X",
        rect(-29.5, 29.5, 0, 3.5), 0, 1.5, lower_collection, lumber,
    ))
    lower.append(_center_board(
        "CENTER_LOWER_FRONT_RAIL_59IN", "LOWER_FRONT_RAIL", 59, "X",
        rect(-29.5, 29.5, 25.5, 29), 0, 1.5, lower_collection, lumber,
    ))
    lower_positions = [-27.75, -9.25, 9.25, 27.75]
    lower_purposes = [
        "LOWER_LEFT_OUTSIDE_MEMBER", "LOWER_INTERIOR_CROSSMEMBER_01",
        "LOWER_INTERIOR_CROSSMEMBER_02", "LOWER_RIGHT_OUTSIDE_MEMBER",
    ]
    for index, (x, purpose) in enumerate(zip(lower_positions, lower_purposes), 1):
        lower.append(_center_board(
            f"CENTER_{purpose}_22IN_{index:02d}", purpose, 22, "Y",
            rect(x - 1.75, x + 1.75, 3.5, 25.5), 0, 1.5,
            lower_collection, lumber,
        ))

    for row, y, size_x, size_y in (
        ("REAR", 1.75, 3.5, 1.5),
        ("FRONT", 27.25, 1.5, 3.5),
    ):
        for index, x in enumerate(upper_positions, 1):
            post = add_box(
                f"CENTER_{row}_POST_3.5X1.5X6.75IN_{index:02d}",
                x - size_x / 2, x + size_x / 2,
                y - size_y / 2, y + size_y / 2,
                1.5, 8.25, post_collection, lumber,
                **_structural_props("CENTER", f"{row}_POST_{index:02d}", 6.75, "Z", "RESOLVED"),
                row=row,
            )
            posts.append(post)
    return {"upper": upper, "lower": lower, "posts": posts}


def structural_volume_overlap(a, b):
    az0, az1 = float(a["z0"]), float(a["z1"])
    bz0, bz1 = float(b["z0"]), float(b["z1"])
    return min(az1, bz1) - max(az0, bz0) > TOL and positive_overlap_area(
        object_footprint(a), object_footprint(b)
    ) > TOL


def _supported_area(footprint, supports):
    return sum(positive_overlap_area(footprint, object_footprint(support)) for support in supports)


def validate_center(center):
    upper, lower, posts = center["upper"], center["lower"], center["posts"]
    assert len(upper) == 7
    assert len(lower) == 6
    assert len(posts) == 10
    assert union_bounds(upper) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75)
    assert union_bounds(lower) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5)
    assert sum("INTERIOR_CROSSMEMBER" in obj["purpose"] or "CENTER_CROSSMEMBER" in obj["purpose"] for obj in upper) == 3
    assert sum("INTERIOR_CROSSMEMBER" in obj["purpose"] for obj in lower) == 2
    assert abs(union_bounds(upper)[3] - union_bounds(lower)[3] - 2.5) < TOL

    counts = {}
    for obj in upper + lower + posts:
        length = float(obj["cut_length"])
        counts[length] = counts.get(length, 0) + 1
        assert obj["status"] == "RESOLVED"
        assert obj["cut_type"] == "SQUARE / 90 DEGREE"
    assert counts == {59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}

    for post in posts:
        footprint = object_footprint(post)
        assert abs(polygon_area(footprint) - 5.25) < TOL
        assert abs(_supported_area(footprint, lower) - polygon_area(footprint)) < TOL
        assert abs(_supported_area(footprint, upper) - polygon_area(footprint)) < TOL
        assert abs(float(post["z0"]) - 1.5) < TOL
        assert abs(float(post["z1"]) - 8.25) < TOL
        if post["row"] == "FRONT":
            _, _, y0, y1, _, _ = bounds(post)
            assert abs(y0 - 25.5) < TOL and abs(y1 - 29.0) < TOL
            post["upper_longitudinal_bearing_y"] = 2.5
            post["upper_front_rail_bearing_y"] = 1.0

    structural = upper + lower + posts
    for index, first in enumerate(structural):
        for second in structural[index + 1:]:
            assert not structural_volume_overlap(first, second), f"Center lumber overlap: {first.name} / {second.name}"
    return ["Resolved center validated"]


def side_frame_specs(frame):
    assert frame in {"UPPER", "LOWER"}
    root2 = math.sqrt(2.0)
    rear_outer = SIDE_REAR_STRUCTURAL_SETBACK - root2 * SIDE_EDGE_STRUCTURE_INSET
    near16_outer = 14.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
    near24_outer = 22.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
    front_y0 = 28.0 if frame == "UPPER" else 25.5
    front_y1 = SIDE_UPPER_FRONT_EDGE_Y if frame == "UPPER" else SIDE_LOWER_FRONT_EDGE_Y
    front_outer = front_y0 - root2 * SIDE_EDGE_STRUCTURE_INSET
    spine_y1 = 28.0 if frame == "UPPER" else 25.5
    specs = [
        ("REAR_CLOSURE", "X", 0.0, rear_outer, 8.0, 11.5),
        ("INNER_SPINE", "Y", 0.0, 3.5, 11.5, spine_y1),
        ("TRANSVERSE_16", "X", 3.5, near16_outer, 14.0, 17.5),
        ("TRANSVERSE_24", "X", 3.5, near24_outer, 22.0, 25.5),
        ("FRONT_RAIL" if frame == "UPPER" else "LOWER_FRONT_RAIL", "X", 0.0, front_outer, front_y0, front_y1),
        ("OUTER_STEP_01", "Y", 3.5, 7.0, 11.5, 14.0),
        ("OUTER_STEP_02", "Y", near16_outer - 3.5, near16_outer, 17.5, 22.0),
    ]
    if frame == "UPPER":
        specs.append(("OUTER_STEP_03", "Y", near24_outer - 3.5, near24_outer, 25.5, 28.0))
    return [
        {
            "purpose": purpose, "axis": axis, "u0": u0, "u1": u1,
            "y0": y0, "y1": y1,
            "cut_length": (u1 - u0) if axis == "X" else (y1 - y0),
        }
        for purpose, axis, u0, u1, y0, y1 in specs
    ]


def build_side_frame(module, frame, z0, z1, collection, material):
    objects = []
    for index, spec in enumerate(side_frame_specs(frame), 1):
        local = rect(spec["u0"], spec["u1"], spec["y0"], spec["y1"])
        cut = spec["cut_length"]
        name = f"{module}_{frame}_{spec['purpose']}_{cut:.3f}IN_{index:02d}"
        obj = add_prism(
            name, local_to_world(module, local), z0, z1, collection, material,
            **_structural_props(module, f"{frame}_{spec['purpose']}", cut, spec["axis"], PROVISIONAL_STATUS),
            frame=frame,
            local_footprint=local,
            structural_angle_assumption=STRUCTURAL_SIDE_ANGLE,
        )
        objects.append(obj)
    return objects


def side_post_specs():
    root2 = math.sqrt(2.0)
    rear_outer = SIDE_REAR_STRUCTURAL_SETBACK - root2 * SIDE_EDGE_STRUCTURE_INSET
    near16_outer = 14.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
    near24_outer = 22.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
    return [
        {"purpose": "REAR_INNER", "u0": 0.0, "u1": 3.5, "y0": 10.75, "y1": 12.25,
         "lower": ["LOWER_REAR_CLOSURE", "LOWER_INNER_SPINE"], "upper": ["UPPER_REAR_CLOSURE", "UPPER_INNER_SPINE"]},
        {"purpose": "REAR_OUTER", "u0": 4.292893218813452, "u1": 5.792893218813452,
         "y0": 9.75, "y1": 13.25,
         "lower": ["LOWER_REAR_CLOSURE", "LOWER_OUTER_STEP_01"], "upper": ["UPPER_REAR_CLOSURE", "UPPER_OUTER_STEP_01"]},
        {"purpose": "STATION16_INNER", "u0": 1.75, "u1": 5.25, "y0": 15.0, "y1": 16.5,
         "lower": ["LOWER_INNER_SPINE", "LOWER_TRANSVERSE_16"], "upper": ["UPPER_INNER_SPINE", "UPPER_TRANSVERSE_16"]},
        {"purpose": "STATION16_OUTER", "u0": near16_outer - 3.5, "u1": near16_outer, "y0": 16.75, "y1": 18.25,
         "lower": ["LOWER_TRANSVERSE_16", "LOWER_OUTER_STEP_02"], "upper": ["UPPER_TRANSVERSE_16", "UPPER_OUTER_STEP_02"]},
        {"purpose": "STATION24_INNER", "u0": 1.75, "u1": 5.25, "y0": 23.0, "y1": 24.5,
         "lower": ["LOWER_INNER_SPINE", "LOWER_TRANSVERSE_24"], "upper": ["UPPER_INNER_SPINE", "UPPER_TRANSVERSE_24"]},
        {"purpose": "STATION24_OUTER", "u0": near16_outer - 3.5, "u1": near16_outer, "y0": 21.25, "y1": 22.75,
         "lower": ["LOWER_OUTER_STEP_02", "LOWER_TRANSVERSE_24"], "upper": ["UPPER_OUTER_STEP_02", "UPPER_TRANSVERSE_24"]},
        {"purpose": "FRONT_INNER", "u0": 1.0, "u1": 2.5, "y0": 25.5, "y1": 29.0,
         "lower": ["LOWER_LOWER_FRONT_RAIL"], "upper": ["UPPER_INNER_SPINE", "UPPER_FRONT_RAIL"]},
        {"purpose": "FRONT_OUTER", "u0": near24_outer - 2.5, "u1": near24_outer - 1.0, "y0": 25.5, "y1": 29.0,
         "lower": ["LOWER_LOWER_FRONT_RAIL"], "upper": ["UPPER_OUTER_STEP_03", "UPPER_FRONT_RAIL"]},
    ]


def _purpose_map(objects):
    return {obj["purpose"]: obj for obj in objects}


def build_side_posts(module, height, lower, upper, collection, material):
    posts = []
    for index, spec in enumerate(side_post_specs(), 1):
        local = rect(spec["u0"], spec["u1"], spec["y0"], spec["y1"])
        width_u, width_y = spec["u1"] - spec["u0"], spec["y1"] - spec["y0"]
        obj = add_prism(
            f"{module}_POST_{spec['purpose']}_{width_u:.1f}X{width_y:.1f}X{height:.2f}IN_{index:02d}",
            local_to_world(module, local), 1.5, 1.5 + height, collection, material,
            **_structural_props(module, f"POST_{spec['purpose']}", height, "Z", PROVISIONAL_STATUS),
            local_footprint=local,
            lower_supports=spec["lower"],
            upper_supports=spec["upper"],
            post_screw_access=False,
        )
        posts.append(obj)
    return posts


def build_sides(collections, materials):
    result = {}
    for module, upper_z0, post_height in (("LEFT", 12.25, 10.75), ("RIGHT", 8.25, 6.75)):
        upper = build_side_frame(
            module, "UPPER", upper_z0, upper_z0 + 1.5,
            collections[f"{module}_UPPER_STEP_FRAME"], materials["lumber"],
        )
        lower = build_side_frame(
            module, "LOWER", 0, 1.5,
            collections[f"{module}_LOWER_STEP_FRAME"], materials["lumber"],
        )
        posts = build_side_posts(
            module, post_height, lower, upper,
            collections[f"{module}_POSTS"], materials["lumber"],
        )
        result[module] = {"upper": upper, "lower": lower, "posts": posts}
    return result


def _parse_prop_list(obj, key):
    return json.loads(obj[key])


def _local_footprint(obj):
    return [(float(u), float(y)) for u, y in json.loads(obj["local_footprint"])]


def _support_area_by_names(footprint, support_map, names):
    return sum(positive_overlap_area(footprint, _local_footprint(support_map[name])) for name in names)


def localized_step_metrics(sides):
    root2 = math.sqrt(2.0)
    interfaces, clearances, overlaps = [], [], []
    for data in sides.values():
        for frame in ("upper", "lower"):
            objects = _purpose_map(data[frame])
            prefix = frame.upper()
            step = objects[f"{prefix}_OUTER_STEP_01"]
            spine = objects[f"{prefix}_INNER_SPINE"]
            closure = objects[f"{prefix}_REAR_CLOSURE"]
            step_local = _local_footprint(step)
            closure_local = _local_footprint(closure)
            step_u0 = min(u for u, _ in step_local)
            step_u1 = max(u for u, _ in step_local)
            assert abs(step_u0 - 3.5) < TOL and abs(step_u1 - 7.0) < TOL
            interface = min(step_u1, max(u for u, _ in closure_local)) - max(
                step_u0, min(u for u, _ in closure_local)
            )
            clearance = min((y - u) / root2 for u, y in step_local)
            overlap = positive_overlap_area(step_local, _local_footprint(spine))
            step["rear_closure_fastening_interface"] = interface
            step["minimum_plywood_edge_clearance"] = clearance
            step["inner_spine_overlap_area"] = overlap
            interfaces.append(interface)
            clearances.append(clearance)
            overlaps.append(overlap)
    return {
        "interface": min(interfaces),
        "edge_clearance": min(clearances),
        "max_spine_overlap": max(overlaps),
    }


def validate_sides(sides):
    correction = localized_step_metrics(sides)
    assert correction["max_spine_overlap"] < TOL
    assert correction["interface"] >= 2.75
    assert abs(correction["interface"] - 3.085786437626905) < TOL
    assert correction["edge_clearance"] > 0
    assert abs(correction["edge_clearance"] - 3.181980515339464) < TOL
    for module, data in sides.items():
        upper, lower, posts = data["upper"], data["lower"], data["posts"]
        assert len(upper) == 8 and len(lower) == 7 and len(posts) == 8
        upper_map, lower_map = _purpose_map(upper), _purpose_map(lower)
        assert abs(max(bounds(obj)[3] for obj in upper) - 31.5) < TOL
        assert abs(max(bounds(obj)[3] for obj in lower) - 29.0) < TOL

        for obj in upper + lower:
            assert obj["cut_type"] == "SQUARE / 90 DEGREE"
            assert obj["orientation"] in {"X", "Y"}
            assert obj["status"] == PROVISIONAL_STATUS
            assert float(obj["structural_angle_assumption"]) == 45.0
            local = _local_footprint(obj)
            assert min(y for _, y in local) >= SIDE_REAR_STRUCTURAL_SETBACK - TOL
            assert all(u <= y + TOL for u, y in local)
            minimum_inset = min((y - u) / math.sqrt(2.0) for u, y in local)
            assert minimum_inset >= SIDE_EDGE_STRUCTURE_INSET - TOL

        lower_cross = lower_map["LOWER_TRANSVERSE_24"]
        lower_front = lower_map["LOWER_LOWER_FRONT_RAIL"]
        assert positive_overlap_area(_local_footprint(lower_cross), _local_footprint(lower_front)) < TOL

        for post in posts:
            footprint = _local_footprint(post)
            area = polygon_area(footprint)
            lower_area = _support_area_by_names(footprint, lower_map, _parse_prop_list(post, "lower_supports"))
            upper_area = _support_area_by_names(footprint, upper_map, _parse_prop_list(post, "upper_supports"))
            assert abs(lower_area - area) < TOL, f"Lower bearing conflict: {post.name}"
            assert abs(upper_area - area) < TOL, f"Upper bearing conflict: {post.name}"
            post["lower_bearing_area"] = lower_area
            post["upper_bearing_area"] = upper_area
            post["relies_on_plywood"] = False
            if "FRONT" in post["purpose"]:
                post["upper_longitudinal_bearing_y"] = 2.5
                post["upper_front_rail_bearing_y"] = 1.0

        structural = upper + lower + posts
        for index, first in enumerate(structural):
            for second in structural[index + 1:]:
                assert not structural_volume_overlap(first, second), f"Side lumber overlap: {first.name} / {second.name}"

        module_bounds = union_bounds(structural)
        if module == "LEFT":
            assert module_bounds[0] >= 30.0 - TOL
            assert abs(module_bounds[5] - 13.75) < TOL
        else:
            assert module_bounds[1] <= -30.0 + TOL
            assert abs(module_bounds[5] - 9.75) < TOL
    return ["Square-cut side structures validated"]


def _frame_rail_objects(data, frame):
    prefix = frame.upper()
    return {
        obj["purpose"].replace(f"{prefix}_", "", 1): obj
        for obj in data[frame]
    }


def _add_screw_reference(module, frame, rail, end, lane_u, y0, y1, collection, material, corridor):
    z0 = float(rail["z0"]) + 0.68
    z1 = float(rail["z0"]) + 0.82
    footprint = rect(lane_u - 0.07, lane_u + 0.07, min(y0, y1), max(y0, y1))
    obj = add_prism(
        f"{module}_{frame}_{rail['purpose']}_{end}_SCREW_U{lane_u:.3f}",
        local_to_world(module, footprint), z0, z1, collection, material,
        module=module,
        frame=frame.upper(),
        target_rail=rail.name,
        target_purpose=rail["purpose"],
        end=end,
        nominal_length=5.0,
        rail_penetration=1.5,
        lane_u=lane_u,
        driver_corridor=corridor,
        nonstructural_reference=True,
    )
    return obj


def build_fastener_references(sides, collections, materials):
    result = []
    target_collection = collections["FASTENER_REFERENCE"]
    for module, data in sides.items():
        for frame in ("upper", "lower"):
            rails = _frame_rail_objects(data, frame)
            for purpose in ("OUTER_STEP_01", "OUTER_STEP_02", "OUTER_STEP_03"):
                if purpose not in rails:
                    continue
                rail = rails[purpose]
                local = _local_footprint(rail)
                u0, u1 = min(u for u, _ in local), max(u for u, _ in local)
                y0, y1 = min(y for _, y in local), max(y for _, y in local)
                length = y1 - y0
                short = length < SHORT_RAIL_THRESHOLD
                offsets = (1.0,) if short else (0.875, 2.625)
                rail["fastening_detail"] = SHORT_RAIL_DETAIL if short else "NORMAL_TWO_SCREWS_PER_END"
                rail["screws_per_end"] = 1 if short else 2
                rail["predrill"] = True
                rail["wood_glue"] = True
                rail["clamp_during_fastening"] = True
                rail["nominal_screw_length"] = 5.0
                rail["rail_penetration"] = 1.5
                for offset in offsets:
                    lane = u0 + offset
                    corridor = rect(lane - 0.25, lane + 0.25, y0 - 4.5, y0 - 3.5)
                    result.append(_add_screw_reference(
                        module, frame, rail, "REAR", lane, y0 - 3.5, y0 + 1.5,
                        target_collection, materials["fastener"], corridor,
                    ))
                front_offsets = (2.5,) if short else offsets
                for offset in front_offsets:
                    lane = u0 + offset
                    corridor = rect(lane - 0.25, lane + 0.25, y1 + 3.5, y1 + 4.5)
                    screw = _add_screw_reference(
                        module, frame, rail, "FRONT", lane, y1 - 1.5, y1 + 3.5,
                        target_collection, materials["fastener"], corridor,
                    )
                    if frame == "lower" and purpose == "OUTER_STEP_02":
                        sequence = (
                            "FASTEN OUTER_STEP_02 TO TRANSVERSE_24 BEFORE INSTALLING "
                            "LOWER FRONT RAIL AT Y=25.5–29.0"
                        )
                        screw["ASSEMBLY_SEQUENCE_REQUIRED"] = sequence
                        screw["assembly_sequence_required"] = True
                        rail["ASSEMBLY_SEQUENCE_REQUIRED"] = sequence
                    result.append(screw)
    _validate_post_access(sides)
    return result


def _point_supported(point, support_map, names):
    return any(point_in_polygon(point, _local_footprint(support_map[name])) for name in names)


def _validate_post_access(sides):
    for data in sides.values():
        upper_map, lower_map = _purpose_map(data["upper"]), _purpose_map(data["lower"])
        for post in data["posts"]:
            footprint = _local_footprint(post)
            u0, u1 = min(u for u, _ in footprint), max(u for u, _ in footprint)
            y0, y1 = min(y for _, y in footprint), max(y for _, y in footprint)
            candidates = [
                ((u0 + u1) / 2, y0 + (y1 - y0) / 4),
                (u0 + (u1 - u0) / 4, (y0 + y1) / 2),
                ((u0 + u1) / 2, (y0 + y1) / 2),
            ]
            upper_names = _parse_prop_list(post, "upper_supports")
            lower_names = _parse_prop_list(post, "lower_supports")
            screw_point = next(
                (point for point in candidates
                 if _point_supported(point, upper_map, upper_names)
                 and _point_supported(point, lower_map, lower_names)),
                None,
            )
            assert screw_point is not None, f"No shared vertical screw path: {post.name}"
            unrelated_upper = [obj for name, obj in upper_map.items() if name not in upper_names]
            unrelated_lower = [obj for name, obj in lower_map.items() if name not in lower_names]
            assert not any(point_in_polygon(screw_point, _local_footprint(obj)) for obj in unrelated_upper)
            assert not any(point_in_polygon(screw_point, _local_footprint(obj)) for obj in unrelated_lower)
            post["post_screw_access"] = True
            post["post_screw_point_local"] = json.dumps(screw_point)
            post["bottom_driver_access"] = "UPSIDE-DOWN ASSEMBLY BEFORE FLOOR PLACEMENT"
            post["top_driver_access"] = "DOWNWARD THROUGH FLAT UPPER FRAME"


def validate_fasteners(sides, fasteners):
    assert len(fasteners) == 28
    by_rail = {}
    sequence_dependent = []
    for screw in fasteners:
        by_rail.setdefault(screw["target_rail"], []).append(screw)
        assert abs(float(screw["nominal_length"]) - 5.0) < TOL
        assert abs(float(screw["rail_penetration"]) - 1.5) < TOL
        corridor = [(float(u), float(y)) for u, y in json.loads(screw["driver_corridor"])]
        data = sides[screw["module"]]
        frame_objects = data[screw["frame"].lower()]
        for neighbor in frame_objects:
            if neighbor.name == screw["target_rail"]:
                continue
            overlap = positive_overlap_area(corridor, _local_footprint(neighbor))
            if overlap < TOL:
                continue
            allowed_sequence = (
                bool(screw.get("assembly_sequence_required", False))
                and screw["frame"] == "LOWER"
                and screw["end"] == "FRONT"
                and "LOWER_OUTER_STEP_02" in screw["target_purpose"]
                and neighbor["purpose"] == "LOWER_LOWER_FRONT_RAIL"
            )
            assert allowed_sequence, f"Unannotated driver corridor blocked: {screw.name} / {neighbor.name}"
            assert "ASSEMBLY_SEQUENCE_REQUIRED" in screw
            assert positive_overlap_area(object_footprint(screw), _local_footprint(neighbor)) < TOL
            screw["assembly_state_driver_clear"] = True
            screw["final_state_boundary_only"] = True
            screw["final_state_later_board"] = neighbor.name
            sequence_dependent.append(screw)

    for data in sides.values():
        for frame in ("upper", "lower"):
            for rail in data[frame]:
                if "OUTER_STEP" not in rail["purpose"]:
                    continue
                screws = by_rail[rail.name]
                length = float(rail["cut_length"])
                lanes = sorted({round(float(screw["lane_u"]), 6) for screw in screws})
                if length < SHORT_RAIL_THRESHOLD:
                    assert rail["fastening_detail"] == SHORT_RAIL_DETAIL
                    assert int(rail["screws_per_end"]) == 1 and len(screws) == 2
                    assert abs(lanes[1] - lanes[0] - 1.5) < TOL
                    local = _local_footprint(rail)
                    u0, u1 = min(u for u, _ in local), max(u for u, _ in local)
                    assert abs(lanes[0] - u0 - 1.0) < TOL
                    assert abs(u1 - lanes[1] - 1.0) < TOL
                    assert abs(length - 1.5 - 1.0) < TOL
                    rail["opposing_path_collision"] = False
                    rail["side_edge_distance"] = 1.0
                    rail["vertical_edge_distance"] = 0.75
                    rail["tip_to_opposite_end"] = 1.0
                    rail["driver_access"] = True
                    rail["screw_protrusion"] = False
                else:
                    assert int(rail["screws_per_end"]) == 2 and len(screws) == 4
                    assert abs(length - 3.0 - 1.5) < TOL
                    assert abs(lanes[1] - lanes[0] - 1.75) < TOL
                    rail["opposing_penetration_clearance"] = 1.5
                    rail["driver_access"] = True
        assert all(bool(post["post_screw_access"]) for post in data["posts"])
    assert len(sequence_dependent) == 4
    assert len([s for s in fasteners if s.get("assembly_sequence_required", False)]) == 4
    return ["Frame fastener geometry and post access validated"]


def calculate_support_spans(center, sides):
    center_clear = max(
        b - a - 3.5
        for a, b in zip([-27.75, -13.875, 0.0, 13.875], [-13.875, 0.0, 13.875, 27.75])
    )
    angle = math.radians(STRUCTURAL_SIDE_ANGLE)
    rear_tip = math.hypot(
        SIDE_REAR_STRUCTURAL_SETBACK,
        SIDE_REAR_STRUCTURAL_SETBACK * math.tan(angle),
    )
    stepped_bay = math.hypot(
        SIDE_STEP_INTERVAL,
        SIDE_STEP_INTERVAL * math.tan(angle),
    ) + SIDE_EDGE_STRUCTURE_INSET
    spans = {"CENTER": center_clear, "LEFT": max(rear_tip, stepped_bay), "RIGHT": max(rear_tip, stepped_bay)}
    assert all(span < MAX_UNSUPPORTED_DECK_SPAN for span in spans.values())
    return spans


def _side_finished_local_footprint():
    return [(0.0, 0.0), (32.0, 32.0), (0.0, 32.0)]


def build_decks(collections, materials):
    collection, maple = collections["PLYWOOD_DECKS"], materials["maple"]
    decks = {
        "CENTER": add_box(
            "CENTER_DECK_0.75_MAPLE", -30, 30, 0, 32, 9.75, 10.5,
            collection, maple, module="CENTER", status="RESOLVED", thickness=0.75,
        ),
        "LEFT": add_prism(
            "VIEWER_LEFT_RAISED_LANDING_0.75_MAPLE_FIELD_TEMPLATE",
            local_to_world("LEFT", _side_finished_local_footprint()), 13.75, 14.5,
            collection, maple, module="LEFT", status=PLYWOOD_FIELD_STATUS,
            thickness=0.75, finished_top=14.5, cushion=False,
        ),
        "RIGHT": add_prism(
            "VIEWER_RIGHT_LOWER_DECK_0.75_MAPLE_FIELD_TEMPLATE",
            local_to_world("RIGHT", _side_finished_local_footprint()), 9.75, 10.5,
            collection, maple, module="RIGHT", status=PLYWOOD_FIELD_STATUS,
            thickness=0.75, finished_top=10.5, cushion=True,
        ),
    }
    return decks


def build_finish(collections, materials):
    collection, maple = collections["MAPLE_FINISH"], materials["maple"]
    skins = {
        "CENTER": add_box(
            "CENTER_FRONT_MAPLE_PANEL_0.5IN", -30, 30, 31.5, 32, 3, 10.5,
            collection, maple, module="CENTER", status="RESOLVED", thickness=0.5,
        )
    }
    local_skin = [(0, 31.5), (31.5, 31.5), (32, 32), (0, 32)]
    for module, top in (("LEFT", 14.5), ("RIGHT", 10.5)):
        skins[module] = add_prism(
            f"{module}_FRONT_MAPLE_PANEL_0.5IN_FIELD_TEMPLATE",
            local_to_world(module, local_skin), 3, top, collection, maple,
            module=module, status=PLYWOOD_FIELD_STATUS, thickness=0.5,
        )
    return skins


def build_nailers(collections, materials):
    collection, maple = collections["FRONT_PANEL_NAILERS"], materials["maple"]
    nailers = []
    nailers.append(add_box(
        "CENTER_LOWER_PANEL_NAILER_59IN", -29.5, 29.5, 30.75, 31.5, 3.5, 4.25,
        collection, maple, module="CENTER", nonstructural_nailer=True,
    ))
    for index, x in enumerate((-24, -12, 0, 12, 24), 1):
        nailers.append(add_box(
            f"CENTER_VERTICAL_PANEL_NAILER_{index:02d}", x - 1.25, x + 1.25,
            30.75, 31.5, 4.25, 8.25, collection, maple,
            module="CENTER", nonstructural_nailer=True,
        ))
    for module, upper_bottom in (("LEFT", 12.25), ("RIGHT", 8.25)):
        horizontal_local = rect(0.5, 29.5, 30.75, 31.5)
        nailers.append(add_prism(
            f"{module}_LOWER_PANEL_NAILER", local_to_world(module, horizontal_local),
            3.5, 4.25, collection, maple, module=module, nonstructural_nailer=True,
        ))
        for index, u in enumerate((8, 16, 24), 1):
            vertical_local = rect(u - 1.25, u + 1.25, 30.75, 31.5)
            nailers.append(add_prism(
                f"{module}_VERTICAL_PANEL_NAILER_{index:02d}",
                local_to_world(module, vertical_local), 4.25, upper_bottom,
                collection, maple, module=module, nonstructural_nailer=True,
            ))
    return nailers


def build_cushion(collections, materials):
    footprint = [(-30, 0), (30, 0), (30, 32), (-62, 32)]
    return add_prism(
        "CENTER_RIGHT_SINGLE_CONTINUOUS_CUSHION_REFERENCE", footprint, 10.5, 14.5,
        collections["CUSHION_REFERENCE"], materials["cushion"],
        nonstructural=True, module_coverage="CENTER + VIEWER RIGHT",
        upholstery_dimensions="REFERENCE ONLY / NOT FINAL", front_edge_y=32.0,
    )


def _strip_footprint(a, b, width):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    return [
        (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
        (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny),
    ]


def build_room_reference(collections, materials):
    collection = collections["ROOM_REFERENCE"]
    room = {}
    room["floor"] = add_box(
        "ROOM_FLOOR_REFERENCE", -72, 72, -8, 40, -0.25, 0,
        collection, materials["floor"], reference=True,
    )
    room["center_wall"] = add_box(
        "CENTER_60IN_WALL_REFERENCE", -30, 30, -0.25, 0, 0, 22,
        collection, materials["wall"], reference=True, width=60.0,
    )
    measured_run = DAYBED_FINISHED_DEPTH / math.tan(math.radians(MEASURED_WALL_TURN))
    for module, start, end in (
        ("LEFT", (30, 0), (30 + measured_run, 32)),
        ("RIGHT", (-30, 0), (-30 - measured_run, 32)),
    ):
        room[f"{module.lower()}_wall"] = add_prism(
            f"{module}_MEASURED_44.5DEG_WALL_REFERENCE",
            _strip_footprint(start, end, 0.25), 0, 22, collection, materials["wall"],
            reference=True, measured_wall_turn=MEASURED_WALL_TURN,
            measured_interior_angle=MEASURED_INTERIOR_CORNER_ANGLE,
            measured_outer_run=measured_run,
        )
    room["sill"] = add_box(
        "APPROX_SILL_UNDERSIDE_Z15", -30, 30, 0, APPROX_SILL_PROJECTION,
        15, 15.35, collection, materials["wall"], reference=True,
        sill_underside=15.0, sill_projection=2.5,
    )
    bpy.context.scene.world.color = (0.055, 0.055, 0.055)
    for name, location, energy, size in (
        ("V4_KEY_AREA", (0, 42, 45), 2200, 35),
        ("V4_FILL_AREA", (-45, 18, 30), 1200, 25),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        collection.objects.link(obj)
        _look_at(obj, (0, 18, 6))
    return room


def _add_text(name, body, location, collection, material, size=0.8):
    curve = bpy.data.curves.new(f"{name}_CURVE", "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = 0.015
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.hide_render = True
    obj["viewport_annotation"] = True
    return obj


def _add_outline(name, footprint, z, collection, material):
    curve = bpy.data.curves.new(f"{name}_CURVE", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.10
    spline = curve.splines.new("POLY")
    spline.points.add(len(footprint))
    for point, (x, y) in zip(spline.points, footprint + [footprint[0]]):
        point.co = (x, y, z, 1)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["nonstructural_deck_footprint_reference"] = True
    return obj


def build_dimensions(collections, materials):
    collection = collections["DIMENSIONS"]
    texts = [
        _add_text("V4_LEFT_CONVENTION", "VIEWER LEFT / POSITIVE X / RAISED / NO CUSHION", (31, 34, 15), collection, materials["reference"]),
        _add_text("V4_RIGHT_CONVENTION", "VIEWER RIGHT / NEGATIVE X / LOWER / CONTINUOUS CUSHION", (-61, 34, 11), collection, materials["reference"]),
        _add_text("V4_FIELD_TEMPLATE_NOTE", PLYWOOD_FIELD_STATUS, (-26, -2, 16), collection, materials["reference"], 0.65),
        _add_text("V4_ROOM_ANGLE_NOTE", "ROOM 44.5° TURN / 135.5° INTERIOR; STRUCTURE 45°", (-25, -2, 17.2), collection, materials["reference"], 0.65),
        _add_text("V4_ASSEMBLY_NOTE", "DECK IS PRIMARY SHEAR DIAPHRAGM; SQUARE BARE FRAME FIRST", (-25, -2, 18.4), collection, materials["reference"], 0.65),
    ]
    texts.extend((
        _add_outline("CENTER_DECK_FOOTPRINT", rect(-30, 30, 0, 32), 10.65, collection, materials["reference"]),
        _add_outline("LEFT_DECK_FOOTPRINT", local_to_world("LEFT", _side_finished_local_footprint()), 14.65, collection, materials["reference"]),
        _add_outline("RIGHT_DECK_FOOTPRINT", local_to_world("RIGHT", _side_finished_local_footprint()), 10.65, collection, materials["reference"]),
    ))
    return texts


def _look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_cameras(collections):
    cameras = {}
    specs = {
        "V4_TOP_FRAMING": ((0, 16, 125), (0, 16, 0), 140, "ORTHO"),
        "V4_FRAMING_ISOMETRIC": ((108, 122, 76), (0, 17, 6), 55, "PERSP"),
        "V4_FINISHED_ISOMETRIC": ((112, 126, 78), (0, 17, 8), 55, "PERSP"),
        "V4_FRONT": ((0, 105, 18), (0, 18, 7), 88, "ORTHO"),
        "V4_RIGHT_DETAIL": ((-82, 67, 39), (-45, 22, 7), 52, "PERSP"),
        "V4_LEFT_DETAIL": ((82, 67, 42), (45, 22, 9), 52, "PERSP"),
    }
    for name, (location, target, lens_or_scale, kind) in specs.items():
        data = bpy.data.cameras.new(name)
        data.type = kind
        if kind == "ORTHO":
            data.ortho_scale = lens_or_scale
        else:
            data.lens = lens_or_scale
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        collections["CAMERAS"].objects.link(obj)
        _look_at(obj, target)
        obj["viewer_left_is_positive_x"] = True
        obj["horizontal_projection_mirrored_for_viewer_convention"] = False
        cameras[name] = obj
    cameras["V4_TOP_FRAMING"]["recommended_view_layer"] = "TOP_FRAMING"
    bpy.context.scene.camera = cameras["V4_FINISHED_ISOMETRIC"]
    return cameras


def configure_view_layers():
    scene = bpy.context.scene
    framing = scene.view_layers.get("FRAMING_ONLY") or scene.view_layers.new("FRAMING_ONLY")
    finished = scene.view_layers.get("FINISHED") or scene.view_layers.new("FINISHED")
    top = scene.view_layers.get("TOP_FRAMING") or scene.view_layers.new("TOP_FRAMING")
    hidden = {
        "ROOM_REFERENCE", "PLYWOOD_DECKS", "MAPLE_FINISH",
        "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE",
    }
    top_hidden = hidden | {
        "CENTER_LOWER_FRAME", "CENTER_POSTS", "LEFT_LOWER_STEP_FRAME", "LEFT_POSTS",
        "RIGHT_LOWER_STEP_FRAME", "RIGHT_POSTS", "FASTENER_REFERENCE", "CAMERAS",
    }
    for name, layer in (("FRAMING_ONLY", framing), ("FINISHED", finished), ("TOP_FRAMING", top)):
        for collection_name, child in layer.layer_collection.children.items():
            child.exclude = (
                (name == "FRAMING_ONLY" and collection_name in hidden)
                or (name == "TOP_FRAMING" and collection_name in top_hidden)
            )
    return {"FRAMING_ONLY": framing, "FINISHED": finished, "TOP_FRAMING": top}


def build_visuals(collections, materials, center, sides):
    scene = bpy.context.scene
    scene["LEFT_RIGHT_NAMING_CONVENTION"] = (
        "POSITIVE X = VIEWER LEFT = RAISED LANDING; "
        "NEGATIVE X = VIEWER RIGHT = LOWER CUSHION CONTINUATION"
    )
    scene["viewer_left_module"] = "LEFT / POSITIVE X / RAISED 14.5 / NO CUSHION"
    scene["viewer_right_module"] = "RIGHT / NEGATIVE X / LOWER 10.5 / CONTINUOUS CUSHION"
    scene["measured_wall_turn"] = MEASURED_WALL_TURN
    scene["structural_side_angle"] = STRUCTURAL_SIDE_ANGLE
    scene["anti_racking"] = (
        "SECURELY SCREWED 3/4-IN DECK IS PRIMARY SHEAR DIAPHRAGM; "
        "SQUARE BARE FRAME BEFORE DECK INSTALLATION"
    )
    scene["baseline_angle_brackets_required"] = False
    for module in ("LEFT", "RIGHT"):
        collections[f"{module}_UPPER_STEP_FRAME"]["viewer_convention"] = scene[f"viewer_{module.lower()}_module"]
    decks = build_decks(collections, materials)
    skins = build_finish(collections, materials)
    nailers = build_nailers(collections, materials)
    cushion = build_cushion(collections, materials)
    room = build_room_reference(collections, materials)
    dimensions = build_dimensions(collections, materials)
    cameras = build_cameras(collections)
    layers = configure_view_layers()
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.055, 0.065, 0.075)
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    return {
        "decks": decks, "skins": skins, "nailers": nailers, "cushion": cushion,
        "room": room, "dimensions": dimensions, "cameras": cameras, "layers": layers,
    }


def validate_visuals(visuals, sides):
    decks, skins, cushion = visuals["decks"], visuals["skins"], visuals["cushion"]
    assert set(decks) == {"CENTER", "LEFT", "RIGHT"}
    assert abs(bounds(decks["LEFT"])[5] - 14.5) < TOL
    assert abs(bounds(decks["CENTER"])[5] - 10.5) < TOL
    assert abs(bounds(decks["RIGHT"])[5] - 10.5) < TOL
    assert decks["LEFT"]["status"] == PLYWOOD_FIELD_STATUS
    assert decks["RIGHT"]["status"] == PLYWOOD_FIELD_STATUS
    assert bounds(decks["LEFT"])[0] >= 30 - TOL
    assert bounds(decks["RIGHT"])[1] <= -30 + TOL
    assert len(bpy.data.collections["CUSHION_REFERENCE"].objects) == 1
    assert abs(bounds(cushion)[4] - 10.5) < TOL and abs(bounds(cushion)[5] - 14.5) < TOL
    assert abs(bounds(cushion)[3] - FINISHED_FRONT_Y) < TOL
    assert positive_overlap_area(object_footprint(cushion), object_footprint(decks["LEFT"])) < TOL
    for module, skin in skins.items():
        assert abs(bounds(skin)[3] - FINISHED_FRONT_Y) < TOL
        assert abs(bounds(skin)[4] - 3.0) < TOL
        if module != "CENTER":
            assert skin["status"] == PLYWOOD_FIELD_STATUS
    assert abs(bounds(visuals["room"]["sill"])[4] - 15.0) < TOL
    measured_run = float(visuals["room"]["left_wall"]["measured_outer_run"])
    assert measured_run > 32.0
    assert bpy.context.scene["measured_wall_turn"] == 44.5
    assert bpy.context.scene["structural_side_angle"] == 45.0
    assert set(visuals["cameras"]) == {
        "V4_TOP_FRAMING", "V4_FRAMING_ISOMETRIC", "V4_FINISHED_ISOMETRIC",
        "V4_FRONT", "V4_RIGHT_DETAIL", "V4_LEFT_DETAIL",
    }
    assert {"FRAMING_ONLY", "FINISHED", "TOP_FRAMING"} <= set(visuals["layers"])
    for data in sides.values():
        for step in (obj for obj in data["upper"] + data["lower"] if "OUTER_STEP_01" in obj["purpose"]):
            for nailer in visuals["nailers"]:
                assert not structural_volume_overlap(step, nailer)
    return ["Finish, naming, room references, cameras, and layers validated"]


def all_structural(model):
    objects = model["center"]["upper"] + model["center"]["lower"] + model["center"]["posts"]
    for data in model["sides"].values():
        objects.extend(data["upper"] + data["lower"] + data["posts"])
    return objects


def cutlist_rows(model):
    rows = [
        {"MODULE": "CENTER", "OBJECT": "UPPER_AND_LOWER_FRONT_REAR_RAILS", "QUANTITY": 4,
         "CUT_LENGTH": "59", "CUT_TYPE": "SQUARE / 90 DEGREE", "ORIENTATION": "X", "STATUS": "RESOLVED"},
        {"MODULE": "CENTER", "OBJECT": "UPPER_SIDE_AND_INTERIOR_MEMBERS", "QUANTITY": 5,
         "CUT_LENGTH": "24.5", "CUT_TYPE": "SQUARE / 90 DEGREE", "ORIENTATION": "Y", "STATUS": "RESOLVED"},
        {"MODULE": "CENTER", "OBJECT": "LOWER_SIDE_AND_INTERIOR_MEMBERS", "QUANTITY": 4,
         "CUT_LENGTH": "22", "CUT_TYPE": "SQUARE / 90 DEGREE", "ORIENTATION": "Y", "STATUS": "RESOLVED"},
        {"MODULE": "CENTER", "OBJECT": "VERTICAL_POSTS", "QUANTITY": 10,
         "CUT_LENGTH": "6.75", "CUT_TYPE": "SQUARE / 90 DEGREE", "ORIENTATION": "Z", "STATUS": "RESOLVED"},
    ]
    for module in ("LEFT", "RIGHT"):
        data = model["sides"][module]
        for obj in data["upper"] + data["lower"] + data["posts"]:
            rows.append({
                "MODULE": module,
                "OBJECT": obj.name,
                "QUANTITY": 1,
                "CUT_LENGTH": f"{float(obj['cut_length']):.6f}".rstrip("0").rstrip("."),
                "CUT_TYPE": obj["cut_type"],
                "ORIENTATION": obj["orientation"],
                "STATUS": obj["status"],
            })
    return rows


def _side_board_report(module, data):
    lines = []
    for frame in ("upper", "lower"):
        lines.append(f"  {frame.upper()} FRAME ({len(data[frame])} BOARDS):")
        for obj in data[frame]:
            extra = ""
            if "OUTER_STEP_01" in obj["purpose"]:
                extra = (
                    f" | closure interface {float(obj['rear_closure_fastening_interface']):.4f}"
                    f" | plywood clearance {float(obj['minimum_plywood_edge_clearance']):.4f}"
                )
            if "ASSEMBLY_SEQUENCE_REQUIRED" in obj:
                extra += f" | ASSEMBLY_SEQUENCE_REQUIRED: {obj['ASSEMBLY_SEQUENCE_REQUIRED']}"
            lines.append(
                f"    {obj.name}: {float(obj['cut_length']):.4f} in, "
                f"{obj['cut_type']}, {obj['status']}{extra}"
            )
    lines.append(f"  POSTS: {len(data['posts'])}")
    for post in data["posts"]:
        lines.append(
            f"    {post.name}: {float(post['cut_length']):.2f} in, "
            f"upper bearing {float(post['upper_bearing_area']):.3f} sq in, "
            f"lower bearing {float(post['lower_bearing_area']):.3f} sq in, "
            f"screw access={bool(post['post_screw_access'])}"
        )
    return lines


def dimensions_report(model):
    spans = model["spans"]
    correction = localized_step_metrics(model["sides"])
    lines = [
        "BAY-WINDOW DAYBED V4 — BEGINNER CONSTRUCTION DIMENSIONS",
        "========================================================",
        "",
        "LEFT / RIGHT CONVENTION",
        "Positive X = viewer-left = raised landing/table = no cushion.",
        "Negative X = viewer-right = lower module beneath continuous center/right cushion.",
        "",
        "ARCHITECTURE AND PROVISIONAL GEOMETRY",
        f"Center flat wall: {CENTER_FLAT_WALL_WIDTH:.1f} in",
        f"Measured interior corner angle: {MEASURED_INTERIOR_CORNER_ANGLE:.1f} degrees",
        f"Measured wall turn: {MEASURED_WALL_TURN:.1f} degrees",
        f"Hidden structural station assumption: {STRUCTURAL_SIDE_ANGLE:.1f} degrees",
        f"Measured corner-to-corner reference: {MEASURED_CORNER_TO_CORNER_WIDTH:.1f} in",
        f"Finished front plane: Y={FINISHED_FRONT_Y:.1f} in",
        f"Upper structural front edge: Y={SIDE_UPPER_FRONT_EDGE_Y:.1f} in",
        f"Lower structural front edge: Y={SIDE_LOWER_FRONT_EDGE_Y:.1f} in",
        "Structural upper-to-lower recess: 2.5 in",
        "Finished-face-to-lower-frame setback: 3.0 in",
        f"Side plywood: {PLYWOOD_FIELD_STATUS}",
        "The displayed ±62-in/45-degree side wedges are design references, not final cut sizes.",
        "",
        "CENTER — RESOLVED",
        "Upper frame: 59 x 31.5 x 1.5 in, Z=8.25..9.75",
        "Lower frame: 59 x 29 x 1.5 in, Z=0..1.5",
        "Posts: 10 x 6.75 in, Z=1.5..8.25",
        "Deck: 60 x 32 x 0.75 in, Z=9.75..10.5",
        "Resolved cut list: 4 x 59; 5 x 24.5; 4 x 22; 10 x 6.75",
        f"Maximum reported plywood support span: {spans['CENTER']:.4f} in",
        "",
        "VIEWER LEFT — RAISED WOOD LANDING — NO CUSHION",
        "Finished reference wedge: rear-inner (30,0), front-inner (30,32), front-outer (62,32)",
        "Finished deck Z=13.75..14.5; upper frame Z=12.25..13.75; posts=10.75 in",
        f"Maximum conservative plywood support span: {spans['LEFT']:.4f} in",
    ]
    lines.extend(_side_board_report("LEFT", model["sides"]["LEFT"]))
    lines.extend([
        "",
        "VIEWER RIGHT — LOWER MODULE — CONTINUOUS CUSHION",
        "Finished reference wedge: rear-inner (-30,0), front-inner (-30,32), front-outer (-62,32)",
        "Finished deck Z=9.75..10.5; upper frame Z=8.25..9.75; posts=6.75 in",
        f"Maximum conservative plywood support span: {spans['RIGHT']:.4f} in",
    ])
    lines.extend(_side_board_report("RIGHT", model["sides"]["RIGHT"]))
    sequence_screws = [
        obj for obj in model["fasteners"] if obj.get("assembly_sequence_required", False)
    ]
    lines.extend([
        "",
        "LOCALIZED OUTER_STEP_01 CORRECTION",
        "Local U footprint: 3.5..7.0 in; length: 2.5 in; square cuts.",
        f"Rear-closure fastening interface: {correction['interface']:.6f} in (minimum 2.75).",
        f"Closest perpendicular plywood-edge clearance: {correction['edge_clearance']:.6f} in.",
        f"Inner-spine overlap area: {correction['max_spine_overlap']:.6f} sq in.",
        "Rear outer posts: 1.5 X by 3.5 Y plan, full direct bearing.",
        "",
        "FASTENING",
        "Ordinary flat-frame joints: nominal 5-in structural screws; two per end only where validated.",
        "SHORT_RAIL_SINGLE_SCREW_DETAIL: one predrilled nominal 5-in structural screw per end,",
        "opposing paths staggered 1.5 in, wood glue, clamp during fastening.",
        "Post connections: nominal 3 to 3-1/8-in structural screws through the 1.5-in flat frame.",
        "Do not use drywall screws. Baseline V4 requires no angle brackets.",
        f"ASSEMBLY_SEQUENCE_REQUIRED screw paths: {len(sequence_screws)}",
        "ASSEMBLY_SEQUENCE_REQUIRED: fasten lower OUTER_STEP_02 to TRANSVERSE_24 before",
        "installing each lower front rail at Y=25.5..29.0.",
        "",
        "ANTI-RACKING",
        "The securely screwed 3/4-in plywood deck is the PRIMARY SHEAR DIAPHRAGM.",
        "Square the bare stepped frame before installing the deck.",
        "Orthogonal frame loops assist stiffness but are not rigid diaphragms by themselves.",
        "",
        "HEIGHTS",
        "Viewer-left landing top: 14.5 in",
        "Center deck top: 10.5 in",
        "Viewer-right deck top: 10.5 in",
        "Single center/right cushion: Z=10.5..14.5 in",
        "Approximate sill underside: 15.0 in",
        "",
        "WARNING: SIDE MODULE FRAMING POSITIONS AND FINISHED PLYWOOD ARE PROVISIONAL / FIELD VERIFY.",
        "TEMPLATE FINISHED SIDE PLYWOOD TO THE ACTUAL ROOM BEFORE CUTTING.",
        "",
        "V4 BEGINNER CONSTRUCTION:",
        "ALL LEFT/RIGHT STRUCTURAL 2x4 CUTS ARE 90-DEGREE SQUARE CUTS.",
        "THE FINISHED BAY ANGLES ARE CREATED BY PLYWOOD, NOT STRUCTURAL LUMBER.",
        "LEFT/RIGHT ARE DEFINED FROM THE VIEWER'S PERSPECTIVE FACING THE DAYBED.",
        "",
        "VALIDATION: PASSED",
    ])
    return "\n".join(lines) + "\n"


def validate_all(model):
    messages = []
    messages.extend(validate_parameters())
    messages.extend(validate_center(model["center"]))
    messages.extend(validate_sides(model["sides"]))
    messages.extend(validate_fasteners(model["sides"], model["fasteners"]))
    messages.extend(validate_visuals(model["visuals"], model["sides"]))
    model["spans"] = calculate_support_spans(model["center"], model["sides"])
    structural = all_structural(model)
    assert len(structural) == 69
    for index, first in enumerate(structural):
        for second in structural[index + 1:]:
            assert not structural_volume_overlap(first, second), (
                f"Structural lumber overlap: {first.name} / {second.name}"
            )
    side_structural = [obj for obj in structural if obj["module"] in {"LEFT", "RIGHT"}]
    assert len(side_structural) == 46
    assert all(obj["cut_type"] == "SQUARE / 90 DEGREE" for obj in side_structural)
    assert all(obj["status"] == PROVISIONAL_STATUS for obj in side_structural)
    assert len([obj for obj in model["fasteners"] if obj.get("assembly_sequence_required", False)]) == 4
    assert bpy.context.scene["viewer_left_module"].startswith("LEFT / POSITIVE X")
    assert bpy.context.scene["viewer_right_module"].startswith("RIGHT / NEGATIVE X")
    assert bpy.context.scene["baseline_angle_brackets_required"] is False
    assert set(COLLECTION_NAMES) <= set(bpy.data.collections.keys())
    bpy.context.scene["validation_status"] = "PASSED"
    bpy.context.scene["validation_messages"] = json.dumps(messages)
    return messages


def write_cutlist(rows):
    fields = ["MODULE", "OBJECT", "QUANTITY", "CUT_LENGTH", "CUT_TYPE", "ORIENTATION", "STATUS"]
    with CUTLIST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(model):
    correction = localized_step_metrics(model["sides"])
    print("\nCENTER: RESOLVED 59 x 31.5 upper / 59 x 29 lower / deck top 10.5")
    print("CUT LIST: 4 x 59; 5 x 24.5; 4 x 22; 10 x 6.75")
    print("\nVIEWER LEFT — RAISED WOOD LANDING — NO CUSHION")
    print(f"8 upper boards / 7 lower boards / 8 posts / deck top 14.5 / max span {model['spans']['LEFT']:.4f}")
    print("\nVIEWER RIGHT — LOWER MODULE — CONTINUOUS CUSHION")
    print(f"8 upper boards / 7 lower boards / 8 posts / deck top 10.5 / max span {model['spans']['RIGHT']:.4f}")
    print(f"\nOUTER_STEP_01 interface {correction['interface']:.6f}; plywood clearance {correction['edge_clearance']:.6f}")
    print("ASSEMBLY_SEQUENCE_REQUIRED: lower OUTER_STEP_02 before lower front rail (4 screw paths)")
    print("\nV4 BEGINNER CONSTRUCTION:")
    print("ALL LEFT/RIGHT STRUCTURAL 2x4 CUTS ARE 90-DEGREE SQUARE CUTS.")
    print("THE FINISHED BAY ANGLES ARE CREATED BY PLYWOOD, NOT STRUCTURAL LUMBER.")
    print("LEFT/RIGHT ARE DEFINED FROM THE VIEWER'S PERSPECTIVE FACING THE DAYBED.")
    print("WARNING: SIDE MODULE FRAMING POSITIONS AND FINISHED PLYWOOD ARE PROVISIONAL / FIELD VERIFY. TEMPLATE FINISHED SIDE PLYWOOD TO THE ACTUAL ROOM BEFORE CUTTING.")


def main():
    try:
        reset_scene()
        configure_units()
        collections = create_collections()
        materials = create_materials()
        center = build_center(collections, materials)
        sides = build_sides(collections, materials)
        fasteners = build_fastener_references(sides, collections, materials)
        visuals = build_visuals(collections, materials, center, sides)
        model = {"center": center, "sides": sides, "fasteners": fasteners, "visuals": visuals}
        validate_all(model)
    except AssertionError as error:
        print(f"V4 VALIDATION CONFLICT: {error}")
        raise

    write_cutlist(cutlist_rows(model))
    DIMENSIONS_PATH.write_text(dimensions_report(model), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print_summary(model)
    print(f"SAVED: {BLEND_PATH}")
    print(f"SAVED: {CUTLIST_PATH}")
    print(f"SAVED: {DIMENSIONS_PATH}")
    print("V4 VALIDATION PASSED")


if __name__ == "__main__":
    main()
