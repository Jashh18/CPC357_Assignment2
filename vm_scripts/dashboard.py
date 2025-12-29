from flask import Flask, jsonify, render_template_string
import sqlite3

app = Flask(__name__)
DB_FILE = "smart_home.db"

# ========= DATABASE HELPER =========
def fetch_all_readings():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT device_id, room, temperature, humidity,
               air_quality, air_status, light_level,timestamp
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT 50
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# ========= HTML =========
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Home Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            padding: 20px;
        }
        h1 {
            text-align: center;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        th, td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }
        th {
            background: #2c7be5;
            color: white;
        }
        tr:nth-child(even) {
            background: #f9f9f9;
        }
        .status-good {
            color: green;
            font-weight: bold;
        }
        .status-poor {
            color: red;
            font-weight: bold;
        }
        #last-update {
            margin: 10px 0;
            color: #555;
        }
    </style>
</head>
<body>

<h1>Smart Home Sensor Dashboard</h1>
<div id="last-update">Last update: --</div>

<table>
    <thead>
        <tr>
            <th>Time</th>
            <th>Device</th>
            <th>Room</th>
            <th>Temp (°C)</th>
            <th>Humidity (%)</th>
            <th>AQI</th>
            <th>Status</th>
            <th>Light (lux)</th>
        </tr>
    </thead>
    <tbody id="data-body">
        <tr>
            <td colspan="9">Waiting for data...</td>
        </tr>
    </tbody>
</table>

<script>
function loadData() {
    fetch("/api/readings")
        .then(res => res.json())
        .then(data => {
            const body = document.getElementById("data-body");
            body.innerHTML = "";

            if (data.length === 0) {
                body.innerHTML =
                    "<tr><td colspan='9'>No data yet</td></tr>";
                return;
            }

            data.forEach(row => {
                const statusClass =
                    row.air_status === "GOOD"
                        ? "status-good"
                        : "status-poor";

                body.innerHTML += `
                    <tr>
                        <td>${row.timestamp}</td>
                        <td>${row.device_id}</td>
                        <td>${row.room}</td>
                        <td>${row.temperature}</td>
                        <td>${row.humidity}</td>
                        <td>${row.air_quality}</td>
                        <td class="${statusClass}">
                            ${row.air_status}
                        </td>
                        <td>${row.light_level}</td>
                    </tr>
                `;
            });

            document.getElementById("last-update").innerText =
                "Last update: " +
                new Date().toLocaleTimeString();
        })
        .catch(err => console.error(err));
}

loadData();
setInterval(loadData, 15000); // update every 5 seconds
</script>

</body>
</html>
"""

# ========= ROUTES =========
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/readings")
def api_readings():
    return jsonify(fetch_all_readings())

# ========= MAIN =========
if __name__ == "__main__":
    print("Smart Home Dashboard running")
    print("Open: http://YOUR_VM_IP:8081")
    app.run(host="0.0.0.0", port=8081, debug=False)
