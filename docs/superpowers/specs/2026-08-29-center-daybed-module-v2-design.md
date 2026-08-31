# Center Daybed Module V2 Design

## Scope and Deliverables

Build a new center-module construction model without reading, modifying, or inheriting V1 geometry. Generate `center_daybed_module_v2_generator.py`, `center_daybed_module_v2.blend`, `center_daybed_module_v2_cutlist.csv`, and `center_daybed_module_v2_dimensions.txt`. Do not create the future angled side modules.

## Coordinates and Units

- One Blender unit represents one inch.
- X is left/right, Y is rear/front, and Z is vertical.
- Both frame rear edges are Y = 0; the structure extends toward positive Y.
- Floor elevation is Z = 0.
- Structural width is exactly 59 inches, centered on X = 0, within a 60-inch-wide reference wall.

## Structural Geometry

Every board is a separate named object with purpose, dimensions, cut length, and stock metadata. Nominal 2x4 stock is actual 1.5 by 3.5 inches.

### Flat Upper Frame

- Z range: 8.25 to 9.75 inches.
- Rear and front rails: two boards, each 59 X by 3.5 Y by 1.5 Z inches, at Y = 0–3.5 and Y = 28–31.5.
- Front-to-back members: five boards, each 3.5 X by 24.5 Y by 1.5 Z inches, spanning Y = 3.5–28.
- X centerlines: -27.75, -13.875, 0, 13.875, and 27.75 inches.
- The outside dimensions are exactly 59 by 31.5 by 1.5 inches.

### Flat Lower Frame

- Z range: 0 to 1.5 inches.
- Rear and front rails: two boards, each 59 X by 3.5 Y by 1.5 Z inches, at Y = 0–3.5 and Y = 25.5–29.
- Front-to-back members: four boards, each 3.5 X by 22 Y by 1.5 Z inches, spanning Y = 3.5–25.5.
- X centerlines: -27.75, -9.25, 9.25, and 27.75 inches.
- The outside dimensions are exactly 59 by 29 by 1.5 inches.
- Its rear aligns with the upper frame; its front is exactly 2.5 inches behind the upper front.

### Vertical Posts

- Ten boards, each 3.5 X by 1.5 Y by 6.75 Z inches, spanning Z = 1.5–8.25.
- Both rows use X = -27.75, -13.875, 0, 13.875, and 27.75 inches.
- Rear post centers use Y = 1.75; their footprints lie fully on the lower rear rail and fully beneath the upper rear rail.
- Front post centers use Y = 27.25; their footprints are Y = 26.5–28, fully on the lower front rail and fully below the front ends of the five upper front-to-back members.
- The outer post footprints end exactly at X = +/-29.5 and do not exceed the structural envelope.

## Finish Geometry

- Maple deck: 60 X by 32 Y by 0.75 Z inches, spanning Y = -0.5–31.5 and Z = 9.75–10.5. Name: `CENTER_DECK_0.75_MAPLE`.
- Maple front panel: approximately 60 X by 0.5 Y by 7.5 Z inches, spanning Y = 31.5–32 and Z = 3–10.5.
- The panel remains physically and visually independent of the recessed lower frame, preserving the 3-inch floor shadow gap.

## Front Panel Nailers

Nailers are nonstructural, excluded from the 2x4 cut list, and remain entirely behind the panel and above the recessed lower-frame area.

- One approximate nominal 1x3 lower nailer: 59 X by 2.5 Y by 0.75 Z inches, spanning Y = 29–31.5 and approximately Z = 3.5–4.25.
- Five approximate 3/4-inch plywood vertical strips: 2.5 X by 0.75 Y by 4 Z inches, centered on the five upper-frame X centerlines, spanning Y = 30.75–31.5 and Z = 4.25–8.25.
- The vertical strips terminate against the lower nailer and the underside of the upper front rail without volumetric overlap.
- No nailer contacts or bridges to the lower frame.

## Joinery and Construction Notes

- Flat-frame 90-degree joints: approximately 5 to 5-1/8-inch structural wood screws driven horizontally through the 3.5-inch-deep rail into member ends; use two per joint where practical and predrill.
- Post connections: approximately 3 to 3-1/8-inch structural wood screws driven vertically through the 1.5-inch-thick flat frame into posts.
- Wood glue may supplement both connection types.
- Do not use drywall screws. Metal angle brackets are not required in the baseline V2 design.
- Store these notes as readable Blender text objects and in the generated dimensions text file.

## Presentation

- Collections: `ROOM_REFERENCE`, `UPPER_FRAME_FLAT_2X4`, `LOWER_FRAME_FLAT_2X4`, `VERTICAL_POSTS`, `PLYWOOD_DECK`, `FRONT_PANEL_NAILERS`, `MAPLE_FINISH`, `DIMENSIONS`, and `CAMERAS`.
- Materials: natural framing lumber, light maple, off-white wall, neutral wood floor, and dark annotation material.
- Cameras: `TOP_ORTHO`, `FRONT`, `SIDE`, `ISOMETRIC_FRAMING`, and `ISOMETRIC_FINISHED`.
- A framing view layer excludes the finish collections and clearly exposes both flat frames, all posts, and the 2.5-inch front recess.
- Use a clear technical Workbench presentation rather than photoreal rendering.

## Cut List

The structural 2x4 CSV contains purpose rows totaling exactly:

- 4 at 59 inches: two upper and two lower front/rear rails.
- 5 at 24.5 inches: two upper outside members and three upper interior crossmembers.
- 4 at 22 inches: two lower outside members and two lower interior crossmembers.
- 10 at 6.75 inches: five rear and five front vertical posts.

Nailers are excluded.

## Generator and Validation

The self-contained generator clears the scene, constructs V2 from literal specification constants, writes both text exports, validates, prints the full report before saving, and saves the V2 blend beside the script.

Validation must assert:

- Exact upper/lower outside bounds, member dimensions, flat 1.5-inch frame height, counts, purposes, and cut lengths.
- Aligned rear edges and exact 2.5-inch front recess.
- Exactly ten 6.75-inch posts in two exact five-position rows, within the 59-inch envelope and Z = 1.5–8.25.
- Full rear-post bearing between aligned rear rails.
- Full front-post bearing on the lower front rail and beneath matching upper front-to-back members; no unsupported post tops.
- Upper frame Z = 8.25–9.75; deck Z = 9.75–10.5; finished deck height = 10.5.
- No positive-volume intersections between structural lumber; shared bearing faces are allowed.
- Exact cut totals: 4 x 59, 5 x 24.5, 4 x 22, and 10 x 6.75 inches.

If any assertion fails, generation stops before either text export or the blend is saved.

## Verification

A small end-to-end test runs Blender headlessly and checks the V2 validation marker and all four requested artifacts. Final verification reopens the saved blend, independently audits board counts, bounds, bearing/contact, and cut totals, then render-checks the finished, framing, and dimensioned views.
