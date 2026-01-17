from flask import Flask, jsonify, render_template, request
import sqlite3
from functools import lru_cache
import time

app = Flask(__name__)
DB_FILE = "smart_home.db"

# Database connection function
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable optimizations
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    return conn


# Get all readings from database
def fetch_all_readings(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()

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


# Get latest reading for each room
def fetch_latest_by_room():
    conn = get_db_connection()
    cursor = conn.cursor()

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


# Cache stats for 30 seconds
@lru_cache(maxsize=1)
def get_room_stats_cached(cache_key):
    conn = get_db_connection()
    cursor = conn.cursor()

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


# Get room stats with caching
def get_room_stats():
    cache_key = int(time.time() / 30)
    return get_room_stats_cached(cache_key)


# Main dashboard page
@app.route("/")
def index():
    return render_template("dashboard.html")


# API endpoint for readings history
@app.route("/api/readings")
def api_readings():
    try:
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 100)
        return jsonify(fetch_all_readings(limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API endpoint for latest reading per room
@app.route("/api/latest")
def api_latest():
    try:
        return jsonify(fetch_latest_by_room())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API endpoint for room statistics
@app.route("/api/stats")
def api_stats():
    try:
        return jsonify(get_room_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Create database indexes for better performance
def create_indexes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Index for latest readings query
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_room_timestamp 
            ON sensor_readings(room, timestamp DESC)
        """)
        
        # Index for timestamp ordering
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


# Run the application
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

    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)