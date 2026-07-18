#!/usr/bin/env python3
"""
Ramses Virtual Client Simulator
Emulates different device sizes, configurations, data modes for testing.
TDD-driven implementation for Sprint 1 CYD POC.
"""

import json
import time
import random
import copy
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class DisplayType(Enum):
    EPAPER = "ePaper"
    LCD = "LCD"
    CYD = "CYD"


class DataMode(Enum):
    DUMMY = "dummy"
    REAL = "real"


class Tier(Enum):
    FREE = "free"
    PAID = "paid"


@dataclass
class ScreenProfile:
    inches: float
    width: int
    height: int
    dpi: int
    color_mode: str
    display_type: DisplayType
    refresh_ms: int


class VirtualClient:
    """Virtual client simulator for Ramses system."""
    
    # Track active instances for monetization
    _active_instances: Dict[str, int] = {"free": 0, "paid": 0}
    _max_free_instances = 1
    
    STANDARD_PROFILES = {
        1.5: ScreenProfile(1.5, 200, 200, 200, "1-bit", DisplayType.EPAPER, 500),
        2.8: ScreenProfile(2.8, 320, 240, 120, "16-bit", DisplayType.CYD, 100),
        4.0: ScreenProfile(4.0, 480, 320, 140, "16-bit", DisplayType.LCD, 50),
        7.0: ScreenProfile(7.0, 800, 480, 130, "24-bit", DisplayType.LCD, 16),
    }
    
    def __init__(self, screen_size_inches: float = 2.8, config: Optional[Dict] = None, 
                 tier: str = "free", data_mode: str = "dummy"):
        """Initialize virtual client with screen params."""
        if tier not in [t.value for t in Tier]:
            raise ValueError(f"Invalid tier: {tier}")
        if data_mode not in [m.value for m in DataMode]:
            raise ValueError(f"Invalid data_mode: {data_mode}")
        
        self.screen_size_inches = screen_size_inches
        self.tier = Tier(tier)
        self.data_mode = DataMode(data_mode)
        self.config = config or {}
        self.instance_id = f"{tier}-{int(time.time())}"
        
        # Enforce monetization limits
        self._enforce_tier_limits()
        
        # Load profile
        self.profile = self._get_screen_profile()
        
        # Merge config
        self._apply_config()
        
        # State
        self.is_connected = True
        self.battery_level = 100
        self.current_data = {}
        self.framebuffer = None  # Simulated display buffer
        
        VirtualClient._active_instances[self.tier.value] += 1
        print(f"Initialized {self.tier.value.upper()} tier virtual client for {screen_size_inches}\" {self.profile.display_type.value}")
    
    def _enforce_tier_limits(self):
        """Enforce free tier limit of 1 instance."""
        current_count = VirtualClient._active_instances.get(self.tier.value, 0)
        if self.tier == Tier.FREE and current_count >= VirtualClient._max_free_instances:
            raise RuntimeError("Free tier limited to 1 active instance. Upgrade to paid for more.")
    
    def _get_screen_profile(self) -> ScreenProfile:
        """Get or interpolate screen profile for given size. Returns fresh copy each time."""
        if self.screen_size_inches in self.STANDARD_PROFILES:
            # Return a copy to prevent mutation of shared profiles
            return copy.deepcopy(self.STANDARD_PROFILES[self.screen_size_inches])
        
        # Interpolate for dynamic sizes (simple linear for POC)
        sizes = sorted(self.STANDARD_PROFILES.keys())
        for i in range(len(sizes) - 1):
            if sizes[i] < self.screen_size_inches < sizes[i+1]:
                # For POC, snap to nearest
                nearest = min(sizes, key=lambda x: abs(x - self.screen_size_inches))
                return copy.deepcopy(self.STANDARD_PROFILES[nearest])
        
        if self.screen_size_inches < 1.0 or self.screen_size_inches > 10.0:
            raise ValueError(f"Unsupported screen size: {self.screen_size_inches}\". Range: 1.5\" to 7\".")
        return copy.deepcopy(self.STANDARD_PROFILES[2.8])  # Default to CYD
    
    def _apply_config(self):
        """Apply and validate configuration."""
        default_config = {
            "theme": "default",
            "update_interval": 30,
            "widgets": ["weather", "notifications", "status"],
            "orientation": "portrait"
        }
        self.config = {**default_config, **self.config}
        
        # Validate required fields
        if "resolution" in self.config:
            res = self.config["resolution"]
            if isinstance(res, str) and 'x' in res:
                w, h = map(int, res.split('x'))
                self.profile.width = w
                self.profile.height = h
    
    def get_display_info(self) -> Dict[str, Any]:
        """Return current display configuration."""
        return {
            "screen_size_inches": self.screen_size_inches,
            "resolution": f"{self.profile.width}x{self.profile.height}",
            "dpi": self.profile.dpi,
            "color_mode": self.profile.color_mode,
            "display_type": self.profile.display_type.value,
            "tier": self.tier.value,
            "data_mode": self.data_mode.value,
            "instance_id": self.instance_id
        }
    
    def fetch_data(self) -> Dict[str, Any]:
        """Fetch data based on mode (dummy vs real)."""
        if self.data_mode == DataMode.DUMMY:
            return self._get_dummy_data()
        else:
            return self._get_real_data()
    
    def _get_dummy_data(self) -> Dict[str, Any]:
        """Consistent dummy data for testing."""
        return {
            "weather": {
                "temp": 72,
                "condition": "sunny",
                "humidity": 45
            },
            "notifications": [
                {"id": 1, "title": "Test Alert", "message": "This is dummy data"},
                {"id": 2, "title": "System Status", "message": "All good"}
            ],
            "status": {
                "battery": self.battery_level,
                "connected": self.is_connected,
                "uptime": "2h 15m"
            },
            "timestamp": "2026-07-04T12:00:00"
        }
    
    def _get_real_data(self) -> Dict[str, Any]:
        """Simulate real data with latency and variability."""
        time.sleep(0.05)  # Simulate network latency
        data = self._get_dummy_data()
        # Add variability
        data["weather"]["temp"] = random.randint(60, 85)
        data["weather"]["condition"] = random.choice(["sunny", "cloudy", "rainy"])
        data["notifications"].append({
            "id": 3, 
            "title": "Live Update", 
            "message": f"Real data at {time.strftime('%H:%M:%S')}"
        })
        return data
    
    def render(self, data: Optional[Dict] = None) -> str:
        """Simulate rendering to virtual display. Returns ASCII preview."""
        if data is None:
            data = self.fetch_data()
        self.current_data = data
        
        # Simulate framebuffer size
        width = min(self.profile.width, 40)  # Limit for text preview
        height = min(self.profile.height // 20, 20)  # Rough scaling
        
        preview = [
            f"Ramses Virtual Display: {self.screen_size_inches}\" {self.profile.display_type.value}",
            f"Resolution: {self.profile.width}x{self.profile.height} | Mode: {self.data_mode.value.upper()} | Tier: {self.tier.value.upper()}",
            "=" * width,
            f"Weather: {data.get('weather', {}).get('temp', 0)}°F - {data.get('weather', {}).get('condition', 'N/A')}",
            f"Notifications: {len(data.get('notifications', []))} alerts",
            f"Battery: {data.get('status', {}).get('battery', 100)}% | Connected: {data.get('status', {}).get('connected', True)}",
            "-" * width,
            "Layout adapted for screen size. (Simulated framebuffer)",
            " " * (width // 2) + "[ VIRTUAL SCREEN ]",
            "=" * width
        ]
        
        # Add size-specific notes
        if self.screen_size_inches <= 2.0:
            preview.insert(3, "NOTE: Compact ePaper layout - minimal widgets")
        elif self.screen_size_inches >= 5.0:
            preview.insert(3, "NOTE: Rich layout with images and multiple columns")
        
        self.framebuffer = "\n".join(preview)
        return self.framebuffer
    
    def simulate_input(self, event_type: str, payload: Dict = None) -> str:
        """Simulate user input or events."""
        payload = payload or {}
        if event_type == "button_press":
            return f"Processed {payload.get('button', 'unknown')} on {self.screen_size_inches}\" screen"
        elif event_type == "touch":
            return f"Touch at ({payload.get('x', 0)}, {payload.get('y', 0)}) - handled for larger display"
        return "Event processed"
    
    def update_config(self, new_config: Dict) -> bool:
        """Hot update configuration."""
        self.config.update(new_config)
        self._apply_config()
        return True
    
    def cleanup(self):
        """Cleanup instance and decrement counter."""
        if self.tier.value in VirtualClient._active_instances:
            VirtualClient._active_instances[self.tier.value] -= 1
        print(f"Cleaned up instance {self.instance_id}")


# Factory for easy testing
def create_virtual_client(screen_size: float = 2.8, tier: str = "free", data_mode: str = "dummy", **kwargs):
    """Factory function for creating configured clients."""
    return VirtualClient(screen_size_inches=screen_size, tier=tier, data_mode=data_mode, **kwargs)


if __name__ == "__main__":
    # Demo
    client = create_virtual_client(2.8, tier="free", data_mode="dummy")
    print(client.get_display_info())
    print("\nRender output:")
    print(client.render())
    client.cleanup()
