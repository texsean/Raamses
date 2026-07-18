#!/usr/bin/env python3
"""
RAAMSES Software Console Emulator
Configurable via XML config file to simulate different hardware (e-paper, CYD, desktop).
Used for unit testing without physical devices.
"""
import sys
import xml.etree.ElementTree as ET
from tkinter import Tk, Canvas, Label, Frame, ttk
from pathlib import Path

class SoftwareConsole:
    def __init__(self, config_path="configs/epaper-1.5inch.xml"):
        self.root = Tk()
        self.root.title("RAAMSES Software Console Emulator")
        
        tree = ET.parse(config_path)
        self.capabilities = {elem.tag: elem.text for elem in tree.iter() if elem.text}
        
        self.width = int(self.capabilities.get("WidthPixels", 320))
        self.height = int(self.capabilities.get("HeightPixels", 240))
        self.display_type = self.capabilities.get("DisplayType", "LCD")
        
        self.root.geometry(f"{self.width}x{self.height+100}")
        
        Label(self.root, text=f"RAAMSES {self.display_type} Emulator", font=("Arial", 14, "bold")).pack()
        Label(self.root, text=f"Config: {Path(config_path).name} | Size: {self.width}x{self.height}", font=("Arial", 10)).pack()
        
        self.canvas = Canvas(self.root, width=self.width, height=self.height, bg="black" if self.display_type == "EPaper" else "darkblue")
        self.canvas.pack(pady=10)
        
        self.status_label = Label(self.root, text="Waiting for messages...", fg="lime", bg="black")
        self.status_label.pack()
        
        self.draw_mock_display()
        
    def draw_mock_display(self):
        self.canvas.delete("all")
        if self.display_type == "EPaper":
            self.canvas.create_rectangle(10, 10, self.width-10, self.height-10, outline="white", width=2)
            self.canvas.create_text(self.width//2, self.height//2, text="RAAMSES\nE-PAPER\nSIMULATOR", fill="white", font=("Courier", 12, "bold"))
        else:
            self.canvas.create_text(self.width//2, self.height//2, text="RAAMSES\nLIVE CONSOLE\nSIMULATOR", fill="cyan", font=("Arial", 16, "bold"))
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    config = sys.argv[1] if len(sys.argv) > 1 else "configs/epaper-1.5inch.xml"
    app = SoftwareConsole(config)
    app.run()
