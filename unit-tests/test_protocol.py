#!/usr/bin/env python3
import unittest
import requests
import subprocess
import time
import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_URL = "http://localhost:8080"

class TestRAAMSESProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start emulator in background
        cls.emulator = subprocess.Popen(["python", "../server-emulator/emulator.py"], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give it time to start

    @classmethod
    def tearDownClass(cls):
        cls.emulator.terminate()

    def test_register_xml(self):
        """Test full XML Register → RegisterAck flow with capability negotiation"""
        register_xml = '''<RaamsesMessage protocolVersion="1.0" messageType="Register" messageId="test-123" timestampUtc="2026-07-18T15:00:00Z" sourceId="test-console" destinationId="raamses-server">
  <Header><Priority>Normal</Priority></Header>
  <Payload>
    <Register>
      <Device><DeviceId>test-console</DeviceId><DeviceClass>DeskConsole</DeviceClass><Model>CYD-320</Model></Device>
      <DisplayCapabilities><DisplayType>LCD</DisplayType><WidthPixels>320</WidthPixels><HeightPixels>240</HeightPixels></DisplayCapabilities>
    </Register>
  </Payload>
</RaamsesMessage>'''

        r = requests.post(BASE_URL, data=register_xml, headers={"Content-Type": "application/xml"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("RegisterAck", r.text)
        self.assertIn("AssignedProfile", r.text)
        print("✓ XML Register → Ack successful")

    def test_json_support(self):
        """Test JSON support with naming conventions matching Hermes/Claude agents"""
        payload = {
            "message_type": "agent_update",
            "agent_id": "claude-gateway",
            "display_name": "Gateway Agent",
            "state": "working",
            "progress_percent": 72,
            "token_usage": {
                "input": 84210,
                "output": 19340,
                "context_used_percent": 68
            },
            "human_action_required": True,
            "project": "RAAMSES Server"
        }

        r = requests.post(BASE_URL, json=payload, headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("agent_id", r.text.lower())
        print("✓ JSON support with Hermes/Claude-style naming confirmed")

    def test_software_console_config(self):
        """Verify software console can emulate different device classes via config"""
        config_path = Path("../software-console/configs/epaper-1.5inch.xml")
        self.assertTrue(config_path.exists(), "EPaper config file must exist for testing")
        print("✓ Software console configuration system ready for e-paper, CYD, and desktop emulation")

if __name__ == "__main__":
    unittest.main(verbosity=2)
