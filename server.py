from flask import Flask, request, jsonify
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

peers = []
peer_ready = {}
simulation_started = threading.Event()
peer_data = {}

# Shared data for the example
energy_data = {
    "balance": 0,
    "currency": 100.0,
    "demand": 0,
    "generation": 0
}

@app.route('/ready', methods=['POST'])
def ready():
    peer_ip = request.remote_addr
    peer_ready[peer_ip] = True
    return jsonify({"status": "ready"})

@app.route('/start', methods=['POST'])
def start():
    global peers
    data = request.json
    peers = data.get('peers', [])

    while not all(peer_ready.get(peer, False) for peer in peers):
        time.sleep(0.1)
    simulation_started.set()
    return jsonify({"status": "Simulation started"})

start_time = None

@app.route('/sync_start', methods=['POST'])
def sync_start():
    global start_time
    data = request.json
    start_time = data.get('start_time')
    if start_time:
        return jsonify({"status": "start time set", "start_time": start_time})
    else:
        return jsonify({"error": "Invalid start time"}), 400

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    return jsonify({"status": "Simulation already running"})

@app.route('/get_data', methods=['GET'])
def get_data():
    global energy_data
    try:
        return jsonify(energy_data)
    except Exception as e:
        logging.error(f"Error getting data: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/update_peer_data', methods=['POST'])
def update_peer_data():
    data = request.json
    peer_ip = request.remote_addr
    if peer_ip not in peer_data:
        peer_data[peer_ip] = {}
    peer_data[peer_ip].update(data)
    return jsonify({"status": "updated"})

@app.route('/get_peer_data', methods=['GET'])
def get_peer_data():
    return jsonify(peer_data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)