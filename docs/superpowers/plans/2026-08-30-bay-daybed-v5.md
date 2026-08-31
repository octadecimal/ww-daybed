# Bay-Window Daybed V5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and independently audit a new V5 Blender construction model with the approved taller vertical stacks, three measured sill references, field-templated rear geometry, square-cut side framing, supported front edges, module packers/bolts, and two-direction hidden bracing.

**Architecture:** One self-contained `bpy` generator owns parameters, pure planar geometry, scene construction, metadata, fail-closed validation, reporting, and saving. One standard-library test driver runs pure checks, deliberate corruption cases, the complete background-Blender build, a second-process saved-model audit, and inspection renders. V1–V4 are read-only references; V5 imports no older generator or `.blend` file.

**Tech Stack:** Python standard library, Blender 5.2 Python API (`bpy`), CSV/text output, assertion-based geometry validation.

**Spec:** `docs/superpowers/specs/2026-08-30-bay-daybed-v5-design.md`

## Global Constraints

- Positive X is viewer-left: raised 20.5-inch maple landing, no cushion.
- Negative X is viewer-right: 14.5-inch deck beneath the one center/right cushion.
- Measured walls/sills use 44.5 degrees; hidden side framing uses simplified 45-degree, axis-aligned, square-cut boards only.
- Finished front is Y=32; upper structural front is Y=31.5; lower structural front is Y=29.
- Center structural rear is Y=4.5; finished center rear is Y=3 with approved chamfers.
- Center cuts resolve to 4×59, 5×20, 4×17.5, 10×10.75 only after geometry validation.
- Each side has seven upper boards, five lower boards, seven posts, and the approved edge-load rail.
- `MAX_EDGE_CANTILEVER_GEOMETRIC_TARGET=6.25`; the expected 6.020797-inch result is `ENGINEER / FIELD VERIFY`, never certified capacity.
- Nominal 0.5-inch module packers are field-fit to the actual assembled seam because sheet thickness and built gap may vary.
- Exactly one cushion spans center plus negative-X viewer-right.
- Every module has continuous supported hidden bracing planes in X-Z and Y-Z; geometric paths may pass while capacity remains not engineering-certified.
- Validation completes before creating any final `.blend`, CSV, or dimensions file.
- The workspace is not a Git repository; checkpoint records replace commits, and implementation must not initialize Git.

## File map

- Create `bay_daybed_v5_generator.py`: parameters, geometry, model building, validation, metadata, reports, and final save.
- Create `test_bay_daybed_v5.py`: pure checks, corruption cases, complete generation, saved-model audit, and render verification.
- Generate `bay_daybed_v5.blend`, `bay_daybed_v5_cutlist.csv`, and `bay_daybed_v5_dimensions.txt` only after mandatory validation passes.
- Modify only the approved V5 spec/plan documents; preserve every V1–V4 output byte-for-byte.

---

### Task 1: Test harness, parameters, and planar geometry

**Files:**
- Create: `bay_daybed_v5_generator.py`
- Create: `test_bay_daybed_v5.py`

**Interfaces:**
- Produces `rect`, `polygon_area`, `polygon_intersection`, `point_in_polygon`, `positive_overlap_area`, `side_x`, and `local_to_world`.
- Produces `finished_polygons() -> dict[str, list[tuple[float, float]]]`.
- Produces `validate_parameters() -> None` and success token `V5 PARAMETER VALIDATION PASSED`.

- [ ] **Step 1: Write the failing parameter/geometry harness**

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
GENERATOR = ROOT / "bay_daybed_v5_generator.py"

def run_expr(expr):
    boot = f"import runpy; n=runpy.run_path({str(GENERATOR)!r}); {expr}"
    return subprocess.run([str(BLENDER), "--background", "--python-expr", boot], cwd=ROOT, capture_output=True, text=True)

def require_ok(result, token):
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert token in output, output
```

- [ ] **Step 2: Run RED**

Run: `python test_bay_daybed_v5.py`

Expected: nonzero exit because the V5 generator is absent.

- [ ] **Step 3: Add exact approved parameters and derived geometry**

Define the spec values, output paths, status strings, and these formulas:

```python
WALL_SLOPE = math.tan(math.radians(44.5))
BAY_MOUTH_Y = 23.0 * WALL_SLOPE
SIDE_FINISHED_OFFSET_INTERCEPT = 3.0 * math.sqrt(1.0 + WALL_SLOPE**2)
SIDE_MOUTH_U = 23.0 - SIDE_FINISHED_OFFSET_INTERCEPT / WALL_SLOPE
CENTER_REAR_X = (3.0 - SIDE_FINISHED_OFFSET_INTERCEPT) / WALL_SLOPE
```

Build the center six-vertex polygon and approved mirrored side quadrilaterals. Derive the front-face X at Y=31.5 from the mouth-to-front flare line; do not hard-code 61.293456 as source geometry.

- [ ] **Step 4: Add dependency-free convex geometry helpers**

Implement shoelace area, Sutherland–Hodgman convex clipping, boundary-inclusive point containment, rectangle creation, and positive-overlap area. Include internal asserts proving disjoint, boundary-touching, and positive-overlap cases.

- [ ] **Step 5: Validate parameters and arithmetic**

Require:

```python
assert close(BAY_MOUTH_Y, 22.602037, 1e-5)
assert close(CENTER_REAR_X, -28.772668, 1e-5)
assert close(front_face_outer_x("LEFT", 31.5), 61.293456, 1e-5)
assert close(math.hypot(6.0, 0.5), 6.020797, 1e-6)
assert STRUCTURAL_SIMPLIFIED_ANGLE == 45.0
assert MEASURED_WALL_TURN == 44.5
```

Run the harness and require `V5 PARAMETER VALIDATION PASSED`.

### Task 2: Scene helpers and exact center structure

**Files:**
- Modify: `bay_daybed_v5_generator.py`
- Modify: `test_bay_daybed_v5.py`

**Interfaces:**
- Produces `reset_scene`, `configure_units`, `create_collections`, `create_materials`, `add_prism`, `add_box`, `bounds`, `object_footprint`, and `structural_volume_overlap`.
- Produces `build_center(...) -> dict` and `validate_center(center) -> None`.

- [ ] **Step 1: Add failing center assertions**

Require seven upper boards, six lower boards, ten posts, upper bounds `(-29.5,29.5,4.5,31.5,12.25,13.75)`, lower bounds `(-29.5,29.5,4.5,29,0,1.5)`, and cut aggregate `{59:4,20:5,17.5:4,10.75:10}`.

- [ ] **Step 2: Implement minimal scene creation**

Reset the scene, set inches, create every required collection, create simple materials, and create arbitrary polygon prisms. Store dimensions, role, module, cut, orientation, status, and validation metadata directly on each object.

- [ ] **Step 3: Build the rectangular center module**

Create separate upper/lower rails and members at the approved X stations and Y bounds. Create rear posts centered Y=6.25 and front posts spanning Y=25.5..29, all Z=1.5..12.25.

- [ ] **Step 4: Validate center geometry and bearing**

Check exact bounds/counts/cuts, three upper interior members, two lower interior members, frame rectangularity, post support unions, touching-only frame joints, no positive-volume lumber overlap, 2.5-inch structural recess, and complete containment beneath the chamfered center deck.

- [ ] **Step 5: Run GREEN**

Require `V5 CENTER VALIDATION PASSED` and record checkpoint 2.

### Task 3: Side staircase framing, posts, edge support, and fasteners

**Files:**
- Modify: `bay_daybed_v5_generator.py`
- Modify: `test_bay_daybed_v5.py`

**Interfaces:**
- Produces `side_frame_specs(frame)`, `side_post_specs()`, `build_side_frame`, `build_side_posts`, `build_fastener_references`, `validate_sides`, and `calculate_side_support_metrics`.

- [ ] **Step 1: Add failing side topology assertions**

For both sides require seven upper boards, five lower boards, seven posts, no deleted rear closure/step/post references, and every lumber object marked `SQUARE / 90 DEGREE` plus `PROVISIONAL / FIELD VERIFY`.

- [ ] **Step 2: Build the approved local-U frame footprints**

Use the exact spec footprints for `INNER_SPINE`, `TRANSVERSE_16`, `TRANSVERSE_24`, extended upper/lower front rails, `OUTER_STEP_02`, `OUTER_STEP_03`, and `FRONT_EDGE_LOAD_RAIL`. Mirror only local U into world X; never rotate a board to the field-templated edge.

- [ ] **Step 3: Build seven directly supported posts per side**

Use the seven approved local footprints. Set left height 16.75 and right height 10.75. Validate each post plan area against the union of named lower boards and the union of named upper boards, including the `FRONT_EDGE` post's load-rail/front-rail upper union.

- [ ] **Step 4: Validate full footprint containment and support distance**

Intersect every entire board rectangle with the side polygon and require equal area. Compute support against the complete upper footprint union. Report rear distance about 7.293904, interior maximum below 16, and `MAX_EDGE_CANTILEVER=math.hypot(32-26,32-31.5)` about 6.020797. Label the edge result `ENGINEER / FIELD VERIFY`, not capacity.

- [ ] **Step 5: Model remaining fastener details**

Retain `SHORT_RAIL_SINGLE_SCREW_DETAIL` only where length is below 3 inches. Validate the front-edge load rail's single predrilled nominal 5-inch screw, glue, deck connection, direct post bearing, edge distance, 1.5-inch penetration, contained tip, and front driver corridor. Preserve lower `OUTER_STEP_02` assembly-before-front-rail metadata and validate its pre-install driver corridor.

- [ ] **Step 6: Run GREEN**

Require `V5 SIDE/EDGE/FASTENER VALIDATION PASSED` and record checkpoint 3.

### Task 4: Room, independent sills, decks, exact faces, and cushion

**Files:**
- Modify: `bay_daybed_v5_generator.py`
- Modify: `test_bay_daybed_v5.py`

**Interfaces:**
- Produces `build_room_reference`, `build_decks`, `build_finish`, `build_nailers`, `build_cushion`, and `validate_finish_room`.

- [ ] **Step 1: Add failing room/finish assertions**

Require three exact sill names, one cushion, center/right deck top 14.5, cushion top 18.5, left top 20.5, no left cushion, all visible fronts at Y=32, and no face/deck positive-volume overlap.

- [ ] **Step 2: Build measured walls and three separate sills**

Build the 60-inch center wall and side walls ending at `(±53,BAY_MOUTH_Y)`. Create independent 1-inch-thick sill prisms Z=15..16 with 2.5-inch inward perpendicular projection. Apply the 0.5-inch end gap only to sill visualization metadata/length, never framing or cut geometry.

- [ ] **Step 3: Build the three field-templated decks**

Use the exact polygons from `finished_polygons()`, deck thickness 0.75, center/right Z=13.75..14.5, and left Z=19.75..20.5. Store `FIELD VERIFY / TEMPLATE TO ACTUAL ROOM` on all angled/rear finish pieces.

- [ ] **Step 4: Build exact maple faces**

Create center face `X=-30..30,Y=31.5..32,Z=3..13.75`; left trapezoid using the calculated X at Y=31.5 and X=62 at Y=32, Z=3..19.75; and its right mirror Z=3..13.75. Require face/deck boundary contact at one Z plane and zero volume overlap.

- [ ] **Step 5: Build one center/right cushion**

Create one mesh from the union outline of the center and right polygons at Z=14.5..18.5. Validate it follows the approved rear boundary, stays out of left plan area, has one straight front at Y=32, and has at least nominal 0.5-inch clearance from sill noses only in the physical sill region.

- [ ] **Step 6: Run GREEN**

Require `V5 ROOM/FINISH VALIDATION PASSED` and record checkpoint 4.

### Task 5: Bracing and module connections

**Files:**
- Modify: `bay_daybed_v5_generator.py`
- Modify: `test_bay_daybed_v5.py`

**Interfaces:**
- Produces `build_bracing`, `validate_bracing_graph`, `build_module_connections`, and `validate_module_connections`.

- [ ] **Step 1: Add failing two-plane bracing tests**

For each module require one continuous X-Z and one continuous Y-Z structural-plywood panel path, continuous backing on all edges, a connected contact graph to upper/lower frames and vertical cleats/posts, and clear module seams.

- [ ] **Step 2: Build structural-plywood panels and square cleats**

Use the approved center rear/internal and side inner/forward clear regions. Create distinct generic 1/2-inch structural plywood and square-cut cleat objects. Keep all panel and cleat volumes outside lumber, finish, plinth visibility, post paths, and connection-access corridors.

- [ ] **Step 3: Build eight nominal field-fit packers**

Create the four approved packer envelopes per seam in `MODULE_CONNECTION_PARTS`, mirror at negative X, and store:

```python
nominal_thickness = 0.5
field_fit_required = True
field_fit_note = "FIELD-FIT TO ACTUAL ASSEMBLED SEAM; SHEET-GOODS THICKNESS MAY DIFFER FROM NOMINAL"
primary_connection = False
```

The two front-return packers are seam fillers only.

- [ ] **Step 4: Build and validate eight through-bolt references**

Place two upper and two lower nominal 3/8-by-9 bolt references per seam at Y=12.75 and 20, Z=13 and 0.75. Validate member/packer/spine penetration, hole containment, modeled edge/end distance, head/washer/nut/socket zones, drill corridor, and a 9-inch insertion/removal corridor.

- [ ] **Step 5: Enforce assembly sequence and bracing clearance**

Store `MODULE_CONNECTION_ASSEMBLY_SEQUENCE_REQUIRED`: packers first, clamp bare modules, drill/install bolts, then install any bracing/finish component that would restrict access. Fail if panels, cleats, decks, faces, or nailers block either bolt side. Keep hardware specification/capacity `ENGINEER / FIELD VERIFY`.

- [ ] **Step 6: Run GREEN**

Require both exact report lines:

```text
GEOMETRIC RACKING PATH: PASS
STRUCTURAL CAPACITY: NOT ENGINEERING-CERTIFIED
```

Record checkpoint 5.

### Task 6: Reports, cameras, fail-closed save, corruption tests, and saved audit

**Files:**
- Modify: `bay_daybed_v5_generator.py`
- Modify: `test_bay_daybed_v5.py`
- Generate: `bay_daybed_v5.blend`
- Generate: `bay_daybed_v5_cutlist.csv`
- Generate: `bay_daybed_v5_dimensions.txt`

**Interfaces:**
- Produces `build_dimensions`, `build_cameras`, `configure_view_layers`, `cutlist_rows`, `dimensions_report`, `validate_all`, and `main`.
- Final tokens: `V5 VALIDATION PASSED` and `V5 SAVED MODEL AUDIT PASSED`.

- [ ] **Step 1: Add cameras and view layers**

Create all eight required V5 cameras and `FRAMING_ONLY`, `BRACING_INSPECTION`, and `FINISHED` view layers. Keep camera transforms unmirrored and store the viewer-left/right convention on scene and cameras.

- [ ] **Step 2: Build CSV/report rows in memory**

Use the exact eight-column CSV schema. Include resolved center rows, provisional side 2x4 rows, separate bracing panels/cleats, field-fit packers, nominal bolt references, and field-templated finish plywood. Do not open final files yet.

- [ ] **Step 3: Implement one fail-closed validator**

`validate_all` calls every earlier validator, checks required collections/cameras/layers/counts/status strings, validates no impossible structural overlap, and renders the exact success statements in memory. On any assertion print `V5 VALIDATION CONFLICT: <object/dimension>` and raise before writing any final artifact.

- [ ] **Step 4: Add deliberate corruption cases**

Run isolated Blender expressions that reverse left/right, duplicate cushion, delete a sill, angle a side cut, reference a deleted rear part, break one bracing edge/direction, block a driver/bolt corridor, remove a packer, exceed interior or edge support targets, overlap face/deck, and violate sill clearance. Require nonzero exits and unchanged/nonexistent final output hashes.

- [ ] **Step 5: Save validated outputs and model**

After validation only, atomically replace the CSV and dimensions files from temporary files, then save the `.blend` last. Print the full required summary and `V5 VALIDATION PASSED`.

- [ ] **Step 6: Run syntax and complete generation**

Run:

```powershell
python -m py_compile bay_daybed_v5_generator.py test_bay_daybed_v5.py
python test_bay_daybed_v5.py
```

Require all final files nonempty and schema/report contracts exact.

- [ ] **Step 7: Audit the saved `.blend` in a fresh Blender process**

Open `bay_daybed_v5.blend` independently and recompute object bounds, actual mesh footprints, counts, heights, bearing contacts, packer dimensions/metadata, bolt corridors, face/deck contacts, sill geometry, side convention, bracing continuity, and camera names from saved data. Print `V5 SAVED MODEL AUDIT PASSED` only from this second process.

- [ ] **Step 8: Render and inspect all required views**

Render all eight cameras. Verify the left detail shows +X raised/no cushion/2-inch difference; the right detail shows -X lower continuous cushion, measured rear fit, and no Y>32 protrusion; the sill detail shows three separate sills and nominal gap; top framing shows square side steps below smooth field-templated decks.

- [ ] **Step 9: Prove V1–V4 preservation**

Compare pre/post SHA-256 hashes for every V1–V4 `.py`, `.blend`, `.csv`, and `.txt` file. Require exact equality and record checkpoint 6.
