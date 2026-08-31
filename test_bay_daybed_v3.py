from pathlib import Path
import subprocess
from collections import Counter
import csv
import math
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
WARNING = ("WARNING: SIDE MODULE ANGLES AND LENGTHS ARE PROVISIONAL UNTIL THE REAL BAY WALLS "
           "ARE FULL-SIZE TEMPLATED / FIELD MEASURED.")


def run_generator():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "bay_daybed_v3_generator.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_center_audit():
    code = '''import bpy
from collections import Counter

def bounds(obj):
    points = [obj.matrix_world @ point.co for point in obj.data.vertices]
    return tuple(value for axis in range(3) for value in (
        min(point[axis] for point in points), max(point[axis] for point in points)
    ))

def union(objects):
    values = [bounds(obj) for obj in objects]
    return tuple(value for axis in range(3) for value in (
        min(item[axis * 2] for item in values), max(item[axis * 2 + 1] for item in values)
    ))

assert "CENTER_UPPER_FRAME" in bpy.data.collections
assert "CENTER_LOWER_FRAME" in bpy.data.collections
assert "CENTER_POSTS" in bpy.data.collections
center_upper = list(bpy.data.collections["CENTER_UPPER_FRAME"].objects)
center_lower = list(bpy.data.collections["CENTER_LOWER_FRAME"].objects)
center_posts = list(bpy.data.collections["CENTER_POSTS"].objects)
assert len(center_upper) == 7
assert len(center_lower) == 6
assert len(center_posts) == 10
assert union(center_upper) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75)
assert union(center_lower) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5)
assert Counter(obj["cut_length_in"] for obj in center_upper + center_lower + center_posts) == {
    59: 4, 24.5: 5, 22: 4, 6.75: 10,
}
assert all(obj["module"] == "CENTER" and obj["status"] == "RESOLVED"
           and obj["purpose"] and obj["validation_group"]
           for obj in center_upper + center_lower + center_posts)
upper_members = sorted((obj for obj in center_upper if obj["purpose"] == "upper member"),
                       key=lambda obj: bounds(obj)[0])
lower_members = sorted((obj for obj in center_lower if obj["purpose"] == "lower member"),
                       key=lambda obj: bounds(obj)[0])
assert [bounds(obj)[1] - bounds(obj)[0] for obj in upper_members] == [3.5] * 5
assert [bounds(obj)[3] - bounds(obj)[2] for obj in upper_members] == [24.5] * 5
assert [bounds(obj)[1] - bounds(obj)[0] for obj in lower_members] == [3.5] * 4
assert [bounds(obj)[3] - bounds(obj)[2] for obj in lower_members] == [22.0] * 4
assert bounds(upper_members[0])[0] == bounds(lower_members[0])[0] == -29.5
assert bounds(upper_members[-1])[1] == bounds(lower_members[-1])[1] == 29.5
front_posts = [obj for obj in center_posts if obj["purpose"] == "front post"]
rear_posts = [obj for obj in center_posts if obj["purpose"] == "rear post"]
assert len(front_posts) == 5
assert len(rear_posts) == 5
assert all(obj["primary_fastening_note"] ==
           "Primary top fastening: through the upper front-to-back member into the post."
           for obj in front_posts)
for post in rear_posts:
    post_bounds = bounds(post)
    for rail in (center_lower[0], center_upper[0]):
        rail_bounds = bounds(rail)
        assert rail_bounds[0] <= post_bounds[0] and post_bounds[1] <= rail_bounds[1]
        assert rail_bounds[2] <= post_bounds[2] and post_bounds[3] <= rail_bounds[3]
for post, member in zip(sorted(front_posts, key=lambda obj: bounds(obj)[0]), upper_members):
    post_bounds, member_bounds = bounds(post), bounds(member)
    lower_front, upper_front = bounds(center_lower[1]), bounds(center_upper[1])
    assert lower_front[0] <= post_bounds[0] and post_bounds[1] <= lower_front[1]
    assert lower_front[2] <= post_bounds[2] and post_bounds[3] <= lower_front[3]
    assert member_bounds[0] <= post_bounds[0] and post_bounds[1] <= member_bounds[1]
    assert member_bounds[2] <= 25.5 and member_bounds[3] >= 28.0
    assert upper_front[0] <= post_bounds[0] and post_bounds[1] <= upper_front[1]
    assert upper_front[2] <= 28.0 and upper_front[3] >= 29.0
print("V3 CENTER AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_side_frame_audit():
    code = f'''import math
import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def bounds(obj):
    points = [obj.matrix_world @ point.co for point in obj.data.vertices]
    return tuple(value for axis in range(3) for value in (
        min(point[axis] for point in points), max(point[axis] for point in points)
    ))

def mesh_footprint(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    z0 = min(point.z for point in points)
    return [(point.x, point.y) for point in points if abs(point.z - z0) <= 1e-5]

def longitudinal_mesh_edges(obj, axis):
    """Measure continuous polygon edges parallel to axis; never read cut metadata."""
    points = mesh_footprint(obj)
    axis_length = math.hypot(*axis)
    unit = (axis[0] / axis_length, axis[1] / axis_length)
    normal = (-unit[1], unit[0])
    groups = []
    for start, end in zip(points, points[1:] + points[:1]):
        direction = (end[0] - start[0], end[1] - start[1])
        if abs(direction[0] * unit[1] - direction[1] * unit[0]) > 1e-5:
            continue
        offset = start[0] * normal[0] + start[1] * normal[1]
        interval = sorted((start[0] * unit[0] + start[1] * unit[1],
                           end[0] * unit[0] + end[1] * unit[1]))
        group = next((item for item in groups if abs(item[0] - offset) <= 1e-5), None)
        if group is None:
            group = [offset, []]
            groups.append(group)
        group[1].append(interval)
    lengths = []
    for _, intervals in groups:
        intervals.sort()
        low, high = intervals[0]
        for next_low, next_high in intervals[1:]:
            if next_low <= high + 1e-5:
                high = max(high, next_high)
            else:
                lengths.append(high - low)
                low, high = next_low, next_high
        lengths.append(high - low)
    return sorted(lengths, reverse=True)

expected_z = {{
    "LEFT_UPPER_FRAME": (12.25, 13.75),
    "LEFT_LOWER_FRAME": (0.0, 1.5),
    "RIGHT_UPPER_FRAME": (8.25, 9.75),
    "RIGHT_LOWER_FRAME": (0.0, 1.5),
}}
for name, z_bounds in expected_z.items():
    objects = list(bpy.data.collections[name].objects)
    assert len(objects) == 7, (name, len(objects))
    assert all(bounds(obj)[2] >= 8.0 and bounds(obj)[4:] == z_bounds for obj in objects)
    braces = [obj for obj in objects if "CROSS_BRACE" in obj.name]
    assert len(braces) == 2
    assert all(bounds(obj)[2:4] == (22.0, 25.5) for obj in braces)
    assert all(obj["module"] == name.split("_")[0]
               and obj["status"] == "PROVISIONAL / FIELD VERIFY"
               and obj["centerline_length_in"] > 0
               and obj["long_edge_in"] >= obj["short_edge_in"] > 0
               and "end_a_angle_deg" in obj and "end_b_angle_deg" in obj
               and "orientation_deg" in obj for obj in objects)
    diagonal = next(obj for obj in objects if obj["board_type"] == "diagonal_rail")
    expected_length = (28.0 - 11.5 if "UPPER" in name else 25.5 - 11.5) * math.sqrt(2.0)
    assert abs(diagonal["centerline_length_in"] - expected_length) <= 1e-9
    assert diagonal["end_a_angle_deg"] == diagonal["end_b_angle_deg"] == 45.0
    assert diagonal["orientation_deg"] == (45.0 if name.startswith("LEFT") else 135.0)
    radial = next(obj for obj in objects if obj["board_type"] == "radial_rail")
    sign = 1 if name.startswith("LEFT") else -1
    measured_edges = longitudinal_mesh_edges(radial, (sign * 0.5, 1.0))
    assert len(measured_edges) == 2, (radial.name, measured_edges)
    assert abs(radial["long_edge_in"] - measured_edges[0]) <= 1e-5
    assert abs(radial["short_edge_in"] - measured_edges[1]) <= 1e-5
    assert "long_point_in" not in radial and "short_point_in" not in radial
    if "UPPER" in name:
        expected_radial_length = (28.0 - generator.SIDE_REAR_STRUCTURAL_SETBACK
                                  - generator.ACTUAL_2X4_WIDTH) * math.sqrt(1.25)
        assert abs(radial["centerline_length_in"] - expected_radial_length) <= 1e-9
        expected_edges = (17.271158, 15.650291)
    else:
        expected_edges = (14.476073, 12.855206)
    assert abs(radial["long_edge_in"] - expected_edges[0]) <= 1e-5
    assert abs(radial["short_edge_in"] - expected_edges[1]) <= 1e-5
    assert radial["cut_profile"] == "CUSTOM NOTCHED REAR PROFILE"
    assert len([float(value) for value in radial["end_a_angle_deg"].split("|")]) == 3
    assert all(obj["cut_length_in"] == obj["centerline_length_in"] for obj in objects)

keys = {{"rear_closure", "inner_rail", "radial_rail", "diagonal_rail",
        "cross_brace_inner", "cross_brace_outer", "front_rail"}}

def local(sign, footprint):
    return [(generator.side_u(sign, x), y) for x, y in footprint]

def extents(footprint):
    return (min(x for x, _ in footprint), max(x for x, _ in footprint),
            min(y for _, y in footprint), max(y for _, y in footprint))

for sign in (-1, 1):
    upper = generator.side_frame_footprints(sign, 28.0)
    lower = generator.side_frame_footprints(sign, 25.5)
    assert set(upper) == keys and set(lower) == keys
    upper_local = {{name: local(sign, footprint) for name, footprint in upper.items()}}
    lower_local = {{name: local(sign, footprint) for name, footprint in lower.items()}}
    assert set(upper_local["rear_closure"]) == {{(-0.5, 8.0), (8.0, 8.0),
                                                 (8.0, 11.5), (-0.5, 11.5)}}
    assert extents(upper_local["inner_rail"]) == (-0.5, 3.0, 11.5, 28.0)
    diagonal = upper_local["diagonal_rail"]
    assert all(0.0 <= u <= y for u, y in diagonal)
    for y in (11.5, 28.0):
        inner_u, outer_u = sorted(u for u, vertex_y in diagonal if vertex_y == y)
        assert abs((y - outer_u) / math.sqrt(2.0) - 1.0) <= 1e-9
        assert abs((outer_u - inner_u) / math.sqrt(2.0) - 3.5) <= 1e-9
        if y == 28.0:
            radial_inner, radial_outer = sorted(
                u for u, vertex_y in upper_local["radial_rail"] if vertex_y == y)
            assert abs((radial_outer - radial_inner) / math.sqrt(1.25) - 3.5) <= 1e-9
            assert abs((radial_inner + radial_outer) / 2
                       - (1.25 + (inner_u + outer_u) / 2) / 2) <= 1e-9
    radial_rear = sorted(u for u, y in upper_local["radial_rail"] if y == 11.5)
    assert len(upper_local["radial_rail"]) > 4
    assert len(radial_rear) == 2
    assert abs(radial_rear[0] - 3.0) <= 1e-9
    assert abs(radial_rear[1] - 5.1360389693210715) <= 1e-9
    assert radial_rear[0] <= 4.430456351736995 <= radial_rear[1]
    rear_diagonal_inner = min(u for u, y in diagonal if y == 11.5)
    rear_interface = 8.0 - rear_diagonal_inner
    assert abs(rear_interface - 2.8639610306789285) <= 1e-9
    assert rear_interface >= generator.MIN_REAR_FASTENING_INTERFACE
    for rail in ("inner_rail", "radial_rail", "diagonal_rail"):
        assert generator.polygons_overlap_area(
            upper_local["rear_closure"], upper_local[rail]) <= 1e-9
    assert generator.polygons_overlap_area(
        upper_local["inner_rail"], upper_local["diagonal_rail"]) <= 1e-9
    for footprints in (upper_local, lower_local):
        assert generator.polygons_overlap_area(
            footprints["radial_rail"], footprints["inner_rail"]) <= 1e-9
        assert generator.polygons_overlap_area(
            footprints["radial_rail"], footprints["diagonal_rail"]) <= 1e-9
    assert generator.polygons_overlap_area(
        upper_local["cross_brace_inner"], upper_local["cross_brace_outer"]) <= 1e-9
    for brace in ("cross_brace_inner", "cross_brace_outer"):
        assert extents(upper_local[brace])[2:] == (22.0, 25.5)
        assert generator.polygons_overlap_area(
            lower_local[brace], lower_local["front_rail"]) <= 1e-9
        assert extents(lower_local[brace])[3] == extents(lower_local["front_rail"])[2] == 25.5

trapezoid = [(0.0, 0.0), (10.0, 0.0), (12.0, 3.0), (0.0, 3.0)]
metadata = generator.board_cut_metadata(
    trapezoid, (1.0, 0.0), ((trapezoid[3], trapezoid[0]), (trapezoid[1], trapezoid[2])),
)
assert metadata["centerline_length_in"] == 11.0
assert metadata["long_edge_in"] == 12.0 and metadata["short_edge_in"] == 10.0
assert metadata["end_a_angle_deg"] == 0.0
assert abs(metadata["end_b_angle_deg"] - 33.690067525979785) <= 1e-9
assert metadata["orientation_deg"] == 0.0
print("V3 SIDE FRAME AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_nominal_stock_cross_section_audit():
    """Independently inspect every saved structural mesh, without trusting its size metadata."""
    code = '''import math
import bpy

def footprint(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    z0 = min(point.z for point in points)
    result = []
    for point in points:
        xy = (point.x, point.y)
        if abs(point.z - z0) <= 1e-5 and not any(
                math.hypot(xy[0] - old[0], xy[1] - old[1]) <= 1e-5 for old in result):
            result.append(xy)
    return result

def minimum_plan_width(points):
    widths = []
    for start, end in zip(points, points[1:] + points[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 1e-5:
            continue
        normal = (-dy / length, dx / length)
        projections = [x * normal[0] + y * normal[1] for x, y in points]
        widths.append(max(projections) - min(projections))
    return min(widths)

structural = [obj for obj in bpy.data.objects if obj.get("validation_group") == "STRUCTURAL"]
assert len(structural) == 65
for obj in structural:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    z_size = max(point.z for point in points) - min(point.z for point in points)
    plan = footprint(obj)
    if "post" in obj["purpose"]:
        edges = sorted(math.hypot(end[0] - start[0], end[1] - start[1])
                       for start, end in zip(plan, plan[1:] + plan[:1]))
        assert len(edges) == 4, (obj.name, edges)
        assert all(abs(actual - expected) <= 1e-5
                   for actual, expected in zip(edges, (1.5, 1.5, 3.5, 3.5))), (obj.name, edges)
        assert abs(z_size - obj["cut_length_in"]) <= 1e-5, (obj.name, z_size)
    else:
        assert abs(z_size - 1.5) <= 1e-5, (obj.name, z_size)
        assert abs(minimum_plan_width(plan) - 3.5) <= 1e-5, (obj.name, minimum_plan_width(plan))
print("V3 NOMINAL STOCK CROSS-SECTION AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_resolved_center_mating_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def edge(obj, side):
    bounds = generator.bounds(obj)
    return bounds[0] if side == "left" else bounds[1]

center_lower = [obj for obj in bpy.data.collections["CENTER_LOWER_FRAME"].objects
                if obj["purpose"] == "lower member"]
center_upper = [obj for obj in bpy.data.collections["CENTER_UPPER_FRAME"].objects
                if obj["purpose"] == "upper member"]
for module, side, wanted_x in (("LEFT", "right", 29.5), ("RIGHT", "left", -29.5)):
    center_member = min(center_lower, key=lambda obj: generator.bounds(obj)[0]) if side == "left" \
                    else max(center_lower, key=lambda obj: generator.bounds(obj)[1])
    side_inner = next(obj for obj in bpy.data.collections[f"{{module}}_LOWER_FRAME"].objects
                      if obj["board_type"] == "inner_rail")
    side_edge = generator.bounds(side_inner)[0] if side == "right" else generator.bounds(side_inner)[1]
    assert abs(edge(center_member, side) - wanted_x) <= 1e-5
    assert abs(side_edge - wanted_x) <= 1e-5
    assert not generator.structural_volume_overlap(center_member, side_inner)

right_member = min(center_upper, key=lambda obj: generator.bounds(obj)[0])
right_inner = next(obj for obj in bpy.data.collections["RIGHT_UPPER_FRAME"].objects
                   if obj["board_type"] == "inner_rail")
assert abs(generator.bounds(right_member)[0] + 29.5) <= 1e-5
assert abs(generator.bounds(right_inner)[1] + 29.5) <= 1e-5
assert not generator.structural_volume_overlap(right_member, right_inner)
print("V3 RESOLVED CENTER MATING AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_side_post_audit():
    code = f'''import sys
from collections import Counter
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def footprint(obj):
    z0 = min((obj.matrix_world @ point.co).z for point in obj.data.vertices)
    points = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        xy = (point.x, point.y)
        if abs(point.z - z0) <= 1e-9 and xy not in points:
            points.append(xy)
    return points

def z_bounds(obj):
    values = [(obj.matrix_world @ point.co).z for point in obj.data.vertices]
    return min(values), max(values)

def contained(inner, outer):
    return all(generator.point_in_polygon(point, outer) for point in inner)

for module, sign, expected_height, expected_top in (
    ("LEFT", 1, 10.75, 12.25), ("RIGHT", -1, 6.75, 8.25),
):
    posts = list(bpy.data.collections[f"{{module}}_POSTS"].objects)
    upper_objects = list(bpy.data.collections[f"{{module}}_UPPER_FRAME"].objects)
    lower_objects = list(bpy.data.collections[f"{{module}}_LOWER_FRAME"].objects)
    upper = {{obj["board_type"]: footprint(obj) for obj in upper_objects}}
    lower = {{obj["board_type"]: footprint(obj) for obj in lower_objects}}
    assert len(posts) == 7
    assert Counter(obj["post_role"] for obj in posts) == {{"rear": 2, "cross_brace": 2, "front": 3}}
    assert all(z_bounds(obj) == (1.5, expected_top) and obj["cut_length_in"] == expected_height
               for obj in posts)
    assert all(obj["module"] == module and obj["status"] == "PROVISIONAL / FIELD VERIFY"
               and obj["driver_access"] and obj["top_driver_access"] and obj["bottom_driver_access"]
               and obj["fastener_edge_distance_in"] >= 0.75
               and obj["plan_short_in"] == 1.5 and obj["plan_long_in"] == 3.5
               and obj["end_a_angle_deg"] == obj["end_b_angle_deg"] == 0.0
               and 0.0 <= obj["orientation_deg"] < 180.0
               for obj in posts)

    for post in posts:
        plan = footprint(post)
        role = post["post_role"]
        if role == "rear":
            assert contained(plan, lower["rear_closure"])
            assert contained(plan, upper["rear_closure"])
            assert max(y for _, y in plan) <= 10.5 + 1e-9
        elif role == "cross_brace":
            brace = post["support_member"]
            assert contained(plan, lower[brace]) and contained(plan, upper[brace])
            assert post["joint_clearance_in"] >= generator.MIN_CROSS_BRACE_JOINT_CLEARANCE
        else:
            path = post["upper_load_path"]
            rear_patch = [(x, y) for x, y in plan if y <= 28.0 + 1e-9]
            front_patch = [(x, y) for x, y in plan if y >= 28.0 - 1e-9]
            assert min(y for _, y in plan) == 25.5 and max(y for _, y in plan) == 29.0
            assert contained(plan, lower["front_rail"])
            assert contained(rear_patch, upper[path])
            assert contained(front_patch, upper["front_rail"])
            assert post["upper_path_bearing_in"] == 2.5
            assert post["upper_front_bearing_in"] == 1.0
            assert post["primary_fastening_member"] == path

    for index, post in enumerate(posts):
        for other in posts[index + 1:]:
            assert generator.polygons_overlap_area(footprint(post), footprint(other)) <= 1e-9

    outer = next(obj for obj in posts if obj["purpose"] == "cross-brace post outer")
    assert 45.0 <= abs(outer["post_rotation_deg"]) <= 48.0

pose = generator.fit_post_in_support([(0, 0), (6, 0), (6, 6), (0, 6)])
assert pose is not None and len(pose.footprint) == 4 and pose.clearance_in > 0
print("V3 SIDE POST AND FASTENING AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_finish_room_audit():
    code = '''import bpy

def bounds(obj):
    points = [obj.matrix_world @ point.co for point in obj.data.vertices]
    return tuple(value for axis in range(3) for value in (
        min(point[axis] for point in points), max(point[axis] for point in points)
    ))

decks = bpy.data.collections["PLYWOOD_DECKS"].objects
assert {obj.name for obj in decks} == {"CENTER_MAPLE_DECK", "LEFT_MAPLE_DECK", "RIGHT_MAPLE_DECK"}
assert bounds(bpy.data.objects["CENTER_MAPLE_DECK"])[4:] == (9.75, 10.5)
assert bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[4:] == (13.75, 14.5)
assert bounds(bpy.data.objects["RIGHT_MAPLE_DECK"])[4:] == (9.75, 10.5)
assert bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[1] == 62.0
assert bounds(bpy.data.objects["RIGHT_MAPLE_DECK"])[0] == -62.0
skins = [obj for obj in bpy.data.collections["MAPLE_FINISH"].objects if obj.get("purpose") == "front skin"]
assert len(skins) == 3 and all(bounds(obj)[4] == 3.0 for obj in skins)
assert bounds(bpy.data.objects["LEFT_FRONT_SKIN"])[1] == 62.0
assert bounds(bpy.data.objects["RIGHT_FRONT_SKIN"])[0] == -62.0
cushion = bpy.data.objects["CENTER_RIGHT_CUSHION_REFERENCE"]
assert bounds(cushion)[4:] == (10.5, 14.5)
assert bounds(cushion)[1] <= 29.5
sill = bpy.data.objects["SILL_UNDERSIDE_REFERENCE"]
assert bounds(sill)[4] == bounds(sill)[5] == 15.0
assert bounds(sill)[:2] == (-62.0, 62.0)
assert not (bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[4] < bounds(sill)[4] < bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[5])
assert {obj.name for obj in bpy.data.objects if obj.type == "CAMERA"} == {
    "TOP_ORTHO_COMPLETE", "FRONT_COMPLETE", "SIDE_COMPLETE", "ISOMETRIC_FRAMING_COMPLETE",
    "ISOMETRIC_FINISHED_COMPLETE", "ISOMETRIC_CENTER", "ISOMETRIC_LEFT", "ISOMETRIC_RIGHT",
}
assert all(bpy.data.objects[name].data.type == "ORTHO" for name in (
    "TOP_ORTHO_COMPLETE", "FRONT_COMPLETE", "SIDE_COMPLETE",
    "ISOMETRIC_FRAMING_COMPLETE", "ISOMETRIC_FINISHED_COMPLETE"))
assert bpy.data.objects["ISOMETRIC_LEFT"].location.x > 0
assert bpy.data.objects["ISOMETRIC_RIGHT"].location.x < 0
assert bpy.data.objects["SIDE_COMPLETE"].data.ortho_scale <= 45.0
assert {layer.name for layer in bpy.context.scene.view_layers} >= {"FRAMING_ONLY", "FINISHED"}
framing = bpy.context.scene.view_layers["FRAMING_ONLY"]
for name in ("PLYWOOD_DECKS", "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE"):
    assert framing.layer_collection.children[name].exclude
assert all(obj.get("status") == "PROVISIONAL / FIELD VERIFY"
           for obj in bpy.data.collections["ROOM_REFERENCE"].objects if obj.get("side_reference"))
print("V3 FINISH AND ROOM AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_foundation_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

assert generator.ACTUAL_2X4_THICKNESS == 1.5
assert generator.ACTUAL_2X4_WIDTH == 3.5
generator.main()
assert abs(bpy.context.scene.unit_settings.scale_length - 0.0254) <= 1e-9
assert len(bpy.data.collections) == 17
assert len(bpy.data.materials) == 5
assert len(bpy.data.objects) == 104
assert len(bpy.data.meshes) == 92

collection = bpy.data.collections["DIMENSIONS"]
material = bpy.data.materials["LIGHT_MAPLE"]
prism = generator.add_prism(
    "VALID_PRISM", [(0, 0), (1, 0), (1, 1), (0, 1)], 0, 1,
    collection, material, module="TEST",
)
assert {{item.name for item in prism.users_collection}} == {{"DIMENSIONS"}}
assert prism["module"] == "TEST"
assert len(prism.data.vertices) == 8

for footprint in (
    [(0, 0), (0, 1), (1, 1), (1, 0)],
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (1, 1), (0, 1), (1, 0)],
):
    try:
        generator.add_prism("INVALID_PRISM", footprint, 0, 1, collection, material)
    except AssertionError:
        pass
    else:
        raise AssertionError(f"accepted invalid footprint: {{footprint}}")

generator.main()
assert len(bpy.data.collections) == 17
assert len(bpy.data.objects) == 104
assert len(bpy.data.meshes) == 92
assert len(bpy.data.materials) == 5
print("V3 FOUNDATION AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def audit_final_artifacts():
    outputs = {
        "blend": ROOT / "bay_daybed_v3.blend",
        "generator": ROOT / "bay_daybed_v3_generator.py",
        "cutlist": ROOT / "bay_daybed_v3_cutlist.csv",
        "dimensions": ROOT / "bay_daybed_v3_dimensions.txt",
    }
    assert all(path.is_file() and path.stat().st_size > 0 for path in outputs.values()), outputs
    with outputs["cutlist"].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == [
            "MODULE", "OBJECT", "QUANTITY", "CUT_LENGTH_IN", "END_A_ANGLE_DEG",
            "END_B_ANGLE_DEG", "ORIENTATION", "STATUS",
        ]
    center = Counter()
    for row in rows:
        quantity = int(row["QUANTITY"])
        length = float(row["CUT_LENGTH_IN"])
        assert row["OBJECT"] and row["ORIENTATION"]
        if row["MODULE"] == "CENTER":
            assert row["STATUS"] == "RESOLVED"
            center[length] += quantity
        else:
            assert row["MODULE"] in {"LEFT", "RIGHT"}
            assert row["STATUS"] == "PROVISIONAL / FIELD VERIFY"
            assert quantity == 1
    assert center == {59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}
    assert Counter(row["MODULE"] for row in rows) == {"CENTER": 4, "LEFT": 21, "RIGHT": 21}
    report = outputs["dimensions"].read_text(encoding="utf-8")
    assert report.rstrip().endswith(WARNING)
    assert "long_edge/short_edge=" in report and "long/short=" not in report
    for text in (
        "CENTER MODULE", "4 x 59", "5 x 24.5", "4 x 22", "10 x 6.75",
        "LEFT MODULE", "RIGHT MODULE", "14.5", "10.5", "SIDE_REAR_STRUCTURAL_SETBACK = 8.0",
        "SIDE_DIAGONAL_RAIL_INSET = 1.0", "SIDE_CROSS_BRACE_CENTER_Y = 23.75",
        "Maximum unsupported plywood span", "PROVISIONAL / FIELD VERIFY",
    ):
        assert text in report, text
    post_lines = [line for line in report.splitlines()
                  if line.startswith("  ") and "_POST_" in line]
    assert len(post_lines) == 14
    assert all("joint_clearance_in=" in line and "fastener_edge_distance_in=" in line
               and "driver_clearance_prism_in=" in line for line in post_lines)


def run_final_saved_model_audit():
    code = f'''import sys
from collections import Counter
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

expected_collections = set(generator.COLLECTION_NAMES)
assert {{collection.name for collection in bpy.data.collections}} == expected_collections
assert {{layer.name for layer in bpy.context.scene.view_layers}} == {{"FRAMING_ONLY", "FINISHED"}}
assert bpy.context.scene.camera.name == "ISOMETRIC_FINISHED_COMPLETE"
assert len(bpy.data.collections["CENTER_UPPER_FRAME"].objects) == 7
assert len(bpy.data.collections["CENTER_LOWER_FRAME"].objects) == 6
assert len(bpy.data.collections["CENTER_POSTS"].objects) == 10
for module in ("LEFT", "RIGHT"):
    assert len(bpy.data.collections[f"{{module}}_UPPER_FRAME"].objects) == 7
    assert len(bpy.data.collections[f"{{module}}_LOWER_FRAME"].objects) == 7
    assert len(bpy.data.collections[f"{{module}}_POSTS"].objects) == 7

structural = [obj for obj in bpy.data.objects if obj.get("validation_group") == "STRUCTURAL"]
assert len(structural) == 65
required = {{"module", "purpose", "status", "cut_length_in", "centerline_length_in",
            "long_edge_in", "short_edge_in", "end_a_angle_deg", "end_b_angle_deg", "orientation_deg",
            "modeled_size_x_in", "modeled_size_y_in", "modeled_size_z_in"}}
assert all(required <= set(obj.keys()) for obj in structural)
assert all(obj["status"] == "PROVISIONAL / FIELD VERIFY"
           for obj in structural if obj["module"] in {{"LEFT", "RIGHT"}})
for index, obj in enumerate(structural):
    for other in structural[index + 1:]:
        assert not generator.structural_volume_overlap(obj, other), (obj.name, other.name)

assert generator.SIDE_REAR_STRUCTURAL_SETBACK == 8.0
assert generator.SIDE_DIAGONAL_RAIL_INSET == 1.0
assert generator.SIDE_CROSS_BRACE_CENTER_Y == 23.75
assert min(generator.bounds(obj)[2] for obj in structural if obj["module"] != "CENTER") >= 8.0
assert generator.bounds(bpy.data.objects["CENTER_MAPLE_DECK"])[5] == 10.5
assert generator.bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[5] == 14.5
assert generator.bounds(bpy.data.objects["RIGHT_MAPLE_DECK"])[5] == 10.5
assert generator.bounds(bpy.data.objects["CENTER_RIGHT_CUSHION_REFERENCE"])[5] == 14.5
assert min(x for x, _ in generator.side_finished_vertices("LEFT")) >= 30.0
assert max(x for x, _ in generator.side_finished_vertices("RIGHT")) <= -30.0
assert generator.bounds(bpy.data.objects["SILL_UNDERSIDE_REFERENCE"])[4] == 15.0

for module, sign in (("LEFT", 1), ("RIGHT", -1)):
    upper = {{obj["board_type"]: generator._local_object_footprint(sign, obj)
             for obj in bpy.data.collections[f"{{module}}_UPPER_FRAME"].objects}}
    lower = {{obj["board_type"]: generator._local_object_footprint(sign, obj)
             for obj in bpy.data.collections[f"{{module}}_LOWER_FRAME"].objects}}
    diagonal = upper["diagonal_rail"]
    assert all(0 <= u <= generator.finished_outer_u(y) + 1e-9 for u, y in diagonal)
    scale = 2 ** .5
    assert all(abs((generator.finished_outer_u(y) - max(u for u, yy in diagonal if yy == y))
                       / scale - 1.0) <= 1e-5 for y in {{yy for _, yy in diagonal}})
    for brace in ("cross_brace_inner", "cross_brace_outer"):
        assert generator.polygons_overlap_area(lower[brace], lower["front_rail"]) <= 1e-9
        assert max(y for _, y in lower[brace]) == min(y for _, y in lower["front_rail"]) == 25.5
    for post in bpy.data.collections[f"{{module}}_POSTS"].objects:
        assert post["driver_access"] and post["top_driver_access"] and post["bottom_driver_access"]
        assert post["fastener_edge_distance_in"] >= .75
        if post["post_role"] == "cross_brace":
            assert post["joint_clearance_in"] >= 1.0

assert Counter(round(obj["cut_length_in"], 6) for obj in structural if obj["module"] == "CENTER") == {{
    59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10,
}}
print("V3 SAVED MODEL AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr


def run_render_audit():
    target = Path(tempfile.gettempdir()) / "bay_daybed_v3_render_audit"
    target.mkdir(exist_ok=True)
    code = f'''import bpy
from pathlib import Path
target = Path({str(target)!r})
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 900
scene.render.resolution_y = 650
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
views = (
    ("FINISHED", "TOP_ORTHO_COMPLETE", "top.png"),
    ("FINISHED", "FRONT_COMPLETE", "front.png"),
    ("FRAMING_ONLY", "SIDE_COMPLETE", "side.png"),
    ("FRAMING_ONLY", "ISOMETRIC_FRAMING_COMPLETE", "framing.png"),
    ("FINISHED", "ISOMETRIC_FINISHED_COMPLETE", "finished.png"),
    ("FINISHED", "ISOMETRIC_CENTER", "center.png"),
    ("FINISHED", "ISOMETRIC_LEFT", "left.png"),
    ("FINISHED", "ISOMETRIC_RIGHT", "right.png"),
)
assert bpy.data.objects["SIDE_COMPLETE"].data.ortho_scale <= 45.0
assert bpy.data.objects["SIDE_COMPLETE"]["inspection_layer"] == "FRAMING_ONLY"
assert scene.view_layers["FRAMING_ONLY"].layer_collection.children["ROOM_REFERENCE"].exclude
assert all(obj.show_in_front and obj.data.size >= 1.25
           for obj in bpy.data.collections["DIMENSIONS"].objects)
for _, _, filename in views:
    path = target / filename
    if path.exists():
        path.unlink()
for layer_name, camera_name, filename in views:
    scene.camera = bpy.data.objects[camera_name]
    scene.render.filepath = str(target / filename)
    bpy.context.window.view_layer = scene.view_layers[layer_name]
    bpy.ops.render.render(write_still=True, layer=layer_name)
assert all((target / filename).is_file() and (target / filename).stat().st_size > 1000
           for _, _, filename in views)
print("V3 RENDER AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr, target


def run_radial_profile_cut_audit():
    code = f'''import csv
import math
import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def parsed(value):
    return [float(item) for item in str(value).split("|")]

for module, sign in (("LEFT", 1), ("RIGHT", -1)):
    for level, y1 in (("UPPER", 28.0), ("LOWER", 25.5)):
        radial = next(obj for obj in bpy.data.collections[f"{{module}}_{{level}}_FRAME"].objects
                      if obj["board_type"] == "radial_rail")
        footprint = generator._local_object_footprint(sign, radial)
        y0 = min(y for _, y in footprint)
        expected = (max(y for _, y in footprint) - y0) * math.sqrt(
            1.0 + (generator.SIDE_RUN / generator.DAYBED_FINISHED_DEPTH / 2.0) ** 2)
        assert abs(radial["cut_length_in"] - expected) <= generator.METADATA_TOLERANCE
        assert radial["cut_profile"] == "CUSTOM NOTCHED REAR PROFILE"
        axis = (generator.SIDE_RUN / generator.DAYBED_FINISHED_DEPTH / 2.0, 1.0)
        axis_length = math.hypot(*axis)
        unit = (axis[0] / axis_length, axis[1] / axis_length)
        normal = (-unit[1], unit[0])
        rear_segments = []
        for start, end in zip(footprint, footprint[1:] + footprint[:1]):
            direction = (end[0] - start[0], end[1] - start[1])
            if abs(direction[0] * axis[1] - direction[1] * axis[0]) <= 1e-5:
                continue
            if abs(start[1] - y1) <= 1e-5 and abs(end[1] - y1) <= 1e-5:
                continue
            rear_segments.append(direction)
        assert len(rear_segments) == 3
        cut_angles = [math.degrees(math.atan2(
            abs(direction[0] * unit[0] + direction[1] * unit[1]),
            abs(direction[0] * normal[0] + direction[1] * normal[1])))
            for direction in rear_segments]
        segment_angles = [math.degrees(math.atan2(direction[1], direction[0])) % 180
                          for direction in rear_segments]
        assert all(abs(actual - expected_angle) <= generator.METADATA_TOLERANCE
                   for actual, expected_angle in zip(parsed(radial["end_a_angle_deg"]), cut_angles))
        assert all(abs(actual - expected_angle) <= generator.METADATA_TOLERANCE for actual, expected_angle in zip(
            parsed(radial["rear_profile_segment_orientations_deg"]), segment_angles))
        assert "CUSTOM NOTCHED REAR PROFILE" in radial["orientation_note"]
print("V3 RADIAL PROFILE/CUT AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V3 RADIAL PROFILE/CUT AUDIT PASSED" in output, output
    with (ROOT / "bay_daybed_v3_cutlist.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if "RADIAL_RAIL" in row["OBJECT"]]
    assert len(rows) == 4
    assert all("|" in row["END_A_ANGLE_DEG"]
               and "CUSTOM NOTCHED REAR PROFILE" in row["ORIENTATION"]
               and "LONG EDGE" in row["ORIENTATION"] and "SHORT EDGE" in row["ORIENTATION"]
               and row["STATUS"] == "PROVISIONAL / FIELD VERIFY" for row in rows)


def run_finish_contact_and_nailer_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def volume_overlap(a, b):
    az, bz = generator.bounds(a)[4:], generator.bounds(b)[4:]
    return (min(az[1], bz[1]) - max(az[0], bz[0]) > 1e-6
            and generator.polygons_overlap_area(
                generator.object_footprint(a), generator.object_footprint(b)) > 1e-6)

finish = []
for collection in ("PLYWOOD_DECKS", "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE"):
    finish.extend(bpy.data.collections[collection].objects)
assert not [(a.name, b.name) for index, a in enumerate(finish)
            for b in finish[index + 1:] if volume_overlap(a, b)]
for module in ("CENTER", "LEFT", "RIGHT"):
    deck = bpy.data.objects[f"{{module}}_MAPLE_DECK"]
    skin = bpy.data.objects[f"{{module}}_FRONT_SKIN"]
    assert abs(generator.bounds(skin)[5] - generator.bounds(deck)[4]) <= 1e-6
    assert generator.polygons_overlap_area(
        generator.object_footprint(deck), generator.object_footprint(skin)) > 1e-6
    nailers = [obj for obj in bpy.data.collections["FRONT_PANEL_NAILERS"].objects
               if obj["module"] == module]
    skin_bounds = generator.bounds(skin)
    lower_top = max(generator.bounds(obj)[5]
                    for obj in bpy.data.collections[f"{{module}}_LOWER_FRAME"].objects)
    for nailer in nailers:
        nailer_bounds = generator.bounds(nailer)
        assert abs(nailer_bounds[3] - skin_bounds[2]) <= 1e-6
        assert min(nailer_bounds[1], skin_bounds[1]) - max(nailer_bounds[0], skin_bounds[0]) > 0
        assert min(nailer_bounds[5], skin_bounds[5]) - max(nailer_bounds[4], skin_bounds[4]) > 0
        assert nailer_bounds[4] - lower_top >= 2.0 - 1e-6
print("V3 FINISH CONTACT/NAILER AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V3 FINISH CONTACT/NAILER AUDIT PASSED" in output, output


def run_side_fastening_path_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def decode(value):
    return [tuple(float(number) for number in point.split(","))
            for point in str(value).split(";")]

for module, sign in (("LEFT", 1), ("RIGHT", -1)):
    posts = list(bpy.data.collections[f"{{module}}_POSTS"].objects)
    for level in ("UPPER", "LOWER"):
        objects = list(bpy.data.collections[f"{{module}}_{{level}}_FRAME"].objects)
        by_type = {{obj["board_type"]: obj for obj in objects}}
        local = {{key: generator._local_object_footprint(sign, obj) for key, obj in by_type.items()}}
        closure = by_type["rear_closure"]
        assert closure["rear_fastening_method"] == \
            "STRAIGHT FROM REAR DURING MODULE ASSEMBLY THROUGH CLOSURE INTO RAIL END"
        assert closure["rear_inner_interface_in"] >= 3.5 - 1e-6
        assert closure["rear_diagonal_interface_in"] >= generator.MIN_REAR_FASTENING_INTERFACE
        for target in ("inner", "diagonal"):
            assert closure[f"rear_{{target}}_driver_access"]
            prism = decode(closure[f"rear_{{target}}_driver_prism_local"])
            assert max(y for _, y in prism) <= generator.SIDE_REAR_STRUCTURAL_SETBACK + 1e-6
            assert min(y for _, y in prism) <= generator.SIDE_REAR_STRUCTURAL_SETBACK - 5.0 + 1e-6
            assert all(generator.polygons_overlap_area(prism, footprint) <= 1e-6
                       for footprint in local.values())
        for brace_type, opposing_type in (("cross_brace_inner", "cross_brace_outer"),
                                           ("cross_brace_outer", "cross_brace_inner")):
            brace = by_type[brace_type]
            assert brace["radial_joint_fastening_method"] == \
                "ANGLED TOE-SCREW/PILOT FROM EXPOSED BRACE TOP/SIDE INTO RADIAL; NO THROUGH-RADIAL PATH"
            assert brace["radial_joint_driver_access"]
            assert brace["radial_joint_post_clearance_in"] >= generator.MIN_CROSS_BRACE_JOINT_CLEARANCE
            prism = decode(brace["radial_joint_driver_prism_local"])
            assert all(generator.point_in_polygon(point, local[brace_type]) for point in prism)
            post = next(item for item in posts if item.get("support_member") == brace_type)
            post_plan = generator._local_object_footprint(sign, post)
            assert generator.polygons_overlap_area(prism, post_plan) <= 1e-6
            assert generator.polygons_overlap_area(prism, local[opposing_type]) <= 1e-6
            assert generator.polygons_overlap_area(prism, local["radial_rail"]) <= 1e-6
            for key, footprint in local.items():
                if key not in {{brace_type, opposing_type, "radial_rail"}}:
                    assert generator.polygons_overlap_area(prism, footprint) <= 1e-6, key
report = open({str(ROOT / 'bay_daybed_v3_dimensions.txt')!r}, encoding="utf-8").read()
assert "REAR CLOSURE FASTENING ACCESS" in report
assert "CROSS-BRACE FASTENING ACCESS" in report
assert "NO THROUGH-RADIAL PATH" in report
print("V3 SIDE JOINT FASTENING-PATH AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V3 SIDE JOINT FASTENING-PATH AUDIT PASSED" in output, output


def run_connection_marker_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

markers = list(bpy.data.collections["MODULE_CONNECTION_REFERENCE"].objects)
assert len(markers) == 3
assert {{obj.name for obj in markers}} == {{
    "LEFT_LOWER_FRONT_CONNECTION_ZONE", "RIGHT_LOWER_FRONT_CONNECTION_ZONE",
    "RIGHT_UPPER_FRONT_CONNECTION_ZONE",
}}
for marker in markers:
    assert marker["validation_group"] == "NONSTRUCTURAL"
    center = bpy.data.objects[marker["center_support_object"]]
    side = bpy.data.objects[marker["side_support_object"]]
    marker_bounds = generator.bounds(marker)
    center_bounds, side_bounds = generator.bounds(center), generator.bounds(side)
    assert abs(marker_bounds[0] - marker_bounds[1]) <= 1e-6
    assert abs(marker_bounds[0] - center_bounds[1 if marker_bounds[0] > 0 else 0]) <= 1e-5
    assert abs(marker_bounds[0] - side_bounds[0 if marker_bounds[0] > 0 else 1]) <= 1e-5
    assert marker_bounds[2] >= max(center_bounds[2], side_bounds[2]) - 1e-6
    assert marker_bounds[3] <= min(center_bounds[3], side_bounds[3]) + 1e-6
    assert marker_bounds[4] >= max(center_bounds[4], side_bounds[4]) - 1e-6
    assert marker_bounds[5] <= min(center_bounds[5], side_bounds[5]) + 1e-6
print("V3 MODULE CONNECTION MARKER AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V3 MODULE CONNECTION MARKER AUDIT PASSED" in output, output


def run_setback_and_room_angle_audit():
    setback = _run_isolated_success(r'''import sys
from pathlib import Path
sys.path.insert(0, r"{folder}")
import bpy
import bay_daybed_v3_generator as generator
generator.SIDE_REAR_STRUCTURAL_SETBACK = 9.0
generator.main()
for module in ("LEFT", "RIGHT"):
    for level, end_y in (("UPPER", 28.0), ("LOWER", 25.5)):
        objects = list(bpy.data.collections[f"{{module}}_{{level}}_FRAME"].objects)
        closure = next(obj for obj in objects if obj["board_type"] == "rear_closure")
        assert generator.bounds(closure)[2:4] == (9.0, 12.5)
        assert all(generator.bounds(obj)[2] >= 12.5 - 1e-6
                   for obj in objects if obj["board_type"] in
                   {{"inner_rail", "radial_rail", "diagonal_rail"}})
report = Path(r"{folder}", "bay_daybed_v3_dimensions.txt").read_text(encoding="utf-8")
assert "SIDE_REAR_STRUCTURAL_SETBACK = 9.0" in report
assert "Rear-tip cantilever = 12.727922" in report
assert "SIDE_REAR_STRUCTURAL_SETBACK = 8.0" not in report
print("V3 SETBACK 9 PARAMETRIC AUDIT PASSED")''')
    assert "V3 VALIDATION PASSED" in setback, setback
    assert "V3 SETBACK 9 PARAMETRIC AUDIT PASSED" in setback, setback

    angle = _run_isolated_success(r'''import math, sys
from pathlib import Path
sys.path.insert(0, r"{folder}")
import bpy
import bay_daybed_v3_generator as generator
generator.APPROX_SIDE_WALL_ANGLE = 50.0
generator.main()
expected_outer = 30.0 + 32.0 * math.tan(math.radians(50.0))
assert generator.side_finished_vertices("LEFT")[1][0] == 62.0
assert abs(generator.side_wall_endpoints("LEFT")[1][0] - expected_outer) <= 1e-9
wall = bpy.data.objects["LEFT_ANGLED_WALL_REFERENCE"]
assert wall["approx_wall_angle_deg"] == 50.0
assert abs(wall["approx_wall_run_in"] - 32.0 * math.tan(math.radians(50.0))) <= 1e-6
report = Path(r"{folder}", "bay_daybed_v3_dimensions.txt").read_text(encoding="utf-8")
assert "APPROX_SIDE_WALL_ANGLE = 50.0" in report
print("V3 ROOM WALL ANGLE PARAMETRIC AUDIT PASSED")''')
    assert "V3 VALIDATION PASSED" in angle, angle
    assert "V3 ROOM WALL ANGLE PARAMETRIC AUDIT PASSED" in angle, angle


def run_structural_name_audit():
    code = f'''import re
import sys
sys.path.insert(0, {str(ROOT)!r})
import bpy
import bay_daybed_v3_generator as generator

def token(value):
    return f"{{float(value):.3f}}".rstrip("0").rstrip(".").replace(".", "p")

structural = [obj for obj in bpy.data.objects if obj.get("validation_group") == "STRUCTURAL"]
assert len(structural) == 65 and len({{obj.name for obj in structural}}) == 65
for obj in structural:
    assert obj["name_function"] in obj.name
    assert f"_CUT{{token(obj['cut_length_in'])}}IN_" in obj.name
    bounds = generator.bounds(obj)
    if obj["module"] == "CENTER":
        dimensions = "x".join(token(bounds[index + 1] - bounds[index]) for index in (0, 2, 4))
        assert f"_{{dimensions}}_" in obj.name and obj.name.endswith("_RESOLVED")
    elif "post_role" in obj:
        dimensions = f"1p5x3p5x{{token(obj['cut_length_in'])}}"
        assert f"_{{dimensions}}_" in obj.name and obj.name.endswith("_PROV")
    else:
        assert "_3p5x1p5_" in obj.name and "_PROV" in obj.name
        if obj["board_type"] == "radial_rail":
            assert obj.name.endswith("_PROV_NOTCHED")
print("V3 STRUCTURAL NAME AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", code], cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V3 STRUCTURAL NAME AUDIT PASSED" in output, output
    with (ROOT / "bay_daybed_v3_cutlist.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    side_csv_names = {row["OBJECT"] for row in rows if row["MODULE"] in {"LEFT", "RIGHT"}}
    saved_names_code = '''import bpy
print("SIDE_NAMES=" + "|".join(sorted(obj.name for obj in bpy.data.objects
      if obj.get("validation_group") == "STRUCTURAL" and obj["module"] in {"LEFT", "RIGHT"})))'''
    result = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "bay_daybed_v3.blend"),
         "--python-expr", saved_names_code], cwd=ROOT, capture_output=True, text=True,
    )
    line = next(item for item in (result.stdout + result.stderr).splitlines()
                if item.startswith("SIDE_NAMES="))
    assert side_csv_names == set(line.removeprefix("SIDE_NAMES=").split("|"))


def run_fail_closed_audit():
    outputs = [ROOT / "bay_daybed_v3.blend", ROOT / "bay_daybed_v3_cutlist.csv",
               ROOT / "bay_daybed_v3_dimensions.txt"]
    before = [(path.stat().st_size, path.stat().st_mtime_ns) for path in outputs]
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bay_daybed_v3_generator as generator
generator.MAX_UNSUPPORTED_DECK_SPAN = 10.0
generator.main()'''
    result = subprocess.run(
        [str(BLENDER), "--background", "--python-expr", code],
        cwd=ROOT, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    after = [(path.stat().st_size, path.stat().st_mtime_ns) for path in outputs]
    assert "V3 VALIDATION CONFLICT:" in output, output
    assert "unsupported plywood spans exceed 10.0" in output, output
    assert "V3 VALIDATION PASSED" not in output, output
    assert "Traceback" in output, output
    assert before == after, (before, after)
    return output


def _run_isolated_generator(code):
    with tempfile.TemporaryDirectory(prefix="bay_daybed_v3_validation_") as folder:
        isolated = Path(folder)
        shutil.copy2(ROOT / "bay_daybed_v3_generator.py", isolated / "bay_daybed_v3_generator.py")
        outputs = [isolated / "bay_daybed_v3.blend", isolated / "bay_daybed_v3_cutlist.csv",
                   isolated / "bay_daybed_v3_dimensions.txt"]
        for path in outputs:
            path.write_bytes(b"UNCHANGED")
        result = subprocess.run(
            [str(BLENDER), "--background", "--python-expr", code.format(folder=str(isolated))],
            cwd=isolated, capture_output=True, text=True,
        )
        output = result.stdout + result.stderr
        assert all(path.read_bytes() == b"UNCHANGED" for path in outputs), output
        return output


def _run_isolated_success(code):
    with tempfile.TemporaryDirectory(prefix="bay_daybed_v3_parametric_") as folder:
        isolated = Path(folder)
        shutil.copy2(ROOT / "bay_daybed_v3_generator.py", isolated / "bay_daybed_v3_generator.py")
        result = subprocess.run(
            [str(BLENDER), "--background", "--python-expr", code.format(folder=str(isolated))],
            cwd=isolated, capture_output=True, text=True,
        )
        return result.stdout + result.stderr


def run_metadata_corruption_audit():
    output = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
original = generator.build_side_frame
def corrupt(*args, **kwargs):
    objects = original(*args, **kwargs)
    for obj in objects:
        if (obj["module"] == "RIGHT" and obj["frame_level"] == "UPPER"
                and obj["board_type"] == "diagonal_rail"):
            for key in ("cut_length_in", "centerline_length_in", "long_edge_in", "short_edge_in"):
                obj[key] = 999.0
    return objects
generator.build_side_frame = corrupt
generator.main()''')
    assert "V3 VALIDATION CONFLICT: RIGHT_UPPER_DIAGONAL_RAIL" in output, output
    assert "999" in output and "recomputed" in output, output
    assert "V3 VALIDATION PASSED" not in output, output

    radial_edges = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
original = generator.build_side_frame
def corrupt(*args, **kwargs):
    objects = original(*args, **kwargs)
    for obj in objects:
        if (obj["module"] == "RIGHT" and obj["frame_level"] == "LOWER"
                and obj["board_type"] == "radial_rail"):
            obj["long_edge_in"] = 999.0
            obj["short_edge_in"] = 998.0
    return objects
generator.build_side_frame = corrupt
generator.main()''')
    assert "V3 VALIDATION CONFLICT: RIGHT_LOWER_RADIAL_RAIL" in radial_edges, radial_edges
    assert "long_edge_in metadata 999" in radial_edges and "recomputed" in radial_edges, radial_edges
    assert "V3 VALIDATION PASSED" not in radial_edges, radial_edges

    radial = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
original = generator.build_side_frame
def corrupt(*args, **kwargs):
    objects = original(*args, **kwargs)
    for obj in objects:
        if (obj["module"] == "LEFT" and obj["frame_level"] == "UPPER"
                and obj["board_type"] == "radial_rail"):
            obj["end_a_angle_deg"] = "0|0|0"
            obj["rear_profile_segment_orientations_deg"] = "0|0|0"
    return objects
generator.build_side_frame = corrupt
generator.main()''')
    assert "V3 VALIDATION CONFLICT: LEFT_UPPER_RADIAL_RAIL" in radial, radial
    assert "custom profile" in radial.lower() or "notched profile" in radial.lower(), radial
    assert "V3 VALIDATION PASSED" not in radial, radial


def run_cross_section_corruption_audit():
    output = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
original = generator.build_center
def corrupt(*args, **kwargs):
    center = original(*args, **kwargs)
    member = next(obj for obj in center["upper"] if obj["purpose"] == "upper member")
    center_x = sum(vertex.co.x for vertex in member.data.vertices) / len(member.data.vertices)
    for vertex in member.data.vertices:
        vertex.co.x = center_x + (vertex.co.x - center_x) / 2.0
    member["modeled_size_x_in"] = 1.75
    return center
generator.build_center = corrupt
generator.validate_center = lambda center: []
generator.main()''')
    assert "V3 VALIDATION CONFLICT: CENTER_UPPER_MEMBER" in output, output
    assert "flat 2x4 plan width" in output and "expected 3.5" in output, output
    assert "V3 VALIDATION PASSED" not in output, output


def run_parameter_conflict_audit():
    output = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.SIDE_ANGLE = 44.0
generator.main()''')
    assert "V3 VALIDATION CONFLICT: SIDE_ANGLE" in output, output
    assert "44" in output and "45" in output, output
    assert "V3 VALIDATION PASSED" not in output, output


def run_parametric_vertex_audit():
    code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import bay_daybed_v3_generator as generator
generator.SIDE_RUN = 30.0
assert generator.side_finished_vertices("LEFT") == [(30.0, 0.0), (60.0, 32.0), (30.0, 32.0)]
assert generator.side_finished_vertices("RIGHT") == [(-30.0, 0.0), (-30.0, 32.0), (-60.0, 32.0)]
assert "(60, 32)" in generator.format_side_finished_vertices("LEFT")
assert "(-60, 32)" in generator.format_side_finished_vertices("RIGHT")
print("V3 PARAMETRIC REPORT VERTEX AUDIT PASSED")'''
    result = subprocess.run(
        [str(BLENDER), "--background", "--python-expr", code], cwd=ROOT,
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert "V3 PARAMETRIC REPORT VERTEX AUDIT PASSED" in output, output


def run_total_width_conflict_audit():
    output = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 125.0
generator.main()''')
    assert "V3 VALIDATION CONFLICT: PROVISIONAL_TOTAL_FRONT_WIDTH" in output, output
    assert "125" in output and "124" in output, output
    assert "V3 VALIDATION PASSED" not in output, output


def run_side_parameter_generation_audit():
    run34 = _run_isolated_success(r'''import sys, math
from pathlib import Path
sys.path.insert(0, r"{folder}")
import bpy
import bay_daybed_v3_generator as generator
generator.SIDE_RUN = 34.0
generator.SIDE_ANGLE = math.degrees(math.atan2(34.0, 32.0))
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 128.0
generator.main()
assert generator.bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[1] == 64.0
assert generator.bounds(bpy.data.objects["RIGHT_MAPLE_DECK"])[0] == -64.0
assert generator.bounds(bpy.data.objects["LEFT_FRONT_SKIN"])[1] == 64.0
assert generator.bounds(bpy.data.objects["RIGHT_FRONT_SKIN"])[0] == -64.0
assert generator.bounds(bpy.data.objects["SILL_UNDERSIDE_REFERENCE"])[:2] == (-64.0, 64.0)
left_wall = generator.object_footprint(bpy.data.objects["LEFT_ANGLED_WALL_REFERENCE"])
right_wall = generator.object_footprint(bpy.data.objects["RIGHT_ANGLED_WALL_REFERENCE"])
assert abs((left_wall[1][0] + left_wall[2][0]) / 2 - 62.0) <= 1e-5
assert abs((right_wall[1][0] + right_wall[2][0]) / 2 + 62.0) <= 1e-5
report = Path(r"{folder}", "bay_daybed_v3_dimensions.txt").read_text(encoding="utf-8")
assert "Finished plan vertices: (-30, 0), (-30, 32), (-64, 32)." in report
assert "Finished plan vertices: (30, 0), (64, 32), (30, 32)." in report
assert "Provisional front width = 128.0" in report
assert bpy.data.objects["DIMENSION_TOTAL_FRONT_WIDTH_PROVISIONAL"].data.body.startswith('128" PROVISIONAL')
print("V3 SIDE_RUN 34 PARAMETRIC GENERATION AUDIT PASSED")''')
    assert "V3 VALIDATION PASSED" in run34, run34
    assert "V3 SIDE_RUN 34 PARAMETRIC GENERATION AUDIT PASSED" in run34, run34

    run30 = _run_isolated_success(r'''import sys, math
from pathlib import Path
sys.path.insert(0, r"{folder}")
import bpy
import bay_daybed_v3_generator as generator
generator.SIDE_RUN = 30.0
generator.SIDE_ANGLE = math.degrees(math.atan2(30.0, 32.0))
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 120.0
generator.main()
assert generator.bounds(bpy.data.objects["LEFT_MAPLE_DECK"])[1] == 60.0
assert generator.bounds(bpy.data.objects["RIGHT_MAPLE_DECK"])[0] == -60.0
assert generator.bounds(bpy.data.objects["LEFT_FRONT_SKIN"])[1] == 60.0
assert generator.bounds(bpy.data.objects["RIGHT_FRONT_SKIN"])[0] == -60.0
assert generator.bounds(bpy.data.objects["SILL_UNDERSIDE_REFERENCE"])[:2] == (-60.0, 60.0)
report = Path(r"{folder}", "bay_daybed_v3_dimensions.txt").read_text(encoding="utf-8")
assert "Finished plan vertices: (-30, 0), (-30, 32), (-60, 32)." in report
assert "Finished plan vertices: (30, 0), (60, 32), (30, 32)." in report
assert "Provisional front width = 120.0" in report
dimension = bpy.data.objects["DIMENSION_TOTAL_FRONT_WIDTH_PROVISIONAL"].data.body
assert dimension.startswith('120" PROVISIONAL')
print("V3 SIDE_RUN 30 PARAMETRIC GENERATION AUDIT PASSED")''')
    assert "V3 VALIDATION PASSED" in run30, run30
    assert "V3 SIDE_RUN 30 PARAMETRIC GENERATION AUDIT PASSED" in run30, run30


def run_resolved_interface_and_side_feasibility_audit():
    center_width = _run_isolated_generator(r'''import sys
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.CENTER_FLAT_WALL_WIDTH = 62.0
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 126.0
generator.main()''')
    assert "V3 VALIDATION CONFLICT: CENTER_FLAT_WALL_WIDTH" in center_width, center_width
    assert "62" in center_width and "60" in center_width and "resolved center" in center_width.lower()

    depth = _run_isolated_generator(r'''import sys, math
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.DAYBED_FINISHED_DEPTH = 34.0
generator.SIDE_ANGLE = math.degrees(math.atan2(generator.SIDE_RUN, 34.0))
generator.main()''')
    assert "V3 VALIDATION CONFLICT: DAYBED_FINISHED_DEPTH" in depth, depth
    assert "34" in depth and "32" in depth and "resolved center" in depth.lower()

    run20 = _run_isolated_generator(r'''import sys, math
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.SIDE_RUN = 20.0
generator.SIDE_ANGLE = math.degrees(math.atan2(20.0, 32.0))
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 100.0
generator.main()''')
    assert "V3 VALIDATION CONFLICT: SIDE_RUN 20" in run20, run20
    assert "rear closure" in run20.lower() and "usable width" in run20.lower(), run20
    assert "required" in run20.lower(), run20

    run_tiny = _run_isolated_generator(r'''import sys, math
sys.path.insert(0, r"{folder}")
import bay_daybed_v3_generator as generator
generator.SIDE_RUN = 0.1
generator.SIDE_ANGLE = math.degrees(math.atan2(0.1, 32.0))
generator.PROVISIONAL_TOTAL_FRONT_WIDTH = 60.2
generator.main()''')
    assert "V3 VALIDATION CONFLICT: SIDE_RUN 0.1" in run_tiny, run_tiny
    assert "rear closure" in run_tiny.lower() and "usable width" in run_tiny.lower(), run_tiny
    assert "required" in run_tiny.lower(), run_tiny


def main():
    result, output = run_generator()
    assert result.returncode == 0, output
    assert "V3 PARAMETER AND POLYGON VALIDATION PASSED" in output, output
    assert "V3 SIDE FRAME VALIDATION PASSED" in output, output
    assert "V3 VALIDATION PASSED" in output, output
    audit_final_artifacts()
    result, output = run_foundation_audit()
    assert result.returncode == 0, output
    assert "V3 FOUNDATION AUDIT PASSED" in output, output
    result, output = run_center_audit()
    assert result.returncode == 0, output
    assert "V3 CENTER AUDIT PASSED" in output, output
    result, output = run_nominal_stock_cross_section_audit()
    assert result.returncode == 0, output
    assert "V3 NOMINAL STOCK CROSS-SECTION AUDIT PASSED" in output, output
    result, output = run_resolved_center_mating_audit()
    assert result.returncode == 0, output
    assert "V3 RESOLVED CENTER MATING AUDIT PASSED" in output, output
    result, output = run_side_frame_audit()
    assert result.returncode == 0, output
    assert "V3 SIDE FRAME AUDIT PASSED" in output, output
    result, output = run_side_post_audit()
    assert result.returncode == 0, output
    assert "V3 SIDE POST AND FASTENING AUDIT PASSED" in output, output
    result, output = run_finish_room_audit()
    assert result.returncode == 0, output
    assert "V3 FINISH AND ROOM AUDIT PASSED" in output, output
    result, output = run_final_saved_model_audit()
    assert result.returncode == 0, output
    assert "V3 SAVED MODEL AUDIT PASSED" in output, output
    run_radial_profile_cut_audit()
    run_finish_contact_and_nailer_audit()
    run_side_fastening_path_audit()
    run_connection_marker_audit()
    run_structural_name_audit()
    result, output, target = run_render_audit()
    assert result.returncode == 0, output
    assert "V3 RENDER AUDIT PASSED" in output, output
    run_fail_closed_audit()
    run_metadata_corruption_audit()
    run_cross_section_corruption_audit()
    run_parameter_conflict_audit()
    run_parametric_vertex_audit()
    run_total_width_conflict_audit()
    run_side_parameter_generation_audit()
    run_resolved_interface_and_side_feasibility_audit()
    run_setback_and_room_angle_audit()
    print(f"V3 RENDER DIRECTORY: {target}")
    print("V3 SIDE POST AND FASTENING VALIDATION PASSED")
    print("V3 FINISH AND ROOM VALIDATION PASSED")
    print("V3 FINAL ARTIFACT AUDIT PASSED")


if __name__ == "__main__":
    main()
