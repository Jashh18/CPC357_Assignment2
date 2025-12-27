import time
import random
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# ========= CONFIGURATION =========
MQTT_SERVER = "136.116.214.222"  # ← REPLACE WITH YOUR VM IP
MQTT_PORT = 1883
DEVICE_ID = "smart-home-sensor-01"
ROOM = "living_room"

# MQTT Topics
TOPIC_TEMP = f"smart-home/{ROOM}/temperature"
TOPIC_HUMID = f"smart-home/{ROOM}/humidity"
TOPIC_AIR = f"smart-home/{ROOM}/air_quality"
TOPIC_LIGHT = f"smart-home/{ROOM}/light"
TOPIC_ALL = f"smart-home/{ROOM}/all"

# ========= MQTT SETUP =========
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, DEVICE_ID)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ Connected to MQTT Broker!")
        print(f"📡 Device ID: {DEVICE_ID}")
        print(f"🏠 Room: {ROOM}")
        print("="*50)
    else:
        print(f"❌ Connection failed with code: {rc}")

client.on_connect = on_connect

# ========= SENSOR SIMULATION =========
def generate_sensor_data():
    """Generate realistic sensor readings"""
    # Temperature: 18-30°C (normal home range)
    temperature = round(random.uniform(18.0, 30.0), 1)
    
    # Humidity: 40-70% (comfortable range)
    humidity = round(random.uniform(40.0, 70.0), 1)
    
    # Air Quality: 0-500 (AQI scale, 0-50 good, 300+ hazardous)
    # Simulate occasional "poor" air quality
    if random.random() > 0.8:  # 20% chance of poor air
        air_quality = round(random.uniform(150.0, 300.0), 1)
        air_status = "POOR"
    else:
        air_quality = round(random.uniform(0.0, 100.0), 1)
        air_status = "GOOD"
    
    # Light: 0-1000 lux (0 dark, 1000 bright room)
    hour = datetime.now().hour
    if 6 <= hour <= 18:  # Daytime
        light_level = round(random.uniform(300.0, 1000.0), 1)
    else:  # Nighttime
        light_level = round(random.uniform(0.0, 100.0), 1)
    
    return {
        "device_id": DEVICE_ID,
        "room": ROOM,
        "temperature": temperature,
        "humidity": humidity,
        "air_quality": air_quality,
        "air_status": air_status,
        "light_level": light_level,
        "timestamp": datetime.now().isoformat(),
        "battery": round(random.uniform(85.0, 100.0), 1)  # Simulate battery
    }

# ========= MAIN =========
def main():
    print("🚀 Smart Home IoT Device Simulator")
    print("="*50)
    
    # Connect to MQTT
    try:
        client.connect(MQTT_SERVER, MQTT_PORT, 60)
    except Exception as e:
        print(f"❌ Cannot connect to {MQTT_SERVER}:{MQTT_PORT}")
        print(f"Error: {e}")
        return
    
    client.loop_start()
    
    message_count = 0
    print("\n📤 Sending sensor data every 15 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            data = generate_sensor_data()
            
            # Send individual sensor data
            client.publish(TOPIC_TEMP, json.dumps({"temperature": data["temperature"]}))
            client.publish(TOPIC_HUMID, json.dumps({"humidity": data["humidity"]}))
            client.publish(TOPIC_AIR, json.dumps({
                "air_quality": data["air_quality"],
                "status": data["air_status"]
            }))
            client.publish(TOPIC_LIGHT, json.dumps({"light": data["light_level"]}))
            
            # Send combined data
            client.publish(TOPIC_ALL, json.dumps(data))
            
            # Display
            print(f"[{message_count:03d}] 📦 Sent: {data['temperature']}°C, "
                  f"{data['humidity']}% RH, AQI: {data['air_quality']} ({data['air_status']}), "
                  f"Light: {data['light_level']} lux")
            
            message_count += 1
            time.sleep(15)  # Send every 15 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping device simulator...")
        client.loop_stop()
        client.disconnect()
        print("✅ Disconnected from MQTT broker")

if __name__ == "__main__":
    main()