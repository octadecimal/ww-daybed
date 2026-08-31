import math
import csv
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import bpy
from mathutils import Vector


CENTER_FLAT_WALL_WIDTH = 60.0
DAYBED_FINISHED_DEPTH = 32.0
APPROX_SIDE_WALL_ANGLE = 45.0
APPROX_SILL_UNDERSIDE_HEIGHT = 15.0
APPROX_SILL_PROJECTION = 2.5
MEASURED_CORNER_TO_CORNER_WIDTH = 106.0
FACET_CENTER_FLAT = 5.0
FACET_TRANSITION = 1.0
PROVISIONAL_TOTAL_FRONT_WIDTH = 124.0
SIDE_RUN = 32.0
SIDE_ANGLE = 45.0
SIDE_REAR_STRUCTURAL_SETBACK = 8.0
SIDE_DIAGONAL_RAIL_INSET = 1.0
SIDE_CROSS_BRACE_CENTER_Y = 23.75
SIDE_FRONT_RECESS = 2.5
MAX_UNSUPPORTED_DECK_SPAN = 16.0
MIN_REAR_FASTENING_INTERFACE = 2.75
MIN_CROSS_BRACE_JOINT_CLEARANCE = 1.0
ACTUAL_2X4_THICKNESS = 1.5
ACTUAL_2X4_WIDTH = 3.5
PRIMARY_FRONT_POST_FASTENING = "Primary top fastening: through the upper front-to-back member into the post."
PROVISIONAL_STATUS = "PROVISIONAL / FIELD VERIFY"
SIDE_UPPER_BOTTOM_Z = {"LEFT": 12.25, "RIGHT": 8.25}
METADATA_TOLERANCE = 1e-4
# ponytail: Blender stores mesh coordinates as float32; overlaps below this square-inch area are boundary noise.
MESH_OVERLAP_AREA_TOLERANCE = 1e-5
FINAL_WARNING = ("WARNING: SIDE MODULE ANGLES AND LENGTHS ARE PROVISIONAL UNTIL THE REAL BAY WALLS "
                 "ARE FULL-SIZE TEMPLATED / FIELD MEASURED.")
OUTPUT_DIR = Path(__file__).resolve().parent
CUTLIST_PATH = OUTPUT_DIR / "bay_daybed_v3_cutlist.csv"
DIMENSIONS_PATH = OUTPUT_DIR / "bay_daybed_v3_dimensions.txt"
BLEND_PATH = OUTPUT_DIR / "bay_daybed_v3.blend"


class PostPose(NamedTuple):
    center_x: float
    center_y: float
    rotation_deg: float
    footprint: list
    clearance_in: float

COLLECTION_NAMES = (
    "ROOM_REFERENCE", "CENTER_UPPER_FRAME", "CENTER_LOWER_FRAME",
    "CENTER_POSTS", "LEFT_UPPER_FRAME", "LEFT_LOWER_FRAME", "LEFT_POSTS",
    "RIGHT_UPPER_FRAME", "RIGHT_LOWER_FRAME", "RIGHT_POSTS", "PLYWOOD_DECKS",
    "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE",
    "MODULE_CONNECTION_REFERENCE", "DIMENSIONS", "CAMERAS",
)
SIDE_BOARD_LOCAL_AXES = {
    "rear_closure": (1.0, 0.0),
    "inner_rail": (0.0, 1.0),
    "radial_rail": (0.5, 1.0),
    "diagonal_rail": (1.0, 1.0),
    "cross_brace_inner": (1.0, 0.0),
    "cross_brace_outer": (1.0, 0.0),
    "front_rail": (1.0, 0.0),
}


def _name_number(value):
    return f"{float(value):.3f}".rstrip("0").rstrip(".").replace(".", "p")


def _structural_name(module, function, dimensions, cut_length, status, profile=""):
    dimension_token = "x".join(_name_number(value) for value in dimensions)
    suffix = "RESOLVED" if status == "RESOLVED" else "PROV"
    return (f"{module}_{function}_{dimension_token}_CUT{_name_number(cut_length)}IN_{suffix}"
            f"{('_' + profile) if profile else ''}")


def _encode_numbers(values):
    return "|".join(f"{float(value):.9f}".rstrip("0").rstrip(".") for value in values)


def _encode_points(points):
    return ";".join(f"{x:.9f},{y:.9f}" for x, y in points)


def _decode_points(value):
    return [tuple(float(number) for number in point.split(","))
            for point in str(value).split(";")]


def side_u(sign, x):
    return sign * (x - sign * CENTER_FLAT_WALL_WIDTH / 2)


def side_x(sign, u):
    return sign * (CENTER_FLAT_WALL_WIDTH / 2 + u)


def module_sign(module):
    assert module in {"LEFT", "RIGHT"}, f"side module must be LEFT or RIGHT, actual {module!r}"
    return 1 if module == "LEFT" else -1


def finished_outer_u(y):
    return SIDE_RUN * y / DAYBED_FINISHED_DEPTH


def side_finished_vertices(module):
    sign = module_sign(module)
    inner_x = side_x(sign, 0.0)
    outer_x = side_x(sign, finished_outer_u(DAYBED_FINISHED_DEPTH))
    return ([(inner_x, 0.0), (inner_x, DAYBED_FINISHED_DEPTH),
             (outer_x, DAYBED_FINISHED_DEPTH)] if sign < 0 else
            [(inner_x, 0.0), (outer_x, DAYBED_FINISHED_DEPTH),
             (inner_x, DAYBED_FINISHED_DEPTH)])


def format_side_finished_vertices(module):
    return ", ".join(f"({_format_number(x)}, {_format_number(y)})"
                     for x, y in side_finished_vertices(module))


def side_front_skin_footprint(module):
    sign = module_sign(module)
    rear_y = DAYBED_FINISHED_DEPTH - 0.5
    inner_x = side_x(sign, 0.0)
    rear_outer_x = side_x(sign, finished_outer_u(rear_y))
    front_outer_x = side_x(sign, finished_outer_u(DAYBED_FINISHED_DEPTH))
    return ([(inner_x, rear_y), (inner_x, DAYBED_FINISHED_DEPTH),
             (front_outer_x, DAYBED_FINISHED_DEPTH), (rear_outer_x, rear_y)] if sign < 0 else
            [(inner_x, rear_y), (rear_outer_x, rear_y),
             (front_outer_x, DAYBED_FINISHED_DEPTH), (inner_x, DAYBED_FINISHED_DEPTH)])


def side_wall_endpoints(module):
    sign = module_sign(module)
    wall_run = DAYBED_FINISHED_DEPTH * math.tan(math.radians(APPROX_SIDE_WALL_ANGLE))
    return ((side_x(sign, 0.0), 0.0),
            (sign * (CENTER_FLAT_WALL_WIDTH / 2 + wall_run), DAYBED_FINISHED_DEPTH))


def _default_side_parameter_set():
    return all(abs(actual - expected) <= 1e-9 for actual, expected in (
        (CENTER_FLAT_WALL_WIDTH, 60.0), (DAYBED_FINISHED_DEPTH, 32.0),
        (SIDE_RUN, 32.0), (SIDE_ANGLE, 45.0), (SIDE_REAR_STRUCTURAL_SETBACK, 8.0),
        (SIDE_DIAGONAL_RAIL_INSET, 1.0), (SIDE_CROSS_BRACE_CENTER_Y, 23.75),
    ))


def _line_value(line, point):
    if len(line) == 3:
        a, b, c = line
    else:
        (x1, y1), (x2, y2) = line
        a, b, c = y1 - y2, x2 - x1, x1 * y2 - x2 * y1
    return a * point[0] + b * point[1] + c


def clip_polygon(poly, line, keep_less):
    """Clip a convex polygon to one line half-plane."""
    if not poly:
        return []
    result = []
    previous = poly[-1]
    previous_value = _line_value(line, previous)
    previous_inside = previous_value <= 1e-9 if keep_less else previous_value >= -1e-9
    for current in poly:
        current_value = _line_value(line, current)
        current_inside = current_value <= 1e-9 if keep_less else current_value >= -1e-9
        if current_inside != previous_inside:
            t = previous_value / (previous_value - current_value)
            result.append((
                previous[0] + t * (current[0] - previous[0]),
                previous[1] + t * (current[1] - previous[1]),
            ))
        if current_inside:
            result.append(current)
        previous, previous_value, previous_inside = current, current_value, current_inside
    return result


def _signed_polygon_area(poly):
    return sum(
        point[0] * poly[(index + 1) % len(poly)][1]
        - point[1] * poly[(index + 1) % len(poly)][0]
        for index, point in enumerate(poly)
    ) / 2 if len(poly) >= 3 else 0.0


def polygon_area(poly):
    return abs(_signed_polygon_area(poly))


def segments_intersect(a, b, c, d):
    def orientation(p, q, r):
        value = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (value > 1e-9) - (value < -1e-9)

    def on_segment(p, q, r):
        return (min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
                and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9)

    ab_c, ab_d = orientation(a, b, c), orientation(a, b, d)
    cd_a, cd_b = orientation(c, d, a), orientation(c, d, b)
    return ((ab_c != ab_d and cd_a != cd_b)
            or (ab_c == 0 and on_segment(a, c, b))
            or (ab_d == 0 and on_segment(a, d, b))
            or (cd_a == 0 and on_segment(c, a, d))
            or (cd_b == 0 and on_segment(c, b, d)))


def point_in_polygon(point, poly):
    """Return True for points inside or on the boundary of a polygon."""
    for start, end in zip(poly, poly[1:] + poly[:1]):
        if abs((end[0] - start[0]) * (point[1] - start[1])
               - (end[1] - start[1]) * (point[0] - start[0])) <= 1e-9:
            if (min(start[0], end[0]) - 1e-9 <= point[0] <= max(start[0], end[0]) + 1e-9
                    and min(start[1], end[1]) - 1e-9 <= point[1] <= max(start[1], end[1]) + 1e-9):
                return True
    inside = False
    for start, end in zip(poly, poly[1:] + poly[:1]):
        if (start[1] > point[1]) != (end[1] > point[1]):
            x_cross = (end[0] - start[0]) * (point[1] - start[1]) / (end[1] - start[1]) + start[0]
            if point[0] < x_cross:
                inside = not inside
    return inside


def polygon_intersection(subject, clipper):
    """Return the intersection of two convex polygons in their input plane."""
    result = list(subject)
    keep_less = _signed_polygon_area(clipper) < 0
    for start, end in zip(clipper, clipper[1:] + clipper[:1]):
        result = clip_polygon(result, (start, end), keep_less)
        if not result:
            break
    return result


def polygons_overlap_area(a, b):
    return polygon_area(polygon_intersection(a, b))


def mirror_to_world(sign, local_polygon):
    return [(side_x(sign, u), y) for u, y in local_polygon]


def _post_footprint(center_x, center_y, rotation_deg):
    angle = math.radians(rotation_deg)
    short = (math.cos(angle), math.sin(angle))
    long = (-math.sin(angle), math.cos(angle))
    return [
        (center_x + sx * .75 * short[0] + sy * 1.75 * long[0],
         center_y + sx * .75 * short[1] + sy * 1.75 * long[1])
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def _rectangle_support(normal, rotation_deg):
    angle = math.radians(rotation_deg)
    short = (math.cos(angle), math.sin(angle))
    long = (-math.sin(angle), math.cos(angle))
    return (.75 * abs(normal[0] * short[0] + normal[1] * short[1])
            + 1.75 * abs(normal[0] * long[0] + normal[1] * long[1]))


def _feasible_post_centers(support_polygon, rotation_deg, extra_clearance,
                           joint_halfplane, min_clearance):
    feasible = list(support_polygon)
    for start, end in zip(support_polygon, support_polygon[1:] + support_polygon[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        normal = (-dy / length, dx / length)
        offset = _rectangle_support(normal, rotation_deg) + extra_clearance
        feasible = clip_polygon(
            feasible,
            (normal[0], normal[1], -normal[0] * start[0] - normal[1] * start[1] - offset),
            keep_less=False,
        )
        if polygon_area(feasible) <= 1e-9:
            return []
    if joint_halfplane:
        a, b, c, keep_less = joint_halfplane
        length = math.hypot(a, b)
        normal = (a / length, b / length)
        c /= length
        offset = _rectangle_support(normal, rotation_deg) + min_clearance + extra_clearance
        feasible = clip_polygon(
            feasible,
            (normal[0], normal[1], c + offset if keep_less else c - offset),
            keep_less,
        )
    return feasible if polygon_area(feasible) > 1e-9 else []


def fit_post_in_support(support_polygon, joint_halfplane=None, min_clearance=0.0):
    """Fit an actual 1.5-by-3.5 post plan inside a convex CCW support polygon."""
    assert _signed_polygon_area(support_polygon) > 0, (
        f"post support polygon must be nondegenerate CCW; area {_signed_polygon_area(support_polygon)}"
    )
    best = None
    for step in range(1800):
        rotation = step / 10
        if not _feasible_post_centers(support_polygon, rotation, 0.0, joint_halfplane,
                                      min_clearance):
            continue
        low, high = (min_clearance, ACTUAL_2X4_WIDTH * 2) if joint_halfplane else (
            0.0, ACTUAL_2X4_WIDTH)
        for _ in range(28):
            middle = (low + high) / 2
            extra = 0.0 if joint_halfplane else middle
            joint_clearance = middle if joint_halfplane else min_clearance
            if _feasible_post_centers(support_polygon, rotation, extra,
                                      joint_halfplane, joint_clearance):
                low = middle
            else:
                high = middle
        extra = 0.0 if joint_halfplane else max(0.0, low - 1e-7)
        joint_clearance = max(min_clearance, low - 1e-7) if joint_halfplane else min_clearance
        feasible = _feasible_post_centers(
            support_polygon, rotation, extra, joint_halfplane, joint_clearance,
        )
        center_x = sum(point[0] for point in feasible) / len(feasible)
        center_y = sum(point[1] for point in feasible) / len(feasible)
        reported_rotation = rotation if rotation <= 90 else rotation - 180
        pose = PostPose(center_x, center_y, reported_rotation,
                        _post_footprint(center_x, center_y, reported_rotation), low)
        if best is None or pose.clearance_in > best.clearance_in + 1e-9:
            best = pose
    return best


def _fixed_y_center_interval(polygon, center_y, half_x, half_y):
    low, high = -float("inf"), float("inf")
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        required = abs(nx) * half_x + abs(ny) * half_y
        rhs = nx * start[0] + ny * start[1] + required - ny * center_y
        if nx > 1e-12:
            low = max(low, rhs / nx)
        elif nx < -1e-12:
            high = min(high, rhs / nx)
        elif ny * center_y - nx * start[0] - ny * start[1] < required - 1e-9:
            return None
    return low, high


def solve_front_post(lower_front, upper_path, upper_front):
    intervals = (
        _fixed_y_center_interval(lower_front, 27.25, .75, 1.75),
        _fixed_y_center_interval(upper_path, 26.75, .75, 1.25),
        _fixed_y_center_interval(upper_front, 28.5, .75, .5),
    )
    if any(interval is None for interval in intervals):
        return None
    low = max(interval[0] for interval in intervals)
    high = min(interval[1] for interval in intervals)
    if high < low - 1e-9:
        return None
    center_x = (low + high) / 2
    return PostPose(center_x, 27.25, 0.0,
                    _post_footprint(center_x, 27.25, 0.0), (high - low) / 2)


def _local_side_frame_footprints(front_rear_y):
    mating_u = -0.5
    inner_outer_u = mating_u + ACTUAL_2X4_WIDTH
    rear_y = SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH
    brace_y0 = SIDE_CROSS_BRACE_CENTER_Y - ACTUAL_2X4_WIDTH / 2
    brace_y1 = SIDE_CROSS_BRACE_CENTER_Y + ACTUAL_2X4_WIDTH / 2
    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
    diagonal_scale = math.sqrt(1 + slope ** 2)
    radial_slope = slope / 2
    radial_scale = math.sqrt(1 + radial_slope ** 2)

    def rectangle(u0, u1, y0, y1):
        return [(u0, y0), (u1, y0), (u1, y1), (u0, y1)]

    def band(inner, outer, y0, y1):
        return [(inner(y0), y0), (outer(y0), y0),
                (outer(y1), y1), (inner(y1), y1)]

    diagonal_center = lambda y: slope * y - (SIDE_DIAGONAL_RAIL_INSET + 1.75) * diagonal_scale
    diagonal_outer = lambda y: slope * y - SIDE_DIAGONAL_RAIL_INSET * diagonal_scale
    diagonal_inner = lambda y: slope * y - (SIDE_DIAGONAL_RAIL_INSET + 3.5) * diagonal_scale
    radial_center = lambda y: (1.25 + diagonal_center(y)) / 2
    radial_inner = lambda y: radial_center(y) - 1.75 * radial_scale
    radial_outer = lambda y: radial_center(y) + 1.75 * radial_scale
    radial = band(radial_inner, radial_outer, rear_y, front_rear_y)
    radial = clip_polygon(radial, (1, 0, -inner_outer_u), keep_less=False)
    radial = clip_polygon(
        radial, (1, -slope, (SIDE_DIAGONAL_RAIL_INSET + 3.5) * diagonal_scale),
        keep_less=True,
    )

    return {
        "rear_closure": rectangle(mating_u, finished_outer_u(SIDE_REAR_STRUCTURAL_SETBACK),
                                  SIDE_REAR_STRUCTURAL_SETBACK, rear_y),
        "inner_rail": rectangle(mating_u, inner_outer_u, rear_y, front_rear_y),
        "radial_rail": radial,
        "diagonal_rail": band(diagonal_inner, diagonal_outer, rear_y, front_rear_y),
        "cross_brace_inner": band(lambda _y: inner_outer_u, radial_inner, brace_y0, brace_y1),
        "cross_brace_outer": band(radial_outer, diagonal_inner, brace_y0, brace_y1),
        "front_rail": band(lambda _y: mating_u, diagonal_outer,
                           front_rear_y, front_rear_y + ACTUAL_2X4_WIDTH),
    }


def side_frame_footprints(sign, front_rear_y):
    footprints = {name: mirror_to_world(sign, footprint)
                  for name, footprint in _local_side_frame_footprints(front_rear_y).items()}
    return footprints if sign > 0 else {name: list(reversed(footprint))
                                        for name, footprint in footprints.items()}


def board_cut_metadata(footprint, axis, end_lines):
    axis_length = math.hypot(*axis)
    assert footprint and axis_length > 0 and len(end_lines) == 2, (
        f"board cut metadata requires a footprint, positive axis length, and two end lines; "
        f"actual footprint vertices {len(footprint)}, axis length {axis_length}, end lines {len(end_lines)}"
    )
    unit = (axis[0] / axis_length, axis[1] / axis_length)
    normal = (-unit[1], unit[0])

    def dot(point, vector):
        return point[0] * vector[0] + point[1] * vector[1]

    ends = [sorted(line, key=lambda point: dot(point, normal)) for line in end_lines]
    lengths = [abs(dot((b[0] - a[0], b[1] - a[1]), unit))
               for a, b in zip(*ends)]

    def cut_angle(line):
        direction = (line[1][0] - line[0][0], line[1][1] - line[0][1])
        return math.degrees(math.atan2(abs(dot(direction, unit)), abs(dot(direction, normal))))

    return {
        "centerline_length_in": sum(lengths) / 2,
        "long_edge_in": max(lengths),
        "short_edge_in": min(lengths),
        "end_a_angle_deg": cut_angle(end_lines[0]),
        "end_b_angle_deg": cut_angle(end_lines[1]),
        "orientation_deg": math.degrees(math.atan2(unit[1], unit[0])) % 180,
    }


def _continuous_parallel_edge_lengths(footprint, axis):
    """Return physical collinear edge-chain lengths parallel to ``axis``."""
    axis_length = math.hypot(*axis)
    assert axis_length > 0, "longitudinal edge axis must be nonzero"
    unit = (axis[0] / axis_length, axis[1] / axis_length)
    normal = (-unit[1], unit[0])
    groups = []
    for start, end in zip(footprint, footprint[1:] + footprint[:1]):
        direction = (end[0] - start[0], end[1] - start[1])
        segment_length = math.hypot(*direction)
        if segment_length <= 1e-9 or abs(direction[0] * unit[1] - direction[1] * unit[0]) > 1e-5:
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


def radial_cut_metadata(local_footprint, sign):
    """Describe the clipped radial board from its actual edges and custom rear profile."""
    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH / 2
    local_axis = (slope, 1.0)
    world_axis = (sign * slope, 1.0)
    axis_length = math.hypot(*local_axis)
    unit = (local_axis[0] / axis_length, local_axis[1] / axis_length)
    normal = (-unit[1], unit[0])
    y0, y1 = min(y for _, y in local_footprint), max(y for _, y in local_footprint)
    longitudinal_edges = _continuous_parallel_edge_lengths(local_footprint, local_axis)
    assert len(longitudinal_edges) == 2, (
        f"radial footprint requires two physical longitudinal edges, found {longitudinal_edges}"
    )
    rear_segments, front_segments = [], []
    for start, end in zip(local_footprint, local_footprint[1:] + local_footprint[:1]):
        direction = (end[0] - start[0], end[1] - start[1])
        if abs(direction[0] * local_axis[1] - direction[1] * local_axis[0]) <= 1e-5:
            continue
        if abs(start[1] - y1) <= 1e-5 and abs(end[1] - y1) <= 1e-5:
            front_segments.append(direction)
        else:
            rear_segments.append(direction)
    assert len(rear_segments) == 3 and len(front_segments) == 1, (
        f"radial custom profile requires three rear segments and one front segment; "
        f"found {len(rear_segments)} and {len(front_segments)}"
    )

    def cut_angle(direction):
        return math.degrees(math.atan2(
            abs(direction[0] * unit[0] + direction[1] * unit[1]),
            abs(direction[0] * normal[0] + direction[1] * normal[1])))

    centerline_length = (y1 - y0) * axis_length
    return {
        "centerline_length_in": centerline_length,
        "cut_length_in": centerline_length,
        "long_edge_in": longitudinal_edges[0],
        "short_edge_in": longitudinal_edges[1],
        "end_a_angle_deg": _encode_numbers(cut_angle(direction) for direction in rear_segments),
        "end_b_angle_deg": cut_angle(front_segments[0]),
        "orientation_deg": math.degrees(math.atan2(world_axis[1], world_axis[0])) % 180,
        "cut_profile": "CUSTOM NOTCHED REAR PROFILE",
        "rear_profile_segment_orientations_deg": _encode_numbers(
            math.degrees(math.atan2(direction[1], direction[0])) % 180
            for direction in rear_segments
        ),
        "rear_profile_segment_lengths_in": _encode_numbers(math.hypot(*direction)
                                                              for direction in rear_segments),
        "orientation_note": ("CUSTOM NOTCHED REAR PROFILE; TWO ACTUAL LONGITUDINAL EDGES; "
                             "REAR SEGMENTS HORIZONTAL/VERTICAL/DIAGONAL; TEMPLATE AND FIELD VERIFY"),
    }


def _recompute_radial_mesh_metadata(local_footprint, sign):
    """Fail-closed mesh audit path; intentionally does not call ``radial_cut_metadata``."""
    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH / 2
    axis = (slope, 1.0)
    axis_length = math.hypot(*axis)
    unit = (axis[0] / axis_length, axis[1] / axis_length)
    normal = (-unit[1], unit[0])
    y0, y1 = min(y for _, y in local_footprint), max(y for _, y in local_footprint)
    edge_lengths = _continuous_parallel_edge_lengths(local_footprint, axis)
    assert len(edge_lengths) == 2, (
        f"mesh radial footprint requires two physical longitudinal edges, found {edge_lengths}"
    )
    rear, front = [], []
    for start, end in zip(local_footprint, local_footprint[1:] + local_footprint[:1]):
        direction = (end[0] - start[0], end[1] - start[1])
        if abs(direction[0] * axis[1] - direction[1] * axis[0]) <= 1e-5:
            continue
        (front if abs(start[1] - y1) <= 1e-5 and abs(end[1] - y1) <= 1e-5 else rear).append(direction)
    assert len(rear) == 3 and len(front) == 1, (
        f"mesh radial profile segments are ambiguous: rear {len(rear)}, front {len(front)}"
    )

    def angle(direction):
        return math.degrees(math.atan2(
            abs(direction[0] * unit[0] + direction[1] * unit[1]),
            abs(direction[0] * normal[0] + direction[1] * normal[1])))

    centerline = (y1 - y0) * axis_length
    world_axis = (sign * slope, 1.0)
    return {
        "centerline_length_in": centerline,
        "cut_length_in": centerline,
        "long_edge_in": edge_lengths[0],
        "short_edge_in": edge_lengths[1],
        "end_a_angle_deg": _encode_numbers(angle(direction) for direction in rear),
        "end_b_angle_deg": angle(front[0]),
        "orientation_deg": math.degrees(math.atan2(world_axis[1], world_axis[0])) % 180,
        "cut_profile": "CUSTOM NOTCHED REAR PROFILE",
        "rear_profile_segment_orientations_deg": _encode_numbers(
            math.degrees(math.atan2(direction[1], direction[0])) % 180 for direction in rear
        ),
        "rear_profile_segment_lengths_in": _encode_numbers(math.hypot(*direction)
                                                              for direction in rear),
        "orientation_note": ("CUSTOM NOTCHED REAR PROFILE; TWO ACTUAL LONGITUDINAL EDGES; "
                             "REAR SEGMENTS HORIZONTAL/VERTICAL/DIAGONAL; TEMPLATE AND FIELD VERIFY"),
    }


def _brace_driver_prism(brace, inner):
    joint = (brace[1], brace[2]) if inner else (brace[3], brace[0])
    start, end = joint
    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    tangent_length = math.hypot(end[0] - start[0], end[1] - start[1])
    tangent = ((end[0] - start[0]) / tangent_length, (end[1] - start[1]) / tangent_length)
    centroid = (sum(x for x, _ in brace) / len(brace), sum(y for _, y in brace) / len(brace))
    inward_length = math.hypot(centroid[0] - midpoint[0], centroid[1] - midpoint[1])
    inward = ((centroid[0] - midpoint[0]) / inward_length,
              (centroid[1] - midpoint[1]) / inward_length)
    half_width, near_depth, far_depth = .375, .05, 1.0
    prism = [
        (midpoint[0] - tangent[0] * half_width + inward[0] * near_depth,
         midpoint[1] - tangent[1] * half_width + inward[1] * near_depth),
        (midpoint[0] + tangent[0] * half_width + inward[0] * near_depth,
         midpoint[1] + tangent[1] * half_width + inward[1] * near_depth),
        (midpoint[0] + tangent[0] * half_width + inward[0] * far_depth,
         midpoint[1] + tangent[1] * half_width + inward[1] * far_depth),
        (midpoint[0] - tangent[0] * half_width + inward[0] * far_depth,
         midpoint[1] - tangent[1] * half_width + inward[1] * far_depth),
    ]
    return prism if _signed_polygon_area(prism) > 0 else list(reversed(prism))


def _annotate_side_frame_fastening(objects, local):
    by_type = {obj["board_type"]: obj for obj in objects}
    closure = by_type["rear_closure"]
    rear_face_y = SIDE_REAR_STRUCTURAL_SETBACK
    joint_y = SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH
    closure_min, closure_max = min(u for u, _ in local["rear_closure"]), max(
        u for u, _ in local["rear_closure"])
    method = "STRAIGHT FROM REAR DURING MODULE ASSEMBLY THROUGH CLOSURE INTO RAIL END"
    closure["rear_fastening_method"] = method
    closure["rear_driver_clearance_in"] = 5.0
    for label, board_type in (("inner", "inner_rail"), ("diagonal", "diagonal_rail")):
        target = by_type[board_type]
        section = sorted(u for u, y in local[board_type] if abs(y - joint_y) <= 1e-9)
        interface_min, interface_max = max(closure_min, section[0]), min(closure_max, section[-1])
        interface = interface_max - interface_min
        center_u = (interface_min + interface_max) / 2
        driver = [(center_u - .375, rear_face_y - 5.0), (center_u + .375, rear_face_y - 5.0),
                  (center_u + .375, rear_face_y), (center_u - .375, rear_face_y)]
        assert interface >= .75 and _is_simple_ccw(driver), (
            f"{closure.name}: {label} rear screw interface {interface} cannot accept driver prism"
        )
        closure[f"rear_{label}_interface_in"] = interface
        closure[f"rear_{label}_driver_prism_local"] = _encode_points(driver)
        closure[f"rear_{label}_driver_access"] = False
        closure[f"rear_{label}_target_object"] = target.name
        target["rear_fastening_method"] = method
        target["rear_fastening_source_object"] = closure.name
    for brace_type in ("cross_brace_inner", "cross_brace_outer"):
        brace = by_type[brace_type]
        prism = _brace_driver_prism(local[brace_type], brace_type == "cross_brace_inner")
        assert _contains_polygon(local[brace_type], prism), (
            f"{brace.name}: toe-screw driver prism is not inside exposed brace top/side area"
        )
        brace["radial_joint_fastening_method"] = (
            "ANGLED TOE-SCREW/PILOT FROM EXPOSED BRACE TOP/SIDE INTO RADIAL; NO THROUGH-RADIAL PATH"
        )
        brace["radial_joint_driver_prism_local"] = _encode_points(prism)
        brace["radial_joint_driver_width_in"] = .75
        brace["radial_joint_driver_depth_in"] = 1.0
        brace["radial_joint_driver_access"] = False
        brace["radial_joint_target_object"] = by_type["radial_rail"].name


def build_side_frame(module, sign, z0, z1, front_rear_y, collection, material):
    local_footprints = _local_side_frame_footprints(front_rear_y)
    world_footprints = side_frame_footprints(sign, front_rear_y)
    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
    axes = dict(SIDE_BOARD_LOCAL_AXES)
    axes["radial_rail"] = (slope / 2, 1.0)
    axes["diagonal_rail"] = (slope, 1.0)
    longitudinal = {"inner_rail", "radial_rail", "diagonal_rail"}
    level = collection.name.split("_")[1]
    objects = []
    for board_type, local in local_footprints.items():
        if board_type in longitudinal:
            end_lines = tuple(
                tuple((side_x(sign, u), y) for u, y in local if abs(y - end_y) <= 1e-9)
                for end_y in (min(y for _, y in local), max(y for _, y in local))
            )
        else:
            end_lines = tuple(
                tuple((side_x(sign, local[index][0]), local[index][1]) for index in pair)
                for pair in ((3, 0), (1, 2))
            )
        axis = (sign * axes[board_type][0], axes[board_type][1])
        metadata = (radial_cut_metadata(local, sign) if board_type == "radial_rail" else
                    board_cut_metadata(world_footprints[board_type], axis, end_lines))
        metadata.setdefault("cut_length_in", metadata["centerline_length_in"])
        function = f"{level}_{board_type.upper()}"
        name = _structural_name(
            module, function, (ACTUAL_2X4_WIDTH, ACTUAL_2X4_THICKNESS),
            metadata["centerline_length_in"], PROVISIONAL_STATUS,
            "NOTCHED" if board_type == "radial_rail" else "",
        )
        objects.append(add_prism(
            name, world_footprints[board_type], z0, z1,
            collection, material, module=module, status="PROVISIONAL / FIELD VERIFY",
            purpose=board_type.replace("_", " "), board_type=board_type,
            frame_level=level, name_function=function,
            validation_group="STRUCTURAL", **metadata,
        ))
    _annotate_side_frame_fastening(objects, local_footprints)
    return objects


def object_footprint(obj):
    count = len(obj.data.vertices) // 2
    return [(point.co.x, point.co.y) for point in obj.data.vertices[:count]]


def _actual_mesh_footprint(obj):
    vertices = obj.data.vertices
    assert obj.type == "MESH", f"{obj.name}: structural object is not a mesh"
    assert len(vertices) >= 8 and len(vertices) % 2 == 0, (
        f"{obj.name}: expected paired bottom/top mesh vertices, actual {len(vertices)}"
    )
    count = len(vertices) // 2
    bottom = [obj.matrix_world @ vertex.co for vertex in vertices[:count]]
    top = [obj.matrix_world @ vertex.co for vertex in vertices[count:]]
    z0, z1 = min(point.z for point in bottom), max(point.z for point in top)
    assert all(abs(point.z - z0) <= 1e-5 for point in bottom), f"{obj.name}: nonplanar bottom face"
    assert all(abs(point.z - z1) <= 1e-5 for point in top), f"{obj.name}: nonplanar top face"
    assert z1 - z0 > 0, f"{obj.name}: nonpositive modeled height {z1 - z0}"
    assert len(obj.data.polygons) == count + 2, (
        f"{obj.name}: expected {count + 2} prism faces, actual {len(obj.data.polygons)}"
    )
    footprint = [(point.x, point.y) for point in bottom]
    assert _is_simple_ccw(footprint), f"{obj.name}: footprint is not simple CCW geometry"
    return footprint, z0, z1


def _plan_edge_lengths_and_angles(footprint):
    edges = [
        (math.hypot(end[0] - start[0], end[1] - start[1]),
         math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])) % 180)
        for start, end in zip(footprint, footprint[1:] + footprint[:1])
    ]
    return sorted(edges)


def recompute_structural_metadata(obj):
    footprint, z0, z1 = _actual_mesh_footprint(obj)
    actual_bounds = bounds(obj)
    actual = {
        "modeled_size_x_in": actual_bounds[1] - actual_bounds[0],
        "modeled_size_y_in": actual_bounds[3] - actual_bounds[2],
        "modeled_size_z_in": z1 - z0,
    }
    if "board_type" in obj:
        module = obj["module"]
        assert module in {"LEFT", "RIGHT"}, f"{obj.name}: side board has invalid module {module!r}"
        sign = module_sign(module)
        board_type = obj["board_type"]
        local = [(side_u(sign, x), y) for x, y in footprint]
        if _signed_polygon_area(local) < 0:
            local.reverse()
        slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
        axes = dict(SIDE_BOARD_LOCAL_AXES)
        axes["radial_rail"] = (slope / 2, 1.0)
        axes["diagonal_rail"] = (slope, 1.0)
        assert board_type in axes, f"{obj.name}: unsupported board_type {board_type!r}"
        if board_type in {"inner_rail", "radial_rail", "diagonal_rail"}:
            y0, y1 = min(y for _, y in local), max(y for _, y in local)
            end_local = tuple(
                tuple(point for point in local if abs(point[1] - end_y) <= 1e-5)
                for end_y in (y0, y1)
            )
        else:
            assert len(local) == 4, f"{obj.name}: transverse board footprint must have four vertices"
            end_local = tuple(tuple(local[index] for index in pair) for pair in ((3, 0), (1, 2)))
        assert all(len(line) == 2 for line in end_local), f"{obj.name}: modeled end lines are ambiguous"
        end_lines = tuple(tuple((side_x(sign, u), y) for u, y in line) for line in end_local)
        axis = (sign * axes[board_type][0], axes[board_type][1])
        actual.update(_recompute_radial_mesh_metadata(local, sign) if board_type == "radial_rail" else
                      board_cut_metadata(footprint, axis, end_lines))
        actual["cut_length_in"] = actual["centerline_length_in"]
    elif "post" in obj["purpose"]:
        edge_data = _plan_edge_lengths_and_angles(footprint)
        assert abs(edge_data[0][0] - 1.5) <= 1e-5 and abs(edge_data[-1][0] - 3.5) <= 1e-5, (
            f"{obj.name}: modeled post plan is not 1.5 x 3.5; edges "
            f"{edge_data[0][0]}, {edge_data[-1][0]}"
        )
        orientation = edge_data[0][1] if "post_role" in obj else edge_data[-1][1]
        actual.update({
            "cut_length_in": z1 - z0,
            "centerline_length_in": z1 - z0,
            "long_edge_in": z1 - z0,
            "short_edge_in": z1 - z0,
            "end_a_angle_deg": 0.0,
            "end_b_angle_deg": 0.0,
            "orientation_deg": orientation,
        })
    else:
        size_x, size_y = actual["modeled_size_x_in"], actual["modeled_size_y_in"]
        cut_length = max(size_x, size_y)
        actual.update({
            "cut_length_in": cut_length,
            "centerline_length_in": cut_length,
            "long_edge_in": cut_length,
            "short_edge_in": cut_length,
            "end_a_angle_deg": 0.0,
            "end_b_angle_deg": 0.0,
            "orientation_deg": 0.0 if size_x >= size_y else 90.0,
        })
    return actual


def validate_structural_metadata(structural):
    numeric_keys = (
        "modeled_size_x_in", "modeled_size_y_in", "modeled_size_z_in", "cut_length_in",
        "centerline_length_in", "long_edge_in", "short_edge_in", "orientation_deg",
    )
    recomputed = {}
    for obj in structural:
        actual = recompute_structural_metadata(obj)
        recomputed[obj.name] = actual
        assert abs(obj["stock_width_in"] - ACTUAL_2X4_WIDTH) <= 1e-9, (
            f"{obj.name}: stock_width_in metadata {obj['stock_width_in']}, expected {ACTUAL_2X4_WIDTH}"
        )
        assert abs(obj["stock_thickness_in"] - ACTUAL_2X4_THICKNESS) <= 1e-9, (
            f"{obj.name}: stock_thickness_in metadata {obj['stock_thickness_in']}, "
            f"expected {ACTUAL_2X4_THICKNESS}"
        )
        for key in numeric_keys:
            metadata_value, actual_value = float(obj[key]), float(actual[key])
            if key == "orientation_deg":
                difference = abs((metadata_value - actual_value + 90) % 180 - 90)
            else:
                difference = abs(metadata_value - actual_value)
            assert difference <= METADATA_TOLERANCE, (
                f"{obj.name}: {key} metadata {metadata_value} does not match "
                f"recomputed modeled value {actual_value}"
            )
        for key in ("end_a_angle_deg", "end_b_angle_deg"):
            metadata_value, actual_value = obj[key], actual[key]
            if isinstance(actual_value, str):
                metadata_numbers = [float(value) for value in str(metadata_value).split("|")]
                actual_numbers = [float(value) for value in actual_value.split("|")]
                assert len(metadata_numbers) == len(actual_numbers) and all(
                    abs(left - right) <= METADATA_TOLERANCE
                    for left, right in zip(metadata_numbers, actual_numbers)
                ), (f"{obj.name}: {key} metadata {metadata_value!r} does not match "
                    f"recomputed custom profile {actual_value!r}")
            else:
                assert abs(float(metadata_value) - float(actual_value)) <= METADATA_TOLERANCE, (
                    f"{obj.name}: {key} metadata {metadata_value} does not match "
                    f"recomputed modeled value {actual_value}"
                )
        if obj.get("board_type") == "radial_rail":
            for key in ("cut_profile", "orientation_note"):
                assert str(obj[key]) == str(actual[key]), (
                    f"{obj.name}: {key} metadata does not match recomputed notched profile"
                )
            for key in ("rear_profile_segment_orientations_deg",
                        "rear_profile_segment_lengths_in"):
                metadata_numbers = [float(value) for value in str(obj[key]).split("|")]
                actual_numbers = [float(value) for value in str(actual[key]).split("|")]
                assert len(metadata_numbers) == len(actual_numbers) and all(
                    abs(left - right) <= METADATA_TOLERANCE
                    for left, right in zip(metadata_numbers, actual_numbers)
                ), f"{obj.name}: {key} metadata does not match recomputed notched profile"
    return recomputed


def _minimum_plan_width(footprint):
    widths = []
    for start, end in zip(footprint, footprint[1:] + footprint[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        normal = (-dy / length, dx / length)
        projections = [x * normal[0] + y * normal[1] for x, y in footprint]
        widths.append(max(projections) - min(projections))
    assert widths, "structural footprint has no measurable plan edges"
    return min(widths)


def validate_nominal_structural_stock(structural):
    """Audit actual meshes against nominal 2x4 stock without trusting size metadata."""
    for obj in structural:
        footprint, z0, z1 = _actual_mesh_footprint(obj)
        if "post" in obj["purpose"]:
            edges = sorted(length for length, _ in _plan_edge_lengths_and_angles(footprint))
            assert len(edges) == 4 and all(
                abs(actual - expected) <= METADATA_TOLERANCE
                for actual, expected in zip(edges, (1.5, 1.5, 3.5, 3.5))
            ), f"{obj.name}: post mesh is not actual 1.5 x 3.5 stock; edges {edges}"
            assert abs((z1 - z0) - obj["cut_length_in"]) <= METADATA_TOLERANCE, (
                f"{obj.name}: post height {z1 - z0} differs from cut {obj['cut_length_in']}"
            )
        else:
            assert abs((z1 - z0) - ACTUAL_2X4_THICKNESS) <= METADATA_TOLERANCE, (
                f"{obj.name}: flat 2x4 thickness {z1 - z0}, expected {ACTUAL_2X4_THICKNESS}"
            )
            width = _minimum_plan_width(footprint)
            assert abs(width - ACTUAL_2X4_WIDTH) <= METADATA_TOLERANCE, (
                f"{obj.name}: flat 2x4 plan width {width}, expected {ACTUAL_2X4_WIDTH}"
            )


def structural_volume_overlap(a, b):
    az, bz = bounds(a)[4:], bounds(b)[4:]
    return (min(az[1], bz[1]) - max(az[0], bz[0]) > 1e-9
            and polygons_overlap_area(object_footprint(a), object_footprint(b))
            > MESH_OVERLAP_AREA_TOLERANCE)


def _local_object_footprint(sign, obj):
    footprint = [(side_u(sign, x), y) for x, y in object_footprint(obj)]
    return footprint if _signed_polygon_area(footprint) > 0 else list(reversed(footprint))


def _contains_polygon(container, contained):
    return all(point_in_polygon(point, container) for point in contained)


def _driver_access(pose, support, neighbors):
    x, y = pose.center_x, pose.center_y
    driver = [(x - .5, y - .5), (x + .5, y - .5),
              (x + .5, y + .5), (x - .5, y + .5)]
    return (_contains_polygon(support, driver)
            and all(polygons_overlap_area(driver, polygon) <= 1e-9
                    for polygon in neighbors))


def build_side_posts(module, sign, upper, lower, collection, material):
    upper_by_type = {obj["board_type"]: _local_object_footprint(sign, obj) for obj in upper}
    lower_by_type = {obj["board_type"]: _local_object_footprint(sign, obj) for obj in lower}
    top = SIDE_UPPER_BOTTOM_Z[module]
    cut_length = top - 1.5
    posts = []

    def add_post(name, purpose, role, pose, lower_member, upper_member,
                 upper_secondary=None, **props):
        assert pose is not None, f"{module} {purpose}: no feasible post pose"
        assert _contains_polygon(lower_by_type[lower_member], pose.footprint)
        assert upper_secondary or _contains_polygon(upper_by_type[upper_member], pose.footprint)
        lower_neighbors = [polygon for key, polygon in lower_by_type.items() if key != lower_member]
        upper_neighbors = [polygon for key, polygon in upper_by_type.items() if key != upper_member]
        bottom_driver_access = _driver_access(pose, lower_by_type[lower_member], lower_neighbors)
        top_driver_access = _driver_access(pose, upper_by_type[upper_member], upper_neighbors)
        driver_access = bottom_driver_access and top_driver_access
        assert driver_access, f"{module} {purpose}: blocked vertical driver prism"
        footprint = mirror_to_world(sign, pose.footprint)
        if _signed_polygon_area(footprint) < 0:
            footprint.reverse()
        world_center_x = side_x(sign, pose.center_x)
        world_orientation = (pose.rotation_deg if sign > 0 else 180 - pose.rotation_deg) % 180
        object_name = _structural_name(
            module, name, (1.5, 3.5, cut_length), cut_length, PROVISIONAL_STATUS,
        )
        posts.append(add_prism(
            object_name, footprint, 1.5, top, collection, material,
            module=module, status="PROVISIONAL / FIELD VERIFY", purpose=purpose,
            post_role=role, name_function=name, validation_group="STRUCTURAL",
            cut_length_in=cut_length,
            plan_short_in=1.5, plan_long_in=3.5, post_rotation_deg=pose.rotation_deg,
            world_orientation_deg=world_orientation, orientation_deg=world_orientation,
            centerline_length_in=cut_length, long_edge_in=cut_length, short_edge_in=cut_length,
            end_a_angle_deg=0.0, end_b_angle_deg=0.0,
            local_center_u=pose.center_x, center_y=pose.center_y,
            fastener_x=world_center_x, fastener_y=pose.center_y,
            fastener_edge_distance_in=.75, driver_clearance_prism_in=1.0,
            driver_access=driver_access, top_driver_access=top_driver_access,
            bottom_driver_access=bottom_driver_access, lower_support=lower_member,
            upper_support=(f"{upper_member} + {upper_secondary}" if upper_secondary else upper_member),
            **props,
        ))

    closure = lower_by_type["rear_closure"]
    closure_min_u, closure_max_u = min(u for u, _ in closure), max(u for u, _ in closure)
    closure_width = closure_max_u - closure_min_u
    minimum_two_post_width = 2 * ACTUAL_2X4_WIDTH + 1.0
    assert closure_width >= minimum_two_post_width - 1e-9, (
        f"{module} rear closure usable width {closure_width} is below {minimum_two_post_width} "
        "required for two 3.5-inch post footprints plus 1-inch fastening gap"
    )
    rear_centers = (("INNER", closure_min_u + ACTUAL_2X4_WIDTH / 2),
                    ("OUTER", closure_max_u - ACTUAL_2X4_WIDTH / 2))
    for label, center_u in rear_centers:
        center_y = SIDE_REAR_STRUCTURAL_SETBACK + 1.5
        pose = PostPose(center_u, center_y, 90.0,
                        _post_footprint(center_u, center_y, 90.0), 1.25)
        assert _contains_polygon(closure, pose.footprint), (
            f"{module} rear post {label} footprint at center_u {center_u} does not fit "
            f"closure U range {closure_min_u}..{closure_max_u}"
        )
        add_post(f"REAR_POST_{label}", f"rear post {label.lower()}", "rear", pose,
                 "rear_closure", "rear_closure", joint_clearance_in=1.25)

    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
    diagonal_scale = math.sqrt(1 + slope ** 2)
    radial_scale = math.sqrt(1 + (slope / 2) ** 2)
    radial_intercept = (1.25 - (SIDE_DIAGONAL_RAIL_INSET + 1.75) * diagonal_scale) / 2
    radial_inner_intercept = radial_intercept - 1.75 * radial_scale
    radial_outer_intercept = radial_intercept + 1.75 * radial_scale
    brace_specs = (
        ("INNER", "cross_brace_inner", (1.0, -slope / 2, -radial_inner_intercept, True)),
        ("OUTER", "cross_brace_outer", (1.0, -slope / 2, -radial_outer_intercept, False)),
    )
    for label, member, joint in brace_specs:
        pose = fit_post_in_support(upper_by_type[member], joint, MIN_CROSS_BRACE_JOINT_CLEARANCE)
        assert pose is not None, f"{module} {member}: no direct-bearing post solution"
        a, b, c, keep_less = joint
        joint_values = [(a * x + b * y + c) / math.hypot(a, b) for x, y in pose.footprint]
        joint_clearance = -max(joint_values) if keep_less else min(joint_values)
        assert joint_clearance >= MIN_CROSS_BRACE_JOINT_CLEARANCE - 1e-8, (
            f"{module} {member} post radial-joint clearance {joint_clearance} is below "
            f"minimum {MIN_CROSS_BRACE_JOINT_CLEARANCE}"
        )
        add_post(f"CROSS_BRACE_POST_{label}", f"cross-brace post {label.lower()}",
                 "cross_brace", pose, member, member, support_member=member,
                 joint_clearance_in=joint_clearance)

    for label, path in (("INNER", "inner_rail"), ("RADIAL", "radial_rail"),
                        ("DIAGONAL", "diagonal_rail")):
        pose = solve_front_post(lower_by_type["front_rail"], upper_by_type[path],
                                upper_by_type["front_rail"])
        assert pose is not None, f"{module} {path}: front-post support interval is under 1.5 inches"
        rear_patch = [(pose.center_x - .75, 25.5), (pose.center_x + .75, 25.5),
                      (pose.center_x + .75, 28.0), (pose.center_x - .75, 28.0)]
        front_patch = [(pose.center_x - .75, 28.0), (pose.center_x + .75, 28.0),
                       (pose.center_x + .75, 29.0), (pose.center_x - .75, 29.0)]
        assert _contains_polygon(upper_by_type[path], rear_patch)
        assert _contains_polygon(upper_by_type["front_rail"], front_patch)
        add_post(f"FRONT_POST_{label}", f"front post {label.lower()}", "front", pose,
                 "front_rail", path, upper_secondary="front_rail", upper_load_path=path,
                 primary_fastening_member=path,
                 upper_path_bearing_in=2.5, upper_front_bearing_in=1.0,
                 available_x_span_in=1.5 + 2 * pose.clearance_in, joint_clearance_in=0.0)
    return posts


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def configure_units():
    units = bpy.context.scene.unit_settings
    units.system = "IMPERIAL"
    units.length_unit = "INCHES"
    units.scale_length = 0.0254


def create_collections():
    root = bpy.context.scene.collection
    collections = {}
    for name in COLLECTION_NAMES:
        collection = bpy.data.collections.new(name)
        root.children.link(collection)
        collections[name] = collection
    return collections


def create_materials():
    colors = {
        "NATURAL_LUMBER": (0.55, 0.32, 0.15, 1.0),
        "LIGHT_MAPLE": (0.75, 0.56, 0.32, 1.0),
        "OATMEAL_CUSHION": (0.72, 0.64, 0.50, 1.0),
        "OFF_WHITE_WALL": (0.85, 0.83, 0.78, 1.0),
        "LIGHT_NEUTRAL_FLOOR": (0.45, 0.45, 0.43, 1.0),
    }
    materials = {}
    for name, color in colors.items():
        material = bpy.data.materials.new(name)
        material.diffuse_color = color
        materials[name] = material
    return materials


def add_prism(name, footprint, z0, z1, collection, material, **props):
    assert _is_simple_ccw(footprint), "footprint must be simple, non-degenerate, and CCW"
    assert z1 > z0, f"{name}: prism top Z {z1} must exceed bottom Z {z0}"
    count = len(footprint)
    vertices = [(x, y, z0) for x, y in footprint] + [(x, y, z1) for x, y in footprint]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces.extend((index, (index + 1) % count, (index + 1) % count + count, index + count)
                 for index in range(count))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if props.get("validation_group") == "STRUCTURAL":
        x_values = [point[0] for point in footprint]
        y_values = [point[1] for point in footprint]
        size_x = max(x_values) - min(x_values)
        size_y = max(y_values) - min(y_values)
        props.setdefault("modeled_size_x_in", size_x)
        props.setdefault("modeled_size_y_in", size_y)
        props.setdefault("modeled_size_z_in", z1 - z0)
        props.setdefault("stock_width_in", ACTUAL_2X4_WIDTH)
        props.setdefault("stock_thickness_in", ACTUAL_2X4_THICKNESS)
        props.setdefault("centerline_length_in", props["cut_length_in"])
        props.setdefault("long_edge_in", props["cut_length_in"])
        props.setdefault("short_edge_in", props["cut_length_in"])
        props.setdefault("end_a_angle_deg", 0.0)
        props.setdefault("end_b_angle_deg", 0.0)
        props.setdefault("orientation_deg", 0.0 if size_x >= size_y else 90.0)
    for key, value in props.items():
        obj[key] = value
    return obj


def add_box(name, size, center, collection, material, **props):
    x_size, y_size, z_size = size
    x, y, z = center
    return add_prism(
        name,
        [(x - x_size / 2, y - y_size / 2), (x + x_size / 2, y - y_size / 2),
         (x + x_size / 2, y + y_size / 2), (x - x_size / 2, y + y_size / 2)],
        z - z_size / 2, z + z_size / 2, collection, material, **props,
    )


def bounds(obj):
    points = [obj.matrix_world @ point.co for point in obj.data.vertices]
    return tuple(value for axis in range(3) for value in (
        min(point[axis] for point in points), max(point[axis] for point in points)
    ))


def union_bounds(objects):
    values = [bounds(obj) for obj in objects]
    return tuple(value for axis in range(3) for value in (
        min(item[axis * 2] for item in values), max(item[axis * 2 + 1] for item in values)
    ))


def positive_volume_overlap(a, b):
    a_bounds, b_bounds = bounds(a), bounds(b)
    return all(min(a_bounds[axis * 2 + 1], b_bounds[axis * 2 + 1])
               - max(a_bounds[axis * 2], b_bounds[axis * 2]) > 1e-9
               for axis in range(3))


def build_center(collections, materials):
    """Create the resolved 60-inch center module in inch scene coordinates."""
    structural = []
    upper, lower, posts, nailers = [], [], [], []
    common = {"module": "CENTER", "status": "RESOLVED"}

    def structural_box(function, size, center, collection, purpose, cut_length):
        name = _structural_name("CENTER", function, size, cut_length, "RESOLVED")
        obj = add_box(
            name, size, center, collection, materials["NATURAL_LUMBER"], **common,
            purpose=purpose, name_function=function, cut_length_in=cut_length,
            validation_group="STRUCTURAL",
        )
        structural.append(obj)
        return obj

    for function, y in (("UPPER_REAR_RAIL", 1.75), ("UPPER_FRONT_RAIL", 29.75)):
        upper.append(structural_box(function, (59, 3.5, 1.5), (0, y, 9),
                                    collections["CENTER_UPPER_FRAME"], "upper rail", 59))
    for index, x in enumerate((-27.75, -13.875, 0.0, 13.875, 27.75), 1):
        upper.append(structural_box(f"UPPER_MEMBER_{index:02d}", (3.5, 24.5, 1.5), (x, 15.75, 9),
                                    collections["CENTER_UPPER_FRAME"], "upper member", 24.5))

    for function, y in (("LOWER_REAR_RAIL", 1.75), ("LOWER_FRONT_RAIL", 27.25)):
        lower.append(structural_box(function, (59, 3.5, 1.5), (0, y, 0.75),
                                    collections["CENTER_LOWER_FRAME"], "lower rail", 59))
    for index, x in enumerate((-27.75, -9.25, 9.25, 27.75), 1):
        lower.append(structural_box(f"LOWER_MEMBER_{index:02d}", (3.5, 22, 1.5), (x, 14.5, 0.75),
                                    collections["CENTER_LOWER_FRAME"], "lower member", 22))

    for index, x in enumerate((-27.75, -13.875, 0.0, 13.875, 27.75), 1):
        posts.append(structural_box(f"REAR_POST_{index:02d}", (3.5, 1.5, 6.75), (x, 1.75, 4.875),
                                    collections["CENTER_POSTS"], "rear post", 6.75))
        function = f"FRONT_POST_{index:02d}"
        posts.append(add_box(
            _structural_name("CENTER", function, (1.5, 3.5, 6.75), 6.75, "RESOLVED"),
            (1.5, 3.5, 6.75), (x, 27.25, 4.875),
            collections["CENTER_POSTS"], materials["NATURAL_LUMBER"], **common,
            purpose="front post", name_function=function, cut_length_in=6.75,
            validation_group="STRUCTURAL",
            primary_fastening_note=PRIMARY_FRONT_POST_FASTENING,
        ))
        structural.append(posts[-1])

    deck = add_box("CENTER_MAPLE_DECK", (60, 32, 0.75), (0, 16, 10.125),
                   collections["PLYWOOD_DECKS"], materials["LIGHT_MAPLE"], **common,
                   purpose="maple deck", cut_length_in=60, validation_group="NONSTRUCTURAL")
    skin = add_box("CENTER_FRONT_SKIN", (60, 0.5, 6.75), (0, 31.75, 6.375),
                   collections["MAPLE_FINISH"], materials["LIGHT_MAPLE"], **common,
                   purpose="front skin", cut_length_in=60, validation_group="NONSTRUCTURAL")
    nailers.append(add_box("CENTER_LOWER_NAILER", (59, 2.5, 0.75), (0, 30.25, 3.875),
                           collections["FRONT_PANEL_NAILERS"], materials["NATURAL_LUMBER"], **common,
                           purpose="front skin lower nailer", cut_length_in=59,
                           validation_group="NONSTRUCTURAL"))
    for index, x in enumerate((-27.75, -13.875, 0.0, 13.875, 27.75), 1):
        nailers.append(add_box(
            f"CENTER_VERTICAL_NAILER_{index}", (2.5, 0.75, 4), (x, 31.125, 6.25),
            collections["FRONT_PANEL_NAILERS"], materials["NATURAL_LUMBER"], **common,
            purpose="front skin vertical nailer", cut_length_in=4, validation_group="NONSTRUCTURAL",
        ))
    return {"upper": upper, "lower": lower, "posts": posts, "deck": deck, "skin": skin,
            "nailers": nailers, "structural": structural}


def validate_center(center):
    errors = []
    upper, lower, posts = center["upper"], center["lower"], center["posts"]
    front_posts, rear_posts = posts[1::2], posts[::2]
    all_objects = upper + lower + posts + [center["deck"], center["skin"]] + center["nailers"]

    def expect(condition, message):
        if not condition:
            errors.append(message)

    expect((len(upper), len(lower), len(posts)) == (7, 6, 10), "center frame/post count")
    expect(union_bounds(upper) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75), "upper frame bounds")
    expect(union_bounds(lower) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5), "lower frame bounds")
    upper_x = (-27.75, -13.875, 0.0, 13.875, 27.75)
    lower_x = (-27.75, -9.25, 9.25, 27.75)
    expect([bounds(obj) for obj in upper] == [
        (-29.5, 29.5, 0.0, 3.5, 8.25, 9.75), (-29.5, 29.5, 28.0, 31.5, 8.25, 9.75),
        *[(x - 1.75, x + 1.75, 3.5, 28.0, 8.25, 9.75) for x in upper_x],
    ], "upper member dimensions")
    expect([bounds(obj) for obj in lower] == [
        (-29.5, 29.5, 0.0, 3.5, 0.0, 1.5), (-29.5, 29.5, 25.5, 29.0, 0.0, 1.5),
        *[(x - 1.75, x + 1.75, 3.5, 25.5, 0.0, 1.5) for x in lower_x],
    ], "lower member dimensions")
    expect([bounds(obj) for obj in posts] == [
        item for x in upper_x for item in (
            (x - 1.75, x + 1.75, 1.0, 2.5, 1.5, 8.25),
            (x - .75, x + .75, 25.5, 29.0, 1.5, 8.25),
        )
    ], "post dimensions")
    expect(all(bounds(obj)[4:] == (8.25, 9.75) for obj in upper), "upper frame elevation")
    expect(all(bounds(obj)[4:] == (0.0, 1.5) for obj in lower), "lower frame elevation")
    expect(all(bounds(obj)[4:] == (1.5, 8.25) for obj in posts), "post Z contact")
    expect(bounds(center["deck"]) == (-30.0, 30.0, 0.0, 32.0, 9.75, 10.5), "deck dimensions")
    expect(bounds(center["skin"]) == (-30.0, 30.0, 31.5, 32.0, 3.0, 9.75), "front skin dimensions")
    expect([bounds(obj) for obj in center["nailers"]] == [
        (-29.5, 29.5, 29.0, 31.5, 3.5, 4.25),
        *[(x - 1.25, x + 1.25, 30.75, 31.5, 4.25, 8.25) for x in upper_x],
    ], "nailer dimensions")
    expect(Counter(obj["cut_length_in"] for obj in center["structural"]) ==
           {59: 4, 24.5: 5, 22: 4, 6.75: 10}, "structural cut totals")
    expect(all(obj["module"] == "CENTER" and obj["status"] == "RESOLVED" and obj["purpose"]
               and "cut_length_in" in obj and obj["validation_group"] for obj in all_objects), "metadata")
    expect(all(obj.get("primary_fastening_note") == PRIMARY_FRONT_POST_FASTENING for obj in front_posts),
           "front post primary fastening note")
    expect(all(abs(bounds(center["skin"])[2] - bounds(post)[3] - 2.5) <= 1e-9 for post in front_posts),
           "2.5-inch front recess")
    expect(all(abs(min(bounds(post)[3], bounds(member)[3]) - max(bounds(post)[2], bounds(member)[2]) - 2.5) <= 1e-9
               for post, member in zip(front_posts, upper[2:])), "front post/member bearing")
    expect(all(abs(min(bounds(post)[3], bounds(upper[1])[3]) - max(bounds(post)[2], bounds(upper[1])[2]) - 1.0) <= 1e-9
               for post in front_posts), "front post/rail bearing")
    expect(not any(positive_volume_overlap(a, b) for index, a in enumerate(all_objects)
                   for b in all_objects[index + 1:]),
           "center positive-volume intersections")
    return errors


def validate_side_frames(side_frames):
    errors = []

    def expect(condition, message):
        if not condition:
            errors.append(message)

    for name, (sign, front_rear_y, z0, z1, objects) in side_frames.items():
        local = _local_side_frame_footprints(front_rear_y)
        closure = local["rear_closure"]
        diagonal = local["diagonal_rail"]
        by_type = {obj["board_type"]: obj for obj in objects}
        rear_y = SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH
        expect(len(objects) == 7, f"{name} board count")
        expect(all(bounds(obj)[2] >= SIDE_REAR_STRUCTURAL_SETBACK
                   and bounds(obj)[4:] == (z0, z1) for obj in objects), f"{name} bounds")
        expect(all(obj["module"] == name.split("_")[0]
                   and obj["status"] == "PROVISIONAL / FIELD VERIFY" for obj in objects),
               f"{name} metadata")
        expect(all(0 <= u <= finished_outer_u(y) + 1e-9 for u, y in diagonal),
               f"{name} diagonal containment")
        scale = math.sqrt(1 + (SIDE_RUN / DAYBED_FINISHED_DEPTH) ** 2)
        expect(all(abs((finished_outer_u(y) - max(u for u, point_y in diagonal if point_y == y))
                       / scale - SIDE_DIAGONAL_RAIL_INSET) <= 1e-9
                   for y in {point[1] for point in diagonal}), f"{name} diagonal inset")
        rear_inner = min(u for u, y in diagonal if abs(y - rear_y) <= 1e-9)
        rear_interface = max(u for u, _ in closure) - rear_inner
        expect(rear_interface >= MIN_REAR_FASTENING_INTERFACE,
               f"{name} rear interface {rear_interface} is below minimum "
               f"{MIN_REAR_FASTENING_INTERFACE} at SIDE_RUN {SIDE_RUN}")
        expect(all(polygons_overlap_area(closure, local[rail]) <= 1e-9
                   for rail in ("inner_rail", "radial_rail", "diagonal_rail")),
               f"{name} closure boundary contact")
        closure_obj = by_type["rear_closure"]
        for label in ("inner", "diagonal"):
            driver = _decode_points(closure_obj[f"rear_{label}_driver_prism_local"])
            clear = (max(y for _, y in driver) <= SIDE_REAR_STRUCTURAL_SETBACK + 1e-9
                     and min(y for _, y in driver) <= SIDE_REAR_STRUCTURAL_SETBACK - 5.0 + 1e-9
                     and all(polygons_overlap_area(driver, footprint) <= 1e-9
                             for footprint in local.values()))
            closure_obj[f"rear_{label}_driver_access"] = clear
            expect(clear, f"{name} rear {label} straight driver access")
        expect(closure_obj["rear_inner_interface_in"] >= ACTUAL_2X4_WIDTH - 1e-9,
               f"{name} rear inner fastening interface")
        expect(closure_obj["rear_diagonal_interface_in"] >= MIN_REAR_FASTENING_INTERFACE,
               f"{name} rear diagonal fastening interface")
        expect(polygons_overlap_area(local["inner_rail"], diagonal) <= 1e-9,
               f"{name} inner/diagonal overlap")
        expect(polygons_overlap_area(local["radial_rail"], local["inner_rail"]) <= 1e-9,
               f"{name} radial/inner overlap")
        expect(polygons_overlap_area(local["radial_rail"], diagonal) <= 1e-9,
               f"{name} radial/diagonal overlap")
        expect(polygons_overlap_area(local["cross_brace_inner"], local["cross_brace_outer"]) <= 1e-9,
               f"{name} brace overlap")
        expect(all((min(y for _, y in local[brace]), max(y for _, y in local[brace])) == (22.0, 25.5)
                   for brace in ("cross_brace_inner", "cross_brace_outer")),
               f"{name} brace bounds")
        if front_rear_y == 25.5:
            expect(all(polygons_overlap_area(local[brace], local["front_rail"]) <= 1e-9
                       for brace in ("cross_brace_inner", "cross_brace_outer")),
                   f"{name} brace/front boundary contact")
    return errors


def validate_side_posts(side_posts, side_frames):
    errors = []

    def expect(condition, message):
        if not condition:
            errors.append(message)

    for module, (sign, posts) in side_posts.items():
        upper_objects = side_frames[f"{module}_UPPER_FRAME"][4]
        lower_objects = side_frames[f"{module}_LOWER_FRAME"][4]
        upper_by_type = {obj["board_type"]: obj for obj in upper_objects}
        lower_by_type = {obj["board_type"]: obj for obj in lower_objects}
        upper = {key: _local_object_footprint(sign, obj) for key, obj in upper_by_type.items()}
        lower = {key: _local_object_footprint(sign, obj) for key, obj in lower_by_type.items()}
        expected_top = SIDE_UPPER_BOTTOM_Z[module]
        expected_cut = expected_top - 1.5
        expect(len(posts) == 7, f"{module} post count")
        expect(Counter(obj["post_role"] for obj in posts) ==
               {"rear": 2, "cross_brace": 2, "front": 3}, f"{module} post purposes")
        expect(all(bounds(obj)[4:] == (1.5, expected_top)
                   and abs(obj["cut_length_in"] - expected_cut) <= 1e-9 for obj in posts),
               f"{module} post heights and Z contacts")
        expect(all(obj["status"] == "PROVISIONAL / FIELD VERIFY" and obj["module"] == module
                   and obj["driver_access"] and obj["top_driver_access"]
                   and obj["bottom_driver_access"] and obj["fastener_edge_distance_in"] >= .75
                   for obj in posts), f"{module} post metadata and driver access")
        for post in posts:
            plan = _local_object_footprint(sign, post)
            role = post["post_role"]
            if role == "rear":
                expect(_contains_polygon(lower["rear_closure"], plan)
                       and _contains_polygon(upper["rear_closure"], plan),
                       f"{post.name} rear closure bearing")
                expect(max(y for _, y in plan) <=
                       SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH - 1.0 + 1e-9,
                       f"{post.name} rear fastening clearance")
            elif role == "cross_brace":
                member = post["support_member"]
                expect(_contains_polygon(lower[member], plan) and _contains_polygon(upper[member], plan),
                       f"{post.name} cross-brace bearing")
                expect(post["joint_clearance_in"] >= MIN_CROSS_BRACE_JOINT_CLEARANCE - 1e-8,
                       f"{post.name} radial-joint clearance")
                opposing = ("cross_brace_outer" if member == "cross_brace_inner"
                            else "cross_brace_inner")
                for frame_objects, frame_footprints in ((upper_by_type, upper),
                                                        (lower_by_type, lower)):
                    brace = frame_objects[member]
                    prism = _decode_points(brace["radial_joint_driver_prism_local"])
                    access = (
                        _contains_polygon(frame_footprints[member], prism)
                        and polygons_overlap_area(prism, plan) <= 1e-6
                        and polygons_overlap_area(prism, frame_footprints[opposing]) <= 1e-6
                        and polygons_overlap_area(prism, frame_footprints["radial_rail"]) <= 1e-6
                        and all(polygons_overlap_area(prism, footprint) <= 1e-6
                                for key, footprint in frame_footprints.items()
                                if key not in {member, opposing, "radial_rail"})
                    )
                    brace["radial_joint_post_clearance_in"] = post["joint_clearance_in"]
                    brace["radial_joint_driver_access"] = access
                    expect(access, f"{brace.name} toe-screw driver prism collision")
            else:
                path = post["upper_load_path"]
                center_u = post["local_center_u"]
                rear_patch = [(center_u - .75, 25.5), (center_u + .75, 25.5),
                              (center_u + .75, 28.0), (center_u - .75, 28.0)]
                front_patch = [(center_u - .75, 28.0), (center_u + .75, 28.0),
                               (center_u + .75, 29.0), (center_u - .75, 29.0)]
                expect(_contains_polygon(lower["front_rail"], plan),
                       f"{post.name} lower-front bearing")
                expect(_contains_polygon(upper[path], rear_patch)
                       and _contains_polygon(upper["front_rail"], front_patch),
                       f"{post.name} named upper load-path bearing")
                expect(post["upper_path_bearing_in"] == 2.5
                       and post["upper_front_bearing_in"] == 1.0
                       and post["available_x_span_in"] >= 1.5,
                       f"{post.name} front bearing dimensions")
            pose = PostPose(post["local_center_u"], post["center_y"], post["post_rotation_deg"],
                            plan, post["joint_clearance_in"])
            lower_member = post["lower_support"]
            upper_member = post.get("upper_load_path", post["upper_support"])
            expect(_driver_access(pose, lower[lower_member],
                                  [polygon for key, polygon in lower.items() if key != lower_member])
                   and _driver_access(pose, upper[upper_member],
                                      [polygon for key, polygon in upper.items() if key != upper_member]),
                   f"{post.name} recomputed driver access")
        expect(not any(polygons_overlap_area(_local_object_footprint(sign, post),
                                             _local_object_footprint(sign, other)) > 1e-9
                       for index, post in enumerate(posts) for other in posts[index + 1:]),
               f"{module} post intersections")
        outer = next(obj for obj in posts if obj["purpose"] == "cross-brace post outer")
        expect(math.isfinite(outer["post_rotation_deg"]),
               f"{module} outer-brace post solved nonfinite rotation {outer['post_rotation_deg']}")
        if _default_side_parameter_set():
            expect(abs(abs(outer["post_rotation_deg"]) - 46.4) <= .11,
                   f"{module} default outer-brace post rotation expected about 46.4, "
                   f"actual {outer['post_rotation_deg']}")
    return errors


def _is_simple_ccw(footprint):
    if len(footprint) < 3 or _signed_polygon_area(footprint) <= 1e-9:
        return False
    edges = list(zip(footprint, footprint[1:] + footprint[:1]))
    if any(start == end for start, end in edges):
        return False
    for index, (start, end) in enumerate(edges):
        for other_index, (other_start, other_end) in enumerate(edges[index + 1:], index + 1):
            if other_index == index + 1 or (index == 0 and other_index == len(edges) - 1):
                continue
            if segments_intersect(start, end, other_start, other_end):
                return False
    return True


def validate_side_feasibility():
    assert math.isfinite(SIDE_RUN) and SIDE_RUN > 0, (
        f"SIDE_RUN {SIDE_RUN}: required a finite positive side expansion before framing can be built"
    )
    assert math.isfinite(SIDE_REAR_STRUCTURAL_SETBACK) and SIDE_REAR_STRUCTURAL_SETBACK >= 5.0, (
        f"SIDE_REAR_STRUCTURAL_SETBACK {SIDE_REAR_STRUCTURAL_SETBACK}: at least 5.0 inches is "
        "required for the straight rear assembly driver path"
    )
    mating_u = -0.5
    inner_outer_u = mating_u + ACTUAL_2X4_WIDTH
    rear_y = SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH
    closure_outer_u = finished_outer_u(SIDE_REAR_STRUCTURAL_SETBACK)
    closure_width = closure_outer_u - mating_u
    required_closure_width = 2 * ACTUAL_2X4_WIDTH + 1.0
    assert closure_width >= required_closure_width - 1e-9, (
        f"SIDE_RUN {SIDE_RUN}: rear closure usable width {closure_width} is below required "
        f"{required_closure_width} for two 3.5-inch rear-post footprints plus 1-inch fastening gap"
    )

    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
    diagonal_scale = math.sqrt(1 + slope ** 2)
    radial_scale = math.sqrt(1 + (slope / 2) ** 2)
    diagonal_inner = lambda y: slope * y - (SIDE_DIAGONAL_RAIL_INSET + 3.5) * diagonal_scale
    diagonal_outer = lambda y: slope * y - SIDE_DIAGONAL_RAIL_INSET * diagonal_scale
    diagonal_center = lambda y: slope * y - (SIDE_DIAGONAL_RAIL_INSET + 1.75) * diagonal_scale
    radial_center = lambda y: (1.25 + diagonal_center(y)) / 2
    radial_inner = lambda y: radial_center(y) - 1.75 * radial_scale
    radial_outer = lambda y: radial_center(y) + 1.75 * radial_scale

    rear_corridor = diagonal_inner(rear_y) - inner_outer_u
    assert rear_corridor > 1e-9, (
        f"SIDE_RUN {SIDE_RUN}: rear longitudinal support corridor {rear_corridor} at Y={rear_y} "
        f"is nonpositive between inner-rail outer U={inner_outer_u} and diagonal-rail inner U="
        f"{diagonal_inner(rear_y)}"
    )
    rear_interface = closure_outer_u - diagonal_inner(rear_y)
    assert rear_interface >= MIN_REAR_FASTENING_INTERFACE - 1e-9, (
        f"SIDE_RUN {SIDE_RUN}: rear closure/diagonal fastening interface {rear_interface} is below "
        f"required {MIN_REAR_FASTENING_INTERFACE}"
    )

    brace_y0 = SIDE_CROSS_BRACE_CENTER_Y - ACTUAL_2X4_WIDTH / 2
    brace_y1 = SIDE_CROSS_BRACE_CENTER_Y + ACTUAL_2X4_WIDTH / 2
    assert rear_y < brace_y0, (
        f"SIDE_REAR_STRUCTURAL_SETBACK {SIDE_REAR_STRUCTURAL_SETBACK}: longitudinal rail start "
        f"Y={rear_y} must remain behind cross-brace rear edge Y={brace_y0}"
    )
    for y in (brace_y0, brace_y1):
        inner_brace_corridor = radial_inner(y) - inner_outer_u
        outer_brace_corridor = diagonal_inner(y) - radial_outer(y)
        assert inner_brace_corridor > 1e-9, (
            f"SIDE_RUN {SIDE_RUN}: inner cross-brace support corridor {inner_brace_corridor} "
            f"is nonpositive at Y={y}"
        )
        assert outer_brace_corridor > 1e-9, (
            f"SIDE_RUN {SIDE_RUN}: outer cross-brace support corridor {outer_brace_corridor} "
            f"is nonpositive at Y={y}"
        )

    for front_rear_y in (25.5, 28.0):
        for y in (front_rear_y, front_rear_y + ACTUAL_2X4_WIDTH):
            front_corridor = diagonal_outer(y) - mating_u
            assert front_corridor > 1e-9, (
                f"SIDE_RUN {SIDE_RUN}: front-rail footprint corridor {front_corridor} is "
                f"nonpositive at Y={y}"
            )


def validate_parameters_and_polygons():
    assert CENTER_FLAT_WALL_WIDTH == 60.0, (
        f"CENTER_FLAT_WALL_WIDTH actual {CENTER_FLAT_WALL_WIDTH}, required 60.0; "
        "the V3 resolved center module and side-module mating interface would otherwise mismatch"
    )
    assert DAYBED_FINISHED_DEPTH == 32.0, (
        f"DAYBED_FINISHED_DEPTH actual {DAYBED_FINISHED_DEPTH}, required 32.0; "
        "the V3 resolved center module depth and side-module mating interface would otherwise mismatch"
    )
    implied_angle = math.degrees(math.atan2(SIDE_RUN, DAYBED_FINISHED_DEPTH))
    expected_front_width = CENTER_FLAT_WALL_WIDTH + 2 * SIDE_RUN
    assert abs(PROVISIONAL_TOTAL_FRONT_WIDTH - expected_front_width) <= 1e-6, (
        f"PROVISIONAL_TOTAL_FRONT_WIDTH actual {PROVISIONAL_TOTAL_FRONT_WIDTH}, "
        f"expected {expected_front_width} = CENTER_FLAT_WALL_WIDTH {CENTER_FLAT_WALL_WIDTH} "
        f"+ 2 * SIDE_RUN {SIDE_RUN}"
    )
    assert abs(implied_angle - SIDE_ANGLE) <= 1e-6, (
        f"SIDE_ANGLE actual {SIDE_ANGLE} does not match implied angle {implied_angle} "
        f"from SIDE_RUN {SIDE_RUN} / DAYBED_FINISHED_DEPTH {DAYBED_FINISHED_DEPTH}"
    )
    assert math.isfinite(APPROX_SIDE_WALL_ANGLE) and 0 < APPROX_SIDE_WALL_ANGLE < 90, (
        f"APPROX_SIDE_WALL_ANGLE actual {APPROX_SIDE_WALL_ANGLE}; required finite 0..90 degrees"
    )
    assert SIDE_CROSS_BRACE_CENTER_Y == 23.75, (
        f"SIDE_CROSS_BRACE_CENTER_Y expected 23.75, actual {SIDE_CROSS_BRACE_CENTER_Y}"
    )
    assert SIDE_CROSS_BRACE_CENTER_Y - 1.75 == 22.0, (
        f"cross-brace rear edge expected 22.0, actual {SIDE_CROSS_BRACE_CENTER_Y - 1.75}"
    )
    assert SIDE_CROSS_BRACE_CENTER_Y + 1.75 == 25.5, (
        f"cross-brace front edge expected 25.5, actual {SIDE_CROSS_BRACE_CENTER_Y + 1.75}"
    )
    validate_side_feasibility()

    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    touching = [(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)]
    overlap = [(0.5, 0.0), (1.5, 0.0), (1.5, 1.0), (0.5, 1.0)]
    assert polygon_area(square) == 1.0, "polygon kernel unit-square area"
    assert polygons_overlap_area(square, touching) == 0.0, "polygon kernel touching-boundary area"
    assert abs(polygons_overlap_area(square, overlap) - 0.5) <= 1e-9, "polygon kernel overlap area"
    half_width = CENTER_FLAT_WALL_WIDTH / 2
    assert side_u(module_sign("RIGHT"), -half_width) == 0.0 \
        and side_u(module_sign("LEFT"), half_width) == 0.0, (
        f"side coordinate origins mismatch resolved half-width {half_width}"
    )
    assert mirror_to_world(module_sign("RIGHT"), [(0.0, 0.0)])[0] == (-half_width, 0.0), (
        f"viewer-right world mirror mismatch resolved half-width {half_width}"
    )


def build_decks(collections, materials, center):
    """Add the two provisional side decks; the resolved center deck already exists."""
    decks = [center["deck"]]
    for module in ("LEFT", "RIGHT"):
        z0 = SIDE_UPPER_BOTTOM_Z[module] + ACTUAL_2X4_THICKNESS
        z1 = z0 + 0.75
        decks.append(add_prism(
            f"{module}_MAPLE_DECK", side_finished_vertices(module), z0, z1,
            collections["PLYWOOD_DECKS"],
            materials["LIGHT_MAPLE"], module=module, purpose="maple deck",
            status="PROVISIONAL / FIELD VERIFY", validation_group="NONSTRUCTURAL",
            provisional_note="PROVISIONAL / FIELD VERIFY",
        ))
    return decks


def build_finish(collections, materials, center):
    """Add separate, clipped maple side-front skins without touching framing."""
    skins = [center["skin"]]
    for module in ("LEFT", "RIGHT"):
        z1 = SIDE_UPPER_BOTTOM_Z[module] + ACTUAL_2X4_THICKNESS
        skins.append(add_prism(
            f"{module}_FRONT_SKIN", side_front_skin_footprint(module), 3.0, z1,
            collections["MAPLE_FINISH"],
            materials["LIGHT_MAPLE"], module=module, purpose="front skin",
            status="PROVISIONAL / FIELD VERIFY", validation_group="NONSTRUCTURAL",
            provisional_note="PROVISIONAL / FIELD VERIFY",
        ))
    return skins


def build_nailers(collections, materials, center):
    """Lightweight finish-only nailers stay behind skins and above the recessed lower frames."""
    nailers = list(center["nailers"])
    for module in ("LEFT", "RIGHT"):
        sign = module_sign(module)
        top = SIDE_UPPER_BOTTOM_Z[module]
        x = side_x(sign, SIDE_RUN / 2)
        common = {"module": module, "status": "PROVISIONAL / FIELD VERIFY",
                  "validation_group": "NONSTRUCTURAL", "provisional_note": "PROVISIONAL / FIELD VERIFY"}
        nailers.append(add_box(
            f"{module}_LOWER_NAILER", (20.0, .75, .75), (x, 31.125, 3.875),
            collections["FRONT_PANEL_NAILERS"], materials["NATURAL_LUMBER"], **common,
            purpose="front skin lower nailer",
        ))
        nailers.append(add_box(
            f"{module}_VERTICAL_NAILER", (2.0, .75, top - 4.25), (x, 31.125, (top + 4.25) / 2),
            collections["FRONT_PANEL_NAILERS"], materials["NATURAL_LUMBER"], **common,
            purpose="front skin vertical nailer",
        ))
    return nailers


def build_cushion(collections, materials):
    sign = module_sign("RIGHT")
    footprint = [
        (29.5, DAYBED_FINISHED_DEPTH - .5),
        (side_x(sign, finished_outer_u(DAYBED_FINISHED_DEPTH - .5) - 1.0),
         DAYBED_FINISHED_DEPTH - .5),
        (side_x(sign, finished_outer_u(1.5) - 1.0), 1.5),
        (-29.5, .5), (29.5, .5),
    ]
    return add_prism(
        "CENTER_RIGHT_CUSHION_REFERENCE", footprint, 10.5, 14.5,
        collections["CUSHION_REFERENCE"], materials["OATMEAL_CUSHION"], module="CENTER_RIGHT",
        purpose="nonstructural cushion reference", status="PROVISIONAL / FIELD VERIFY",
        validation_group="NONSTRUCTURAL", provisional_note="NOT FINAL UPHOLSTERY DIMENSION",
    )


def _strip_footprint(a, b, width):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    return [(a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny),
            (b[0] + nx, b[1] + ny), (a[0] + nx, a[1] + ny)]


def add_reference_plane(name, footprint, z, collection, material, **props):
    assert _is_simple_ccw(footprint), f"{name}: reference footprint must be simple nondegenerate CCW"
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata([(x, y, z) for x, y in footprint], [], [tuple(range(len(footprint)))])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    for key, value in props.items():
        obj[key] = value
    return obj


def add_vertical_reference_face(name, x, y0, y1, z0, z1, collection, material, **props):
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], [],
                     [(0, 1, 2, 3)])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.show_in_front = True
    for key, value in props.items():
        obj[key] = value
    return obj


def build_room_reference(collections, materials):
    room = collections["ROOM_REFERENCE"]
    left_wall = side_wall_endpoints("LEFT")
    right_wall = side_wall_endpoints("RIGHT")
    wall_run = DAYBED_FINISHED_DEPTH * math.tan(math.radians(APPROX_SIDE_WALL_ANGLE))
    outer_x = CENTER_FLAT_WALL_WIDTH / 2 + SIDE_RUN
    refs = [
        add_box("ROOM_FLOOR_REFERENCE", (PROVISIONAL_TOTAL_FRONT_WIDTH + 16.0, 80.0, .25),
                (0.0, 18.0, -.125), room,
                materials["LIGHT_NEUTRAL_FLOOR"], purpose="floor reference", status="REFERENCE"),
        add_box("CENTER_REAR_WALL_REFERENCE", (60.0, .5, 15.0), (0.0, -.25, 7.5), room,
                materials["OFF_WHITE_WALL"], purpose="resolved center wall", status="REFERENCE"),
        add_prism("LEFT_ANGLED_WALL_REFERENCE", _strip_footprint(*left_wall, .5),
                  0.0, 15.0, room, materials["OFF_WHITE_WALL"], purpose="approximate angled wall",
                  status="PROVISIONAL / FIELD VERIFY", side_reference=True,
                  provisional_note="PROVISIONAL / FIELD VERIFY",
                  approx_wall_angle_deg=APPROX_SIDE_WALL_ANGLE, approx_wall_run_in=wall_run),
        add_prism("RIGHT_ANGLED_WALL_REFERENCE", _strip_footprint(*right_wall, .5),
                  0.0, 15.0, room, materials["OFF_WHITE_WALL"], purpose="approximate angled wall",
                  status="PROVISIONAL / FIELD VERIFY", side_reference=True,
                  provisional_note="PROVISIONAL / FIELD VERIFY",
                  approx_wall_angle_deg=APPROX_SIDE_WALL_ANGLE, approx_wall_run_in=wall_run),
        add_reference_plane("SILL_UNDERSIDE_REFERENCE", [(-outer_x, 0.0), (outer_x, 0.0),
                                                           (outer_x, APPROX_SILL_PROJECTION),
                                                           (-outer_x, APPROX_SILL_PROJECTION)],
                            APPROX_SILL_UNDERSIDE_HEIGHT, room, materials["OFF_WHITE_WALL"],
                            purpose="approximate sill underside", status="REFERENCE"),
    ]
    if FACET_CENTER_FLAT > 0 and FACET_TRANSITION > 0:
        for side in ("LEFT", "RIGHT"):
            x = side_x(module_sign(side), 0.0)
            refs.append(add_box(
                f"{side}_FACET_REFERENCE", (FACET_TRANSITION, FACET_CENTER_FLAT, 15.0),
                (x, FACET_CENTER_FLAT / 2, 7.5), room, materials["OFF_WHITE_WALL"],
                purpose="optional bay facet", status="PROVISIONAL / FIELD VERIFY", side_reference=True,
                provisional_note="PROVISIONAL / FIELD VERIFY",
            ))
    return refs


def build_connection_markers(collections, materials, center, side_frames):
    markers = []
    side_front = {
        key: next(obj for obj in value[4] if obj["board_type"] == "front_rail")
        for key, value in side_frames.items()
    }
    specs = (
        ("LEFT_LOWER_FRONT_CONNECTION_ZONE", 29.5, center["lower"][1],
         side_front["LEFT_LOWER_FRAME"]),
        ("RIGHT_LOWER_FRONT_CONNECTION_ZONE", -29.5, center["lower"][1],
         side_front["RIGHT_LOWER_FRAME"]),
        ("RIGHT_UPPER_FRONT_CONNECTION_ZONE", -29.5, center["upper"][1],
         side_front["RIGHT_UPPER_FRAME"]),
    )
    for name, x, center_support, side_support in specs:
        center_bounds, side_bounds = bounds(center_support), bounds(side_support)
        y0, y1 = max(center_bounds[2], side_bounds[2]) + .25, min(
            center_bounds[3], side_bounds[3]) - .25
        z0, z1 = max(center_bounds[4], side_bounds[4]) + .1, min(
            center_bounds[5], side_bounds[5]) - .1
        assert y1 > y0 and z1 > z0, f"{name}: no physical structural mating-face area"
        markers.append(add_vertical_reference_face(
            name, x, y0, y1, z0, z1, collections["MODULE_CONNECTION_REFERENCE"],
            materials["LIGHT_MAPLE"], purpose="nonstructural module joining zone",
            status="REFERENCE", module="CENTER_SIDE", validation_group="NONSTRUCTURAL",
            center_support_object=center_support.name, side_support_object=side_support.name,
            contact_verified=True,
        ))
    return markers


def _add_text(name, body, location, collection, material, **props):
    curve = bpy.data.curves.new(f"{name}_CURVE", "FONT")
    curve.body, curve.align_x, curve.size, curve.extrude = body, "CENTER", 1.5, .02
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.show_in_front = True
    curve.materials.append(material)
    collection.objects.link(obj)
    for key, value in props.items():
        obj[key] = value
    return obj


def build_dimensions(collections, materials):
    return [
        _add_text("DIMENSION_106IN_MEASURED", '106" MEASURED CORNER-TO-CORNER', (0, -2, 1),
                  collections["DIMENSIONS"], materials["NATURAL_LUMBER"], status="REFERENCE"),
        _add_text("DIMENSION_TOTAL_FRONT_WIDTH_PROVISIONAL",
                  f'{_format_number(PROVISIONAL_TOTAL_FRONT_WIDTH)}" PROVISIONAL — VERIFY FROM ROOM TEMPLATE',
                  (0, DAYBED_FINISHED_DEPTH + 2, 1),
                  collections["DIMENSIONS"], materials["NATURAL_LUMBER"], status="PROVISIONAL / FIELD VERIFY"),
        _add_text("DIMENSION_SIDE_GEOMETRY",
                  f"SIDE STRUCTURE PROVISIONAL; ROOM WALL ≈ {_format_number(APPROX_SIDE_WALL_ANGLE)}°",
                  (0, 36, 3), collections["DIMENSIONS"], materials["NATURAL_LUMBER"],
                  status="PROVISIONAL / FIELD VERIFY"),
        _add_text("DIMENSION_SILL_15IN", 'SILL UNDERSIDE ≈ 15"', (0, 3, 15),
                  collections["DIMENSIONS"], materials["NATURAL_LUMBER"], status="REFERENCE"),
    ]


def _look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_cameras(collections):
    views = (
        ("TOP_ORTHO_COMPLETE", (0, 16, 80), (0, 16, 0), 110, "FINISHED"),
        ("FRONT_COMPLETE", (0, 82, 20), (0, 16, 8), 105, "FINISHED"),
        ("SIDE_COMPLETE", (95, 16, 24), (20, 16, 7), 42, "FRAMING_ONLY"),
        ("ISOMETRIC_FRAMING_COMPLETE", (92, 85, 68), (0, 16, 7), 150, "FRAMING_ONLY"),
        ("ISOMETRIC_FINISHED_COMPLETE", (92, 85, 68), (0, 16, 9), 150, "FINISHED"),
        ("ISOMETRIC_CENTER", (56, 60, 42), (0, 16, 7), 70, "FINISHED"),
        ("ISOMETRIC_LEFT", (85, DAYBED_FINISHED_DEPTH + 30, 54), (45, 16, 9), 70, "FINISHED"),
        ("ISOMETRIC_RIGHT", (-85, DAYBED_FINISHED_DEPTH + 30, 45), (-45, 16, 7), 70, "FINISHED"),
    )
    cameras = []
    for name, location, target, scale, inspection_layer in views:
        data = bpy.data.cameras.new(name)
        data.type, data.ortho_scale = "ORTHO", scale
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        _look_at(obj, target)
        obj["inspection_layer"] = inspection_layer
        collections["CAMERAS"].objects.link(obj)
        cameras.append(obj)
    return cameras


def configure_view_layers(collections):
    scene = bpy.context.scene
    while len(scene.view_layers) > 1:
        scene.view_layers.remove(scene.view_layers[-1])
    finished = scene.view_layers[0]
    finished.name = "FINISHED"
    framing = scene.view_layers.new("FRAMING_ONLY")
    for name in ("PLYWOOD_DECKS", "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE",
                 "ROOM_REFERENCE"):
        framing.layer_collection.children[name].exclude = True
    return finished, framing


def validate_finish_room(center, decks, skins, nailers, cushion, room, cameras):
    errors = []

    def expect(condition, message):
        if not condition:
            errors.append(message)

    deck_by_name = {obj.name: obj for obj in decks}
    skin_by_module = {obj["module"]: obj for obj in skins}
    expect(set(deck_by_name) == {"CENTER_MAPLE_DECK", "LEFT_MAPLE_DECK", "RIGHT_MAPLE_DECK"}, "deck objects")
    expect(bounds(deck_by_name["CENTER_MAPLE_DECK"])[4:] == (9.75, 10.5)
           and bounds(deck_by_name["RIGHT_MAPLE_DECK"])[4:] == (9.75, 10.5), "center right deck height")
    expect(bounds(deck_by_name["LEFT_MAPLE_DECK"])[4:] == (13.75, 14.5), "left landing deck height")
    expect(abs(bounds(deck_by_name["LEFT_MAPLE_DECK"])[5]
               - bounds(deck_by_name["CENTER_MAPLE_DECK"])[5] - 4.0) <= 1e-9,
           "left landing difference")
    expect(all(bounds(skin)[4] == 3.0 for skin in skins), "front skin lower shadow gaps")
    expect(bounds(cushion)[4:] == (10.5, 14.5) and bounds(cushion)[1] <= 29.5,
           "cushion height and left-landing clearance")
    sill = next(obj for obj in room if obj.name == "SILL_UNDERSIDE_REFERENCE")
    expect(bounds(sill)[4:] == (15.0, 15.0), "sill underside elevation")
    expect(bounds(deck_by_name["LEFT_MAPLE_DECK"])[5] < bounds(sill)[4], "left deck below sill")
    expect(all(bounds(nailer)[4] >= 3.5 for nailer in nailers), "nailers above lower frame")
    finish_objects = decks + skins + nailers + [cushion]
    finish_intersections = [
        (obj.name, other.name)
        for index, obj in enumerate(finish_objects) for other in finish_objects[index + 1:]
        if (min(bounds(obj)[5], bounds(other)[5]) - max(bounds(obj)[4], bounds(other)[4]) > 1e-6
            and polygons_overlap_area(object_footprint(obj), object_footprint(other)) > 1e-6)
    ]
    expect(not finish_intersections, f"finish positive-volume intersections: {finish_intersections}")
    for module, deck_name in (("CENTER", "CENTER_MAPLE_DECK"),
                              ("LEFT", "LEFT_MAPLE_DECK"), ("RIGHT", "RIGHT_MAPLE_DECK")):
        skin, deck = skin_by_module[module], deck_by_name[deck_name]
        expect(abs(bounds(skin)[5] - bounds(deck)[4]) <= 1e-6
               and polygons_overlap_area(object_footprint(skin), object_footprint(deck)) > 1e-6,
               f"{module} deck/front-skin boundary joint")
        lower_top = max(bounds(obj)[5] for obj in bpy.data.collections[f"{module}_LOWER_FRAME"].objects)
        for nailer in (obj for obj in nailers if obj["module"] == module):
            nailer_bounds, skin_bounds = bounds(nailer), bounds(skin)
            expect(abs(nailer_bounds[3] - skin_bounds[2]) <= 1e-6,
                   f"{nailer.name} front-face/skin-back contact")
            expect(nailer_bounds[4] - lower_top >= 2.0 - 1e-6,
                   f"{nailer.name} must not bridge to recessed lower frame")
    expected = {"TOP_ORTHO_COMPLETE", "FRONT_COMPLETE", "SIDE_COMPLETE", "ISOMETRIC_FRAMING_COMPLETE",
                "ISOMETRIC_FINISHED_COMPLETE", "ISOMETRIC_CENTER", "ISOMETRIC_LEFT", "ISOMETRIC_RIGHT"}
    expect({obj.name for obj in cameras} == expected, "camera set")
    expect({layer.name for layer in bpy.context.scene.view_layers} >= {"FRAMING_ONLY", "FINISHED"}, "view layers")
    framing = bpy.context.scene.view_layers["FRAMING_ONLY"]
    expect(all(framing.layer_collection.children[name].exclude
               for name in ("PLYWOOD_DECKS", "MAPLE_FINISH", "FRONT_PANEL_NAILERS", "CUSHION_REFERENCE")),
           "framing visibility exclusions")
    expect(framing.layer_collection.children["ROOM_REFERENCE"].exclude,
           "framing inspection room-reference exclusion")
    side_camera = next(obj for obj in cameras if obj.name == "SIDE_COMPLETE")
    expect(side_camera.data.ortho_scale <= 45.0
           and side_camera["inspection_layer"] == "FRAMING_ONLY", "side inspection framing")
    expect(all(obj.show_in_front and obj.data.size >= 1.25
               for obj in bpy.data.collections["DIMENSIONS"].objects),
           "dimension annotation readability")
    expect(all(obj["status"] == "PROVISIONAL / FIELD VERIFY" for obj in room if obj.get("side_reference")),
           "provisional side references")
    wall_run = DAYBED_FINISHED_DEPTH * math.tan(math.radians(APPROX_SIDE_WALL_ANGLE))
    for module in ("LEFT", "RIGHT"):
        wall = next(obj for obj in room if obj.name == f"{module}_ANGLED_WALL_REFERENCE")
        footprint = object_footprint(wall)
        start = ((footprint[0][0] + footprint[3][0]) / 2,
                 (footprint[0][1] + footprint[3][1]) / 2)
        end = ((footprint[1][0] + footprint[2][0]) / 2,
               (footprint[1][1] + footprint[2][1]) / 2)
        expected_start, expected_end = side_wall_endpoints(module)
        expect(all(abs(a - b) <= 1e-5 for a, b in zip(start + end,
                                                       expected_start + expected_end)),
               f"{module} approximate wall angle-derived geometry")
        expect(abs(wall["approx_wall_angle_deg"] - APPROX_SIDE_WALL_ANGLE) <= 1e-9
               and abs(wall["approx_wall_run_in"] - wall_run) <= 1e-6,
               f"{module} approximate wall metadata")
    return errors


def validate_connection_markers(markers):
    errors = []
    expected = {"LEFT_LOWER_FRONT_CONNECTION_ZONE", "RIGHT_LOWER_FRONT_CONNECTION_ZONE",
                "RIGHT_UPPER_FRONT_CONNECTION_ZONE"}
    if {obj.name for obj in markers} != expected:
        errors.append("module connection markers do not match the three physical mating zones")
        return errors
    for marker in markers:
        marker_bounds = bounds(marker)
        center = bpy.data.objects.get(marker.get("center_support_object", ""))
        side = bpy.data.objects.get(marker.get("side_support_object", ""))
        if not center or not side:
            errors.append(f"{marker.name}: named structural support missing")
            continue
        center_bounds, side_bounds = bounds(center), bounds(side)
        side_index = 0 if marker_bounds[0] > 0 else 1
        center_index = 1 if marker_bounds[0] > 0 else 0
        valid = (
            abs(marker_bounds[0] - marker_bounds[1]) <= 1e-6
            and abs(marker_bounds[0] - center_bounds[center_index]) <= 1e-5
            and abs(marker_bounds[0] - side_bounds[side_index]) <= 1e-5
            and marker_bounds[2] >= max(center_bounds[2], side_bounds[2]) - 1e-6
            and marker_bounds[3] <= min(center_bounds[3], side_bounds[3]) + 1e-6
            and marker_bounds[4] >= max(center_bounds[4], side_bounds[4]) - 1e-6
            and marker_bounds[5] <= min(center_bounds[5], side_bounds[5]) + 1e-6
            and marker.get("validation_group") == "NONSTRUCTURAL"
        )
        if not valid:
            errors.append(f"{marker.name}: marker does not lie on both named structural mating faces")
    return errors


def _support_span_components():
    slope = SIDE_RUN / DAYBED_FINISHED_DEPTH
    scale = math.sqrt(1 + slope ** 2)
    widest_y = 28.0
    inner_center = 1.25
    diagonal_center = slope * widest_y - (SIDE_DIAGONAL_RAIL_INSET + 1.75) * scale
    radial_center = (inner_center + diagonal_center) / 2
    rail_gap = max(radial_center - inner_center, diagonal_center - radial_center)
    rear_tip = math.hypot(SIDE_REAR_STRUCTURAL_SETBACK,
                          finished_outer_u(SIDE_REAR_STRUCTURAL_SETBACK))
    row_gap = max(SIDE_CROSS_BRACE_CENTER_Y - (SIDE_REAR_STRUCTURAL_SETBACK + 1.75),
                  (28.0 + 1.75) - SIDE_CROSS_BRACE_CENTER_Y)
    return {"rear_tip": rear_tip, "support_rail": rail_gap, "support_row": row_gap}


def calculate_support_spans(center, left, right):
    upper_members = sorted(
        (bounds(obj)[0] + bounds(obj)[1]) / 2
        for obj in center["upper"] if obj["purpose"] == "upper member"
    )
    assert len(upper_members) == 5 and left["upper"] and right["upper"], (
        f"support-span inputs require five center upper members and populated side frames; "
        f"actual center {len(upper_members)}, left {len(left['upper'])}, right {len(right['upper'])}"
    )
    center_span = max(b - a for a, b in zip(upper_members, upper_members[1:]))
    side_span = max(_support_span_components().values())
    return {"CENTER": center_span, "LEFT": side_span, "RIGHT": side_span}


def _format_number(value):
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def _cutlist_rows(structural):
    rows = [
        ("CENTER", "CENTER_UPPER_LOWER_RAILS_59IN_FLAT_3.5X1.5", 4, 59.0, 0.0, 0.0,
         "FLAT 2X4 / 3.5 W X 1.5 H / X-AXIS", "RESOLVED"),
        ("CENTER", "CENTER_UPPER_MEMBERS_24.5IN_FLAT_3.5X1.5", 5, 24.5, 0.0, 0.0,
         "FLAT 2X4 / 3.5 X X 1.5 Z / Y-AXIS", "RESOLVED"),
        ("CENTER", "CENTER_LOWER_MEMBERS_22IN_FLAT_3.5X1.5", 4, 22.0, 0.0, 0.0,
         "FLAT 2X4 / 3.5 X X 1.5 Z / Y-AXIS", "RESOLVED"),
        ("CENTER", "CENTER_VERTICAL_POSTS_6.75IN_ACTUAL_1.5X3.5", 10, 6.75, 0.0, 0.0,
         "VERTICAL 2X4", "RESOLVED"),
    ]
    for module in ("LEFT", "RIGHT"):
        for obj in sorted((item for item in structural if item["module"] == module), key=lambda item: item.name):
            if "post_role" in obj:
                orientation = f"VERTICAL 2X4; PLAN {obj['orientation_deg']:.6f} DEG"
            else:
                orientation = f"FLAT 2X4; PLAN {obj['orientation_deg']:.6f} DEG"
                if obj.get("board_type") == "radial_rail":
                    orientation += (f"; {obj['orientation_note']}; REAR SEGMENT ORIENTATIONS "
                                    f"{obj['rear_profile_segment_orientations_deg']} DEG; "
                                    f"REAR SEGMENT LENGTHS {obj['rear_profile_segment_lengths_in']} IN; "
                                    f"LONG EDGE {obj['long_edge_in']:.6f} IN; "
                                    f"SHORT EDGE {obj['short_edge_in']:.6f} IN")
            rows.append((
                module, obj.name, 1, obj["cut_length_in"], obj["end_a_angle_deg"],
                obj["end_b_angle_deg"], orientation, PROVISIONAL_STATUS,
            ))
    return rows


def write_cutlist(structural):
    header = ("MODULE", "OBJECT", "QUANTITY", "CUT_LENGTH_IN", "END_A_ANGLE_DEG",
              "END_B_ANGLE_DEG", "ORIENTATION", "STATUS")
    with CUTLIST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for module, name, quantity, length, angle_a, angle_b, orientation, status in _cutlist_rows(structural):
            writer.writerow((module, name, quantity, _format_number(length),
                             str(angle_a) if isinstance(angle_a, str) else _format_number(angle_a),
                             str(angle_b) if isinstance(angle_b, str) else _format_number(angle_b),
                             orientation, status))
    return CUTLIST_PATH


def _dimensions_report(model, spans):
    components = _support_span_components()
    rear_y = SIDE_REAR_STRUCTURAL_SETBACK + ACTUAL_2X4_WIDTH
    interface = finished_outer_u(SIDE_REAR_STRUCTURAL_SETBACK) - (
        (SIDE_RUN / DAYBED_FINISHED_DEPTH) * rear_y
        - (SIDE_DIAGONAL_RAIL_INSET + 3.5)
        * math.sqrt(1 + (SIDE_RUN / DAYBED_FINISHED_DEPTH) ** 2)
    )
    lines = [
        "BAY WINDOW DAYBED V3 — CONSTRUCTION DIMENSIONS",
        "Units: inches. Nominal 2x4 actual size: 1.5 x 3.5.",
        "",
        "CENTER MODULE — RESOLVED",
        "Finished envelope: 60 W x 32 D; finished wood deck top Z = 10.5.",
        "Upper flat frame: 59 W x 31.5 D x 1.5 H; Z = 8.25–9.75.",
        "Upper front-to-back members: actual 3.5 X x 24.5 Y x 1.5 Z at resolved centerlines; outside edges at X = +/-29.5.",
        "Lower flat frame: 59 W x 29 D x 1.5 H; Z = 0–1.5; front recess = 2.5.",
        "Lower front-to-back members: actual 3.5 X x 22 Y x 1.5 Z; outside edges at X = +/-29.5.",
        "Posts: 10 x 6.75; Z = 1.5–8.25.",
        "Resolved structural cut list: 4 x 59; 5 x 24.5; 4 x 22; 10 x 6.75.",
        f"Maximum unsupported plywood span: {_format_number(spans['CENTER'])}.",
        "",
        "LEFT MODULE — PROVISIONAL / FIELD VERIFY",
        f"Finished plan vertices: {format_side_finished_vertices('LEFT')}.",
        "Finished landing deck: 0.75 thick; Z = 13.75–14.5; no cushion.",
        "Upper flat frame: Z = 12.25–13.75; lower flat frame: Z = 0–1.5.",
        "Seven posts: 1.5 x 3.5 plan, cut length 10.75; Z = 1.5–12.25.",
        f"Maximum unsupported plywood span: {_format_number(spans['LEFT'])}.",
        "",
        "RIGHT MODULE — PROVISIONAL / FIELD VERIFY",
        f"Finished plan vertices: {format_side_finished_vertices('RIGHT')}.",
        "Finished deck: 0.75 thick; Z = 9.75–10.5; cushion reference continues over most of module.",
        "Upper flat frame: Z = 8.25–9.75; lower flat frame: Z = 0–1.5.",
        "Seven posts: 1.5 x 3.5 plan, cut length 6.75; Z = 1.5–8.25.",
        f"Maximum unsupported plywood span: {_format_number(spans['RIGHT'])}.",
        "",
        "SIDE PARAMETERS — ALL PROVISIONAL / FIELD VERIFY",
        f"SIDE_REAR_STRUCTURAL_SETBACK = {SIDE_REAR_STRUCTURAL_SETBACK:.1f}",
        f"SIDE_DIAGONAL_RAIL_INSET = {SIDE_DIAGONAL_RAIL_INSET:.1f} (perpendicular to rail outer edge)",
        f"SIDE_CROSS_BRACE_CENTER_Y = {SIDE_CROSS_BRACE_CENTER_Y:.2f}; footprint Y = "
        f"{_format_number(SIDE_CROSS_BRACE_CENTER_Y - ACTUAL_2X4_WIDTH / 2)}–"
        f"{_format_number(SIDE_CROSS_BRACE_CENTER_Y + ACTUAL_2X4_WIDTH / 2)}.",
        f"SIDE_RUN = {SIDE_RUN:.1f}; SIDE_ANGLE = {SIDE_ANGLE:.1f} degrees.",
        f"APPROX_SIDE_WALL_ANGLE = {APPROX_SIDE_WALL_ANGLE:.1f} degrees; room reference only.",
        f"Rear closure/diagonal fastening interface = {_format_number(interface)} (minimum {MIN_REAR_FASTENING_INTERFACE}).",
        f"Rear-tip cantilever = {_format_number(components['rear_tip'])}.",
        f"Maximum adjacent support-rail spacing = {_format_number(components['support_rail'])}.",
        f"Maximum adjacent support-row spacing = {_format_number(components['support_row'])}.",
        "Each side uses matching seven-board upper/lower frames and seven direct-bearing posts.",
        "REAR CLOSURE FASTENING ACCESS: straight from rear during module assembly through the "
        "closure into inner/diagonal rail ends; 5-inch driver approach validated.",
        "CROSS-BRACE FASTENING ACCESS: angled toe-screw/pilot from exposed brace top/side into "
        "the radial rail; NO THROUGH-RADIAL PATH is claimed; no brackets required.",
        "",
        "CALCULATED SIDE STRUCTURAL PIECES — PROVISIONAL / FIELD VERIFY",
    ]
    for module in ("LEFT", "RIGHT"):
        lines.append(f"{module}:")
        for obj in sorted((item for item in model["structural"] if item["module"] == module),
                          key=lambda item: item.name):
            if "post_role" in obj:
                lines.append(
                    f"  {obj.name}: cut {_format_number(obj['cut_length_in'])}; vertical; "
                    f"center=({_format_number(obj['fastener_x'])}, {_format_number(obj['center_y'])}); "
                    f"plan rotation={_format_number(obj['world_orientation_deg'])} deg; "
                    f"joint_clearance_in={_format_number(obj['joint_clearance_in'])}; "
                    f"fastener_edge_distance_in={_format_number(obj['fastener_edge_distance_in'])}; "
                    f"driver_clearance_prism_in={_format_number(obj['driver_clearance_prism_in'])}; "
                    f"driver_access={bool(obj['driver_access'])}."
                )
            else:
                angle_a = (obj["end_a_angle_deg"] if isinstance(obj["end_a_angle_deg"], str)
                           else _format_number(obj["end_a_angle_deg"]))
                angle_b = (obj["end_b_angle_deg"] if isinstance(obj["end_b_angle_deg"], str)
                           else _format_number(obj["end_b_angle_deg"]))
                profile_details = (
                    f"; rear segment orientations={obj['rear_profile_segment_orientations_deg']} deg; "
                    f"rear segment lengths={obj['rear_profile_segment_lengths_in']} in."
                    if obj.get("board_type") == "radial_rail" else ""
                )
                lines.append(
                    f"  {obj.name}: centerline {_format_number(obj['cut_length_in'])}; "
                    f"long_edge/short_edge={_format_number(obj['long_edge_in'])}/{_format_number(obj['short_edge_in'])}; "
                    f"end angles={angle_a}/{angle_b} deg; "
                    f"orientation={_format_number(obj['orientation_deg'])} deg"
                    f"{'; ' + obj['orientation_note'] if obj.get('orientation_note') else '.'}"
                    f"{profile_details}"
                )
    lines.extend((
        "",
        "OVERALL",
        f"Provisional front width = {PROVISIONAL_TOTAL_FRONT_WIDTH:.1f}; finished depth = {DAYBED_FINISHED_DEPTH:.1f}.",
        "Finished heights: viewer-left landing 14.5; center/viewer-right wood 10.5; cushion top 14.5; sill underside 15.",
        f"Measured corner-to-corner room reference = {MEASURED_CORNER_TO_CORNER_WIDTH:.1f} (independent; not reconciled).",
        "Validation result: all resolved center, provisional side geometry, bearing, access, metadata, "
        "nonintersection, height, recess, and unsupported-span assertions passed before export/save.",
        "",
        FINAL_WARNING,
    ))
    return "\n".join(lines) + "\n"


def write_report(report):
    DIMENSIONS_PATH.write_text(report, encoding="utf-8")
    return DIMENSIONS_PATH


def validate_structural_names(structural):
    for obj in structural:
        assert obj["name_function"] in obj.name, f"{obj.name}: missing function token"
        assert f"_CUT{_name_number(obj['cut_length_in'])}IN_" in obj.name, (
            f"{obj.name}: missing calculated cut-length token"
        )
        if obj["module"] == "CENTER":
            obj_bounds = bounds(obj)
            dimensions = "x".join(_name_number(obj_bounds[index + 1] - obj_bounds[index])
                                   for index in (0, 2, 4))
            assert f"_{dimensions}_" in obj.name and obj.name.endswith("_RESOLVED"), (
                f"{obj.name}: resolved center name lacks modeled dimensions/status"
            )
        elif "post_role" in obj:
            dimensions = f"1p5x3p5x{_name_number(obj['cut_length_in'])}"
            assert f"_{dimensions}_" in obj.name and obj.name.endswith("_PROV"), (
                f"{obj.name}: provisional post name lacks plan/height dimensions"
            )
        else:
            assert "_3p5x1p5_" in obj.name and "_PROV" in obj.name, (
                f"{obj.name}: provisional flat-board name lacks actual stock dimensions/status"
            )
            if obj["board_type"] == "radial_rail":
                assert obj.name.endswith("_PROV_NOTCHED"), (
                    f"{obj.name}: radial name must expose custom notched profile"
                )


def validate_all(model):
    validate_parameters_and_polygons()
    checks = (
        validate_center(model["center"]),
        validate_side_frames(model["side_frames"]),
        validate_side_posts(model["side_posts"], model["side_frames"]),
        validate_finish_room(
            model["center"], model["decks"], model["skins"], model["nailers"],
            model["cushion"], model["room"], model["cameras"],
        ),
        validate_connection_markers(model["markers"]),
    )
    for errors in checks:
        assert not errors, "\n".join(errors)

    assert {collection.name for collection in bpy.data.collections} == set(COLLECTION_NAMES), \
        "primary collection set"
    expected_cameras = {"TOP_ORTHO_COMPLETE", "FRONT_COMPLETE", "SIDE_COMPLETE",
                        "ISOMETRIC_FRAMING_COMPLETE", "ISOMETRIC_FINISHED_COMPLETE",
                        "ISOMETRIC_CENTER", "ISOMETRIC_LEFT", "ISOMETRIC_RIGHT"}
    assert {obj.name for obj in bpy.data.objects if obj.type == "CAMERA"} == expected_cameras, "camera set"
    assert {layer.name for layer in bpy.context.scene.view_layers} == {"FRAMING_ONLY", "FINISHED"}, "view layers"

    structural = model["structural"]
    assert Counter(obj["module"] for obj in structural) == {"CENTER": 23, "LEFT": 21, "RIGHT": 21}, \
        "exactly three module structural assemblies"
    assert len({obj.name for obj in structural}) == len(structural), "unique structural object names"
    required = {"module", "purpose", "status", "cut_length_in", "centerline_length_in",
                "long_edge_in", "short_edge_in", "end_a_angle_deg", "end_b_angle_deg",
                "orientation_deg", "modeled_size_x_in", "modeled_size_y_in", "modeled_size_z_in",
                "stock_width_in", "stock_thickness_in", "name_function"}
    assert all(required <= set(obj.keys()) for obj in structural), "structural metadata completeness"
    recomputed = validate_structural_metadata(structural)
    validate_nominal_structural_stock(structural)
    validate_structural_names(structural)
    assert all(obj.name.startswith(obj["module"] + "_") for obj in structural), "structural object naming"
    assert all(obj["cut_length_in"] > 0 and abs(obj["cut_length_in"] - obj["centerline_length_in"]) <= 1e-9
               for obj in structural), "cut length/model metadata agreement"
    assert Counter(round(recomputed[obj.name]["cut_length_in"], 6) for obj in structural
                   if obj["module"] == "CENTER") == \
        {59: 4, 24.5: 5, 22: 4, 6.75: 10}, "resolved center cut totals"
    assert all(obj["status"] == PROVISIONAL_STATUS for obj in structural
               if obj["module"] in {"LEFT", "RIGHT"}), "side provisional status"
    assert len(_cutlist_rows(structural)) == 46, "cut-list row agreement"
    intersections = [(obj.name, other.name,
                      polygons_overlap_area(object_footprint(obj), object_footprint(other)))
                     for index, obj in enumerate(structural)
                     for other in structural[index + 1:] if structural_volume_overlap(obj, other)]
    assert not intersections, (
        "structural positive-volume intersections: "
        + "; ".join(f"{first} / {second} area {area}" for first, second, area in intersections)
    )

    left = {"upper": model["side_frames"]["LEFT_UPPER_FRAME"][4],
            "lower": model["side_frames"]["LEFT_LOWER_FRAME"][4]}
    right = {"upper": model["side_frames"]["RIGHT_UPPER_FRAME"][4],
             "lower": model["side_frames"]["RIGHT_LOWER_FRAME"][4]}
    spans = calculate_support_spans(model["center"], left, right)
    assert all(span < MAX_UNSUPPORTED_DECK_SPAN for span in spans.values()), \
        f"unsupported plywood spans exceed {MAX_UNSUPPORTED_DECK_SPAN}: {spans}"
    report = _dimensions_report(model, spans)
    assert report.rstrip().endswith(FINAL_WARNING), "required final warning"
    model["support_spans"] = spans
    return report


def main():
    try:
        reset_scene()
        configure_units()
        validate_parameters_and_polygons()
        collections = create_collections()
        materials = create_materials()
        center = build_center(collections, materials)
        side_frames = {}
        for module, sign, level, z0, z1, front_rear_y in (
            ("LEFT", module_sign("LEFT"), "UPPER", 12.25, 13.75, 28.0),
            ("LEFT", module_sign("LEFT"), "LOWER", 0.0, 1.5, 25.5),
            ("RIGHT", module_sign("RIGHT"), "UPPER", 8.25, 9.75, 28.0),
            ("RIGHT", module_sign("RIGHT"), "LOWER", 0.0, 1.5, 25.5),
        ):
            name = f"{module}_{level}_FRAME"
            objects = build_side_frame(
                module, sign, z0, z1, front_rear_y, collections[name], materials["NATURAL_LUMBER"],
            )
            side_frames[name] = (sign, front_rear_y, z0, z1, objects)
        side_posts = {}
        for module in ("LEFT", "RIGHT"):
            sign = module_sign(module)
            posts = build_side_posts(
                module, sign, side_frames[f"{module}_UPPER_FRAME"][4],
                side_frames[f"{module}_LOWER_FRAME"][4], collections[f"{module}_POSTS"],
                materials["NATURAL_LUMBER"],
            )
            side_posts[module] = (sign, posts)
        decks = build_decks(collections, materials, center)
        skins = build_finish(collections, materials, center)
        nailers = build_nailers(collections, materials, center)
        cushion = build_cushion(collections, materials)
        room = build_room_reference(collections, materials)
        markers = build_connection_markers(collections, materials, center, side_frames)
        dimensions = build_dimensions(collections, materials)
        cameras = build_cameras(collections)
        configure_view_layers(collections)
        structural = center["structural"] + [
            obj for _, _, _, _, objects in side_frames.values() for obj in objects
        ] + [obj for _, posts in side_posts.values() for obj in posts]
        model = {
            "collections": collections, "materials": materials, "center": center,
            "side_frames": side_frames, "side_posts": side_posts, "decks": decks,
            "skins": skins, "nailers": nailers, "cushion": cushion, "room": room,
            "markers": markers, "dimensions": dimensions, "cameras": cameras,
            "structural": structural,
        }
        report = validate_all(model)
    except AssertionError as error:
        print(f"V3 VALIDATION CONFLICT: {error}")
        raise

    write_cutlist(structural)
    write_report(report)
    bpy.context.scene.camera = bpy.data.objects["ISOMETRIC_FINISHED_COMPLETE"]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("V3 PARAMETER AND POLYGON VALIDATION PASSED")
    print("V3 CENTER VALIDATION PASSED")
    print("V3 SIDE FRAME VALIDATION PASSED")
    print("V3 SIDE POST AND FASTENING VALIDATION PASSED")
    print("V3 FINISH AND ROOM VALIDATION PASSED")
    print(report, end="")
    print(f"WROTE: {Path(__file__).resolve()}")
    print(f"WROTE: {CUTLIST_PATH}")
    print(f"WROTE: {DIMENSIONS_PATH}")
    print(f"WROTE: {BLEND_PATH}")
    print("V3 VALIDATION PASSED")


if __name__ == "__main__":
    main()
