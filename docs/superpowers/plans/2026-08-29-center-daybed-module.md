# Center Daybed Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and verify an accurately dimensioned Blender construction model, reproducible generator, and exact structural 2x4 cut list for the center daybed module.

**Architecture:** A single Blender Python generator owns scene construction, CSV output, validation, cameras, and saving. One small standard-library smoke test invokes Blender as a subprocess and checks the real generated artifacts and validation output.

**Tech Stack:** Blender 5.2, Blender Python API (`bpy`), Python standard library.

**Spec:** `docs/superpowers/specs/2026-08-29-center-daybed-module-design.md`

## Global Constraints

- One Blender unit equals one inch; X is left/right, Y rear/front, Z vertical, and floor is Z = 0.
- Structural 2x4 cross sections are actual 1.5 by 3.5 inches.
- Upper frame is exactly 59 by 31.5 inches from Z = 6.25 to 9.75.
- Lower frame is exactly 59 by 29 inches from Z = 0 to 3.5, with its front exactly 2.5 inches behind the upper front.
- Eight risers are 3.5 by 1.5 by 2.75 inches from Z = 3.5 to 6.25.
- Deck is exactly 60 by 32 by 0.75 inches from Z = 9.75 to 10.5.
- Structural cut totals are 4 x 59, 5 x 28.5, 4 x 26, and 8 x 2.75 inches; nailers are excluded.
- Only the center module is generated.

---

### Task 1: End-to-End Generation Check

**Files:**
- Create: `test_center_daybed_module.py`
- Test: `test_center_daybed_module.py`

**Interfaces:**
- Consumes: Blender executable at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` and `center_daybed_module_generator.py`.
- Produces: an exit status suitable for repeatable verification of the generator and its three requested outputs.

- [ ] **Step 1: Write the failing smoke test**

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def main():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "center_daybed_module_generator.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "VALIDATION PASSED" in output, output
    assert (ROOT / "center_daybed_module.blend").is_file()
    assert (ROOT / "center_daybed_2x4_cutlist.csv").is_file()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and verify RED**

Run: `python test_center_daybed_module.py`

Expected: FAIL because `center_daybed_module_generator.py` does not yet exist.

### Task 2: Blender Generator and Structural Validation

**Files:**
- Create: `center_daybed_module_generator.py`
- Create: `center_daybed_module.blend` (generated)
- Create: `center_daybed_2x4_cutlist.csv` (generated)
- Test: `test_center_daybed_module.py`

**Interfaces:**
- Consumes: the approved dimensions in the design specification.
- Produces: `main()`, which creates the scene, calls `validate_scene()`, writes the CSV, prints `VALIDATION PASSED`, and saves the `.blend` in the script directory.

- [ ] **Step 1: Add the minimal scene primitives and metadata**

Implement these direct helpers in the generator:

```python
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


def add_material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    return material


def add_camera(name, location, target, orthographic=False, scale=1):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO" if orthographic else "PERSP"
    data.ortho_scale = scale
    return camera


def add_dimension(name, start, end, label, offset):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.035
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    for point, coordinate in zip(spline.points, (Vector(start) + Vector(offset), Vector(end) + Vector(offset))):
        point.co = (*coordinate, 1.0)
    line = bpy.data.objects.new(name, curve)
    bpy.data.collections["DIMENSIONS"].objects.link(line)
    text_data = bpy.data.curves.new(f"{name}_TEXT", "FONT")
    text_data.body = label
    text = bpy.data.objects.new(f"{name}_TEXT", text_data)
    text.location = (Vector(start) + Vector(end)) / 2 + Vector(offset)
    bpy.data.collections["DIMENSIONS"].objects.link(text)
    return line, text
```

`add_box` creates one cube, applies its scale, assigns exactly one collection/material, and records `cut_length_in`, `purpose`, and `approximate` custom properties when supplied.

- [ ] **Step 2: Build the exact structure**

Create separate objects using these literal placements:

```python
upper_rails_y = (0.75, 30.75)
upper_member_x = (-28.75, -14.375, 0.0, 14.375, 28.75)
lower_rails_y = (0.75, 28.25)
lower_member_x = (-28.75, -14.375, 14.375, 28.75)
riser_x = (-28.75, -14.375, 14.375, 28.75)
riser_y = (0.75, 28.25)
```

Upper rails use `(59, 1.5, 3.5)` at Z = 8; upper members use `(1.5, 28.5, 3.5)` at Y = 15.75 and Z = 8. Lower rails use `(59, 1.5, 3.5)` at Z = 1.75; lower members use `(1.5, 26, 3.5)` at Y = 14.5 and Z = 1.75. Risers use `(3.5, 1.5, 2.75)` at Z = 4.875.

- [ ] **Step 3: Add finish, references, nailers, annotations, and cameras**

Create the deck `(60, 32, 0.75)` at `(0, 15.5, 10.125)` and front panel `(60, 0.5, 7.5)` at `(0, 31.75, 6.75)`. Add lightweight nonstructural nailers without volume intersections. Add the requested collections, simple materials, wall/floor reference geometry, five cameras, framing view layer, and requested measurement labels.

- [ ] **Step 4: Implement validation and CSV output**

`validate_scene()` must derive bounds from generated structural objects, reject positive-volume AABB intersections, count named purposes, and assert these literal totals:

```python
assert upper_bounds == (-29.5, 29.5, 0.0, 31.5, 6.25, 9.75)
assert lower_bounds == (-29.5, 29.5, 0.0, 29.0, 0.0, 3.5)
assert riser_z_bounds == (3.5, 6.25)
assert deck_z_bounds == (9.75, 10.5)
assert cut_totals == {59.0: 4, 28.5: 5, 26.0: 4, 2.75: 8}
```

Write one CSV row per purpose with headers `purpose,cut_length_in,quantity,stock`, excluding nailers.

- [ ] **Step 5: Run the smoke test and verify GREEN**

Run: `python test_center_daybed_module.py`

Expected: PASS with Blender exit code 0, `VALIDATION PASSED`, and all three requested output files present.

### Task 3: Independent Reopen and Visual Verification

**Files:**
- Verify: `center_daybed_module.blend`
- Verify: `center_daybed_module_generator.py`
- Verify: `center_daybed_2x4_cutlist.csv`

**Interfaces:**
- Consumes: generated artifacts from Task 2.
- Produces: fresh evidence that the saved file reopens, contains the expected scene, and presents usable framing/finished views.

- [ ] **Step 1: Reopen the saved model headlessly**

Run:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background center_daybed_module.blend --python-expr "import bpy; assert len(bpy.data.objects) > 0; print('REOPEN PASSED')"
```

Expected: exit 0 and `REOPEN PASSED`.

- [ ] **Step 2: Render representative views**

Render `ISOMETRIC_FINISHED` with finish collections visible and `ISOMETRIC_FRAMING` with finish collections excluded. Inspect both PNGs for occlusion, framing, dimensional clarity, and the visible 2.5-inch lower-frame recess; adjust only camera/annotation presentation if necessary.

- [ ] **Step 3: Run final verification**

Run `python test_center_daybed_module.py`, reopen the saved blend headlessly, and inspect the CSV contents. Expected: every command exits 0, the structural validation prints all requested measurements, and CSV totals match the approved cut list.
