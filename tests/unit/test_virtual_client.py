#!/usr/bin/env python3
"""
Unit Tests for Ramses Virtual Client Simulator
TDD approach: Tests define the expected behavior for screen sizes,
configurations, data modes, and monetization.
"""

import unittest
import time
from tests.simulator.virtual_client_simulator import (
    VirtualClient, create_virtual_client, 
    DisplayType, DataMode, Tier, ScreenProfile
)


class TestVirtualClient(unittest.TestCase):
    """Comprehensive test suite for VirtualClient."""
    
    def setUp(self):
        """Reset instance counters before each test."""
        VirtualClient._active_instances = {"free": 0, "paid": 0}
    
    def test_screen_size_profiles(self):
        """Test dynamic screen sizes from 1.5\" ePaper to 7\"."""
        # Standard sizes
        client_15 = create_virtual_client(1.5, tier="free")
        self.assertEqual(client_15.profile.inches, 1.5)
        self.assertEqual(client_15.profile.display_type, DisplayType.EPAPER)
        self.assertEqual(client_15.profile.color_mode, "1-bit")
        
        client_cyd = create_virtual_client(2.8, tier="paid")
        self.assertEqual(client_cyd.profile.display_type, DisplayType.CYD)
        self.assertEqual(client_cyd.profile.width, 320)
        self.assertEqual(client_cyd.profile.height, 240)
        
        client_7 = create_virtual_client(7.0, tier="paid")
        self.assertEqual(client_7.profile.inches, 7.0)
        self.assertEqual(client_7.profile.display_type, DisplayType.LCD)
        self.assertIn("24-bit", client_7.profile.color_mode)
        
        # Dynamic/interpolated size
        client_dyn = create_virtual_client(4.5, tier="paid")
        self.assertGreaterEqual(client_dyn.profile.width, 400)
        
        # Cleanup to reset counters
        client_15.cleanup()
        client_cyd.cleanup()
        client_7.cleanup()
        client_dyn.cleanup()
        
        # Edge case: invalid size (use paid tier to test size validation specifically)
        with self.assertRaises(ValueError):
            create_virtual_client(0.5, tier="paid")
        with self.assertRaises(ValueError):
            create_virtual_client(12.0, tier="paid")

    def test_configuration_testing(self):
        """Test config loading, validation, and hot-reload."""
        custom_config = {
            "theme": "dark",
            "resolution": "400x300",
            "widgets": ["weather", "calendar"],
            "orientation": "landscape"
        }
        client = create_virtual_client(2.8, config=custom_config, tier="free")
        
        info = client.get_display_info()
        self.assertEqual(info["resolution"], "400x300")  # Config override
        self.assertEqual(client.config["theme"], "dark")
        self.assertIn("calendar", client.config["widgets"])
        
        # Hot update
        self.assertTrue(client.update_config({"update_interval": 60, "new_flag": True}))
        self.assertEqual(client.config["update_interval"], 60)
        self.assertTrue(client.config["new_flag"])
    
    def test_dummy_vs_real_data_modes(self):
        """Test dummy data consistency vs real data variability."""
        # Dummy mode - deterministic
        client_dummy = create_virtual_client(2.8, data_mode="dummy", tier="free")
        data1 = client_dummy.fetch_data()
        data2 = client_dummy.fetch_data()
        self.assertEqual(data1["weather"]["temp"], 72)
        self.assertEqual(data1["notifications"][0]["title"], "Test Alert")
        self.assertEqual(len(data1), len(data2))  # Consistent structure
        
        # Real mode - variable + latency simulation
        client_real = create_virtual_client(2.8, data_mode="real", tier="paid")
        start = time.time()
        data_real = client_real.fetch_data()
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.04)  # Simulated latency
        self.assertIn("Live Update", [n["title"] for n in data_real["notifications"]])
        self.assertNotEqual(data_real["weather"]["temp"], 72)  # Variability likely
    
    def test_monetization_edge_cases(self):
        """Test free tier (1 instance) vs paid tier."""
        # Free tier - first instance OK
        client1 = create_virtual_client(2.8, tier="free")
        self.assertEqual(client1.tier, Tier.FREE)
        
        # Second free tier should fail
        with self.assertRaises(RuntimeError) as cm:
            create_virtual_client(4.0, tier="free")
        self.assertIn("Free tier limited to 1 active instance", str(cm.exception))
        
        # Paid tier allows multiple
        client_paid1 = create_virtual_client(2.8, tier="paid")
        client_paid2 = create_virtual_client(7.0, tier="paid")
        self.assertEqual(client_paid1.tier, Tier.PAID)
        self.assertEqual(client_paid2.tier, Tier.PAID)
        
        # Invalid tier
        with self.assertRaises(ValueError):
            create_virtual_client(tier="enterprise")
        
        # Cleanup decrements count
        client1.cleanup()
        # Now free tier should allow new one
        client_free2 = create_virtual_client(1.5, tier="free")
        self.assertIsNotNone(client_free2)
        client_free2.cleanup()
        client_paid1.cleanup()
        client_paid2.cleanup()
    
    def test_rendering_simulation(self):
        """Test rendering for different sizes and modes."""
        client_small = create_virtual_client(1.5, data_mode="dummy")
        render_small = client_small.render()
        self.assertIn("1.5\" ePaper", render_small)
        self.assertIn("Compact ePaper layout", render_small)
        self.assertIn("Weather: 72°F", render_small)
        
        client_large = create_virtual_client(7.0, data_mode="real", tier="paid")
        render_large = client_large.render()
        self.assertIn("7.0\" LCD", render_large)
        self.assertIn("Rich layout with images", render_large)
        
        # Verify framebuffer
        self.assertIsNotNone(client_small.framebuffer)
        self.assertIn("VIRTUAL SCREEN", render_large)
    
    def test_interaction_and_events(self):
        """Test simulated inputs."""
        client = create_virtual_client(4.0, tier="paid")
        result = client.simulate_input("button_press", {"button": "next"})
        self.assertIn("next", result)
        self.assertIn("4.0", result)
        
        touch_result = client.simulate_input("touch", {"x": 100, "y": 150})
        self.assertIn("Touch at (100, 150)", touch_result)
    
    def test_cyd_poc_specific(self):
        """Specific tests for CYD 2.8\" used in Sprint 1 POC."""
        cyd_client = create_virtual_client(2.8, tier="free", data_mode="dummy")
        info = cyd_client.get_display_info()
        self.assertEqual(info["display_type"], "CYD")
        self.assertEqual(info["resolution"], "320x240")
        self.assertEqual(info["dpi"], 120)
        
        render = cyd_client.render()
        self.assertIn("CYD", render)
        # Should work with free tier as first instance
        cyd_client.cleanup()
    
    def test_error_handling(self):
        """Test various edge cases and errors."""
        # Invalid data mode
        with self.assertRaises(ValueError):
            create_virtual_client(data_mode="invalid")
        
        # Config with bad resolution
        client = create_virtual_client(config={"resolution": "invalid"}, tier="paid")
        # Should not crash, fallback handled in _apply_config
        self.assertIsNotNone(client.get_display_info())
    
    def test_instance_tracking(self):
        """Verify class-level instance tracking for monetization."""
        VirtualClient._active_instances = {"free": 0, "paid": 0}
        self.assertEqual(VirtualClient._active_instances["free"], 0)
        client = create_virtual_client(tier="paid")
        self.assertEqual(VirtualClient._active_instances["paid"], 1)
        client.cleanup()
        self.assertEqual(VirtualClient._active_instances["paid"], 0)


if __name__ == "__main__":
    unittest.main()
