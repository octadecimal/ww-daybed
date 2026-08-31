# Center Daybed Module V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a new dimensionally accurate V2 center-daybed construction model using flat 2x4 frames, ten full-height posts, finish parts, construction notes, and exact exports.

**Architecture:** One self-contained Blender Python generator creates every V2 object from literal specification constants, validates the complete load path and cut list, writes the CSV and dimension report, then saves the blend. One standard-library smoke test invokes the real Blender executable and checks all four requested artifacts.

**Tech Stack:** Blender 5.2.1, Blender Python API (`bpy`), Python standard library.

**Spec:** `docs/superpowers/specs/2026-08-29-center-daybed-module-v2-design.md`

## Global Constraints

- Create only V2 files; do not read, import, or modify V1 geometry or V1 outputs.
- One Blender unit equals one inch; X is left/right, Y rear/front, Z vertical, and the floor is Z = 0.
- Every lumber piece is a separate named object with dimensions, purpose, stock, and cut-length metadata.
- Both structural frames use flat 2x4s with Z thickness exactly 1.5 inches.
- Upper frame: 59 by 31.5 by 1.5 inches at Z = 8.25–9.75.
- Lower frame: 59 by 29 by 1.5 inches at Z = 0–1.5, recessed exactly 2.5 inches at the front.
- Posts: ten pieces measuring 3.5 X by 1.5 Y by 6.75 Z inches at Z = 1.5–8.25.
- Exact cut totals: 4 x 59, 5 x 24.5, 4 x 22, and 10 x 6.75 inches.
- The workspace is not a Git repository, so commit steps are unavailable.

---

### Task 1: V2 End-to-End Smoke Test

**Files:**
- Create: `test_center_daybed_module_v2.py`
- Test: `test_center_daybed_module_v2.py`

**Interfaces:**
- Consumes: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` and `center_daybed_module_v2_generator.py`.
- Produces: process exit status plus checks for the V2 validation marker and four requested files.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from collections import Counter
import csv
import subprocess

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def main():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "center_daybed_module_v2_generator.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V2 VALIDATION PASSED" in output, output
    for name in (
        "center_daybed_module_v2.blend",
        "center_daybed_module_v2_cutlist.csv",
        "center_daybed_module_v2_dimensions.txt",
    ):
        assert (ROOT / name).is_file(), name
    with (ROOT / "center_daybed_module_v2_cutlist.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    totals = Counter()
    for row in rows:
        totals[float(row["cut_length_in"])] += int(row["quantity"])
    assert totals == Counter({59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10})


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify RED**

Run: `python test_center_daybed_module_v2.py`

Expected: FAIL because `center_daybed_module_v2_generator.py` does not exist.

### Task 2: New V2 Generator

**Files:**
- Create: `center_daybed_module_v2_generator.py`
- Create: `center_daybed_module_v2.blend` (generated)
- Create: `center_daybed_module_v2_cutlist.csv` (generated)
- Create: `center_daybed_module_v2_dimensions.txt` (generated)
- Test: `test_center_daybed_module_v2.py`

**Interfaces:**
- Consumes: only literal constants from the approved V2 specification.
- Produces: `main()`, which creates, validates, reports, exports, and saves V2.

- [ ] **Step 1: Define the literal V2 construction data**

```python
UPPER_MEMBER_X = (-27.75, -13.875, 0.0, 13.875, 27.75)
LOWER_MEMBER_X = (-27.75, -9.25, 9.25, 27.75)
POST_X = UPPER_MEMBER_X
POST_ROWS = (("REAR", 1.75), ("FRONT", 27.25))
CUTLIST_ROWS = (
    ("UPPER_FRONT_REAR_RAILS", "59", 2, "2x4"),
    ("LOWER_FRONT_REAR_RAILS", "59", 2, "2x4"),
    ("UPPER_OUTSIDE_SIDE_MEMBERS", "24.5", 2, "2x4"),
    ("UPPER_INTERIOR_CROSSMEMBERS", "24.5", 3, "2x4"),
    ("LOWER_OUTSIDE_SIDE_MEMBERS", "22", 2, "2x4"),
    ("LOWER_INTERIOR_CROSSMEMBERS", "22", 2, "2x4"),
    ("VERTICAL_POSTS", "6.75", 10, "2x4"),
)
```

- [ ] **Step 2: Add direct scene helpers**

Implement `clear_scene()`, `add_material(name, color)`, `add_box(name, size, center, collection, material, **props)`, `add_text(name, body, location, rotation, collection, material, size)`, `add_camera(name, location, target, collection, orthographic=False, scale=1)`, `bounds(obj)`, `union_bounds(objects)`, `xy_contains(support, load)`, `xy_overlaps(first, second)`, and `positive_volume_overlap(first, second)`.

`add_box` must apply dimensions, move the cube into exactly one target collection, assign its material, and write every supplied custom property. Bounds helpers use object centers and applied dimensions; positive overlap requires positive extent on X, Y, and Z, so shared faces remain valid.

```python
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def add_material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    return material


def add_box(name, size, center, collection, material, **props):
    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for owner in tuple(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    for key, value in props.items():
        obj[key] = value
    return obj


def add_text(name, body, location, rotation, collection, material, size):
    data = bpy.data.curves.new(f"{name}_DATA", "FONT")
    data.body = body
    data.size = size
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    return obj


def add_camera(name, location, target, collection, orthographic=False, scale=1):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO" if orthographic else "PERSP"
    data.ortho_scale = scale
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(obj)
    return obj


def bounds(obj):
    half = obj.dimensions / 2
    return (obj.location.x-half.x, obj.location.x+half.x,
            obj.location.y-half.y, obj.location.y+half.y,
            obj.location.z-half.z, obj.location.z+half.z)


def union_bounds(objects):
    boxes = [bounds(obj) for obj in objects]
    return tuple(round(value, 6) for value in (
        min(box[0] for box in boxes), max(box[1] for box in boxes),
        min(box[2] for box in boxes), max(box[3] for box in boxes),
        min(box[4] for box in boxes), max(box[5] for box in boxes)))


def xy_contains(support, load):
    outer, inner = bounds(support), bounds(load)
    return (outer[0] <= inner[0]+EPSILON and outer[1] >= inner[1]-EPSILON
            and outer[2] <= inner[2]+EPSILON and outer[3] >= inner[3]-EPSILON)


def xy_overlaps(first, second):
    a, b = bounds(first), bounds(second)
    return (min(a[1], b[1])-max(a[0], b[0]) > EPSILON
            and min(a[3], b[3])-max(a[2], b[2]) > EPSILON)


def positive_volume_overlap(first, second):
    a, b = bounds(first), bounds(second)
    return all(min(a[hi], b[hi])-max(a[lo], b[lo]) > EPSILON
               for lo, hi in ((0, 1), (2, 3), (4, 5)))
```

- [ ] **Step 3: Build the structural pieces**

Create these exact axis-aligned objects:

```python
upper_rails = (
    ("UPPER_REAR_RAIL_FLAT_3.5x1.5_CUT_59in", (59, 3.5, 1.5), (0, 1.75, 9.0)),
    ("UPPER_FRONT_RAIL_FLAT_3.5x1.5_CUT_59in", (59, 3.5, 1.5), (0, 29.75, 9.0)),
)
lower_rails = (
    ("LOWER_REAR_RAIL_FLAT_3.5x1.5_CUT_59in", (59, 3.5, 1.5), (0, 1.75, 0.75)),
    ("LOWER_FRONT_RAIL_FLAT_3.5x1.5_CUT_59in", (59, 3.5, 1.5), (0, 27.25, 0.75)),
)
```

Upper front-to-back members are `(3.5, 24.5, 1.5)` centered at Y = 15.75 and Z = 9 using `UPPER_MEMBER_X`. Lower members are `(3.5, 22, 1.5)` centered at Y = 14.5 and Z = 0.75 using `LOWER_MEMBER_X`. Posts are `(3.5, 1.5, 6.75)` centered at Z = 4.875 using every combination of `POST_X` and `POST_ROWS`.

- [ ] **Step 4: Build finishes, nailers, references, notes, and cameras**

Create the deck `(60, 32, 0.75)` at `(0, 15.5, 10.125)` and the front panel `(60, 0.5, 7.5)` at `(0, 31.75, 6.75)`. Create the lower nailer `(59, 2.5, 0.75)` at `(0, 30.25, 3.875)` and five vertical nailers `(2.5, 0.75, 4)` at Y = 31.125, Z = 6.25, using `UPPER_MEMBER_X`.

```python
deck = add_box("CENTER_DECK_0.75_MAPLE", (60, 32, 0.75), (0, 15.5, 10.125), deck_collection, maple)
panel = add_box("CENTER_FRONT_PANEL_0.5_MAPLE", (60, 0.5, 7.5), (0, 31.75, 6.75), finish_collection, maple)
lower_nailer = add_box("FRONT_PANEL_LOWER_NAILER_APPROX", (59, 2.5, 0.75), (0, 30.25, 3.875), nailer_collection, nailer_material)
vertical_nailers = [
    add_box(f"FRONT_PANEL_VERTICAL_NAILER_APPROX_{index:02d}", (2.5, 0.75, 4), (x, 31.125, 6.25), nailer_collection, nailer_material)
    for index, x in enumerate(UPPER_MEMBER_X, 1)
]
```

Create every requested collection and material, a 60-inch wall and approximate floor/sill references, the five requested cameras in `CAMERAS`, finish/framing/dimensioned view layers, requested dimension labels, and two readable construction-note text blocks containing the exact screw guidance from the specification.

- [ ] **Step 5: Implement exact validation**

`validate_scene(upper, lower, posts, deck)` derives all measurements from objects, performs the required assertions, and returns the dimension/construction report string:

```python
assert union_bounds(upper) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75)
assert union_bounds(lower) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5)
assert union_bounds(posts)[4:] == (1.5, 8.25)
assert union_bounds([deck])[4:] == (9.75, 10.5)
assert Counter(round(float(obj["cut_length_in"]), 3) for obj in upper + lower + posts) == Counter({59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10})
```

Also assert exact member/group counts, exact X/Y post rows, 2.5-inch recess, full rear bearing between aligned rails, full front bearing on the lower front rail, full front post coverage beneath matching upper members, structural containment, and zero positive-volume structural intersections.

- [ ] **Step 6: Print and export only after validation**

Create one report string containing all requested dimensions, counts, elevations, load-path checks, cut totals, and both construction-note sections. After `validate_scene()` succeeds, print the report, write it to `center_daybed_module_v2_dimensions.txt`, write the CSV with headers `purpose,cut_length_in,quantity,stock`, save `center_daybed_module_v2.blend`, and print `V2 VALIDATION PASSED`.

```python
report = validate_scene(upper, lower, posts, deck)
print(report)
DIMENSIONS_PATH.write_text(report + "\n", encoding="utf-8")
with CUTLIST_PATH.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(("purpose", "cut_length_in", "quantity", "stock"))
    writer.writerows(CUTLIST_ROWS)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
print("V2 VALIDATION PASSED")
```

- [ ] **Step 7: Verify GREEN**

Run: `python test_center_daybed_module_v2.py`

Expected: exit 0 with all assertions passing and all four requested V2 artifacts present.

### Task 3: Saved-Artifact and Visual Audit

**Files:**
- Verify: `center_daybed_module_v2_generator.py`
- Verify: `center_daybed_module_v2.blend`
- Verify: `center_daybed_module_v2_cutlist.csv`
- Verify: `center_daybed_module_v2_dimensions.txt`

**Interfaces:**
- Consumes: Task 2 artifacts.
- Produces: fresh evidence from the saved model and rendered views.

- [ ] **Step 1: Reopen and independently audit the saved blend**

Run Blender headlessly against `center_daybed_module_v2.blend`. Recalculate bounds, counts, post rows, bearing, upper contacts, intersections, collections, cameras, and cut totals from saved object metadata. Print `V2 SAVED MODEL AUDIT PASSED` only after every assertion succeeds.

- [ ] **Step 2: Audit both text exports**

Parse the CSV with Python's `csv` module and assert totals `{59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}`. Read the dimension report and assert it includes `FRAME 90-DEGREE JOINTS`, `POST CONNECTIONS`, `5 to 5-1/8 in`, `3 to 3-1/8 in`, and `Do not use drywall screws`.

- [ ] **Step 3: Render and inspect**

Render `ISOMETRIC_FINISHED` on the finish view layer, `ISOMETRIC_FRAMING` on the framing view layer, and representative orthographic dimension views. Inspect that flat 1.5-inch frames, all ten posts, rear bearing, front-member bearing, 2.5-inch recess, nailer independence, and readable notes are visually clear.

- [ ] **Step 4: Run final verification**

Run `python test_center_daybed_module_v2.py` and `python -m py_compile center_daybed_module_v2_generator.py test_center_daybed_module_v2.py`. Expected: both commands exit 0 without warnings or failures.
