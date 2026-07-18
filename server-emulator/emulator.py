#!/usr/bin/env python3
"""
RAAMSES Dual XML + JSON Emulator (v1.0)
Uses naming conventions that match Hermes/Claude-style agents for maximum compatibility
and pass-through ease (agent_id, human_action_required, token_usage, progress_percent, etc.).
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid

PROFILES = {
    "DeskConsole": "CYD-Landscape-LargeText",
    "WearableConsole": "EPaper-Watch-Small",
    "DevelopmentConsole": "Desktop-Full",
    "default": "Generic-Summary"
}

class Handler(BaseHTTPRequestHandler):
    def _send_response(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        raw_data = self.rfile.read(content_length)
        content_type = self.headers.get('Content-Type', '')

        try:
            if 'application/json' in content_type:
                data = json.loads(raw_data.decode('utf-8'))
                msg_type = data.get('message_type', 'unknown')
                source = data.get('source_id', 'test-console')
                print(f"[JSON] Received {msg_type} from {source}")

                if msg_type in ("agent_update", "register"):
                    response = {
                        "message_type": "register_ack" if msg_type == "register" else "agent_update_ack",
                        "session_id": f"sess-{uuid.uuid4().hex[:8].upper()}",
                        "assigned_profile": PROFILES.get(data.get("device_class", "default"), "Generic-Summary"),
                        "accepted": True,
                        "server_name": "RAAMSES-EMULATOR",
                        "status": "ok"
                    }
                    self._send_response(200, "application/json", json.dumps(response, indent=2))
                    return

            else:  # XML
                root = ET.fromstring(raw_data.decode('utf-8'))
                msg_type = root.get('messageType', 'unknown')
                source = root.get('sourceId', 'test-console')
                print(f"[XML] Received {msg_type} from {source}")

                if msg_type == "Register":
                    device_class = root.find(".//DeviceClass")
                    device_class = device_class.text if device_class is not None else "default"
                    profile = PROFILES.get(device_class, PROFILES["default"])

                    ack = ET.Element("RegisterAck")
                    ET.SubElement(ack, "Accepted").text = "true"
                    ET.SubElement(ack, "SessionId").text = f"sess-{uuid.uuid4().hex[:8].upper()}"
                    ET.SubElement(ack, "AssignedProfile").text = profile
                    ET.SubElement(ack, "ServerName").text = "RAAMSES-EMULATOR"

                    response_xml = ET.tostring(ET.Element("RaamsesMessage", {
                        "protocolVersion": "1.0",
                        "messageType": "RegisterAck",
                        "messageId": str(uuid.uuid4()),
                        "timestampUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "sourceId": "raamses-server",
                        "destinationId": source
                    }), encoding="unicode")
                    self._send_response(200, "application/xml", response_xml)
                    return

            self._send_response(200, "application/json", json.dumps({"status": "ok", "message": "received"}))
        except Exception as e:
            self._send_response(400, "application/json", json.dumps({"error": str(e)}))

    def do_GET(self):
        self._send_response(200, "application/json", json.dumps({
            "message_type": "agent_update",
            "agent_id": "claude-gateway",
            "state": "working",
            "progress_percent": 72,
            "token_usage": {"input": 84210, "output": 19340},
            "human_action_required": False
        }, indent=2))

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    print("RAAMSES Dual XML+JSON Emulator running on http://127.0.0.1:8080")
    print("Supports Hermes/Claude-style naming conventions for easy integration.")
    server.serve_forever()
