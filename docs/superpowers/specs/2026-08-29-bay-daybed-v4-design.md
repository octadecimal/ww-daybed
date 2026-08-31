# Bay-Window Daybed V4 — Beginner Construction Design

Date: 2026-08-29  
Status: Approved design; implementation requires a separate approved plan.

## 1. Scope and outputs

V4 is a new, self-contained Blender construction model. It does not import, modify, or overwrite V1, V2, or V3 geometry or files.

The generator will create:

- `bay_daybed_v4.blend`
- `bay_daybed_v4_generator.py`
- `bay_daybed_v4_cutlist.csv`
- `bay_daybed_v4_dimensions.txt`

The model contains three independent modules: a raised viewer-left landing, the resolved center daybed module, and a lower viewer-right cushion continuation. The center remains the approved V2/V3 structure. Both side modules use only square-cut, axis-aligned, flat 2x4 framing hidden below smooth wedge-shaped plywood.

## 2. Authoritative left/right convention

LEFT and RIGHT are always named from the perspective of a person standing in the bedroom and looking at the daybed:

- Positive X: **VIEWER LEFT — RAISED WOOD LANDING — NO CUSHION**
- Center: rectangular cushioned module
- Negative X: **VIEWER RIGHT — LOWER MODULE — CONTINUOUS CUSHION**

This convention is stored as scene metadata, repeated in the dimensions report, and assertion-checked. Any reversal is a generation failure.

## 3. Units, axes, and lumber

- Blender scene units are inches, represented with a single consistent inch-to-Blender conversion.
- X is left/right, Y is rear/front, and Z is vertical.
- Rear center wall plane: Y = 0.
- Finished front plane: Y = 32.
- Floor: Z = 0.
- Nominal 2x4 actual size: 1.5 by 3.5 inches.
- Every board is a separate, clearly named Blender object.
- Every horizontal structural 2x4 is laid flat: 1.5 inches in Z and 3.5 inches perpendicular to its long axis.

## 4. Measured architecture versus provisional construction geometry

Editable top-level parameters include:

| Parameter | Default | Meaning |
|---|---:|---|
| `CENTER_FLAT_WALL_WIDTH` | 60.0 | Measured center flat wall width |
| `DAYBED_FINISHED_DEPTH` | 32.0 | Finished design depth |
| `MEASURED_INTERIOR_CORNER_ANGLE` | 135.5 degrees | Measured bay interior corner |
| `MEASURED_WALL_TURN` | 44.5 degrees | Measured change in wall direction |
| `STRUCTURAL_SIDE_ANGLE` | 45.0 degrees | Simplified hidden framing calculation only |
| `APPROX_SILL_UNDERSIDE_HEIGHT` | 15.0 | Room reference |
| `APPROX_SILL_PROJECTION` | 2.5 | Room reference |
| `MEASURED_CORNER_TO_CORNER_WIDTH` | 106.0 | Preserved annotation; not forced to reconcile |
| `FACET_CENTER_FLAT` | 5.0 | Editable provisional room facet |
| `FACET_TRANSITION` | 1.0 | Editable provisional room facet |
| `SIDE_STEP_INTERVAL` | 8.0 | Simplified framing station interval |
| `SIDE_REAR_STRUCTURAL_SETBACK` | 8.0 | No side framing enters the rear tip |
| `SIDE_EDGE_STRUCTURE_INSET` | 1.0 | Minimum perpendicular framing inset from the simplified diagonal |
| `SIDE_LOWER_FRONT_RECESS` | 2.5 | Structural upper-to-lower front recess |

The room-reference side walls use the measured 44.5-degree turn. At 32 inches of depth they open slightly farther outward than the simplified 45-degree wedge. This difference is intentional fitting tolerance; the exact center module is never distorted to reconcile the room measurements.

Blender may display the provisional finished side wedges with vertices:

- Left: (-30, 0), (-30, 32), (-62, 32)
- Right: (+30, 0), (+30, 32), (+62, 32)

These are design/reference geometry only. The 45-degree edges, the approximately plus/minus 62-inch extents, and all derived side-plywood dimensions are not final cut dimensions. Every side deck and skin carries this exact status:

`FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING`

The hidden structural station calculations use 45.0 degrees. No 45.5-degree assumption is used anywhere. Room angles never create angled structural lumber.

## 5. Center module — resolved and unchanged

### 5.1 Finished envelope

- Width: 60
- Depth: 32
- Deck: 0.75 maple plywood, Z = 9.75 to 10.5
- Finished front face: Y = 32
- Finished wood height: 10.5

### 5.2 Upper flat 2x4 frame

- Outside size: 59 X by 31.5 Y by 1.5 Z
- Z = 8.25 to 9.75
- Rear rail: 59 by 3.5 by 1.5, Y = 0 to 3.5
- Front rail: 59 by 3.5 by 1.5, Y = 28 to 31.5
- Five 3.5-X by 24.5-Y members between the rails
- Member centerlines: X = -27.75, -13.875, 0, 13.875, 27.75
- Cut list: 2 by 59 and 5 by 24.5
- Exactly three of the five front-to-back members are interior crossmembers.

### 5.3 Lower flat 2x4 frame

- Outside size: 59 X by 29 Y by 1.5 Z
- Z = 0 to 1.5
- Rear rail: Y = 0 to 3.5
- Front rail: Y = 25.5 to 29
- Four 3.5-X by 22-Y members between the rails
- Member centerlines: X = -27.75, -9.25, 9.25, 27.75
- Cut list: 2 by 59 and 4 by 22
- The lower front edge is Y = 29, exactly 2.5 behind the upper structural front edge at Y = 31.5 and 3.0 behind the finished face at Y = 32.

### 5.4 Posts

- Ten posts, each 6.75 high, from Z = 1.5 to 8.25
- Five rear posts: 3.5 X by 1.5 Y
- Five front posts: 1.5 X by 3.5 Y
- Front-post footprint: Y = 25.5 to 29
- Each front post has 2.5 inches of bearing beneath its upper front-to-back member, from Y = 25.5 to 28, and 1.0 inch beneath the upper front rail, from Y = 28 to 29.

### 5.5 Resolved structural cut list

- 4 by 59
- 5 by 24.5
- 4 by 22
- 10 by 6.75

All center cut-list rows have `STATUS = RESOLVED`.

## 6. Side-module coordinate convention

For formulas, `u` is the nonnegative outward distance from the center/side module boundary:

- Left world X = -30 - u
- Right world X = +30 + u

At the simplified 45-degree construction assumption, the finished reference triangle is `0 <= u <= Y`. Structural objects must remain within that footprint. For an X-axis transverse member whose rear edge is `Y_min`, the default outer edge is:

`u_outer = Y_min - sqrt(2) * SIDE_EDGE_STRUCTURE_INSET`

With a 1-inch perpendicular inset, this puts the outer edge exactly 1 inch inside the simplified diagonal at the closest corner. The full 3.5-inch width of every Y-axis outer rail remains inward of its chosen outer edge.

## 7. Side upper frames — eight square-cut boards each

Both side upper frames use the same single-spine stepped-ladder topology and the same plan geometry. The viewer-left upper frame is at Z = 12.25 to 13.75; the viewer-right upper frame is at Z = 8.25 to 9.75.

Default board footprints and calculated cut lengths are:

| Board | Axis | Plan footprint in local `(u, Y)` | Default cut length |
|---|---|---|---:|
| Rear closure | X | `u=0..6.585786`, `Y=8..11.5` | 6.585786 |
| Continuous inner spine | Y | `u=0..3.5`, `Y=11.5..28` | 16.5 |
| Transverse near 16 | X | `u=3.5..12.585786`, `Y=14..17.5` | 9.085786 |
| Transverse near 24 | X | `u=3.5..20.585786`, `Y=22..25.5` | 17.085786 |
| Front rail | X | `u=0..26.585786`, `Y=28..31.5` | 26.585786 |
| Outer step rail 1 | Y | `u=3.5..7.0`, `Y=11.5..14` | 2.5 |
| Outer step rail 2 | Y | `u=9.085786..12.585786`, `Y=17.5..22` | 4.5 |
| Outer step rail 3 | Y | `u=17.085786..20.585786`, `Y=25.5..28` | 2.5 |

The transverse members perform the step-out connection; there are no redundant connector boards. All board axes are X or Y and all end cuts are square. Butt joints may share boundary faces but may not overlap volumetrically.

`OUTER_STEP_01` is intentionally shifted outward by 0.414214 inch from the original centered-on-closure proposal. This removes its positive-volume overlap with the 0-to-3.5-inch inner spine. Its rear end still contacts 3.085786 inches of the rear closure, exceeding the 2.75-inch fastening-interface minimum. Its closest perpendicular clearance beneath the provisional plywood edge is approximately 3.181981 inches.

## 8. Side lower frames — seven square-cut boards each

Both lower frames are at Z = 0 to 1.5. Their plan topology matches the upper load paths except that the front connection eliminates the third outer rail:

| Board | Axis | Plan footprint in local `(u, Y)` | Default cut length |
|---|---|---|---:|
| Rear closure | X | `u=0..6.585786`, `Y=8..11.5` | 6.585786 |
| Continuous inner spine | Y | `u=0..3.5`, `Y=11.5..25.5` | 14.0 |
| Transverse near 16 | X | `u=3.5..12.585786`, `Y=14..17.5` | 9.085786 |
| Transverse near 24 | X | `u=3.5..20.585786`, `Y=22..25.5` | 17.085786 |
| Lower front rail | X | `u=0..24.085786`, `Y=25.5..29` | 24.085786 |
| Outer step rail 1 | Y | `u=3.5..7.0`, `Y=11.5..14` | 2.5 |
| Outer step rail 2 | Y | `u=9.085786..12.585786`, `Y=17.5..22` | 4.5 |

The near-24 transverse member ends at Y = 25.5 and touches the lower front rail at its rear boundary. This is a boundary-only joint, not a volumetric overlap. The lower front edge is Y = 29 on both sides, aligned with the center lower frame. It is exactly 2.5 behind the upper structural front edge and exactly 3.0 behind the finished maple front plane.

## 9. Side posts — eight per side

Every side uses eight vertical posts: one inner and one outer post associated with each of the rear, near-16, near-24, and front stations. Each post is a separate board and bears on the union of named lower-frame members and beneath the corresponding union of upper-frame members.

The intended default bearing locations are:

1. Rear inner: straddles the rear-closure/inner-spine boundary.
2. Rear outer: uses a 1.5-X by 3.5-Y plan footprint centered within the 3.085786-inch rear-closure/outer-step-rail-1 interface and straddles their Y=11.5 boundary.
3. Near-16 inner: straddles the inner-spine/transverse joint.
4. Near-16 outer: straddles the transverse/outer-step-rail-2 boundary.
5. Near-24 inner: straddles the inner-spine/transverse joint.
6. Near-24 outer: straddles the outer-step-rail-2/transverse boundary.
7. Front inner: Y footprint 25.5 to 29, with 2.5 inches beneath the upper inner spine and 1.0 inch beneath the upper front rail.
8. Front outer: Y footprint 25.5 to 29, with 2.5 inches beneath upper outer-step-rail-3 and 1.0 inch beneath the upper front rail.

The front posts are 1.5 X by 3.5 Y in plan. Their entire lower footprint bears on the lower front rail. Other post rotations are selected only from the two actual 2x4 plan orientations, 3.5 by 1.5 or 1.5 by 3.5, to maximize direct union bearing without blocking a joint.

- Left post height: 10.75, Z = 1.5 to 12.25
- Right post height: 6.75, Z = 1.5 to 8.25

No post may rely on plywood, an offset block, or a baseline metal bracket. Each post must have an unobstructed vertical screw path through both the upper and lower 1.5-inch-thick frames.

## 10. Side frame fastening

### 10.1 Normal flat-frame joints

At ordinary 90-degree joints, a nominal 5-inch structural screw passes through the adjoining flat 2x4's 3.5-inch width and approximately 1.5 inches into the mating board. Use two screws per end only where modeled spacing, edge distance, penetration, and driver access all validate. Predrilling and supplemental wood glue are required construction notes.

### 10.2 Short rails

Every outer step rail shorter than 3.0 inches receives metadata named:

`SHORT_RAIL_SINGLE_SCREW_DETAIL`

For each 2.5-inch short rail:

- Use one predrilled nominal 5-inch structural screw per end.
- Each screw passes through 3.5 inches of the adjoining transverse board and penetrates approximately 1.5 inches into the short rail.
- Opposing screw centerlines are staggered 1.5 inches laterally across the 3.5-inch rail width.
- Default lateral edge distance is 1.0 inch on each side.
- Default vertical centerline is at mid-thickness, giving 0.75 inch to either Z edge.
- Each screw tip remains 1.0 inch from the opposite end of the 2.5-inch rail.
- Use wood glue at both joints, clamp firmly, and predrill for the selected structural screw.

The generator analytically models the screw centerline segments and driver-approach corridors. It asserts no path collision, no protrusion, the stated lateral and vertical edge distances, the stated tip-to-opposite-end clearance, and no structural obstruction in the driver corridor. These are geometric checks, not a substitute for the selected screw manufacturer's installation requirements.

The 4.5-inch outer rail uses two screws per end only if its modeled paths retain adequate spacing and a clear central separation between opposing penetration zones.

On both lower side frames, the front-end screws joining `OUTER_STEP_02` to `TRANSVERSE_24` require this explicit sequence because the final lower front rail occupies the driver approach corridor:

1. Fasten `OUTER_STEP_02` to `TRANSVERSE_24` before the lower front rail is installed.
2. Install the lower front rail at Y=25.5 to 29.0 afterward.

The affected rail and screw references carry `ASSEMBLY_SEQUENCE_REQUIRED` metadata. Assembly-state validation excludes only the not-yet-installed lower front rail and requires all other driver corridors to remain clear. Final-state validation restores the lower front rail, allows its expected boundary-only contact at Y=25.5, and rejects positive-volume overlap. Any other sequence-dependent joint must be reported and explicitly annotated rather than silently exempted.

If any parameter change invalidates a short-rail detail, generation stops. The dimensions report recommends a simple scrap-plywood or wood cleat/gusset before any station or topology redesign; the generator never silently moves the framing or adds hardware.

### 10.3 Post connections

Post fasteners are nominal 3 to 3-1/8-inch structural screws driven through the 1.5-inch flat frame into the post. Wood glue supplements the bearing surface. The baseline design requires no metal angle brackets.

## 11. Decks, finish, nailers, and cushion

### 11.1 Decks

- Center: 60 by 32 by 0.75 maple, Z = 9.75 to 10.5.
- Viewer-left: smooth provisional wedge, 0.75 maple, Z = 13.75 to 14.5.
- Viewer-right: smooth provisional wedge, 0.75 maple, Z = 9.75 to 10.5.
- Both side decks display `FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING`.

The side decks hide the staircase structure. They do not inherit stepped finished edges.

### 11.2 Maple front skins

The visible front is a single straight plane at Y = 32 across the full provisional width. No module protrudes. Panels occupy the nominal 0.5-inch finish zone behind that plane, stop at approximately Z = 3, and conceal the upper framing while preserving a continuous shadow gap above the recessed lower frames. Side skins are field-template parts.

### 11.3 Nailers

Lightweight 1x3 or 0.75-inch plywood-strip nailers live in `FRONT_PANEL_NAILERS` and are excluded from the structural cut list. They remain behind the maple faces and above the recessed lower-frame area. They support the finish without bridging down to the lower frame or closing the shadow gap.

### 11.4 Cushion

Exactly one nonstructural cushion-reference mesh covers center plus viewer-right and never covers viewer-left. It runs from Z = 10.5 to 14.5, has one perfectly straight front edge at Y = 32, and may follow the provisional rear/right wedge geometry. Its upholstery dimensions are explicitly nonfinal.

## 12. Heights and load paths

| Module | Lower frame | Posts | Upper frame | Deck | Finished top |
|---|---|---|---|---|---:|
| Viewer-left raised landing | Z 0..1.5 | 10.75 high | Z 12.25..13.75 | Z 13.75..14.5 | 14.5 |
| Center | Z 0..1.5 | 6.75 high | Z 8.25..9.75 | Z 9.75..10.5 | 10.5 |
| Viewer-right lower | Z 0..1.5 | 6.75 high | Z 8.25..9.75 | Z 9.75..10.5 | 10.5 |

The cushion top and viewer-left landing top are both 14.5, approximately 0.5 below the sill underside reference at Z = 15.

The structural load path is deck to upper frame to posts to lower frame to floor. The securely screwed 0.75-inch deck is the primary shear diaphragm. The bare stepped frame must be squared before deck installation. Orthogonal framing loops assist stiffness and squareness but are not treated as rigid diaphragms by themselves.

## 13. Plywood support calculation

The generator calculates the maximum plan distance from every point in each smooth deck footprint to the union of upper-frame support footprints. It also reports conservative station bounds.

At the rear tip, the default unsupported distance is `sqrt(8^2 + 8^2)`, approximately 11.31 inches. The conservative stepped-bay bound is approximately `sqrt(8^2 + 8^2) + 1`, or 12.31 inches. Both are below the 16-inch limit, but calculated geometry—not these rounded descriptions—controls validation.

Any module with a maximum unsupported deck distance of 16 inches or more fails generation.

## 14. Room reference and collections

Room-reference geometry includes the floor, 60-inch center rear wall, measured 44.5-degree side walls, approximate sill underside at Z = 15, and 2.5-inch sill projection. It remains visually distinct from construction geometry and does not include detailed windows.

Collections:

- `ROOM_REFERENCE`
- `CENTER_UPPER_FRAME`
- `CENTER_LOWER_FRAME`
- `CENTER_POSTS`
- `LEFT_UPPER_STEP_FRAME`
- `LEFT_LOWER_STEP_FRAME`
- `LEFT_POSTS`
- `RIGHT_UPPER_STEP_FRAME`
- `RIGHT_LOWER_STEP_FRAME`
- `RIGHT_POSTS`
- `PLYWOOD_DECKS`
- `MAPLE_FINISH`
- `FRONT_PANEL_NAILERS`
- `CUSHION_REFERENCE`
- `FASTENER_REFERENCE`
- `DIMENSIONS`
- `CAMERAS`

Simple materials distinguish natural framing lumber, light maple, warm ivory/oatmeal cushion, off-white walls, and light neutral wood floor.

## 15. Cameras and inspection states

Required cameras:

- `V4_TOP_FRAMING`
- `V4_FRAMING_ISOMETRIC`
- `V4_FINISHED_ISOMETRIC`
- `V4_FRONT`
- `V4_RIGHT_DETAIL`
- `V4_LEFT_DETAIL`

The top framing camera shows the smooth wedge footprint reference against the square-cut staircase. The finished isometric shows the positive-X raised landing, one center/right cushion, the straight front, and the negative-X lower wedge. Camera and scene metadata repeat the viewer-facing left/right convention.

Two inspection states or view layers expose framing-only and finished assemblies. The framing state hides decks, skins, and cushion while retaining a nonstructural deck-footprint outline.

## 16. CSV and text reports

The structural CSV columns are exactly:

`MODULE,OBJECT,QUANTITY,CUT_LENGTH,CUT_TYPE,ORIENTATION,STATUS`

- Center rows use the exact resolved aggregate cut list and `STATUS = RESOLVED`.
- Each side structural 2x4 is reported with quantity 1, calculated length, axis/orientation, `CUT_TYPE = SQUARE / 90 DEGREE`, and `STATUS = PROVISIONAL / FIELD VERIFY`.
- Side post rows carry the same provisional status.
- Nailers, finished plywood, cushion, and fastener references are excluded from the structural 2x4 cut list.
- Side plywood sizes appear only as provisional reference dimensions in the text report and are labeled `FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING`.

The dimensions report includes all inputs, derived board footprints and lengths, frame/deck heights, post counts, bearing results, screw-path results, support spans, naming metadata, and the measured-versus-simplified angle distinction.

## 17. Assertion-based validation and fail-closed generation

Validation runs before CSV/dimensions export and before saving the `.blend` file. A failed assertion raises a readable conflict report and prevents output replacement. Touching faces are allowed; positive-volume structural intersections are not.

### 17.1 Center

- Upper outside size is exactly 59 by 31.5 by 1.5, with two 59 rails and five 24.5 members, exactly three interior.
- Lower outside size is exactly 59 by 29 by 1.5, with two 59 rails and four 22 members, exactly two interior.
- Rear edges align; lower front edge is Y = 29; structural front recess is exactly 2.5.
- Exactly ten 6.75 posts occupy Z = 1.5 to 8.25.
- Rear and front bearing areas match the approved V2 geometry.
- Deck occupies Z = 9.75 to 10.5.
- Cut-list counts are exactly 4 by 59, 5 by 24.5, 4 by 22, and 10 by 6.75.

### 17.2 Side structural geometry

- Positive X is the raised viewer-left module; negative X is the lower viewer-right module.
- Each side has exactly eight upper boards, seven lower boards, and eight posts at default parameters.
- Every side board is axis-aligned and has square 90-degree cuts.
- No side structural board follows the diagonal, enters the zero-width rear tip, crosses outside the smooth reference footprint, or violates the 1-inch closest perpendicular inset.
- Rear setback is exactly 8 inches.
- Upper structural front edge is Y = 31.5; lower structural front edge is Y = 29; their recess is exactly 2.5; finished-face-to-lower-frame setback is exactly 3.0.
- All transverse/longitudinal joints are boundary-only; the near-24/lower-front contact is boundary-only.
- `OUTER_STEP_01` spans local U=3.5 to 7.0, has zero positive-volume overlap with the inner spine, retains a 3.085786-inch rear-closure fastening interface, and retains approximately 3.181981 inches of closest perpendicular plywood-edge clearance.
- The shifted first step has no positive-volume overlap with a transverse member, neighboring step rail, finish nailer, or module mating face.
- No structural boards overlap volumetrically within or between modules.

### 17.3 Posts and access

- Every one of the eight posts per side has complete lower-frame support under its plan footprint and meaningful direct upper-frame support under the corresponding named load-path union.
- No post relies on plywood or an unsupported offset.
- Both upper and lower vertical screw paths are unobstructed and have practical driver approach.
- The lower-frame seven-board simplification leaves no post unsupported.
- Front posts occupy Y = 25.5 to 29, fully bear on the lower front rail, and have approximately 2.5 inches beneath the upper longitudinal path plus 1.0 inch beneath the upper front rail.

### 17.4 Frame joints and short rails

- Every short rail's clear length is calculated from board boundaries.
- Rails below 3.0 inches use `SHORT_RAIL_SINGLE_SCREW_DETAIL` and exactly one modeled screw per end.
- Opposing screw centerlines are laterally separated by at least 1.5 inches; paths do not collide.
- Lateral edge distance is at least 1.0 inch; vertical edge distance is at least 0.75 inch.
- Nominal penetration is 1.5 inches; each tip remains at least 1.0 inch from the opposite end; no screw protrudes.
- Driver corridors do not intersect nearby boards or posts.
- The four lower-frame `OUTER_STEP_02` front-end screw paths are clear before lower-front-rail installation, carry `ASSEMBLY_SEQUENCE_REQUIRED`, and are the only sequence-dependent frame joints.
- With the lower front rails installed, their Y=25.5 contact remains boundary-only and no structural positive-volume overlap exists.
- Longer rails receive two screws per end only when their independent modeled paths pass the same geometric checks and opposing penetration zones retain positive clearance.
- If any check fails, the report recommends a scrap-wood/plywood cleat or gusset and generation stops without moving geometry.

### 17.5 Finish, cushion, height, and support

- Viewer-left deck top is exactly 14.5; center and viewer-right deck tops are exactly 10.5.
- Exactly one cushion covers center plus viewer-right, does not cover viewer-left, and tops at 14.5.
- Sill underside reference is 15; finished objects do not intersect it.
- Every visible front face has its maximum/front Y at exactly 32; neither side protrudes.
- Side decks and skins carry the required field-template label.
- Maximum unsupported plywood distance is less than 16 inches for every module.
- Each upper stepped bay forms an orthogonal closed support path tied to the deck, with the deck explicitly identified as the primary shear diaphragm.
- No baseline angle bracket is required.

## 18. Required console summary

The successful run prints the resolved center dimensions and cut list, calculated provisional side board lists and post counts, finish heights, maximum plywood support distances, fastening validations, and these exact identifiers:

`VIEWER LEFT — RAISED WOOD LANDING — NO CUSHION`

`VIEWER RIGHT — LOWER MODULE — CONTINUOUS CUSHION`

It ends with:

```text
V4 BEGINNER CONSTRUCTION:
ALL LEFT/RIGHT STRUCTURAL 2x4 CUTS ARE 90-DEGREE SQUARE CUTS.
THE FINISHED BAY ANGLES ARE CREATED BY PLYWOOD, NOT STRUCTURAL LUMBER.
LEFT/RIGHT ARE DEFINED FROM THE VIEWER'S PERSPECTIVE FACING THE DAYBED.
```

It also prints:

`WARNING: SIDE MODULE FRAMING POSITIONS AND FINISHED PLYWOOD ARE PROVISIONAL / FIELD VERIFY. TEMPLATE FINISHED SIDE PLYWOOD TO THE ACTUAL ROOM BEFORE CUTTING.`

If any statement cannot be truthfully asserted, the generator stops and reports the exact conflict instead of saving or silently adjusting geometry.
