# Bay-Window Daybed V5 Design Specification

Date: 2026-08-30  
Status: Ready for user review  
Outputs: `bay_daybed_v5.blend`, `bay_daybed_v5_generator.py`, `bay_daybed_v5_cutlist.csv`, `bay_daybed_v5_dimensions.txt`

## 1. Scope and safety qualification

V5 is a new, self-contained Blender construction model derived from the approved V4 construction patterns. It does not import V4 at runtime and does not overwrite or modify V1–V4 files.

The generator validates dimensional geometry, contact, bearing, support, connection locations, assembly access, side-footprint containment, and two-direction bracing continuity. It does not calculate or certify lateral capacity.

Every successful report must contain exactly:

`GEOMETRIC RACKING PATH: PASS`

`STRUCTURAL CAPACITY: NOT ENGINEERING-CERTIFIED`

Actual structural capacity depends on plywood thickness and grade, panel orientation, screw type, diameter, penetration, edge and field spacing, framing species and grade, connection slip, module-to-module fastening, floor/wall anchorage, and actual design loads. Bracing material and fastening remain `ENGINEER / FIELD VERIFY`.

## 2. Coordinate and naming convention

Blender world axes are:

- X: left/right.
- Y: rear/front, increasing into the room.
- Z: vertical.
- Floor: Z = 0.
- Rear center wall: Y = 0.
- Finished front: Y = 32.

The approved V4 viewer convention is preserved:

- Positive X: `VIEWER LEFT — RAISED 20.5-INCH WOOD LANDING — NO CUSHION`.
- Negative X: `VIEWER RIGHT — 14.5-INCH DECK — SINGLE CENTER/RIGHT CUSHION`.

No camera has a negative X scale or other horizontal mirror. Scene, collection, object, report, cut-list, and camera metadata repeat this convention. Validation fails if the raised and cushioned sides are reversed.

## 3. Master parameters

```text
CENTER_FLAT_WALL_WIDTH = 60.0
MEASURED_CORNER_TO_CORNER_WIDTH = 106.0
MEASURED_INTERIOR_CORNER_ANGLE = 135.5
MEASURED_WALL_TURN = 44.5
STRUCTURAL_SIMPLIFIED_ANGLE = 45.0
FINISHED_FRONT_Y = 32.0
WALL_TO_FINISHED_REAR_EDGE = 3.0
SILL_UNDERSIDE_Z = 15.0
SILL_TOP_Z = 16.0
SILL_THICKNESS = 1.0
SILL_PROJECTION = 2.5
APPROX_SILL_END_GAP = 0.5
SIDE_EDGE_STRUCTURE_INSET = 1.0
SIDE_UPPER_FRONT_EDGE_Y = 31.5
SIDE_LOWER_FRONT_EDGE_Y = 29.0
MAX_UNSUPPORTED_DECK_SPAN = 16.0
MAX_EDGE_CANTILEVER_GEOMETRIC_TARGET = 6.25
ACTUAL_2X4_THICKNESS = 1.5
ACTUAL_2X4_WIDTH = 3.5
STRUCTURAL_BRACING_THICKNESS = 0.5
```

`APPROX_SILL_END_GAP` is `VISUALIZATION ONLY — FIELD VERIFY`. It must not drive framing, finished daybed geometry, or cut dimensions.

## 4. Measured bay and offset geometry

Let local U be the outward distance from the center/side seam. Positive U maps to increasing X on viewer-left and decreasing X on viewer-right.

```text
m = tan(44.5 degrees)
bay mouth half-run = (106 - 60) / 2 = 23
BAY_MOUTH_Y = 23 * m = approximately 22.602037
```

The physical angled walls terminate at:

- Viewer-left: approximately `(53, 22.602037)`.
- Viewer-right: approximately `(-53, 22.602037)`.

For the 3-inch perpendicular finished offset from an angled wall:

```text
SIDE_FINISHED_OFFSET_INTERCEPT = 3 * sqrt(1 + m^2)
                               = approximately 4.206096
offset line in local coordinates: Y = m * U + SIDE_FINISHED_OFFSET_INTERCEPT
```

The center Y=3 offset and measured side offset intersect at approximately X = ±28.772668. The side offset crosses the module seams X = ±30 at Y = approximately 4.206096. At the physical bay mouth, the side offset is U = approximately 18.719845, or world |X| = approximately 48.719845.

The offset is split into two honest regions:

1. Measured sill-clearance region: seam to bay mouth, following the measured 44.5-degree wall with a true 3-inch perpendicular offset.
2. Forward flare region: bay mouth to Y=32, with no sill present, flaring to the provisional front corner |X|=62.

The 0.5-inch sill-nose clearance requirement applies only in the measured sill-clearance region.

## 5. Finished plan polygons

All angled finished plywood is `FIELD VERIFY / TEMPLATE TO ACTUAL ROOM`.

### 5.1 Center deck polygon

The center deck is a field-templated six-vertex polygon:

```text
(-28.772668, 3.000000)
(+28.772668, 3.000000)
(+30.000000, 4.206096)
(+30.000000, 32.000000)
(-30.000000, 32.000000)
(-30.000000, 4.206096)
```

It is 60 inches wide at the front. Its nominal centerline depth is 29 inches. The short rear corner transitions are part of the true three-wall offset, not hidden framing.

### 5.2 Viewer-left finished polygon

```text
(30.000000, 4.206096)
(48.719845, 22.602037)
(62.000000, 32.000000)
(30.000000, 32.000000)
```

This is the raised landing at Z=19.75 to 20.5 and carries no cushion.

### 5.3 Viewer-right finished polygon

The viewer-right polygon mirrors the viewer-left polygon across X:

```text
(-30.000000, 4.206096)
(-48.719845, 22.602037)
(-62.000000, 32.000000)
(-30.000000, 32.000000)
```

This is the lower deck at Z=13.75 to 14.5 beneath the single center/right cushion.

### 5.4 Cushion polygon

Exactly one nonstructural cushion-reference mesh covers the union of the center and viewer-right finished polygons. It follows the center rear offset, both small center chamfers, the measured viewer-right offset to the bay mouth, the forward flare, and the common Y=32 front. It never overlaps the viewer-left landing in plan.

## 6. Vertical stacks

### 6.1 Center and viewer-right

```text
lower frame: Z=0.0..1.5
posts: Z=1.5..12.25; cut height 10.75
upper frame: Z=12.25..13.75
deck: Z=13.75..14.5
cushion: Z=14.5..18.5
```

### 6.2 Viewer-left raised landing

```text
lower frame: Z=0.0..1.5
posts: Z=1.5..18.25; cut height 16.75
upper frame: Z=18.25..19.75
deck: Z=19.75..20.5
no cushion
```

The raised landing is exactly 2 inches above the cushion top.

## 7. Center structural module

The center frame remains rectangular and 59 inches wide. Horizontal 2x4s lie flat: 1.5 inches high and 3.5 inches wide perpendicular to their long axes.

### 7.1 Upper frame

```text
outside bounds: X=-29.5..29.5, Y=4.5..31.5, Z=12.25..13.75
outside size: 59 x 27 x 1.5
rear rail: 59 x 3.5 x 1.5 at Y=4.5..8.0
front rail: 59 x 3.5 x 1.5 at Y=28.0..31.5
five Y members: 3.5 x 20 x 1.5 at Y=8.0..28.0
X centers: -27.75, -13.875, 0, 13.875, 27.75
```

### 7.2 Lower frame

```text
outside bounds: X=-29.5..29.5, Y=4.5..29.0, Z=0.0..1.5
outside size: 59 x 24.5 x 1.5
rear rail: 59 x 3.5 x 1.5 at Y=4.5..8.0
front rail: 59 x 3.5 x 1.5 at Y=25.5..29.0
four Y members: 3.5 x 17.5 x 1.5 at Y=8.0..25.5
X centers: -27.75, -9.25, 9.25, 27.75
```

### 7.3 Posts and center cut categories

Ten posts use the approved V4 rows and X stations, shifted for the new rear rails:

- Five rear posts: actual plan 3.5 X by 1.5 Y, fully on the rear rails, centered at Y=6.25.
- Five front posts: actual plan 1.5 X by 3.5 Y, footprint Y=25.5..29.0.
- All ten: 10.75 inches high, Z=1.5..12.25.

Resolved center 2x4 categories after validation:

```text
4 x 59
5 x 20
4 x 17.5
10 x 10.75
```

The full 59-inch structural rectangles lie beneath the center finished polygon. Their rear edge at Y=4.5 avoids the 3-inch clearance chamfers. Nominal rear plywood cantilever is approximately 1.5 inches and must remain below 16 inches.

## 8. Side structural envelope and topology

Side structural members remain axis-aligned and square-cut. No 2x4 follows an angled finished edge.

The translated simplified 45-degree structural envelope is:

```text
SIDE_STRUCTURAL_INTERCEPT = SIDE_FINISHED_OFFSET_INTERCEPT
                            + sqrt(2) * SIDE_EDGE_STRUCTURE_INSET
                          = approximately 5.620310
outer structural limit: U <= Y - SIDE_STRUCTURAL_INTERCEPT
```

This stays inside the measured/field-templated finished polygon. The convex containment validator checks each full board footprint by polygon intersection area and corner containment, not only its centerline or endpoints.

The obsolete V4 rear station is deleted from both side modules:

- No `REAR_CLOSURE`.
- No `OUTER_STEP_01`.
- No rear inner or rear outer posts.
- No metadata, fasteners, assertions, or instructions reference those deleted parts.

### 8.1 Upper side frame: seven boards per side

Local U/Y footprints and provisional cuts:

```text
INNER_SPINE:
  U=0..3.5, Y=11.5..28.0, cut 16.5, orientation Y

TRANSVERSE_16:
  U=3.5..8.379690, Y=14.0..17.5, cut 4.879690, orientation X

TRANSVERSE_24:
  U=3.5..16.379690, Y=22.0..25.5, cut 12.879690, orientation X

FRONT_RAIL:
  U=0..26.0, Y=28.0..31.5, cut 26.0, orientation X

OUTER_STEP_02:
  U=4.879690..8.379690, Y=17.5..22.0, cut 4.5, orientation Y

OUTER_STEP_03:
  U=12.879690..16.379690, Y=25.5..28.0, cut 2.5, orientation Y

FRONT_EDGE_LOAD_RAIL:
  U=19.0..22.5, Y=25.5..28.0, cut 2.5, orientation Y
```

### 8.2 Lower side frame: five boards per side

```text
INNER_SPINE:
  U=0..3.5, Y=11.5..25.5, cut 14.0, orientation Y

TRANSVERSE_16:
  U=3.5..8.379690, Y=14.0..17.5, cut 4.879690, orientation X

TRANSVERSE_24:
  U=3.5..16.379690, Y=22.0..25.5, cut 12.879690, orientation X

LOWER_FRONT_RAIL:
  U=0..22.5, Y=25.5..29.0, cut 22.5, orientation X

OUTER_STEP_02:
  U=4.879690..8.379690, Y=17.5..22.0, cut 4.5, orientation Y
```

### 8.3 Seven posts per side

Local plan footprints:

```text
STATION16_INNER: U=1.75..5.25, Y=15.0..16.5
STATION16_OUTER: U=4.879690..8.379690, Y=16.75..18.25
STATION24_INNER: U=1.75..5.25, Y=23.0..24.5
STATION24_OUTER: U=4.879690..8.379690, Y=21.25..22.75
FRONT_INNER: U=1.0..2.5, Y=25.5..29.0
FRONT_OUTER: U=13.879690..15.379690, Y=25.5..29.0
FRONT_EDGE: U=21.0..22.5, Y=25.5..29.0
```

Viewer-left posts are 16.75 inches high. Viewer-right posts are 10.75 inches high. Every post must have full lower bearing, meaningful direct upper bearing, and a shared unobstructed vertical screw point through both frames. `FRONT_EDGE` has full lower bearing on the extended lower front rail and full upper bearing on the union of `FRONT_EDGE_LOAD_RAIL` over Y=25.5..28 and the upper front rail over Y=28..29.

### 8.4 Side support distance

The generator calculates distances against the actual finished quadrilateral and complete upper support-footprint union.

Current expected values:

- Rear seam to remaining frame: approximately 7.293904 inches.
- Interior plywood-to-frame support distance: below 16 inches.
- Front outer corner edge cantilever after the edge-support correction: approximately 6.020797 inches.

The rear/interior support metric must remain below 16 inches. `MAX_EDGE_CANTILEVER` is calculated and validated separately against the 6.25-inch geometric target; both the target and the current approximately 6.021-inch result remain `ENGINEER / FIELD VERIFY` and are not an approved load-bearing capacity. The forward-flare region is not tested for sill-nose clearance because no physical sill exists there.

## 9. Frame and post fastening

All side 2x4 cuts are `SQUARE / 90 DEGREE` and `PROVISIONAL / FIELD VERIFY`.

- Ordinary flat-frame joints: nominal 5-inch structural screws through the 3.5-inch rail dimension into the mating board, two per end only where validated.
- Post connections: nominal 3 to 3-1/8-inch structural screws through the 1.5-inch flat frame into each post.
- Predrilling and supplemental wood glue are specified.
- Drywall screws are prohibited.
- Baseline construction requires no angle brackets.

`SHORT_RAIL_SINGLE_SCREW_DETAIL` remains only on actual remaining rails shorter than 3 inches. In the current topology it applies to each upper `OUTER_STEP_03`:

- One predrilled nominal 5-inch structural screw per end.
- Opposing paths staggered laterally.
- Glue and clamp during assembly.
- No path collision, inadequate edge/end distance, blocked driver path, or protruding tip.

`ASSEMBLY_SEQUENCE_REQUIRED` remains only for the lower `OUTER_STEP_02` front-end joints:

1. Fasten lower `OUTER_STEP_02` to `TRANSVERSE_24`.
2. Install the lower front rail at Y=25.5..29.0.

Assembly-state driver access is validated before the front rail exists. Final-state validation permits boundary-only contact and prohibits volumetric overlap.

Each `FRONT_EDGE_LOAD_RAIL` receives `FRONT_EDGE_LOAD_RAIL_POST_SUPPORTED_DETAIL` metadata:

- Its full U/Y footprint bears directly on the added `FRONT_EDGE` post through the upper bearing union.
- Its front end meets the upper front rail at Y=28.
- One predrilled nominal 5-inch structural screw connects through the 3.5-inch front rail into the load-rail end.
- Wood glue and the securely attached deck supplement the joint.
- Validation checks edge distance, driver access, screw-tip containment, and absence of path collision.
- Connection capacity remains `ENGINEER / FIELD VERIFY`.

## 10. Module connections

The center structural frame ends at X=±29.5 while each side structural mating face begins at X=±30. Four 1/2-inch structural-plywood packers fill each 0.5-inch module gap without moving the finished seams:

```text
upper spine packer: 16.5 Y x 1.5 Z x 0.5 X
lower spine packer: 14.0 Y x 1.5 Z x 0.5 X
upper front-return packer: 3.5 Y x 1.5 Z x 0.5 X
lower front-return packer: 3.5 Y x 1.5 Z x 0.5 X
```

There are four packers per seam and eight total. Packers are preattached to the center frame with glue and short countersunk screws. The front-return packers are seam fillers only and receive no structural-connection credit.

The 0.5-inch packer thickness is nominal. Field-fit every packer to the measured assembled seam because actual structural-plywood thickness and the built module gap may differ from nominal; do not force a nominal sheet into a seam that validates differently in the field.

Exact positive-X seam packer envelopes are:

```text
upper spine: X=29.5..30.0, Y=11.5..28.0, Z=12.25..13.75
lower spine: X=29.5..30.0, Y=11.5..25.5, Z=0.0..1.5
upper front return: X=29.5..30.0, Y=28.0..31.5, Z=12.25..13.75
lower front return: X=29.5..30.0, Y=25.5..29.0, Z=0.0..1.5
```

Negative-X packers mirror these envelopes across X. Each packer receives two short countersunk holding screws plus glue before module assembly; these holding screws are not credited as the primary module connection.

The primary modeled connection at each seam is four nominal 3/8-inch by 9-inch through-bolts with washers and nuts:

- Two through the upper overlapping center outside member / 0.5-inch packer / side inner spine at Y approximately 12.75 and 20.0.
- Two through the corresponding lower members at the same Y positions.
- Four bolts per seam; eight bolts total.

Upper bolt center Z is 13.0 and lower bolt center Z is 0.75. Each modeled corridor includes the 7.5-inch wood stack, head/washer and nut/washer work zones, and at least 9 inches of straight insertion/removal space on the selected insertion side.

Bolt diameter, grade, washer size, tightening/torque, and structural capacity are `ENGINEER / FIELD VERIFY`.

`MODULE_CONNECTION_ASSEMBLY_SEQUENCE_REQUIRED` specifies:

1. Preattach packers to the center module.
2. Bring the unfinished structural modules together and clamp the seams.
3. Drill the full through-holes and install/tighten all module bolts.
4. Install any bracing component, deck, maple face, or finish nailer that would otherwise restrict wrench or insertion access only after the connection remains accessible or is complete.

Geometric validation requires:

- Clear drill path through all three wood layers.
- Hole centerlines remain within each member with reasonable modeled edge/end distances.
- Clear bolt-head access.
- Clear washer, nut, wrench, and socket access.
- A clear insertion/removal corridor for the approximately 9-inch bolt.
- No bracing panel or cleat blocks either side.
- No finish object is credited as a connector.
- Both module mating faces and the finished X=±30 seams remain buildable.

## 11. Structural plywood bracing

Bracing material is distinct from maple finish plywood:

`1/2-IN STRUCTURAL PLYWOOD — GRADE / FASTENING ENGINEER-FIELD VERIFY`

Each module has one continuous X-Z bracing panel and one continuous perpendicular Y-Z bracing panel. A panel may be interrupted only when geometry requires it; any interruption requires a validated continuous load path through framing and cleats.

### 11.1 Center bracing planes

- Rear transverse panel: X-Z plane immediately forward of the center rear structural row.
- Internal longitudinal panel: Y-Z plane inside one outside-member bay, clear of module mating faces.
- The planes meet through a common backed edge/cleat region or connect through common upper/lower framing so the load-path graph is continuous.

Nominal clear panel regions used to seed geometry are:

```text
rear transverse panel: X=-29.5..29.5, Y=8.0..8.5, Z=1.5..12.25
internal longitudinal panel: X=-26.0..-25.5, Y=8.5..25.5, Z=1.5..12.25
```

Perimeter cleats adjust locally within the clear bays to provide continuous backing without intersecting posts or frames. Their final positions are geometry-derived and assertion-checked.

### 11.2 Side bracing planes

Each side uses:

- Longitudinal panel adjacent to, but not on, the module mating face of the inner-spine bay.
- Perpendicular panel near the forward structural stations.
- A common backed boundary/cleat connection between the two planes.

Nominal local clear regions used to seed geometry are:

```text
longitudinal panel: U=0.5..1.0, Y=17.5..25.0,
                    Z=1.5..upper-frame-bottom
forward transverse panel: U=0.5..15.379690, Y=25.0..25.5,
                          Z=1.5..upper-frame-bottom
```

The longitudinal panel remains 0.5 inch clear of the U=0 module mating face and avoids every post footprint. The transverse panel meets it at the Y=25 backed boundary and terminates against the front-post plane at Y=25.5. These panels do not use the field-templated deck as a vertical bracing element. The raised viewer-left plane heights are independently validated over its 16.75-inch cage.

### 11.3 Supported edges and cleats

Every panel edge has continuous backing:

- Top: upper frame or continuous cleat attached to it.
- Bottom: lower frame or continuous cleat attached to it.
- Vertical: post or continuous vertical cleat.

Square-cut perimeter cleats are structural bracing material, not finish nailers and not structural 2x4s. The geometry/contact graph requires:

- Panel-to-cleat continuous contact.
- Cleat-to-frame/post continuous contact.
- No unsupported panel edge.
- No finish-plywood dependency.
- Practical screw/driver access.
- No impossible intersections.
- Clear module-joining zones.
- No cleat protrusion into the visible floating-plinth opening.
- No interference with module-connection drill, bolt-insertion, head, washer, nut, wrench, or socket corridors.

## 12. Room reference and three independent sills

Room-reference geometry includes floor, 60-inch center wall, two measured angled walls terminating at the physical bay mouth, and three independent sill objects:

- `LEFT_WINDOW_SILL` on the positive-X measured wall.
- `CENTER_WINDOW_SILL` on the center wall.
- `RIGHT_WINDOW_SILL` on the negative-X measured wall.

Each sill has:

```text
bottom Z=15
top Z=16
thickness=1
projection=2.5 perpendicular inward from its wall
```

Side sills follow the measured 44.5-degree walls and terminate near Y=22.602037. The visualization-only 0.5-inch end gaps keep the three sill runs visibly separate at transitions and ends. Sills are reference objects and never drive framing or cut-list dimensions.

The measured region has a nominal 0.5-inch perpendicular horizontal gap between sill nose and finished daybed/cushion/landing rear boundary. Validation prohibits cushion/sill and landing/sill volume intersections.

## 13. Finish, faces, and shadow gap

- Horizontal decks: 3/4-inch light maple plywood.
- Visible faces: 1/2-inch maple finish plywood.
- Structural bracing: separate generic 1/2-inch structural plywood material.
- Center maple face: rectangular plan X=-30..30, Y=31.5..32, Z=3..13.75.
- Viewer-left maple face: field-templated trapezoidal plan from X=30..approximately 61.293456 at Y=31.5, flaring to X=62 at Y=32, Z=3..19.75.
- Viewer-right maple face: exact mirrored plan, Z=3..13.75.
- Every maple face reaches its deck underside only at a shared Z boundary; positive-volume face/deck overlap is prohibited.
- All angled outer finish edges remain `FIELD VERIFY / TEMPLATE TO ACTUAL ROOM`.
- Recessed lower-frame front edges align at Y=29.
- Upper structural front edges align at Y=31.5.
- Finished-face-to-lower-frame setback is exactly 3 inches.
- Structural upper-to-lower recess is exactly 2.5 inches.
- Finish nailers remain nonstructural and cannot bridge visibly to the recessed lower frame.

## 14. Collections and view layers

Required collections:

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
STRUCTURAL_BRACING_PANELS
STRUCTURAL_BRACING_CLEATS
PLYWOOD_DECKS
MAPLE_FINISH
FRONT_PANEL_NAILERS
CUSHION_REFERENCE
MODULE_CONNECTION_REFERENCE
MODULE_CONNECTION_PARTS
FASTENER_REFERENCE
DIMENSIONS
CAMERAS
```

View layers include at least `FRAMING_ONLY`, `BRACING_INSPECTION`, and `FINISHED`. Framing views hide finished plywood, maple faces, and cushion. Bracing inspection displays framing, bracing panels, and cleats while hiding finish objects.

## 15. Cameras and render inspection

Required cameras:

```text
V5_TOP_FRAMING
V5_TOP_FINISHED
V5_FRAMING_ISOMETRIC
V5_FINISHED_ISOMETRIC
V5_FRONT
V5_LEFT_RAISED_DETAIL
V5_RIGHT_FIT_DETAIL
V5_SILL_CLEARANCE_DETAIL
```

Required rendered inspections:

- Top framing: full side-board containment and square stepped topology.
- Top finished: measured rear offsets, bay-mouth breaks, forward flares, and common front.
- Framing isometric: posts, bracing planes, recessed lower frames, and module separation.
- Finished isometric: raised positive-X landing and one center/negative-X cushion.
- Front: one straight Y=32 front and 2-inch landing/cushion height difference.
- `V5_LEFT_RAISED_DETAIL`: positive-X viewer-left, 20.5-inch landing, 18.5-inch cushion top, visible 2-inch difference, no left cushion.
- `V5_RIGHT_FIT_DETAIL`: negative-X viewer-right, 14.5-inch deck, continuous center/right cushion, measured rear and field-templated flare geometry, front at Y=32 with no protrusion.
- `V5_SILL_CLEARANCE_DETAIL`: walls, separate sills, 3-inch measured-region setback, nominal 0.5-inch sill-nose gap, 14.5-inch deck, 18.5-inch cushion, and 20.5-inch raised landing where visible.

## 16. CSV output

Columns are exactly:

```text
MODULE
OBJECT
QUANTITY
CUT_LENGTH
CUT_TYPE
ORIENTATION
STATUS
NOTES
```

Sections distinguish:

1. Center structural 2x4s: `RESOLVED` after validation.
2. Side structural 2x4s: `PROVISIONAL / FIELD VERIFY`, every cut `SQUARE / 90 DEGREE`.
3. Structural bracing plywood and cleats: material, thickness, width, height, quantity, module, orientation, and `STRUCTURAL BRACING — ENGINEER / FIELD VERIFY` status.
4. Module-connection packers and nominal bolt references: quantities, dimensions, assembly sequence, and `ENGINEER / FIELD VERIFY` hardware qualification.
5. Field-templated finish plywood: `FIELD VERIFY / TEMPLATE TO ACTUAL ROOM`.

Bracing panels and cleats are not counted in structural 2x4 totals.

## 17. Fail-closed validation

Validation completes before any final V5 file is written. A mandatory failure:

- Prints `V5 VALIDATION CONFLICT` with the failing assertion and relevant object/dimension.
- Does not save `bay_daybed_v5.blend`.
- Does not write final CSV or dimensions files as successful artifacts.
- Is never downgraded to a warning.

Required assertions include:

### 17.1 Convention and quantities

- Positive-X module is the 20.5-inch raised landing with no cushion.
- Negative-X module is the 14.5-inch deck beneath the one center/right cushion.
- Exactly one cushion exists and covers center plus negative-X viewer-right only.
- Exactly three independent sill objects exist with exact required names.

### 17.2 Heights

- Center/right deck tops equal 14.5.
- Cushion Z=14.5..18.5 and thickness equals 4.
- Viewer-left top equals 20.5.
- Viewer-left is exactly 2 inches above cushion.
- Center/right post cuts equal 10.75.
- Viewer-left post cuts equal 16.75.
- Sills equal Z=15..16.

### 17.3 Center

- Upper bounds equal 59 x 27 x 1.5 at Y=4.5..31.5.
- Lower bounds equal 59 x 24.5 x 1.5 at Y=4.5..29.
- Counts equal 4 x 59, 5 x 20, 4 x 17.5, and 10 x 10.75.
- Center frame remains rectangular.
- Entire center structure lies beneath the center finished polygon.
- No center structural corner enters the 3-inch finished clearance envelope.
- Rear plywood cantilever is below 16.

### 17.4 Side framing

- Seven upper boards, five lower boards, and seven posts per side.
- No deleted rear object is present or referenced.
- Every 2x4 cut is square.
- Full convex footprint of every board lies within the revised side polygon.
- Rear/interior support distances remain below 16.
- Edge cantilever is calculated separately, remains at or below 6.25, and currently reports approximately 6.021 inches.
- `FRONT_EDGE_LOAD_RAIL` has direct post bearing and validated one-screw/glue/deck joint geometry without a capacity claim.
- Every post has full lower and meaningful upper bearing.
- Vertical screw paths and frame-joint driver corridors remain accessible.
- Lower `OUTER_STEP_02` assembly order is present and validated.
- Short-rail metadata appears only on actual remaining short rails.

### 17.5 Sills and finished geometry

- Side walls/sills terminate at the calculated bay mouth.
- Side sill orientation is 44.5 degrees.
- Projection equals 2.5 and end-gap metadata equals visualization-only 0.5.
- Measured-region finished offset equals 3 inches perpendicular to each wall.
- Measured-region sill-nose gap is nominally 0.5.
- Forward flare is excluded from sill-clearance assertions.
- No sill/cushion or sill/landing volumetric intersection exists.
- Every finished front reaches but never exceeds Y=32.
- Exact center and side maple face envelopes match Section 13 and touch deck undersides by boundary only.

### 17.6 Module connections

- Exactly eight 0.5-inch structural-plywood packers exist with the approved four-per-seam dimensions.
- Exactly eight nominal through-bolt references exist, four per seam.
- Spine packers fill the complete 0.5-inch structural gap without overlap.
- Front-return packers are explicitly non-primary seam fillers.
- Bolt holes pass through center member, packer, and side spine with modeled edge/end distances.
- Drill, insertion, head, washer/nut, wrench, and socket corridors are clear in the required assembly state.
- Bracing and finishes do not block connection assembly.
- `MODULE_CONNECTION_ASSEMBLY_SEQUENCE_REQUIRED` is present and enforced.
- Connection capacity remains explicitly not engineering-certified.

### 17.7 Bracing

- Every module has continuous X-Z and Y-Z bracing paths.
- Panel edges have continuous backing.
- Contact graph connects panel edges through cleats/posts to both frames.
- The two planes in each module tie through common supported framing/cleats.
- No cage direction remains an open unbraced rectangle.
- No bracing object depends on finish plywood.
- No bracing object intersects framing impossibly or blocks module joins.
- Cleat and panel screw access is practical.
- Raised viewer-left bracing passes independently.
- `GEOMETRIC RACKING PATH: PASS` appears only after every geometric bracing assertion passes.
- `STRUCTURAL CAPACITY: NOT ENGINEERING-CERTIFIED` always remains explicit.

## 18. Testing and independent verification

A new `test_bay_daybed_v5.py` provides the smallest durable regression harness and is not one of the four requested deliverables.

Verification includes:

1. Python syntax compilation.
2. Parameter and pure planar-geometry checks.
3. Center geometry/cut-count audit.
4. Side topology, containment, bearing, fastener, interior-span, and edge-cantilever audit.
5. Sill geometry and clearance audit.
6. Bracing contact-graph and supported-edge audit.
7. Complete generator run.
8. CSV/report contract checks.
9. Deliberate corruption cases covering reversed sides, missing cushion, missing sill, angled side cut, deleted-part reference, unsupported bracing edge, broken bracing direction, impossible overlap, blocked driver path, excessive interior span, excessive edge cantilever, missing packer, blocked bolt insertion/wrench access, and failed clearance.
10. Independent second Blender process reopening the saved `.blend` and recomputing bounds, counts, contacts, heights, convention, sill objects, camera transforms, and bracing continuity from saved objects.
11. Render and visual inspection of all required views, including left raised and right fit details.
12. Pre/post hashes proving V1–V4 files were unchanged.

## 19. Required printed summary

Successful generation prints:

```text
V5 FINAL NOMINAL HEIGHTS

CENTER/RIGHT WOOD DECK:
14.5"

CUSHION:
4.0"

CENTER/RIGHT FINISHED SEAT:
18.5"

VIEWER-LEFT RAISED LANDING:
20.5"

LEFT LANDING ABOVE CUSHION:
2.0"

SILL UNDERSIDE:
15.0"

SILL TOP:
16.0"

SILL PROJECTION:
2.5"

FINISHED REAR OFFSET FROM WALLS:
3.0"

NOMINAL CLEARANCE PAST SILL NOSE:
0.5"

CENTER NOMINAL USABLE DEPTH:
29.0"

VIEWER LEFT = RAISED 20.5-INCH WOOD LANDING, NO CUSHION.

VIEWER RIGHT = 14.5-INCH DECK UNDER THE SINGLE CENTER/RIGHT CUSHION.

V5 ACCOUNTS FOR THREE 2.5-INCH-DEEP WINDOW SILLS BY OFFSETTING THE FINISHED REAR GEOMETRY APPROXIMATELY 3 INCHES FROM ALL THREE WALL PLANES.

ALL FINISHED SIDE/REAR PLYWOOD REMAINS FIELD VERIFY / TEMPLATE TO ACTUAL ROOM.

MAXIMUM MODELED SIDE-DECK EDGE CANTILEVER: APPROXIMATELY 6.021 INCHES — GEOMETRIC TARGET ONLY; CAPACITY ENGINEER / FIELD VERIFY.

MODULE CONNECTIONS: EIGHT 1/2-INCH PACKERS AND EIGHT NOMINAL 3/8 X 9-INCH THROUGH-BOLTS — HARDWARE/CAPACITY ENGINEER / FIELD VERIFY.

GEOMETRIC RACKING PATH: PASS

STRUCTURAL CAPACITY: NOT ENGINEERING-CERTIFIED
```

## 20. Superseded V5 wording

Any earlier V5 text assigning negative X to viewer-left or positive X to viewer-right is superseded. Any requirement to preserve the V4 side `REAR_CLOSURE`, `OUTER_STEP_01`, or associated rear posts is superseded by the approved rear-station deletion. Obsolete fastener and validation rules for those nonexistent parts are removed rather than retained as dead metadata.
