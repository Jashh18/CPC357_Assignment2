# This is our dashboard.py for our project

from flask import Flask, jsonify, render_template, request
import sqlite3
from functools import lru_cache
import time

app = Flask(__name__)
DB_FILE = "smart_home.db"

# Connect to our SQLite database
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # So we can access columns by name
    # These optimizations make queries faster
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    return conn

# Get all readings from database (limited to last 50 by default)
def fetch_all_readings(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()

    # This query gets the readings and calculates temp_status
    cursor.execute("""
        SELECT 
            device_id,
            room,
            temperature,
            humidity,
            air_quality,
            air_status,
            light_level,
            timestamp,
            CASE 
                WHEN temperature > 28 THEN 'HIGH'
                WHEN temperature < 18 THEN 'LOW'
                ELSE 'NORMAL'
            END as temp_status
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# Get the latest reading for each room (for the room cards)
def fetch_latest_by_room():
    conn = get_db_connection()
    cursor = conn.cursor()

    # This uses a window function to get only the most recent reading per room
    cursor.execute("""
        WITH ranked_readings AS (
            SELECT 
                device_id,
                room,
                temperature,
                humidity,
                air_quality,
                air_status,
                light_level,
                timestamp,
                CASE 
                    WHEN temperature > 28 THEN 'HIGH'
                    WHEN temperature < 18 THEN 'LOW'
                    ELSE 'NORMAL'
                END as temp_status,
                CASE 
                    WHEN humidity > 60 THEN 'HIGH'
                    WHEN humidity < 30 THEN 'LOW'
                    ELSE 'NORMAL'
                END as humidity_status,
                ROW_NUMBER() OVER (PARTITION BY room ORDER BY timestamp DESC) as rn
            FROM sensor_readings
        )
        SELECT 
            device_id,
            room,
            temperature,
            humidity,
            air_quality,
            air_status,
            light_level,
            timestamp,
            temp_status,
            humidity_status
        FROM ranked_readings
        WHERE rn = 1
        ORDER BY room
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# Cache statistics for 30 seconds to reduce database load
@lru_cache(maxsize=1)
def get_room_stats_cached(cache_key):
    conn = get_db_connection()
    cursor = conn.cursor()

    # This calculates averages and counts for each room
    cursor.execute("""
        SELECT
            room,
            COUNT(*) AS total_readings,
            ROUND(AVG(temperature), 2) AS avg_temp,
            ROUND(AVG(humidity), 2) AS avg_humidity,
            ROUND(AVG(air_quality), 2) AS avg_air_quality,
            SUM(CASE WHEN temperature > 28 OR temperature < 18 THEN 1 ELSE 0 END) AS temp_alerts,
            SUM(CASE WHEN air_status = 'POOR' THEN 1 ELSE 0 END) AS air_alerts
        FROM sensor_readings
        GROUP BY room
        ORDER BY room
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# Get room statistics (uses cache to avoid hitting DB too often)
def get_room_stats():
    # Create a cache key that changes every 30 seconds
    cache_key = int(time.time() / 30)
    return get_room_stats_cached(cache_key)


# Routes - these are the URLs that our browser can access
@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/readings")
def api_readings():
    """API endpoint that returns reading history"""
    try:
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 100)  # Max 100 readings
        return jsonify(fetch_all_readings(limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest")
def api_latest():
    """API endpoint for latest reading from each room"""
    try:
        return jsonify(fetch_latest_by_room())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    """API endpoint for room statistics"""
    try:
        return jsonify(get_room_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Create database indexes to make queries faster
def create_indexes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Index for finding latest readings by room
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_room_timestamp 
            ON sensor_readings(room, timestamp DESC)
        """)
        
        # Index for sorting by timestamp
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON sensor_readings(timestamp DESC)
        """)
        
        conn.commit()
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Index creation warning: {e}")
    finally:
        conn.close()


# Start the Flask server
if __name__ == "__main__":
    print("=" * 60)
    print("Smart Home Dashboard Server Starting...")
    print("=" * 60)
    
    create_indexes()
    
    print("Dashboard URL: http://<VM_EXTERNAL_IP>:8080")
    print("Auto-refresh: Every 15 seconds (critical data)")
    print("Monitoring: Living Room, Kitchen, Bedroom")
    print("Optimizations: Caching, Indexes, Lazy Loading")
    print("=" * 60)

    # Run on all interfaces (0.0.0.0) so we can access from other computers
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)