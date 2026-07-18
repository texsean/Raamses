 // Premium Ramses CYD Enclosure
// High-end 3D printable case for Cheap Yellow Display (esp32-2432S028r)
CYD_W = 85;
CYD_H = 54;
WALL = 3.5;
CLR = 0.35;
BEV = 2.5;
$fn=64;

module body() {
  difference() {
    // Outer premium beveled body
    minkowski() {
      cube([CYD_W + WALL*2 + 6, CYD_H + WALL*2 + 6, 20], center=true);
      cylinder(r=BEV, h=BEV);
    }
    // Board cavity
    translate([0,0,2]) cube([CYD_W+CLR*2, CYD_H+CLR*2, 22], center=true);
    // Screen cutout
    translate([-20, -10, -11]) cube([60, 45, 8]);
    // Buttons
    for(y=[-15,0,15]) translate([CYD_W/2 - 2, y, -9]) cylinder(d=8, h=15);
    // Vents
    for(i=[-3:3]) {
      translate([-CYD_W/2-2, i*9, 0]) cube([5,3,10], center=true);
      translate([CYD_W/2 -1 , i*9-4, 0]) cube([5,3,10], center=true);
    }
    // Cable slot
    translate([0, -CYD_H/2 -3 , -4]) cube([15, 8, 8], center=true);
    // Logo recess on back
    translate([0,0,9]) linear_extrude(2) scale([0.8,0.8]) import("/c/Users/seanr/Projects/Ramses/CYD-Ramses/ramses-logo.svg", center=true);
  }
}

module stand() {
  difference() {
    cube([100, 70, 5]);
    translate([30,10,-1]) cube([40,8,12]); // slot for body
  }
  translate([20,15,5]) rotate([60,0,0]) cube([60,5,45]);
}

body();
translate([0,-100,0]) stand();

// See accompanying README.md for full instructions, variants, and printing guide.
