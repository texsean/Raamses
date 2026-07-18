#!/bin/bash
echo "=== RAAMSES Pi 5 Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv curl

# Create project directory on the 1TB SSD (assuming it's mounted at /mnt/ssd or /home/pi/ssd)
mkdir -p ~/Raamses
cd ~/Raamses

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install flask requests psutil

# Copy the stats server (you can paste the code below or copy from laptop)
cat > stats_server.py << 'EOF'
import json
import time
import threading
import random
import psutil
from flask import Flask, jsonify

app = Flask(__name__)

stats = {
    "device": "Ramses Pi 5 Server",
    "agents": 5,
    "subagents": 12,
    "tokens_used": 18420,
    "tokens_limit": 25000,
    "tokens_last_hour": 3240,
    "tokens_today": 8740,
    "sprint_status": "Sprint 4 of 7 - Final Review",
    "last_alert": "Server 2 requesting permission (2 min ago)",
    "overall_status": "green",
    "cpu_usage": "23%",
    "memory_usage": "41%",
    "disk_usage": "67%",
    "uptime": "12 days",
    "summary": {"agents": 5, "tokens": "18.4k/25k", "status": "green"},
    "fulldata": {
        "agents": 5,
        "subagents": 12,
        "tokens_used": 18420,
        "tokens_today": 8740,
        "tokens_last_hour": 3240,
        "sprint": "Sprint 4 of 7",
        "last_alert": "Server 2 requesting permission (2 min ago)",
        "cpu": "23%",
        "memory": "41%",
        "disk": "67%"
    }
}

def update_stats():
    while True:
        stats["cpu_usage"] = str(psutil.cpu_percent()) + "%"
        stats["memory_usage"] = str(psutil.virtual_memory().percent) + "%"
        stats["disk_usage"] = str(psutil.disk_usage('/').percent) + "%"
        stats["agents"] = random.randint(3, 8)
        stats["subagents"] = random.randint(5, 15)
        stats["tokens_used"] = min(24900, stats["tokens_used"] + random.randint(100, 600))
        time.sleep(8)

@app.route('/stats')
def get_stats():
    stats["timestamp"] = time.strftime("%H:%M:%S")
    return jsonify(stats)

if __name__ == '__main__':
    threading.Thread(target=update_stats, daemon=True).start()
    print("RAAMSES Server running on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080)
EOF

echo "RAAMSES server code created."
echo "Run with: source venv/bin/activate && python stats_server.py"
echo "Your Pi 5 IP is likely 192.168.7.x - run 'hostname -I' to confirm."
echo "Update the CYD code with this IP and flash it."
echo "The server will serve real system stats (CPU, memory, disk) + mock agent data."
echo "RAAMSES Pi 5 setup complete."
