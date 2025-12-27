# CPC357: Smart Home IoT Monitoring System

A real-time environmental monitoring system that tracks temperature, humidity, air quality, and light levels using MQTT protocol, deployed on Google Cloud Platform with Flask dashboard visualization.

## System Architecture

- **Simulated IoT Device**: Generates sensor data every 15 seconds
- **MQTT Broker**: Mosquitto for message routing
- **Data Processor**: SQLite storage with alert system
- **Web Dashboard**: Real-time Flask visualization (auto-refresh every 5s)

---

## GCP Deployment

### 1. Configure Firewall Rules

Go to **VPC Network > Firewall** and create two rules:

| Setting | Rule 1 (MQTT) | Rule 2 (Dashboard) |
|---------|---------------|-------------------|
| Name | `allow-mqtt-1883` | `allow-http-8080` |
| Direction | Ingress | Ingress |
| Action | Allow | Allow |
| Targets | All instances | All instances |
| Source ranges | `0.0.0.0/0` | `0.0.0.0/0` |
| Protocols/Ports | TCP: 1883 | TCP: 8080 |

### 2. Create VM Instance

- **Machine Type**: e2-micro
- **Region**: us-central1
- **Boot Disk**: 10GB, Ubuntu 22.04 LTS
- **Firewall**: Allow HTTP/HTTPS traffic

### 3. Setup Commands (GCP SSH)

```bash
# Update system & install dependencies
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients python3-pip git

# Clone repository
git clone https://github.com/Jashh18/CPC357_Assignment2.git
cd CPC357_Assignment2

# Configure MQTT Broker
sudo nano /etc/mosquitto/mosquitto.conf
# Add these lines:
listener 1883
allow_anonymous true

# Start Mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Setup Python environment
cd vm_scripts
pip3 install -r requirements.txt
```

### 4. Run IoT Device (Local Machine)

On your **local computer** (not GCP):

```bash
# Clone the repository
git clone https://github.com/Jashh18/CPC357_Assignment2.git
cd CPC357_Assignment2

# Install dependencies
pip install paho-mqtt

# Edit simulated_device.py
# Open the file and update:
# MQTT_SERVER = "YOUR_VM_EXTERNAL_IP"  # ← Replace with your GCP VM External IP

# Run simulator
python simulated_device.py
```

### 5. Run the System (3 SSH Terminals Required)

**Terminal 1** - Monitor MQTT Messages:
```bash
mosquitto_sub -t "smart-home/#" -v
```

**Terminal 2** - Data Processor:
```bash
cd ~/CPC357_Assignment2/vm_scripts
python3 mqtt_subscriber.py
```

**Terminal 3** - Web Dashboard:
```bash
cd ~/CPC357_Assignment2/vm_scripts
python3 dashboard.py
```

### 6. Access Dashboard

Open browser: `http://YOUR_VM_EXTERNAL_IP:8080`

---

## Group Members

- **Tejashree Laxmi A/P Kanthan** - 163506
- **Kavitashini A/P Seluvarajoo** - 164329