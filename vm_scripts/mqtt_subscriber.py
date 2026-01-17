# This is our mqtt_subscriber.py for our project

import paho.mqtt.client as mqtt
import json
import sqlite3
from datetime import datetime
import threading
import time

# ========= OUR DATABASE SETUP =========
def setup_database():
    """Create SQLite database with tables"""
    conn = sqlite3.connect('smart_home.db') # Connect to our database file
    cursor = conn.cursor()

    # Create the main table for storing all our sensor readings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            room TEXT,
            temperature REAL,
            humidity REAL,
            air_quality REAL,
            air_status TEXT,
            light_level REAL,
            timestamp DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create a separate table just for alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            alert_type TEXT,
            value REAL,
            threshold REAL,
            message TEXT,
            timestamp DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit() # Save our changes
    conn.close() # Close the connection
    print("Database setup complete")

# ========= OUR ALERT SYSTEM =========
def check_alerts(data):
    """Check for abnormal readings and create alerts"""
    alerts = []

    # Check if the temperature is too high or too low
    if data.get('temperature', 25) > 28:
        alerts.append({
            'type': 'HIGH_TEMPERATURE',
            'value': data['temperature'],
            'threshold': 28,
            'message': f"High temperature detected: {data['temperature']}°C"
        })
    elif data.get('temperature', 25) < 18:
        alerts.append({
            'type': 'LOW_TEMPERATURE',
            'value': data['temperature'],
            'threshold': 18,
            'message': f"Low temperature detected: {data['temperature']}°C"
        })

    # Check if air quality is over 150
    if data.get('air_quality', 0) > 150:
        alerts.append({
            'type': 'POOR_AIR_QUALITY',
            'value': data['air_quality'],
            'threshold': 150,
            'message': f"Poor air quality: AQI {data['air_quality']}"
        })

    return alerts

# ========= OUR MQTT CALLBACKS =========
def on_connect(client, userdata, flags, rc, properties):
    print("Connected to MQTT Broker")
    client.subscribe("smart-home/#") # This line subscribe to everything under smart-home/ since we are using '#' symbol
    print("Subscribed to: smart-home/#")

def on_message(client, userdata, msg):
    try:
        # Convert the JSON message back into a Python dictionary
        data = json.loads(msg.payload.decode())
        print(f"Received [{msg.topic}]: {data}")

        # Connect to our database
        conn = sqlite3.connect('smart_home.db')
        cursor = conn.cursor()

        # Only process messages that have all the sensor data combined
        if 'room' in data:
            # Check for alerts
            alerts = check_alerts(data)
            # If we found any alerts, save them to the alerts table
            for alert in alerts:
                cursor.execute('''
                    INSERT INTO alerts (
                        device_id, alert_type, value, threshold, message, timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['device_id'],
                    alert['type'],
                    alert['value'],
                    alert['threshold'],
                    alert['message'],
                    data['timestamp']
                ))
                print(f"ALERT: {alert['message']}")

            # Save the sensor reading to our main table
            cursor.execute('''
                INSERT INTO sensor_readings (
                    device_id, room, temperature, humidity,
                    air_quality, air_status, light_level, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('device_id'),
                data.get('room'),
                data.get('temperature'),
                data.get('humidity'),
                data.get('air_quality'),
                data.get('air_status'),
                data.get('light_level'),
                data.get('timestamp')
            ))

            conn.commit() # Save everythin to the database
            print("Data saved to database")

        conn.close() # Close the database connection

    except Exception as e:
        print(f"ERROR: Failed to process message: {e}")

# ========= OUR STATISTICS THREAD =========
def print_statistics():
    """Print statistics every 30 seconds"""
    while True:
        time.sleep(30) # Wait 30 seconds
        try:
            # Connect to database to get statistics
            conn = sqlite3.connect('smart_home.db')
            cursor = conn.cursor()

            # Count total number of readings we've stored
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            total_readings = cursor.fetchone()[0]

            # Count total number of alerts we've recorded
            cursor.execute("SELECT COUNT(*) FROM alerts")
            total_alerts = cursor.fetchone()[0]

            # Get latest reading
            cursor.execute('''
                SELECT temperature, humidity, air_quality, air_status
                FROM sensor_readings
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            latest = cursor.fetchone()

            conn.close()

            print("\n" + "=" * 50)
            print("SYSTEM STATISTICS")
            print("=" * 50)
            print(f"Total Readings: {total_readings}")
            print(f"Total Alerts: {total_alerts}")

            if latest:
                print(
                    f"Latest: {latest[0]}°C, {latest[1]}% RH, "
                    f"AQI: {latest[2]} ({latest[3]})"
                )

            print("=" * 50 + "\n")

        except Exception as e:
            print(f"ERROR: Failed to generate statistics: {e}")

# ========= OUR MAIN =========
def main():
    print("Smart Home Data Processor")
    print("=" * 50)

    # Setup database and tables
    setup_database()

    # Start statistics thread
    stats_thread = threading.Thread(
        target=print_statistics,
        daemon=True
    )
    stats_thread.start()

    # Create our MQTT client
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        "data-processor"
    )
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to local MQTT broker
    try:
        client.connect("localhost", 1883, 60)
    except Exception as e:
        print(f"ERROR: Cannot connect to MQTT broker: {e}")
        return

    print("Starting MQTT listener...")
    client.loop_forever()

if __name__ == "__main__":
    main()