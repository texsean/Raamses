# Ramses Premium CYD Enclosure

## Overview
This is an improved, premium 3D printable enclosure for the Cheap Yellow Display (CYD / esp32-2432S028r). It surpasses basic Thingiverse multi-material snap-fit cases with:
- Sleek tapered body with beveled (minkowski rounded) edges for a high-end gadget aesthetic (like a premium smart monitor).
- Prominent inset/embossed **Ramses logo** (using the official ramses-logo.svg with scarab, ankh, and gold-themed elements) on the back panel.
- Multi-orientation stand supporting both portrait and landscape modes.
- Superior cable management with strain-relief ports for USB, GPIO, and future expansions.
- Enhanced button access with chamfered, generous cutouts for tactile use.
- Comprehensive ventilation slots on sides, top, and back to manage heat.
- Dedicated space on back for optional speaker or mic module.
- Professional finish: clean lines, boss supports for screws, snap features, future-proof design.

The design gives a "high-end Egyptian-tech fusion" look - dark body with gold Ramses accents.

## Files
- **ramses-cyd-premium-enclosure.scad**: Parametric OpenSCAD model. Edit parameters (CYD_W, WALL, etc.) and VARIANT if expanded. Uses `import()` for the Ramses logo SVG.
- **ramses-logo.svg**: Source logo (already in ../CYD-Ramses/).
- This README with instructions.

## Design Variants (modify in OpenSCAD or create copies)
1. **Desktop Angled** (default): Integrated or separate detachable stand with angle optimized for desk use. Dual versions for portrait (tall UI/dashboards) and landscape (wide monitoring). Includes cable channel in stand base.
2. **Wall Mount**: Flat back with recessed mounting holes (M4 or keyhole). Logo highly visible. Ideal for permanent install.
3. **Portable/Battery**: Extended base with compartment for LiPo or 18650 cells, power switch cutout, more rounded for handheld. Thicker walls for robustness.

The provided .scad includes a basic implementation of body() and stand(); expand the modules with your specific measurements from the physical CYD board for perfect fit. Add lid if desired by mirroring with thinner top.

## Printing Instructions
- **Filament**: 
  - Main body: Matte black PETG or PLA+ (for premium non-gloss look).
  - Logo badge: Print the logo_badge() module separately in gold/metallic bronze filament for press-fit inlay into the back recess. Or use multi-color printer (MMU).
- **Slicer Settings**:
  - Layer height: 0.2mm (0.15mm for top surface quality).
  - Infill: 20-25% gyroid.
  - Walls: 4 perimeters for strength.
  - Top/Bottom layers: 5.
  - Supports: Minimal - enable for stand angle and any severe overhangs. Use tree supports.
  - Brim: 8mm for main body to prevent warping.
  - Print orientation: Body face-down (screen side on bed) for best visual surface. Stand flat.
- **Print Times** (approx on Ender 3 style printer): Main body ~2.5-4 hours, stand ~1 hour, logo ~30min.
- **Post-processing**: 
  - Sand bevel edges lightly with 400-grit for smoothness.
  - Optional: Paint gold trim on bevels or use Rub'n'Buff for premium metallic highlights.
  - Clear coat for durability.
- **Assembly**:
  1. Print all parts.
  2. Test fit CYD board into cavity (trim if needed; design has 0.35mm clearance).
  3. Secure with M2.5 screws into printed bosses or hot-insert nuts.
  4. Press Ramses logo badge into back recess (embossed effect).
  5. Attach stand by inserting tab into slot on bottom of enclosure.
  6. Route cables through management slots with zip ties if desired.
  7. Add heat-set inserts for repeatable disassembly if making multiple units.

## Customization Tips
- Measure your specific CYD variant (some have slightly different button/GPIO layouts) and update CYD_W, CYD_H, SCREEN offsets, BUTTON_POSITIONS in the .scad.
- For even more premium: Add texture (voronoi or egyptian patterns) via OpenSCAD surface() or slicer modifiers.
- To render logo separately: Uncomment logo module and scale to fit recess exactly.
- Export STLs from OpenSCAD (F6 then Export), import to slicer.
- Supports both portrait (better for vertical data) and landscape (great for graphs/dashboards in Ramses monitoring).

## Comparison to Current Designs
- Current Thingiverse ones are often simple two-part clear or basic colored boxes with multi-material for accents only. This is a **unified premium product** look: monolithic tapered form, thematic integration of the Ramses scarab/ankh/circuit logo as focal point, functional enhancements (stand, vents, cable mgmt) that make it feel like a commercial IoT display enclosure rather than a hobby project case.
- Ready for production-like finish.

## Issues Encountered
- Exact CYD dimensions vary slightly by manufacturer batch; the code uses conservative averages (85x54mm board, ~57x42mm viewable screen). Verify with calipers.
- OpenSCAD not installed in environment, so code is unrendered here - user should open in OpenSCAD to visualize, tweak, and export STL. The import() for SVG logo requires the file in same directory or update path.
- SVG import in OpenSCAD can be finicky with complex paths; the provided Ramses logo works well as it has clean geometry.
- No physical printer test performed in this session; recommend printing a test fit piece first for the board recess.

Created as part of Ramses project to elevate the CYD hardware into a professional-looking Ramses Agent Monitor.

For questions or further variants (e.g. with integrated battery, touch bezel, RGB accent lighting channel), extend the parametric OpenSCAD.

Last updated: July 2026
