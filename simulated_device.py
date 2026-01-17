# This is the simulated_device.py for our project

import time
import random
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import threading

# ========= OUR CONFIGURATION PART =========
MQTT_SERVER = "35.188.199.125"  # Do replace this with the new External VM IP everytime starting the VM
MQTT_PORT = 1883

# We're defining multiple rooms with their device IDs
# They also have different ranges because they behave differently in real life
ROOMS = {
    "living_room": {
        "device_id": "smart-home-sensor-01",
        "temp_range": (18.0, 26.0),  # Living room usually have moderate temp
        "humidity_range": (40.0, 60.0),
    },
    "kitchen": {
        "device_id": "smart-home-sensor-02",
        "temp_range": (20.0, 30.0),  # Kitchen warmer due to cooking
        "humidity_range": (45.0, 70.0),  # Higher humidity from cooking
    },
    "bedroom": {
        "device_id": "smart-home-sensor-03",
        "temp_range": (16.0, 24.0),  # Bedroom cooler for sleep
        "humidity_range": (40.0, 55.0),
    }
}

# ========= THE ALERT THRESHOLDS =========
TEMP_HIGH_THRESHOLD = 28.0  # °C
TEMP_LOW_THRESHOLD = 18.0   # °C
AIR_QUALITY_THRESHOLD = 150.0  # AQI

# ========= OUR SENSOR SIMULATION =========
def generate_sensor_data(room_name, room_config):
    """Generate realistic sensor readings with alert status for a specific room"""
    
    # Generating a random temp within the room's typical range
    temp_min, temp_max = room_config["temp_range"]
    temperature = round(random.uniform(temp_min, temp_max), 1)
    
    # Check if the temperature is too high, too low, or normal
    if temperature > TEMP_HIGH_THRESHOLD:
        temp_status = "HIGH"
    elif temperature < TEMP_LOW_THRESHOLD:
        temp_status = "LOW"
    else:
        temp_status = "NORMAL"
    
    # Generating a random humidity but within the room's range
    humid_min, humid_max = room_config["humidity_range"]
    humidity = round(random.uniform(humid_min, humid_max), 1)
    humidity_status = "NORMAL" 
    
    # Air Quality: 0-500 (AQI scale)
    # Kitchen has higher chance of poor air quality due to cooking fumes
    poor_air_chance = 0.3 if room_name == "kitchen" else 0.15
    
    # Randomly decide if air quality is good or poor based on the room
    if random.random() > (1 - poor_air_chance):
        air_quality = round(random.uniform(150.0, 500.0), 1)
        air_status = "POOR"
    else:
        air_quality = round(random.uniform(0.0, 150.0), 1)
        air_status = "GOOD"
    
    # Light: 0-1000 lux, we check what time of day it is to make it realistic
    hour = datetime.now().hour
    
    if room_name == "bedroom":
        # Bedroom: dark even during day, very dark at night
        if 6 <= hour <= 18:
            light_level = round(random.uniform(100.0, 400.0), 1)
        else:
            light_level = round(random.uniform(0.0, 50.0), 1)
    elif room_name == "kitchen":
        # Kitchen: bright during cooking hours
        if 7 <= hour <= 9 or 12 <= hour <= 13 or 18 <= hour <= 20:
            light_level = round(random.uniform(500.0, 1000.0), 1)
        elif 6 <= hour <= 22:
            light_level = round(random.uniform(200.0, 600.0), 1)
        else:
            light_level = round(random.uniform(0.0, 100.0), 1)
    else:  # will be living_room
        # Living room: follows normal daylight pattern
        if 6 <= hour <= 18:
            light_level = round(random.uniform(300.0, 1000.0), 1)
        else:
            light_level = round(random.uniform(50.0, 200.0), 1)
    
    light_status = "NORMAL" 
    
    return {
        "device_id": room_config["device_id"],
        "room": room_name,
        "temperature": temperature,
        "temp_status": temp_status,
        "humidity": humidity,
        "humidity_status": humidity_status,
        "air_quality": air_quality,
        "air_status": air_status,
        "light_level": light_level,
        "light_status": light_status,
        "timestamp": datetime.now().isoformat(),
    }

# ========= OUR ROOM SIMULATOR CLASS =========
class RoomSimulator:
    # Initialize the room with its name, config, and the MQTT client
    def __init__(self, room_name, room_config, mqtt_client):
        self.room_name = room_name
        self.room_config = room_config
        self.client = mqtt_client
        self.message_count = 0
        self.running = False
        
        # Setting up MQTT topics for this room
        self.topics = {
            "temp": f"smart-home/{room_name}/temperature",
            "humid": f"smart-home/{room_name}/humidity",
            "air": f"smart-home/{room_name}/air_quality",
            "light": f"smart-home/{room_name}/light",
            "all": f"smart-home/{room_name}/all"
        }
    
    def publish_data(self):
        """Generate and publish sensor data for this room"""
        # Getting the fake sensor data
        data = generate_sensor_data(self.room_name, self.room_config)
        
        # Send individual sensor data to their specific topics
        self.client.publish(self.topics["temp"], json.dumps({
            "temperature": data["temperature"],
            "status": data["temp_status"]
        }))
        self.client.publish(self.topics["humid"], json.dumps({
            "humidity": data["humidity"],
            "status": data["humidity_status"]
        }))
        self.client.publish(self.topics["air"], json.dumps({
            "air_quality": data["air_quality"],
            "status": data["air_status"]
        }))
        self.client.publish(self.topics["light"], json.dumps({
            "light": data["light_level"],
            "status": data["light_status"]
        }))
        
        # Combining the datas and send to one topic
        self.client.publish(self.topics["all"], json.dumps(data))
        
        # Displaying the status
        temp_indicator = "[HIGH]" if data["temp_status"] == "HIGH" else "[LOW]" if data["temp_status"] == "LOW" else "[OK]"
        air_indicator = "[WARN]" if data["air_status"] == "POOR" else "[OK]"
        
        print(f"[{self.room_name.upper():12}] "
              f"[{self.message_count:03d}] "
              f"Temp: {temp_indicator} {data['temperature']}°C, "
              f"Humidity: {data['humidity']}%, "
              f"AQI: {air_indicator} {data['air_quality']:5}, "
              f"Light: {data['light_level']:5} lux")
        
        self.message_count += 1 # Increment our message counter
    
    def start(self):
        """Start publishing data every 15 seconds"""
        self.running = True
        while self.running:
            self.publish_data() # Sends the data
            time.sleep(15) # Wait for 15 seconds before sending again
    
    def stop(self):
        """Stop publishing data"""
        self.running = False

# ========= MQTT SETUP =========
def create_mqtt_client():
    """Create and configure MQTT client"""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "smart-home-hub")
    
    # This function runs when we successfully connect to the MQTT broker
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0: # rc=0 means the connection successful
            print("Connected to MQTT Broker!")
            print(f"Simulating {len(ROOMS)} rooms: {', '.join(ROOMS.keys())}")
            print("="*80)
        else:
            print(f"Connection failed with code: {rc}")
    
    client.on_connect = on_connect
    return client

# ========= OUR MAIN =========
def main():
    print("Multi-Room Smart Home IoT Device Simulator")
    print("="*80)
    
    # Create our MQTT client
    client = create_mqtt_client()
    
    # Connect to the MQTT
    try:
        client.connect(MQTT_SERVER, MQTT_PORT, 60)
    except Exception as e:
        print(f"ERROR: Cannot connect to {MQTT_SERVER}:{MQTT_PORT}")
        print(f"Error: {e}")
        return
    
    client.loop_start()
    time.sleep(2)  # Wait for connection to establish
    
    # Create room simulators
    simulators = []
    threads = []
    
    for room_name, room_config in ROOMS.items():
        simulator = RoomSimulator(room_name, room_config, client)
        simulators.append(simulator)
    
    print("\nSending sensor data from all rooms every 15 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Start all room simulators in separate threads
        for simulator in simulators:
            thread = threading.Thread(target=simulator.start, daemon=True)
            thread.start()
            threads.append(thread)
            time.sleep(0.5)  # Wait a bit between starting each room
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping all room simulators...") # When we run Ctrl+C
        
        # Stop all simulators
        for simulator in simulators:
            simulator.stop()
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=2)
        
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT broker")

if __name__ == "__main__":
    main()