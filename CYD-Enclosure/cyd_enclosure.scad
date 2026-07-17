// CYD (Cheap Yellow Display) Enclosure for Ramses Monitor
// Simple parametric box with screen cutout, button holes, and speaker grille
// Dimensions based on esp32-2432S028r (approx 72x50mm board)

$fn = 50; // Smoothness

// Board dimensions
board_width = 72;
board_height = 50;
board_thickness = 2;
wall_thickness = 2.5;
clearance = 0.5;

// Enclosure outer dimensions
enclosure_width = board_width + 2*wall_thickness + 2*clearance;
enclosure_height = board_height + 2*wall_thickness + 2*clearance;
enclosure_depth = 18; // Height of the box

// Screen cutout (1.54" ~ 35x35mm visible area, centered)
screen_width = 36;
screen_height = 36;
screen_x = (enclosure_width - screen_width)/2;
screen_y = (enclosure_height - screen_height)/2 + 4; // Slightly offset toward top

// USB cutout
usb_width = 12;
usb_height = 6;
usb_x = 8;
usb_y = -1;

// Button holes (BOOT and RESET)
button_diameter = 6;

difference() {
    // Main enclosure body
    cube([enclosure_width, enclosure_height, enclosure_depth]);
    
    // Hollow inside for the board
    translate([wall_thickness, wall_thickness, board_thickness])
        cube([board_width + clearance*2, board_height + clearance*2, enclosure_depth]);
    
    // Screen cutout
    translate([screen_x, screen_y, -1])
        cube([screen_width, screen_height, enclosure_depth+2]);
    
    // USB port cutout
    translate([usb_x, -1, 6])
        cube([usb_width, wall_thickness+2, usb_height]);
    
    // BOOT button hole
    translate([12, 12, -1])
        cylinder(h = enclosure_depth+2, d = button_diameter);
    
    // RESET button hole
    translate([enclosure_width-15, 12, -1])
        cylinder(h = enclosure_depth+2, d = button_diameter);
    
    // Speaker grille (simple slots)
    for (i = [0:4]) {
        translate([enclosure_width-22, 28 + i*4, -1])
            cube([12, 2, enclosure_depth+2]);
    }
}

// Lid mounting tabs (simple)
translate([5, 5, enclosure_depth-2]) cube([8, 8, 2]);
translate([enclosure_width-13, 5, enclosure_depth-2]) cube([8, 8, 2]);
translate([5, enclosure_height-13, enclosure_depth-2]) cube([8, 8, 2]);
translate([enclosure_width-13, enclosure_height-13, enclosure_depth-2]) cube([8, 8, 2]);

echo("CYD Enclosure generated. Dimensions: ", enclosure_width, "x", enclosure_height, "x", enclosure_depth);
echo("Open in OpenSCAD and export as STL.");
