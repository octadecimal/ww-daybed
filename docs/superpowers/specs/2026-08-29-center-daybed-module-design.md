# Center Daybed Module Design

## Scope

Generate only the 60-inch-wide center module of the future three-module daybed. The deliverables are `center_daybed_module_generator.py`, `center_daybed_module.blend`, and `center_daybed_2x4_cutlist.csv`.

## Coordinate System and Units

- Model dimensions are inches, with Blender's scene unit scale set so one Blender unit equals one inch.
- X is left/right, Y is rear/front, and Z is vertical.
- Floor elevation is Z = 0.
- Structural frames are centered on X = 0.
- Upper and lower frame rear edges are Y = 0.
- Upper front edge is Y = 31.5; lower front edge is Y = 29, producing the exact 2.5-inch recess.

## Structural Geometry

All nominal 2x4 pieces use actual 1.5-by-3.5-inch sections and remain separate, clearly named objects.

### Upper Frame

- Two 59-inch rails: X = 59, Y = 1.5, Z = 3.5; centers Y = 0.75 and 30.75, Z = 8.
- Five 28.5-inch front-to-back members: X = 1.5, Y = 28.5, Z = 3.5; center Y = 15.75, Z = 8.
- Member centerlines: X = -28.75, -14.375, 0, 14.375, and 28.75.
- The frame spans Z = 6.25 through 9.75 and measures exactly 59 by 31.5 inches outside.

### Lower Frame

- Two 59-inch rails: X = 59, Y = 1.5, Z = 3.5; centers Y = 0.75 and 28.25, Z = 1.75.
- Four 26-inch front-to-back members: X = 1.5, Y = 26, Z = 3.5; center Y = 14.5, Z = 1.75.
- Outside members use X = -28.75 and 28.75; interior braces use X = -14.375 and 14.375.
- The frame spans Z = 0 through 3.5 and measures exactly 59 by 29 inches outside.

### Riser Blocks

- Eight 2.75-inch risers replace the rejected full-height legs.
- Each riser is X = 3.5, Y = 1.5, Z = 2.75 and spans Z = 3.5 through 6.25.
- X positions are -28.75, -14.375, 14.375, and 28.75.
- Rear risers use Y = 0.75 and bear on the lower rear rail.
- Front risers use Y = 28.25 and bear on the recessed lower front rail.
- Boundary faces may coincide at Z = 3.5 and Z = 6.25; volumes must not overlap.
- The upper frame bears directly on the riser tops through its rails or front-to-back members.

## Finish Geometry

- Deck: one 60-by-32-by-0.75-inch maple object spanning Z = 9.75 through 10.5. It spans Y = -0.5 through 31.5, leaving its front face available for the fascia without overlap.
- Front panel: one 60-by-0.5-by-7.5-inch maple object spanning Y = 31.5 through 32 and Z = 3 through 10.5.
- The panel's bottom is exactly 3 inches above the floor; its top is flush with the deck top.
- The resulting cushion top reference is approximately Z = 14.5, below the approximate sill underside at Z = 15.

## Front Panel Nailers

Use a dedicated `FRONT_PANEL_NAILERS` collection. Nailers are nonstructural and excluded from the 2x4 cut list.

- Several short vertical 3/4-inch plywood strips hang below the upper front rail and provide panel attachment points.
- One light horizontal lower nailer supports the panel's lower edge.
- Nailer widths/spacing are visualization dimensions and will be explicitly labeled approximate in object metadata.
- Nailers terminate against adjacent pieces rather than overlap them volumetrically.

## Reference Geometry and Presentation

- Collections: `ROOM_REFERENCE`, `UPPER_2X4_FRAME`, `LOWER_2X4_FRAME`, `VERTICAL_LEGS`, `PLYWOOD_DECK`, `FRONT_PANEL_NAILERS`, `MAPLE_FINISH`, and `DIMENSIONS`. `VERTICAL_LEGS` retains the requested collection name but contains the revised risers.
- A 60-inch-wide wall is centered behind the module. Its unspecified height/thickness and the floor extent are explicitly approximate reference dimensions.
- Materials are simple natural framing lumber, light maple, off-white wall, and neutral flooring.
- Cameras: `TOP_ORTHO`, `FRONT`, `SIDE`, `ISOMETRIC_FINISHED`, and `ISOMETRIC_FRAMING`.
- The framing view uses a framing view layer that excludes finish collections so the upper frame, recessed lower frame, risers, and 2.5-inch recess remain visible.
- Dimension annotations cover every practical requested measurement, including the approximate sill elevation.

## Generator and Validation

The single Python generator clears the scene, creates materials/collections/objects, adds annotations and cameras, writes the CSV, validates the scene, prints a readable dimensional summary, and saves the `.blend` beside the script.

Validation uses object dimensions and axis-aligned bounding boxes to assert:

- Exact upper and lower outside dimensions and the exact 2.5-inch recess.
- Exact Z ranges for the lower frame, risers, upper frame, and deck.
- No positive-volume overlap among structural 2x4 objects; shared boundary faces are allowed.
- Exactly three upper interior crossmembers, two lower interior crossmembers, and eight risers.
- Exact structural cut-list totals: four at 59 inches, five at 28.5 inches, four at 26 inches, and eight at 2.75 inches.
- The CSV breaks pieces out by purpose and excludes nailers.

Blender 5.2 will run the generator headlessly. Verification includes checking the process exit status, reopening the saved `.blend` headlessly for a second validation pass, and rendering representative finished/framing views for visual inspection.
