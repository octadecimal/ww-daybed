# Bay-Window Daybed V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and independently verify a new V4 Blender construction model with the resolved center module, viewer-left raised landing, viewer-right lower cushion continuation, and square-cut stepped side framing.

**Architecture:** A single self-contained `bpy` generator owns parameters, pure planar calculations, scene construction, assertions, reports, and final save. A standard-library Python audit launches Blender in background mode, checks generated artifacts and saved-object metadata, and renders two temporary inspection views. V1–V3 are read-only references and are never imported by the V4 generator.

**Tech Stack:** Python 3 standard library, Blender 5.2 Python API (`bpy`), Blender mesh primitives, CSV/text output, assertion-based validation.

**Spec:** `docs/superpowers/specs/2026-08-29-bay-daybed-v4-design.md`

## Global Constraints

- Positive X is viewer-left, raised to 14.5 inches, and has no cushion.
- Negative X is viewer-right, finishes at 10.5 inches, and lies beneath the one center/right cushion.
- Room references use the measured 44.5-degree wall turn and 135.5-degree interior angle.
- Side plywood and hidden framing may display/use the provisional 45-degree wedge, but side plywood always says `FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING`.
- Every side structural 2x4 is axis-aligned, flat where horizontal, and has `CUT_TYPE = SQUARE / 90 DEGREE`.
- Every structural board and post is a separate Blender object.
- Each side has exactly eight upper boards, seven lower boards, and eight posts at default parameters.
- Side upper front edge is Y = 31.5; side lower front edge is Y = 29; structural recess is 2.5; finished-face setback is 3.0.
- Side rear structural setback is 8.0 and structural diagonal-edge inset is 1.0 under the simplified 45-degree calculation.
- Short rails below 3.0 inches use `SHORT_RAIL_SINGLE_SCREW_DETAIL`; failed fastener geometry stops generation.
- The 0.75-inch deck is the primary shear diaphragm; the bare stepped frame must be squared before deck installation.
- No third-party geometry, numerical, CSV, or test package is added.
- Validation completes before cut-list/report export or `.blend` save.
- This workspace is not a Git repository; checkpoint steps replace commits, and implementation must not initialize Git.

## File map

- Create `bay_daybed_v4_generator.py`: all V4 parameters, geometry, metadata, validation, reports, and Blender save.
- Create `test_bay_daybed_v4.py`: one runnable background-Blender generator/audit/render check using only the standard library.
- Generate `bay_daybed_v4.blend`: validated construction model.
- Generate `bay_daybed_v4_cutlist.csv`: resolved center and provisional side structural 2x4 rows.
- Generate `bay_daybed_v4_dimensions.txt`: dimensions, statuses, fastening results, support spans, warnings, and final validation summary.
- Preserve every existing V1, V2, and V3 file byte-for-byte.

---

### Task 1: Test harness, parameters, and geometry primitives

**Files:**
- Create: `test_bay_daybed_v4.py`
- Create: `bay_daybed_v4_generator.py`

**Interfaces:**
- Produces `side_x(module: str, u: float) -> float` and `side_u(module: str, x: float) -> float`.
- Produces `rect(x0, x1, y0, y1) -> list[tuple[float, float]]`, `polygon_area(poly) -> float`, `point_in_polygon(point, poly) -> bool`, `polygon_intersection(a, b) -> list[tuple[float, float]]`, and `positive_overlap_area(a, b) -> float`.
- Produces `add_box(...)` and `add_prism(...)`, used by every later construction task.
- Produces `validate_parameters() -> list[str]` and milestone text `V4 PARAMETER VALIDATION PASSED`.

- [ ] **Step 1: Write the failing Blender harness**

Create `test_bay_daybed_v4.py` with a reusable background runner:

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
GENERATOR = ROOT / "bay_daybed_v4_generator.py"

def run_blender_expr(expr):
    bootstrap = f"import runpy; n=runpy.run_path({str(GENERATOR)!r}); {expr}"
    return subprocess.run(
        [str(BLENDER), "--background", "--python-expr", bootstrap],
        cwd=ROOT, capture_output=True, text=True,
    )

def main():
    result = run_blender_expr("n['validate_parameters'](); print('V4 PARAMETER VALIDATION PASSED')")
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 PARAMETER VALIDATION PASSED" in output, output

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run RED**

Run: `python test_bay_daybed_v4.py`

Expected: nonzero exit because `bay_daybed_v4_generator.py` or `validate_parameters` does not exist.

- [ ] **Step 3: Add exact V4 parameters and output paths**

Define the spec values at the top of `bay_daybed_v4_generator.py`, including:

```python
CENTER_FLAT_WALL_WIDTH = 60.0
DAYBED_FINISHED_DEPTH = 32.0
MEASURED_INTERIOR_CORNER_ANGLE = 135.5
MEASURED_WALL_TURN = 44.5
STRUCTURAL_SIDE_ANGLE = 45.0
SIDE_STEP_INTERVAL = 8.0
SIDE_REAR_STRUCTURAL_SETBACK = 8.0
SIDE_EDGE_STRUCTURE_INSET = 1.0
SIDE_LOWER_FRONT_RECESS = 2.5
SIDE_UPPER_FRONT_EDGE_Y = 31.5
SIDE_LOWER_FRONT_EDGE_Y = 29.0
FINISHED_FRONT_Y = 32.0
SHORT_RAIL_THRESHOLD = 3.0
MAX_UNSUPPORTED_DECK_SPAN = 16.0
PROVISIONAL_STATUS = "PROVISIONAL / FIELD VERIFY"
PLYWOOD_FIELD_STATUS = "FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING"
SHORT_RAIL_DETAIL = "SHORT_RAIL_SINGLE_SCREW_DETAIL"
```

Set V4-only output paths beside the script. Do not import any V1–V3 generator.

- [ ] **Step 4: Add dependency-free planar helpers**

Implement rectangle creation, shoelace area, convex polygon clipping, point containment, and positive-area overlap. Add internal assertions for disjoint rectangles, boundary-touching rectangles with zero overlap, and a one-square-inch positive overlap.

- [ ] **Step 5: Add minimal Blender scene helpers**

Implement scene reset, inch units, material creation, collection creation, `add_box`, and arbitrary-footprint `add_prism`. Each creator links the object only to its target collection and stores supplied metadata as custom properties. Create exactly these collections:

```text
ROOM_REFERENCE
CENTER_UPPER_FRAME
CENTER_LOWER_FRAME
CENTER_POSTS
LEFT_UPPER_STEP_FRAME
LEFT_LOWER_STEP_FRAME
LEFT_POSTS
RIGHT_UPPER_STEP_FRAME
RIGHT_LOWER_STEP_FRAME
RIGHT_POSTS
PLYWOOD_DECKS
MAPLE_FINISH
FRONT_PANEL_NAILERS
CUSHION_REFERENCE
FASTENER_REFERENCE
DIMENSIONS
CAMERAS
```

- [ ] **Step 6: Implement and run parameter validation**

`validate_parameters` must assert:

```python
assert MEASURED_WALL_TURN == 44.5
assert MEASURED_INTERIOR_CORNER_ANGLE == 135.5
assert STRUCTURAL_SIDE_ANGLE == 45.0
assert STRUCTURAL_SIDE_ANGLE != 45.5
assert SIDE_REAR_STRUCTURAL_SETBACK == 8.0
assert SIDE_UPPER_FRONT_EDGE_Y - SIDE_LOWER_FRONT_EDGE_Y == 2.5
assert FINISHED_FRONT_Y - SIDE_LOWER_FRONT_EDGE_Y == 3.0
assert PLYWOOD_FIELD_STATUS == "FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING"
```

Run: `python test_bay_daybed_v4.py`

Expected: exit 0 and `V4 PARAMETER VALIDATION PASSED`.

- [ ] **Step 7: Record checkpoint**

Record: `Checkpoint 1 — V4 parameters and planar primitives pass in Blender.`

---

### Task 2: Rebuild and validate the resolved center module

**Files:**
- Modify: `bay_daybed_v4_generator.py`
- Modify: `test_bay_daybed_v4.py`

**Interfaces:**
- Produces `build_center(collections, materials) -> dict[str, object]`.
- Produces `bounds(obj)`, `union_bounds(objects)`, `structural_volume_overlap(a, b)`, and `validate_center(center) -> list[str]`.
- Center structural metadata contains `module`, `purpose`, `cut_length`, `cut_type`, `orientation`, and `status="RESOLVED"`.

- [ ] **Step 1: Add a failing center audit**

Extend the harness expression to reset/build/validate the center, then assert the milestone. Add saved-object expectations to the audit code:

```python
assert len(center["upper"]) == 7
assert len(center["lower"]) == 6
assert len(center["posts"]) == 10
assert n["union_bounds"](center["upper"]) == (-29.5, 29.5, 0.0, 31.5, 8.25, 9.75)
assert n["union_bounds"](center["lower"]) == (-29.5, 29.5, 0.0, 29.0, 0.0, 1.5)
```

Run the test; expected failure because `build_center` is absent.

- [ ] **Step 2: Build the exact center upper and lower frames**

Create separate box objects for the two 59-inch upper rails, five 24.5-inch upper members at X `[-27.75, -13.875, 0, 13.875, 27.75]`, two 59-inch lower rails, and four 22-inch lower members at X `[-27.75, -9.25, 9.25, 27.75]`. Use the exact Y and Z bounds from the spec.

- [ ] **Step 3: Build the ten resolved center posts**

Rear posts are 3.5 X by 1.5 Y by 6.75 Z at Y center 1.75. Front posts are 1.5 X by 3.5 Y by 6.75 Z at Y center 27.25. Use the five upper-member X centerlines for both rows.

- [ ] **Step 4: Assert dimensions, cuts, bearing, and intersections**

`validate_center` must aggregate structural lengths to:

```python
{59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}
```

It must also verify the two frame envelopes, Z stack, exactly three upper interior members, exactly two lower interior members, 2.5-inch structural recess, front-post Y footprint 25.5–29, 2.5-inch upper longitudinal bearing, 1.0-inch upper-front-rail bearing, and no positive-volume structural overlap.

- [ ] **Step 5: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v4.py`

Expected: `V4 CENTER VALIDATION PASSED`.

Record: `Checkpoint 2 — resolved V2 center geometry and cut counts pass.`

---

### Task 3: Build square-cut side frames and direct-bearing posts

**Files:**
- Modify: `bay_daybed_v4_generator.py`
- Modify: `test_bay_daybed_v4.py`

**Interfaces:**
- Produces `side_frame_specs(frame: str) -> list[dict]`, where `frame` is `"UPPER"` or `"LOWER"` and each dictionary has `purpose`, `axis`, `u0`, `u1`, `y0`, `y1`, and `cut_length`.
- Produces `build_side_frame(module, frame, z0, z1, collection, material) -> list[bpy.types.Object]`.
- Produces `side_post_specs() -> list[dict]` and `build_side_posts(module, height, lower, upper, collection, material) -> list[bpy.types.Object]`.
- Produces `validate_side_structure(module_data) -> list[str]` and milestone `V4 SIDE STRUCTURE VALIDATION PASSED`.

- [ ] **Step 1: Add failing side-count and orientation checks**

Require, for both LEFT and RIGHT:

```python
assert len(side["upper"]) == 8
assert len(side["lower"]) == 7
assert len(side["posts"]) == 8
assert all(o["cut_type"] == "SQUARE / 90 DEGREE" for o in side["upper"] + side["lower"] + side["posts"])
assert all(o["status"] == "PROVISIONAL / FIELD VERIFY" for o in side["upper"] + side["lower"] + side["posts"])
```

Run the test; expected failure because the side builders are absent.

- [ ] **Step 2: Calculate the default eight-board upper topology**

Use `root2 = math.sqrt(2)` and generate these local `(u, Y)` rectangles from parameters rather than copying mesh coordinates:

```python
rear_outer = 8.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
near16_outer = 14.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
near24_outer = 22.0 - root2 * SIDE_EDGE_STRUCTURE_INSET
upper_front_outer = 28.0 - root2 * SIDE_EDGE_STRUCTURE_INSET

upper = [
    ("REAR_CLOSURE", "X", 0.0, rear_outer, 8.0, 11.5),
    ("INNER_SPINE", "Y", 0.0, 3.5, 11.5, 28.0),
    ("TRANSVERSE_16", "X", 3.5, near16_outer, 14.0, 17.5),
    ("TRANSVERSE_24", "X", 3.5, near24_outer, 22.0, 25.5),
    ("FRONT_RAIL", "X", 0.0, upper_front_outer, 28.0, 31.5),
    ("OUTER_STEP_01", "Y", 3.5, 7.0, 11.5, 14.0),
    ("OUTER_STEP_02", "Y", near16_outer - 3.5, near16_outer, 17.5, 22.0),
    ("OUTER_STEP_03", "Y", near24_outer - 3.5, near24_outer, 25.5, 28.0),
]
```

Derive cut length from the long-axis bounds. Mirror only the X coordinate into world space; do not rotate any structural board.

- [ ] **Step 3: Calculate the default seven-board lower topology**

Use the same first four members and first two outer rails, including corrected `OUTER_STEP_01` local U = 3.5–7.0. Use inner spine Y = 11.5–25.5 and lower front rail:

```python
lower_front_outer = 25.5 - root2 * SIDE_EDGE_STRUCTURE_INSET
("LOWER_FRONT_RAIL", "X", 0.0, lower_front_outer, 25.5, 29.0)
```

The `TRANSVERSE_24` front face and lower-front rear face both equal Y = 25.5. Assert their polygon intersection area is zero.

- [ ] **Step 4: Build both side frame stacks**

Create:

```python
LEFT upper:  Z=12.25..13.75
LEFT lower:  Z=0.0..1.5
RIGHT upper: Z=8.25..9.75
RIGHT lower: Z=0.0..1.5
```

Object names contain module, frame, function, actual dimensions, and cut length. Every side object receives `status="PROVISIONAL / FIELD VERIFY"`, `cut_type="SQUARE / 90 DEGREE"`, and `structural_angle_assumption=45.0`.

- [ ] **Step 5: Define the eight deterministic post footprints**

Use these local plan footprints; `rear_outer`, `near16_outer`, and `near24_outer` are the derived values above:

```python
posts = [
    ("REAR_INNER", 0.0, 3.5, 10.75, 12.25),
    ("REAR_OUTER", 4.292893, 5.792893, 9.75, 13.25),
    ("STATION16_INNER", 1.75, 5.25, 15.0, 16.5),
    ("STATION16_OUTER", near16_outer-3.5, near16_outer, 16.75, 18.25),
    ("STATION24_INNER", 1.75, 5.25, 23.0, 24.5),
    ("STATION24_OUTER", near16_outer-3.5, near16_outer, 21.25, 22.75),
    ("FRONT_INNER", 1.0, 2.5, 25.5, 29.0),
    ("FRONT_OUTER", near24_outer-2.5, near24_outer-1.0, 25.5, 29.0),
]
```

The rear outer and two front posts use the 1.5-X-by-3.5-Y orientation. The other five posts use 3.5-X by 1.5-Y. The rear outer post is centered at local U=5.042893 and Y=11.5 within the corrected 3.085786-inch closure/step interface. Left posts are 10.75 high from Z 1.5; right posts are 6.75 high from Z 1.5.

- [ ] **Step 6: Validate bearing against support unions**

For each post, intersect its footprint with every named lower support footprint, sum disjoint supported areas, and require coverage of the complete post area within tolerance. Repeat against upper support footprints. Explicitly require:

```python
front_longitudinal_bearing_y == 2.5
front_rail_bearing_y == 1.0
```

Reject plywood-only support, post/frame gaps, positive-volume intersections, and any post whose vertical driver corridor is blocked by another structural object.

- [ ] **Step 7: Validate the staircase envelope and topology**

Assert all side boards have X/Y axes, all are at or forward of Y = 8, every board corner satisfies `u <= Y`, each transverse outer corner has at least 1.0 inch perpendicular inset, no board follows the diagonal, all expected butt joints are boundary-only, and every upper stepped bay is a closed orthogonal path that contacts the future deck diaphragm.

Also assert `OUTER_STEP_01` has zero overlap with the inner spine and all neighboring boards, its rear-closure interface is 3.085786 inches and at least 2.75 inches, its closest perpendicular plywood-edge clearance is approximately 3.181981 inches and positive, and its relocated rear outer post has full upper/lower bearing.

- [ ] **Step 8: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v4.py`

Expected: `V4 SIDE STRUCTURE VALIDATION PASSED`.

Record: `Checkpoint 3 — both eight/seven-board frames and all sixteen side posts pass.`

---

### Task 4: Model and validate frame fasteners and plywood support

**Files:**
- Modify: `bay_daybed_v4_generator.py`
- Modify: `test_bay_daybed_v4.py`

**Interfaces:**
- Produces `fastener_specs_for_outer_rail(module, frame, rail, neighbors) -> list[dict]`.
- Produces `build_fastener_references(specs, collection, material) -> list[bpy.types.Object]`.
- Produces `validate_fasteners(side_data) -> list[str]`.
- Produces `calculate_support_spans(model) -> dict[str, float]`.

- [ ] **Step 1: Add failing short/long rail audit assertions**

Require every 2.5-inch rail to have `fastening_detail="SHORT_RAIL_SINGLE_SCREW_DETAIL"`, exactly two total reference screws, one per end, 1.5-inch lateral path separation, 1.0-inch lateral edge distance, 0.75-inch vertical edge distance, and 1.0-inch tip-to-opposite-end clearance. Require every 4.5-inch rail to have four total screws only after its spacing validation passes.

Run the test; expected failure because fastener references are absent.

- [ ] **Step 2: Generate the short-rail screw centerlines**

For a Y-axis rail of clear length `L < 3.0`, use a nominal 5.0-inch screw from each adjoining transverse member: 3.5 inches through that member and 1.5 inches into the rail. Put the two opposing paths at X/u offsets 1.0 and 2.5 within the rail width, producing 1.5-inch separation and 1.0-inch side clearances.

Store these properties on the rail and reference objects:

```python
fastening_detail = "SHORT_RAIL_SINGLE_SCREW_DETAIL"
screws_per_end = 1
predrill = True
wood_glue = True
clamp_during_fastening = True
nominal_screw_length = 5.0
rail_penetration = 1.5
```

- [ ] **Step 3: Validate short-rail paths and driver corridors**

Represent each screw as a centerline segment and each driver approach as a rectangular prism extending beyond the entry face. Assert lateral separation is at least 1.5, segment-to-segment distance is positive, the tip is 1.0 from the opposite rail end, no tip exits the rail, and each driver prism has zero positive-volume intersection with structural neighbors other than the board being driven through.

- [ ] **Step 4: Validate the 4.5-inch rail's normal detail**

Use two lateral screw lanes per end with at least 0.875-inch side edge distance and 1.75-inch same-end spacing. Opposing 1.5-inch penetration zones leave 1.5 inches of clear rail length. Only then store `screws_per_end=2`; otherwise raise the cleat/gusset conflict without moving a station.

For each lower-frame `OUTER_STEP_02` front-end screw, store `ASSEMBLY_SEQUENCE_REQUIRED`: fasten the rail to `TRANSVERSE_24` before installing the lower front rail at Y=25.5–29. Validate the driver corridor in that assembly state by excluding only the not-yet-installed lower front rail. Then restore the final state and require boundary-only Y=25.5 contact with zero positive-volume overlap. Assert these four screws are the only sequence-dependent frame joints.

- [ ] **Step 5: Add post screw-access reference checks**

For each side post, choose at least one top and one bottom vertical screw center inside the post footprint and within a named upper/lower support. Build a 1-inch-clear driver prism above the upper path and below the lower path; the lower path is validated for the documented upside-down pre-floor assembly sequence. Assert no unrelated board blocks either path and store `post_screw_access=True`.

- [ ] **Step 6: Calculate conservative support-span proofs**

Calculate with live parameters:

```python
rear_tip_bound = math.hypot(SIDE_REAR_STRUCTURAL_SETBACK,
                            SIDE_REAR_STRUCTURAL_SETBACK * math.tan(math.radians(STRUCTURAL_SIDE_ANGLE)))
stepped_bay_bound = math.hypot(SIDE_STEP_INTERVAL,
                               SIDE_STEP_INTERVAL * math.tan(math.radians(STRUCTURAL_SIDE_ANGLE))) + SIDE_EDGE_STRUCTURE_INSET
```

Combine those with actual adjacent support-row and longitudinal-path gaps. Use the maximum conservative value as the reported side unsupported span and require it to be below 16.0. For center, report the maximum gap between adjacent upper-member support edges, not merely centerlines.

- [ ] **Step 7: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v4.py`

Expected: `V4 FASTENER AND SUPPORT VALIDATION PASSED`.

Record: `Checkpoint 4 — short/long rail paths, post access, and support bounds pass.`

---

### Task 5: Add finished geometry, room references, annotations, cameras, and inspection layers

**Files:**
- Modify: `bay_daybed_v4_generator.py`
- Modify: `test_bay_daybed_v4.py`

**Interfaces:**
- Produces `build_decks`, `build_finish`, `build_nailers`, `build_cushion`, `build_room_reference`, `build_dimensions`, `build_cameras`, and `configure_view_layers`.
- Produces `validate_finish_and_room(model) -> list[str]`.

- [ ] **Step 1: Add failing finish and orientation assertions**

Require three decks, exactly one cushion, six named cameras, straight front Y = 32 on every deck/skin/cushion front vertex, left deck top 14.5, center/right deck tops 10.5, cushion top 14.5, and sill underside 15. Require the left deck's minimum X to be positive-side and the right deck's maximum X to be negative-side.

Run the test; expected failure because finish geometry is absent.

- [ ] **Step 2: Build decks, skins, and nailers**

Create the center 60-by-32 deck and mirrored provisional triangle decks with vertices from the approved spec. Store `PLYWOOD_FIELD_STATUS` on both side decks and side skins. Build front skins whose front faces are all Y = 32 and whose bottoms are Z = 3. Add lightweight nailers behind the skins, above the recessed lower-frame area, and outside the structural cut list.

- [ ] **Step 3: Build exactly one center/right cushion**

Create one mesh from the union outline `(-30,0), (30,0), (30,32), (-62,32)` at Z = 10.5–14.5, with any small exposed perimeter encoded as a visualization-only parameter. Assert the cushion has zero overlap with the positive-X side deck interior and one straight front edge at Y = 32.

- [ ] **Step 4: Build measured room references**

Build the center wall, floor, sill underside/projection, and side-wall reference lines using:

```python
measured_outer_run = DAYBED_FINISHED_DEPTH / math.tan(math.radians(MEASURED_WALL_TURN))
```

At Y = 32, the measured room side reference must lie farther outward than the provisional 32-inch 45-degree run. Preserve the independent 106-inch dimension and facet parameters as annotations; neither changes structural geometry.

- [ ] **Step 5: Add metadata and construction annotations**

Store the viewer-facing convention on the scene and module collections. Add readable notes for 5-inch frame screws, 3-to-3-1/8-inch post screws, short-rail predrill/glue/clamp detail, field-template plywood, no baseline angle brackets, and the deck-as-primary-shear-diaphragm/bare-frame-squaring requirement.

- [ ] **Step 6: Add cameras and two inspection layers**

Create exactly:

```text
V4_TOP_FRAMING
V4_FRAMING_ISOMETRIC
V4_FINISHED_ISOMETRIC
V4_FRONT
V4_RIGHT_DETAIL
V4_LEFT_DETAIL
```

Configure `FRAMING_ONLY` to hide decks, finish skins, nailers, and cushion while retaining a deck-footprint outline. Configure `FINISHED` to show the complete assembly. Set `V4_FINISHED_ISOMETRIC` as the final scene camera.

- [ ] **Step 7: Validate finish, room, naming, and layers**

Assert positive X maps to left/raised/no-cushion, negative X maps to right/lower/cushion, exactly one cushion exists, every side plywood object has the exact field-template status, all front vertices are at or behind Y = 32 with visible face vertices at Y = 32, no finish reaches below Z = 3, and the measured 44.5-degree room reference never drives a structural object.

- [ ] **Step 8: Run GREEN and record checkpoint**

Run: `python test_bay_daybed_v4.py`

Expected: `V4 FINISH AND ROOM VALIDATION PASSED`.

Record: `Checkpoint 5 — finish, one cushion, measured room, cameras, and layers pass.`

---

### Task 6: Fail-closed exports, saved-model audit, and rendered inspection

**Files:**
- Modify: `bay_daybed_v4_generator.py`
- Modify: `test_bay_daybed_v4.py`
- Generate: `bay_daybed_v4.blend`
- Generate: `bay_daybed_v4_cutlist.csv`
- Generate: `bay_daybed_v4_dimensions.txt`

**Interfaces:**
- Produces `validate_all(model) -> str`, `cutlist_rows(model) -> list[dict]`, `write_cutlist(rows)`, `dimensions_report(model, spans) -> str`, and `write_outputs_after_validation(model)`.
- Final success token: `V4 VALIDATION PASSED`.

- [ ] **Step 1: Extend the audit to require final artifacts and exact CSV schema**

After a normal generator run, require all four V4 outputs. Parse CSV with `csv.DictReader` and assert:

```python
assert reader.fieldnames == ["MODULE", "OBJECT", "QUANTITY", "CUT_LENGTH", "CUT_TYPE", "ORIENTATION", "STATUS"]
assert center_counts == {59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}
assert all(row["CUT_TYPE"] == "SQUARE / 90 DEGREE" for row in side_rows)
assert all(row["STATUS"] == "PROVISIONAL / FIELD VERIFY" for row in side_rows)
```

Run the test; expected failure until the output stage exists.

- [ ] **Step 2: Implement one complete pre-save validator**

`validate_all` calls every earlier validator and additionally checks required collection/camera/layer names, counts, heights, no structural positive-volume intersections within or between modules, exact front/recess Y values, one cushion, exact status strings, metadata/CSV agreement, and the mandated summary statements. On failure, print `V4 VALIDATION CONFLICT: <message>` and raise before opening output files for writing.

- [ ] **Step 3: Add deliberate corruption checks**

In isolated Blender subprocesses, monkey-patch one parameter or metadata field at a time and require nonzero exit without V4 output replacement for:

```text
STRUCTURAL_SIDE_ANGLE = 45.5
SIDE_LOWER_FRONT_EDGE_Y = 29.5
one short rail length = 2.0
one short rail status = RESOLVED
LEFT upper Z = 8.25
cushion duplicated
```

Each failure must identify the violated rule rather than silently rebuilding around it.

- [ ] **Step 4: Write reports only after validation**

Write center aggregate rows and one row per side structural board/post. The dimensions report includes measured 44.5 versus structural 45.0, all side formulas and default cuts, eight/eight post counts, short/long fastener results, direct-bearing results, support spans, heights, the field-template plywood label, and the exact successful console summary from the spec.

- [ ] **Step 5: Save the `.blend` last**

After CSV and text writes succeed, save `bay_daybed_v4.blend`, print all output paths, the exact beginner-construction statement, the field-template warning, and `V4 VALIDATION PASSED`.

- [ ] **Step 6: Run syntax and full generation checks**

Run:

```powershell
python -m py_compile bay_daybed_v4_generator.py test_bay_daybed_v4.py
python test_bay_daybed_v4.py
```

Expected: exit 0, no traceback, all milestone tokens, `V4 VALIDATION PASSED`, and four nonempty V4 artifacts.

- [ ] **Step 7: Audit the saved Blender file in a fresh process**

Open `bay_daybed_v4.blend` with a second Blender process. Independently read mesh vertices and object properties to verify collection counts, actual bounds, side board axes, upper/lower/post Z contacts, post support coverage, short-rail metadata and screw-reference counts, front Y alignment, deck/cushion heights, camera names, layer exclusions, and absence of positive-volume structural intersections. Print `V4 SAVED MODEL AUDIT PASSED`.

- [ ] **Step 8: Render and inspect framing and finished views**

Render `V4_TOP_FRAMING` under `FRAMING_ONLY` and `V4_FINISHED_ISOMETRIC` under `FINISHED` to temporary PNGs. Inspect them for a visible smooth-wedge-versus-step contrast, positive-X raised landing, negative-X lower module, one center/right cushion, straight front, continuous shadow gap, readable room/reference distinction, and no exposed stepped framing in the finished view.

- [ ] **Step 9: Verify older artifacts are unchanged**

Before implementation, record SHA-256 hashes for every existing V1/V2/V3 `.py`, `.blend`, `.csv`, and `.txt` file. After V4 generation, recalculate them and require exact equality.

Record: `Checkpoint 6 — V4 generated, independently audited, rendered, and V1–V3 preserved.`
