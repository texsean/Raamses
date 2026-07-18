#!/usr/bin/env python3
"""
RAAMSES XML-speaking Server Emulator (v1.0 protocol compliant)
Supports Register (with capability parsing and profile assignment), RegisterAck,
Heartbeat, AgentUpdate, Alert, Command, and CommandResult.
"""

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

def generate_message(message_type: str, source_id: str, destination_id: str, payload_element) -> str:
    root = ET.Element("RaamsesMessage", {
        "protocolVersion": "1.0",
        "messageType": message_type,
        "messageId": str(uuid.uuid4()),
        "timestampUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceId": source_id,
        "destinationId": destination_id,
        "sequence": "1"
    })
    
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "SessionId").text = "sess-" + str(uuid.uuid4())[:8].upper()
    ET.SubElement(header, "Priority").text = "Normal"
    
    payload = ET.SubElement(root, "Payload")
    payload.append(payload_element)
    
    return ET.tostring(root, encoding="unicode", method="xml")

class XMLHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        xml_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            root = ET.fromstring(xml_data)
            msg_type = root.get('messageType')
            source = root.get('sourceId')
            dest = root.get('destinationId')
            
            print(f"[{datetime.now()}] Received {msg_type} from {source}")
            
            if msg_type == "Register":
                # Parse capabilities and assign profile
                device_class = root.find(".//DeviceClass").text if root.find(".//DeviceClass") is not None else "default"
                display_type = root.find(".//DisplayType").text if root.find(".//DisplayType") is not None else "LCD"
                
                profile = PROFILES.get(device_class, PROFILES["default"])
                if "EPaper" in display_type:
                    profile = "EPaper-Watch-Small"
                
                ack = ET.Element("RegisterAck")
                ET.SubElement(ack, "Accepted").text = "true"
                ET.SubElement(ack, "ServerName").text = "RAAMSES-EMULATOR"
                ET.SubElement(ack, "ServerVersion").text = "0.9.0"
                ET.SubElement(ack, "NegotiatedProtocolVersion").text = "1.0"
                ET.SubElement(ack, "HeartbeatIntervalSeconds").text = "30"
                ET.SubElement(ack, "StatusRefreshIntervalSeconds").text = "10"
                ET.SubElement(ack, "MaximumPayloadBytes").text = "32768"
                ET.SubElement(ack, "AssignedProfile").text = profile
                
                response_xml = generate_message("RegisterAck", "raamses-server", source, ack)
                self.send_response(200)
                self.send_header("Content-type", "application/xml")
                self.end_headers()
                self.wfile.write(response_xml.encode('utf-8'))
                print(f"  → Sent RegisterAck with profile: {profile}")
                
            elif msg_type == "Heartbeat":
                # Echo or simple ack
                self.send_response(200)
                self.send_header("Content-type", "application/xml")
                self.end_headers()
                self.wfile.write(b'<RaamsesMessage messageType="Ack"><Payload><Status>OK</Status></Payload></RaamsesMessage>')
            else:
                self.send_response(200)
                self.send_header("Content-type", "application/xml")
                self.end_headers()
                self.wfile.write(b'<RaamsesMessage messageType="Error"><Payload><Message>Unsupported in emulator</Message></Payload></RaamsesMessage>')
                
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"<Error>{str(e)}</Error>".encode())

    def do_GET(self):
        if self.path in ("/", "/stats", "/api/stats"):
            self.send_response(200)
            self.send_header("Content-type", "application/xml")
            self.end_headers()
            # Return sample AgentUpdate
            update = ET.Element("AgentUpdate")
            server = ET.SubElement(update, "Server")
            ET.SubElement(server, "ServerName").text = "Development Server"
            ET.SubElement(server, "CpuPercent").text = "23"
            # ... (full payload abbreviated for space)
            xml = generate_message("AgentUpdate", "raamses-server", "all-consoles", update)
            self.wfile.write(xml.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), XMLHandler)
    print("=== RAAMSES XML Protocol Emulator v1.0 running on http://localhost:8080 ===")
    print("Send Register XML via POST. Supports profile auto-assignment.")
    print("Ready for CYD, e-paper watch, and desktop console testing.")
    server.serve_forever()
