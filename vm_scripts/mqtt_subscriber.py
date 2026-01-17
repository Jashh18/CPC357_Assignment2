import paho.mqtt.client as mqtt
import json
import sqlite3
from datetime import datetime
import threading
import time

# ========= DATABASE SETUP =========
def setup_database():
    """Create SQLite database with tables"""
    conn = sqlite3.connect('smart_home.db')
    cursor = conn.cursor()

    # Main readings table
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

    # Alerts table (for abnormal readings)
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

    conn.commit()
    conn.close()
    print("Database setup complete")

# ========= ALERT SYSTEM =========
def check_alerts(data):
    """Check for abnormal readings and create alerts"""
    alerts = []

    # Temperature alerts
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

    # Air quality alerts
    if data.get('air_quality', 0) > 150:
        alerts.append({
            'type': 'POOR_AIR_QUALITY',
            'value': data['air_quality'],
            'threshold': 150,
            'message': f"Poor air quality: AQI {data['air_quality']}"
        })

    return alerts

# ========= MQTT CALLBACKS =========
def on_connect(client, userdata, flags, rc, properties):
    print("Connected to MQTT Broker")
    # Subscribe to all smart home topics
    client.subscribe("smart-home/#")
    print("Subscribed to: smart-home/#")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"Received [{msg.topic}]: {data}")

        # Store in database
        conn = sqlite3.connect('smart_home.db')
        cursor = conn.cursor()

        # If it's combined data (from TOPIC_ALL)
        if 'room' in data:
            # Check for alerts
            alerts = check_alerts(data)
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

            # Insert into readings
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

            conn.commit()
            print("Data saved to database")

        conn.close()

    except Exception as e:
        print(f"ERROR: Failed to process message: {e}")

# ========= STATISTICS THREAD =========
def print_statistics():
    """Print statistics every 30 seconds"""
    while True:
        time.sleep(30)
        try:
            conn = sqlite3.connect('smart_home.db')
            cursor = conn.cursor()

            # Get counts
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            total_readings = cursor.fetchone()[0]

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

# ========= MAIN =========
def main():
    print("Smart Home Data Processor")
    print("=" * 50)

    # Setup database
    setup_database()

    # Start statistics thread
    stats_thread = threading.Thread(
        target=print_statistics,
        daemon=True
    )
    stats_thread.start()

    # Create MQTT client
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