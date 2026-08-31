# Bay Daybed V3 Design Specification

Date: 2026-08-29

## Scope and deliverables

Create a new, self-contained Blender Python construction model for a three-module bay-window daybed. V1 and V2 files remain untouched. The V3 generator writes:

- `bay_daybed_v3.blend`
- `bay_daybed_v3_generator.py`
- `bay_daybed_v3_cutlist.csv`
- `bay_daybed_v3_dimensions.txt`

The center module is resolved and must be recreated exactly from approved V2 dimensions. All side geometry is provisional, parameter-derived, visibly labeled `PROVISIONAL / FIELD VERIFY`, and rejected by assertions when the parameters cannot produce buildable geometry.

## Coordinate system and primary parameters

Use inches with X left/right, Y rear/front, and Z vertical. The center rear wall is Y=0 and the floor is Z=0. Nominal 2x4 stock is modeled at 1.5 by 3.5 inches.

The generator exposes these parameters together near its top:

```text
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
```

`SIDE_RUN` controls the provisional horizontal expansion at Y=32. `SIDE_ANGLE` records the intended wall assumption. Validation compares the angle implied by `SIDE_RUN / DAYBED_FINISHED_DEPTH` with `SIDE_ANGLE` and stops if they disagree rather than reconciling them silently.

The 106-inch room measurement remains an independent annotation. It does not alter the 60-inch resolved center or the 124-inch provisional idealized front width. Facet parameters affect room-reference geometry or annotations only, never structural framing.

## Collections

Create exactly these primary collections:

- `ROOM_REFERENCE`
- `CENTER_UPPER_FRAME`
- `CENTER_LOWER_FRAME`
- `CENTER_POSTS`
- `LEFT_UPPER_FRAME`
- `LEFT_LOWER_FRAME`
- `LEFT_POSTS`
- `RIGHT_UPPER_FRAME`
- `RIGHT_LOWER_FRAME`
- `RIGHT_POSTS`
- `PLYWOOD_DECKS`
- `MAPLE_FINISH`
- `FRONT_PANEL_NAILERS`
- `CUSHION_REFERENCE`
- `MODULE_CONNECTION_REFERENCE`
- `DIMENSIONS`
- `CAMERAS`

Every board and post is a separate named Blender object. Structural objects carry module, purpose, modeled dimensions, cut length, end-angle, orientation, and status metadata.

## Resolved center module

Recreate approved V2 without redesign:

- Finished envelope: 60 W by 32 D inches.
- Upper frame: 59 W by 31.5 D by 1.5 H, Z=8.25–9.75.
- Upper rails: two 59-inch flat 2x4s.
- Upper front-to-back members: five 24.5-inch flat 2x4s at X=-27.75, -13.875, 0, 13.875, and 27.75.
- Lower frame: 59 W by 29 D by 1.5 H, Z=0–1.5, rear aligned and front recessed 2.5 inches.
- Lower rails: two 59-inch flat 2x4s.
- Lower front-to-back members: four 22-inch flat 2x4s at X=-27.75, -9.25, 9.25, and 27.75.
- Rear posts: five boards, each 3.5 X by 1.5 Y by 6.75 Z, centered at Y=1.75.
- Front posts: five boards, each 1.5 X by 3.5 Y by 6.75 Z, centered at Y=27.25.
- Center deck: 60 by 32 by 0.75 inches, Z=9.75–10.5.
- Center front maple skin: nominal 0.5 inch, bottom at Z=3.

Each center front post spans Y=25.5–29, bears fully on the lower front rail, bears 2.5 inches beneath its upper front-to-back member, and bears 1 inch beneath the upper front rail. Its primary top fastening passes through the front-to-back member, not through the rear edge of the front rail.

The center structural cut totals remain exactly `4 x 59`, `5 x 24.5`, `4 x 22`, and `10 x 6.75`, all with status `RESOLVED`.

## Finished side geometry

The side decks are mirrored triangular prisms derived from `SIDE_RUN` and `DAYBED_FINISHED_DEPTH`.

Left deck vertices are `(-30, 0)`, `(-30, 32)`, and `(-30 - SIDE_RUN, 32)`. Right deck vertices mirror them at positive X. The finished diagonal is the segment from the rear-inner vertex to the front-outer vertex.

The left deck occupies Z=13.75–14.5 and reads as an exposed maple landing with no cushion. The right deck occupies Z=9.75–10.5 and continues the center seating platform. Each deck is one 0.75-inch plywood object. Side deck geometry and dimensions are provisional.

## Side structural frame geometry

Each upper and lower side frame uses the same seven-board topology:

1. Rear closure
2. Inner rail
3. Continuous radial rail
4. Diagonal rail
5. Inner cross-brace half
6. Outer cross-brace half
7. Front rail

All horizontal side boards are flat-oriented 2x4s with Z thickness 1.5 inches. Custom polygonal board meshes model the clipped and mitered plan footprints; boards must not be represented as overlapping rectangular proxies.

### Rear closure and rear setback

No side structural board enters Y<8. The rear closure occupies Y=8–11.5. Its inner end reaches the center structural mating plane at X=-29.5 on the left or X=29.5 on the right. Its outer end is calculated from the finished diagonal at Y=8.

The inner, radial, and diagonal rails begin at Y=11.5. Their rear faces may touch the closure's front face but may not overlap it volumetrically.

At the default parameters, the finished plywood tip extends about 11.31 inches diagonally beyond the rear closure. Validation requires this unsupported distance to remain below 16 inches.

### Inner rail and module mating plane

The inner side rail touches the center frame at the structural mating plane. The left rail occupies X=-33 to -29.5 and the right rail occupies X=29.5 to 33 at the default parameters. The contact with the center module is face-to-face and boundary-only.

The upper inner rail ends at Y=28, the rear face of the upper front rail. The lower inner rail ends at Y=25.5, the rear face of the lower front rail.

### Diagonal rail

`SIDE_DIAGONAL_RAIL_INSET` is the perpendicular distance from the finished plywood diagonal edge to the **outer edge** of the structural diagonal rail. The full 3.5-inch rail width lies inward of that edge and beneath the finished plywood.

At the defaults, the outer edge is inset 1 inch and the inner edge is inset 4.5 inches from the finished diagonal. The rail is clipped between Y=11.5 and the applicable upper or lower front-rail rear face. Its rear and front cuts are calculated from the side geometry and stored as provisional miter metadata.

The rear closure/diagonal interface is calculated from the shared Y=11.5 boundary. At the defaults it is approximately 2.86 inches. Validation requires at least 2.75 inches, verifies the 1-inch perpendicular plywood overhang, and verifies every diagonal-rail footprint vertex is inside the finished side-deck triangle.

### Radial rail

The continuous radial rail follows the calculated midpoint between the inner-rail centerline and diagonal-rail centerline at each Y. It is clipped between Y=11.5 and the applicable front-rail rear face. Its plan angle, length, and end cuts are calculated and reported as provisional values.

### Cross-braces

The cross-brace band is centered at Y=23.75 and occupies Y=22–25.5. It is split into two separate boards that terminate against opposite sides of the continuous radial rail. The inner half spans from the inner rail to the radial rail. The outer half spans from the radial rail to the diagonal rail.

The lower cross-brace front boundary at Y=25.5 touches the lower front rail rear boundary. Polygon-area and positive-volume tests must prove the contact is boundary-only. The corresponding upper members use the same cross-brace footprint, leaving a gap before the upper front rail.

Each cross-brace half must contain the complete plan footprint of its post while maintaining at least 1 inch of perpendicular clearance between the post and radial-rail joint. Post pose is calculated from the brace polygon and reported. At the default geometry the tapered outer brace requires a rotated post footprint; the generator must expose the resulting provisional position and rotation rather than hiding it. If no valid pose exists, generation stops.

### Front rails and 2.5-inch recess

Upper side front rails occupy Y=28–31.5. Lower side front rails occupy Y=25.5–29, preserving the 2.5-inch front recess. Their inner faces meet the center structural front rails at X=±29.5. Their outer ends are clipped to the inset diagonal support line and remain below the finished deck.

## Side posts and load paths

Each side module has exactly seven posts. Every post has an actual 1.5 by 3.5-inch 2x4 plan cross-section; plan rotation may be calculated where required by the angled frame:

- Two rear posts fully contained by the aligned upper and lower rear closures.
- Two cross-brace posts, one fully contained beneath each upper cross-brace half and on the matching lower cross-brace half.
- Three front posts fully supported by the lower front rail and located beneath the upper inner, radial, and diagonal load paths respectively.

Left posts run from Z=1.5 to 12.25 and have a 10.75-inch cut length. Right posts run from Z=1.5 to 8.25 and have a 6.75-inch cut length. All side post values remain provisional.

Front-post poses are solved from the overlap of the lower front rail with the corresponding upper longitudinal rail plus upper front rail. Each front post must have meaningful direct bearing beneath its named longitudinal member and must not rely on plywood for support.

For every side post, validation requires:

- Full plan containment on a lower structural member or documented lower structural union.
- Full plan containment beneath an upper structural member or documented upper structural union.
- Direct Z-face contact at both ends.
- A vertical fastening point with at least 0.75 inch edge distance in the post and clear driver access through the upper and lower frame.
- No intersection with a rail joint or another board.

For cross-brace posts, validation additionally requires at least 1 inch between the post footprint and the radial-rail joint and an unobstructed vertical driver prism at the fastening point. For front posts, the primary top screw passes through the corresponding inner, radial, or diagonal rail.

The load paths are deck to upper frame to posts to lower frame to floor. Side modules remain structurally independent and may touch the center only at intended mating faces.

## Heights

- Lower frames: Z=0–1.5 for all modules.
- Center/right posts: Z=1.5–8.25.
- Center/right upper frames: Z=8.25–9.75.
- Center/right decks: Z=9.75–10.5.
- Left posts: Z=1.5–12.25.
- Left upper frame: Z=12.25–13.75.
- Left deck: Z=13.75–14.5.
- Cushion reference: Z=10.5–14.5.
- Sill underside reference: Z=15.

The left landing is exactly 4 inches above the center/right wood decks and 0.5 inch below the provisional sill underside.

## Finish, nailers, cushion, and module connections

Create separate maple front skins for all three modules. Their lower edges are at approximately Z=3, leaving the lower frames visually recessed. Side skin footprints follow the provisional finished wedge and do not change structural geometry.

Create lightweight center and side finish nailers in `FRONT_PANEL_NAILERS`. Nailers support skins near their lower edge and remain above and independent from the recessed lower frames. They are nonstructural and excluded from the structural cut list.

Create one nonstructural oatmeal-colored cushion reference covering the center and most of the right module, inset approximately 0.5 inch from exposed finished edges. It occupies Z=10.5–14.5 and does not cover or intersect the raised left landing.

Add nonstructural joining-zone markers at X=±29.5 in `MODULE_CONNECTION_REFERENCE`. Markers identify accessible screw/bolt zones and do not represent permanent hardware or occupy structural volume.

## Room reference

Create an off-white 60-inch center rear wall, provisional left/right angled walls derived from the side parameters, a neutral floor, and a simplified sill reference with underside Z=15 and projection 2.5 inches. Optional facet reference objects use `FACET_CENTER_FLAT` and `FACET_TRANSITION` only when enabled.

Annotate both the 106-inch measured corner-to-corner value and the 124-inch idealized front width. The latter must read `PROVISIONAL — VERIFY FROM ROOM TEMPLATE`. Clearly label all side wall and facet geometry provisional.

## Materials, cameras, and view layers

Use simple natural-lumber, light-maple, oatmeal-cushion, off-white-wall, and light-neutral-floor materials.

Create these cameras:

- `TOP_ORTHO_COMPLETE`
- `FRONT_COMPLETE`
- `SIDE_COMPLETE`
- `ISOMETRIC_FRAMING_COMPLETE`
- `ISOMETRIC_FINISHED_COMPLETE`
- `ISOMETRIC_CENTER`
- `ISOMETRIC_LEFT`
- `ISOMETRIC_RIGHT`

Create `FRAMING_ONLY` and `FINISHED` view layers. `FRAMING_ONLY` hides plywood, maple skins, nailers, and cushion. `FINISHED` displays the completed assembly.

## Cut-list export

The CSV columns are:

```text
MODULE,OBJECT,QUANTITY,CUT_LENGTH_IN,END_A_ANGLE_DEG,END_B_ANGLE_DEG,ORIENTATION,STATUS
```

Center rows may be aggregated and must total exactly `4 x 59`, `5 x 24.5`, `4 x 22`, and `10 x 6.75`, with `STATUS=RESOLVED`.

Each side structural board and post receives its own calculated row with `QUANTITY=1` and `STATUS=PROVISIONAL / FIELD VERIFY`. Angled boards use modeled centerline length and calculated end angles; object metadata also records long-point and short-point dimensions when the miter makes a single length ambiguous. Nailers, skins, decks, cushion, room references, and connection markers are excluded from the structural 2x4 cut list.

## Validation and failure behavior

Validation runs before any export or `.blend` save. An assertion failure prints `V3 VALIDATION CONFLICT` with the offending object or calculated value and stops without silently moving geometry.

Required checks include:

- Exact V2 center bounds, elevations, member counts, post geometry, bearing, fastening annotation, nonintersection, and resolved cut totals.
- Exactly one left, center, and right structural assembly in separate collections.
- Exact deck-top elevations: center/right 10.5, left 14.5, cushion 14.5, sill underside 15.
- Side geometry derived from the published parameters and every side-derived object marked provisional.
- Rear setback 8, no side structural geometry at Y<8, and rear-tip unsupported distance below 16.
- Inner and diagonal rails do not overlap at or forward of Y=8.
- Rear closure does not overlap either rail, has usable fastening access, and meets the diagonal over at least 2.75 inches.
- Diagonal rail lies wholly beneath the deck with a 1-inch perpendicular outer-edge inset.
- Seven upper boards, seven lower boards, and seven posts in each side module.
- Cross-brace footprint Y=22–25.5 and boundary-only contact with the lower front rail.
- Both cross-brace posts fully bear on matching upper/lower brace halves, clear the radial joint by at least 1 inch, and have unobstructed fastening prisms.
- All three front posts per side fully bear on the lower front rail and beneath their named upper load paths, without plywood-only support.
- Every post has direct Z contact, sufficient edge distance, and practical top/bottom driver access.
- No positive-volume structural intersection within or between modules; intentional touching faces are allowed.
- Finished skin bottoms are approximately Z=3 and all lower front edges are recessed 2.5 inches.
- Calculated maximum unsupported deck span for center, left, and right; warning and validation failure if any exceeds 16 inches.
- CSV rows, counts, statuses, lengths, angles, orientations, and object metadata agree with modeled geometry.

## Output report

The dimensions text file and console report include exact center dimensions and cut totals; provisional left/right finished dimensions, frame calculations, post poses, cut lengths, and angle values; overall provisional width/depth/heights; rear interface and fastening clearances; maximum unsupported spans; and validation results.

The final line is:

`WARNING: SIDE MODULE ANGLES AND LENGTHS ARE PROVISIONAL UNTIL THE REAL BAY WALLS ARE FULL-SIZE TEMPLATED / FIELD MEASURED.`

## Verification workflow

Use a small runnable smoke test that launches Blender in background mode, runs the V3 generator, confirms the four outputs, opens the saved `.blend`, independently audits collection counts and critical bounds/bearing/nonintersection assertions, aggregates the CSV center totals, verifies every side status, and renders both complete isometric cameras for visual inspection.
