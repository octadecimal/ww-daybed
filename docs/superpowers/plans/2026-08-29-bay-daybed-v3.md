# Bay Daybed V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and verify a new parametric Blender construction model for the three-module V3 bay-window daybed without modifying V1 or V2.

**Architecture:** One self-contained `bpy` generator owns parameters, polygon math, geometry creation, metadata, validation, exports, cameras, and saving. A single standard-library smoke test launches Blender, inspects the saved model independently, validates CSV/report contents, and renders inspection views. Side framing is built in mirrored local coordinates so left and right share calculations while remaining separate objects and collections.

**Tech Stack:** Python 3 standard library, Blender 5.2.1 Python API (`bpy`), `mathutils`; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-29-bay-daybed-v3-design.md`

## Global Constraints

- Do not modify any V1 or V2 file.
- Nominal 2x4 stock is actual 1.5 by 3.5 inches; every board is a separate object.
- The center module and its cut totals remain exactly the approved V2 design.
- `SIDE_REAR_STRUCTURAL_SETBACK = 8.0`.
- `SIDE_DIAGONAL_RAIL_INSET = 1.0`, measured perpendicular from the finished diagonal to the rail's outer edge.
- `SIDE_CROSS_BRACE_CENTER_Y = 23.75`, producing a Y=22–25.5 brace footprint.
- `MIN_CROSS_BRACE_JOINT_CLEARANCE = 1.0`.
- Each side upper frame has seven boards, each side lower frame has seven boards, and each side has seven posts.
- Side values and cuts use `PROVISIONAL / FIELD VERIFY`; center values use `RESOLVED`.
- Validation runs before exports and saving and stops on any geometry or fastening conflict.
- No external geometry, numerical, CSV, or testing package is added.
- This workspace has no Git repository; replace commit steps with named verification checkpoints and do not initialize Git.

## File map

- Create `bay_daybed_v3_generator.py`: complete self-contained generator and assertions.
- Create `test_bay_daybed_v3.py`: one runnable Blender smoke/audit/render test.
- Generate `bay_daybed_v3.blend`: final inspected Blender model.
- Generate `bay_daybed_v3_cutlist.csv`: resolved center and provisional side structural rows.
- Generate `bay_daybed_v3_dimensions.txt`: readable dimensions, calculations, warnings, and validation summary.
- Preserve `center_daybed_module_generator.py`, `center_daybed_module.blend`, `center_daybed_2x4_cutlist.csv`, and all `center_daybed_module_v2*` files unchanged.

---

### Task 1: Test harness, parameters, and planar geometry kernel

**Files:**
- Create: `test_bay_daybed_v3.py`
- Create: `bay_daybed_v3_generator.py`

**Interfaces:**
- Produces: `side_u(sign: int, x: float) -> float`, `side_x(sign: int, u: float) -> float`, `clip_polygon(poly, line, keep_less) -> list[tuple[float,float]]`, `polygon_area(poly) -> float`, `polygons_overlap_area(a, b) -> float`, `add_prism(name, footprint, z0, z1, collection, material, **props)`.
- Produces constants named exactly as the approved spec.
- Later tasks consume the polygon functions for board footprints, containment, and intersection validation.

- [ ] **Step 1: Write the failing smoke test**

Create a standard-library test that first proves the new generator is absent/incomplete:

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

def run_generator():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "bay_daybed_v3_generator.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result, result.stdout + result.stderr

def main():
    result, output = run_generator()
    assert result.returncode == 0, output
    assert "V3 PARAMETER AND POLYGON VALIDATION PASSED" in output, output

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python test_bay_daybed_v3.py`

Expected: FAIL because `bay_daybed_v3_generator.py` does not exist.

- [ ] **Step 3: Add exact parameters and local side coordinates**

Start the generator with the spec constants and these coordinate helpers:

```python
def side_u(sign, x):
    return sign * (x - sign * CENTER_FLAT_WALL_WIDTH / 2)

def side_x(sign, u):
    return sign * (CENTER_FLAT_WALL_WIDTH / 2 + u)

def finished_outer_u(y):
    return SIDE_RUN * y / DAYBED_FINISHED_DEPTH
```

Use `sign=-1` for left and `sign=1` for right. In local coordinates the finished wedge is `0 <= u <= finished_outer_u(y)`.

- [ ] **Step 4: Implement dependency-free convex polygon operations**

Implement Sutherland-Hodgman half-plane clipping, shoelace area, segment intersection, point containment, polygon intersection, and mirror-to-world conversion. Add assertion examples for a unit square, touching rectangles with zero overlap area, and rectangles with positive overlap area.

- [ ] **Step 5: Add scene reset, units, collections, materials, and prism creation**

Create the exact required collections and simple materials. `add_prism` must create a mesh from an arbitrary CCW XY footprint and two Z elevations, link it only to the requested collection, apply material, and store metadata without changing the footprint.

- [ ] **Step 6: Validate parameter consistency and run GREEN**

Assert:

```python
implied_angle = math.degrees(math.atan2(SIDE_RUN, DAYBED_FINISHED_DEPTH))
assert abs(implied_angle - SIDE_ANGLE) <= 1e-6
assert SIDE_REAR_STRUCTURAL_SETBACK == 8.0
assert SIDE_CROSS_BRACE_CENTER_Y == 23.75
assert SIDE_CROSS_BRACE_CENTER_Y - 1.75 == 22.0
assert SIDE_CROSS_BRACE_CENTER_Y + 1.75 == 25.5
```

Print the milestone token and rerun `python test_bay_daybed_v3.py`; expected PASS.

- [ ] **Step 7: Record checkpoint**

Record: `Checkpoint 1 — parameters and polygon kernel pass in Blender 5.2.1.`

---

### Task 2: Recreate and validate the resolved center module

**Files:**
- Modify: `bay_daybed_v3_generator.py`
- Modify: `test_bay_daybed_v3.py`

**Interfaces:**
- Produces: `build_center(collections, materials) -> dict[str, list[bpy.types.Object] | bpy.types.Object]`.
- Produces: `bounds(obj)`, `union_bounds(objects)`, `positive_volume_overlap(a, b)`, `validate_center(center) -> list[str]`.
- Center object metadata includes `module="CENTER"`, `status="RESOLVED"`, `purpose`, `cut_length_in`, and `validation_group`.

- [ ] **Step 1: Extend the test with a saved-center audit and verify RED**

After running the generator, open `bay_daybed_v3.blend` with Blender `--python-expr` and assert:

```python
assert len(bpy.data.collections["CENTER_UPPER_FRAME"].objects) == 7
assert len(bpy.data.collections["CENTER_LOWER_FRAME"].objects) == 6
assert len(bpy.data.collections["CENTER_POSTS"].objects) == 10
assert union(center_upper) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75)
assert union(center_lower) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5)
```

Aggregate `cut_length_in` and require `{59: 4, 24.5: 5, 22: 4, 6.75: 10}`. Run the test; expected FAIL because center geometry is missing.

- [ ] **Step 2: Build the exact V2 center frames and posts**

Use box objects for the resolved rectangular pieces. Keep the five upper X positions and four lower X positions from the spec. Rear posts are `(3.5, 1.5, 6.75)` at Y=1.75. Front posts are `(1.5, 3.5, 6.75)` at Y=27.25.

- [ ] **Step 3: Add center deck, front skin, and lightweight nailers**

Create the 60 by 32 by 0.75 maple deck at Z=9.75–10.5, center skin at Z=3–10.5, and the approved V2 nailer ladder without connecting it to the lower frame.

- [ ] **Step 4: Implement exact center assertions**

Validate all V2 counts, dimensions, frame elevations, 2.5-inch recess, no positive-volume intersections, post Z contact, and the front-post bearing split of 2.5 inches under the upper member plus 1 inch under the upper front rail. Store the primary fastening note on every center front post.

- [ ] **Step 5: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v3.py`

Expected: PASS with `V3 CENTER VALIDATION PASSED`.

Record: `Checkpoint 2 — resolved center recreated without V1/V2 writes.`

---

### Task 3: Build matched seven-board side frames and provisional cut metadata

**Files:**
- Modify: `bay_daybed_v3_generator.py`
- Modify: `test_bay_daybed_v3.py`

**Interfaces:**
- Produces: `build_side_frame(module, sign, z0, z1, front_rear_y, collection, material) -> list[bpy.types.Object]`.
- Produces: `side_frame_footprints(sign, front_rear_y) -> dict[str, list[tuple[float,float]]]` with keys `rear_closure`, `inner_rail`, `radial_rail`, `diagonal_rail`, `cross_brace_inner`, `cross_brace_outer`, and `front_rail`.
- Produces: `board_cut_metadata(footprint, axis, end_lines) -> dict` containing centerline length, long/short lengths, end angles, and orientation.

- [ ] **Step 1: Add failing side-frame assertions**

Require seven objects in every left/right upper/lower frame collection, `min_y >= 8`, brace bounds Y=22–25.5, and status `PROVISIONAL / FIELD VERIFY` on every side object. Run the test; expected FAIL because side frames are absent.

- [ ] **Step 2: Calculate the rear closure and inner rail footprints**

In local `(u, y)` coordinates:

```python
mating_u = -0.5
inner_outer_u = mating_u + 3.5
closure = [(mating_u, 8.0), (finished_outer_u(8.0), 8.0),
           (finished_outer_u(8.0), 11.5), (mating_u, 11.5)]
inner_rail = rectangle(mating_u, inner_outer_u, 11.5, front_rear_y)
```

Mirror the canonical footprint to world X. The closure outer edge remains fixed at its Y=8 value so it lies inside the widening deck wedge.

- [ ] **Step 3: Calculate diagonal and radial rail bands**

For `slope = SIDE_RUN / DAYBED_FINISHED_DEPTH` and `normal_scale = sqrt(1 + slope**2)`:

```python
diagonal_outer_u(y) = slope*y - SIDE_DIAGONAL_RAIL_INSET*normal_scale
diagonal_inner_u(y) = slope*y - (SIDE_DIAGONAL_RAIL_INSET + 3.5)*normal_scale
diagonal_center_u(y) = slope*y - (SIDE_DIAGONAL_RAIL_INSET + 1.75)*normal_scale
radial_center_u(y) = (1.25 + diagonal_center_u(y)) / 2
```

Construct the full 3.5-inch perpendicular-width bands clipped to Y=11.5 through `front_rear_y`.

- [ ] **Step 4: Calculate the split brace and front rail footprints**

Clip the Y=22–25.5 brace band between the inner/radial and radial/diagonal rail edges, producing two distinct polygons with zero intersection area. Build the front rail from `mating_u` to the diagonal outer-edge line over Y=`front_rear_y` through `front_rear_y + 3.5`.

- [ ] **Step 5: Create all four side frames at their correct elevations**

Call `build_side_frame` with:

```python
LEFT upper:  z=12.25..13.75, front_rear_y=28.0
LEFT lower:  z=0.0..1.5,    front_rear_y=25.5
RIGHT upper: z=8.25..9.75,  front_rear_y=28.0
RIGHT lower: z=0.0..1.5,    front_rear_y=25.5
```

- [ ] **Step 6: Calculate and attach provisional cut metadata**

For every board, derive modeled centerline length and end-cut angles from its footprint and intended long axis. Record `long_point_in`, `short_point_in`, `end_a_angle_deg`, `end_b_angle_deg`, `orientation_deg`, `module`, and `status`. Do not round geometry; round only displayed/exported values.

- [ ] **Step 7: Add side-frame geometry assertions**

Assert diagonal footprint containment beneath the finished triangle, 1-inch perpendicular outer-edge inset, rear interface at least 2.75 inches, rear closure/rail boundary-only contact, inner/diagonal nonintersection, and lower brace/front-rail intersection area zero with shared Y=25.5 boundary.

- [ ] **Step 8: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v3.py`

Expected: PASS with `V3 SIDE FRAME VALIDATION PASSED`.

Record: `Checkpoint 3 — four provisional seven-board side frames validated.`

---

### Task 4: Solve and validate seven direct-bearing posts per side

**Files:**
- Modify: `bay_daybed_v3_generator.py`
- Modify: `test_bay_daybed_v3.py`

**Interfaces:**
- Produces: `fit_post_in_support(support_polygon, joint_halfplane=None, min_clearance=0.0) -> PostPose`.
- `PostPose` is a named tuple with `center_x`, `center_y`, `rotation_deg`, `footprint`, and `clearance_in`.
- Produces: `solve_front_post(lower_front, upper_path, upper_front) -> PostPose`.
- Produces: `build_side_posts(module, sign, upper, lower, collection, material) -> list[bpy.types.Object]`.

- [ ] **Step 1: Add failing bearing and access tests**

Require seven posts in each side collection, exact heights 10.75 left and 6.75 right, two rear/two brace/three front purposes, full lower and upper bearing, one-inch brace/radial clearance, and `driver_access=True`. Run the test; expected FAIL because posts are absent.

- [ ] **Step 2: Implement a deterministic rectangle-in-convex-polygon solver**

For a 1.5 by 3.5 post rectangle, iterate plan angles in 0.1-degree increments. Shrink every convex support half-plane by the rectangle's support function, add the radial-joint clearance half-plane when applicable, clip the feasible-center polygon, and choose the pose with greatest clearance. Return no pose when the feasible polygon is empty.

At defaults, assert the tapered outer brace produces a valid rotated pose near 46.4 degrees; report the calculated value rather than hard-coding it.

- [ ] **Step 3: Place rear and brace posts**

Place two rear posts fully within aligned closure footprints and at least 1 inch behind the rail/closure fastening face. Solve one post in each brace half using the matching upper/lower polygon intersection. Both frames use the same brace footprint, so the post bears directly at Z=1.5 and at the applicable upper-frame bottom.

- [ ] **Step 4: Solve the three front posts**

Fix each front post's Y footprint to 25.5–29. For the inner, radial, and diagonal upper paths, calculate an X interval whose rear 2.5-inch patch lies inside the named longitudinal member, whose front 1-inch patch lies inside the upper front rail, and whose entire footprint lies inside the lower front rail. Stop if any interval is narrower than 1.5 inches.

- [ ] **Step 5: Validate fastener edge distance and driver access**

For each post, choose a vertical screw center with at least 0.75-inch post-edge distance. Test a one-inch-clear vertical driver prism from outside the upper/lower frame to the fastening face against every neighboring structural object except the member being fastened. Cross-brace posts must also remain at least 1 inch from the radial joint. Set `driver_access=True` only after these checks pass.

- [ ] **Step 6: Validate direct load paths and structural intersections**

Assert all post bottom/top Z faces touch their supports, no post relies on plywood, and no post or frame board has positive-volume overlap. Verify module-to-module structural contacts are boundary-only.

- [ ] **Step 7: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v3.py`

Expected: PASS with `V3 SIDE POST AND FASTENING VALIDATION PASSED`.

Record: `Checkpoint 4 — fourteen provisional side posts have direct bearing and screw access.`

---

### Task 5: Add finished geometry, room references, annotations, cameras, and layers

**Files:**
- Modify: `bay_daybed_v3_generator.py`
- Modify: `test_bay_daybed_v3.py`

**Interfaces:**
- Produces: `build_decks`, `build_finish`, `build_nailers`, `build_cushion`, `build_room_reference`, `build_connection_markers`, `build_dimensions`, `build_cameras`, and `configure_view_layers`.

- [ ] **Step 1: Add failing finish/height/camera assertions**

Assert three deck objects, skin bottoms at Z=3, cushion top 14.5 with no left overlap, sill underside 15, all eight camera names, and both `FRAMING_ONLY` and `FINISHED` layers. Run the test; expected FAIL.

- [ ] **Step 2: Create decks, skins, and isolated nailers**

Build the center rectangle and mirrored side triangle deck prisms. Create three separate front skins with wedge-clipped side footprints. Create lightweight finish nailers wholly behind the skins, above the lower frames, and outside the structural cut list.

- [ ] **Step 3: Create the cushion and connection references**

Create one oatmeal cushion prism covering the center and most of the right wedge at Z=10.5–14.5, inset about 0.5 inch from exposed edges and clear of the left deck. Add nonstructural connection-zone markers at X=±29.5 without permanent hardware.

- [ ] **Step 4: Build provisional room references and dimensions**

Create center/angled wall references, floor, sill projection, optional facet references, the independent 106-inch annotation, and the 124-inch `PROVISIONAL — VERIFY FROM ROOM TEMPLATE` annotation. Side wall/facet objects carry provisional metadata and never drive center framing.

- [ ] **Step 5: Create cameras and visibility states**

Add all eight named cameras. `FRAMING_ONLY` excludes decks, skins, nailers, and cushion. `FINISHED` displays all finish collections. Frame each camera so complete and module-specific views are useful without changing geometry.

- [ ] **Step 6: Validate finished heights and recess language**

Assert center/right deck tops 10.5, left top 14.5, cushion top 14.5, sill underside 15, left-to-center height difference 4, no left/sill intersection, skin bottoms 3, and all lower front boundaries recessed 2.5 inches.

- [ ] **Step 7: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v3.py`

Expected: PASS with `V3 FINISH AND ROOM VALIDATION PASSED`.

Record: `Checkpoint 5 — finished assembly, references, cameras, and layers validated.`

---

### Task 6: Cut list, dimensions report, final save, and independent verification

**Files:**
- Modify: `bay_daybed_v3_generator.py`
- Modify: `test_bay_daybed_v3.py`
- Generate: `bay_daybed_v3.blend`
- Generate: `bay_daybed_v3_cutlist.csv`
- Generate: `bay_daybed_v3_dimensions.txt`

**Interfaces:**
- Produces: `calculate_support_spans(center, left, right) -> dict[str, float]`.
- Produces: `validate_all(model) -> str`, `write_cutlist(structural)`, and `write_report(report)`.
- Final console token: `V3 VALIDATION PASSED`.

- [ ] **Step 1: Extend the test to require all final artifacts and report text**

Assert all four output files exist. Parse CSV with `csv.DictReader`, aggregate center lengths, require every side row's exact provisional status, and require the final warning sentence in the dimensions report. Run the test; expected FAIL until exports exist.

- [ ] **Step 2: Calculate conservative unsupported deck spans**

Report the maximum of:

```python
center: maximum adjacent upper-member X centerline spacing
sides: rear-tip hypot(setback, finished_outer_u(setback)),
       adjacent support-rail centerline spacing at the widest supported Y,
       adjacent rear/brace/front support-row spacing
```

Raise a validation conflict if any value exceeds 16 inches.

- [ ] **Step 3: Implement complete pre-save validation**

Call every earlier validator and additionally check collection/camera/layer names, exactly three module assemblies, module-to-module nonintersection, all side provisional labels, all object metadata/cut-list agreement, and the final warning text. Catch `AssertionError`, print `V3 VALIDATION CONFLICT: <detail>`, and re-raise before any export or save.

- [ ] **Step 4: Export the CSV and dimensions report**

Write columns exactly:

```text
MODULE,OBJECT,QUANTITY,CUT_LENGTH_IN,END_A_ANGLE_DEG,END_B_ANGLE_DEG,ORIENTATION,STATUS
```

Write resolved center aggregate rows and one row per side structural object. Include calculated post poses, interface widths, unsupported spans, module heights, side angles, and the mandated final warning in the text report.

- [ ] **Step 5: Save the Blender file only after validation and exports**

Set the default camera to `ISOMETRIC_FINISHED_COMPLETE`, save `bay_daybed_v3.blend`, print all output paths, then print `V3 VALIDATION PASSED`.

- [ ] **Step 6: Run the full smoke test and syntax check**

Run:

```powershell
python -m py_compile bay_daybed_v3_generator.py test_bay_daybed_v3.py
python test_bay_daybed_v3.py
```

Expected: exit 0, no traceback, and all milestone/final tokens present.

- [ ] **Step 7: Independently audit the saved `.blend`**

Open the saved file in a second Blender process and assert actual collection counts, critical bounds, deck heights, rear setback, diagonal containment/inset, brace/front boundary-only contact, all post bearing/clearance properties, no positive-volume structural intersections, and side status metadata. Print `V3 SAVED MODEL AUDIT PASSED`.

- [ ] **Step 8: Render and inspect final views**

Render `ISOMETRIC_FRAMING_COMPLETE` using `FRAMING_ONLY` and `ISOMETRIC_FINISHED_COMPLETE` using `FINISHED` to temporary PNG files. Inspect both images for module separation, raised left landing, cushion coverage, continuous recess, seven-post side load paths, and visible room-reference distinction.

- [ ] **Step 9: Confirm V1/V2 preservation and record final checkpoint**

Compare V1/V2 file timestamps and sizes recorded before implementation. Confirm only V3 files, the V3 test, spec, and plan changed.

Record: `Checkpoint 6 — V3 generated, independently audited, rendered, and V1/V2 preserved.`
